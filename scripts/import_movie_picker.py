"""Перенос из Movie Picker: оценённые фильмы со своей оценкой.

Старая база опознаёт кино по Кинопоиску, новая — по TMDB, и мост между ними
один: `imdb_id`. По нему TMDB отдаёт свою карточку, а дальше работает обычный
загрузчик — тот же, что заводит карточку из поиска, с жанрами, составом и
обложкой.

Переносятся только оценённые фильмы: ни сериалов, ни закладок в переносе нет
вовсе — решение пользователя 04.08.2026. Оценки агрегаторов и теги не
переносятся тоже: первые приедут сами и свежими, вторые в новой базе заводит
только человек.

Перенос мягкий: карточку, у которой в новой базе уже стоит своя оценка, он не
трогает — ни балла, ни времени. Старая шкала десятибалльная, и оценка приводится
к настроенной тем же правилом, каким приложение переводит свою библиотеку.

    pipenv run python scripts/import_movie_picker.py [путь к movie_picker.db]
"""

import asyncio
import logging
import os
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app import build_backend  # noqa: E402
from backend.config import load_config  # noqa: E402
from backend.model import CardView, Kind, Source  # noqa: E402
from backend.sources.http import SourceHttp  # noqa: E402
from backend.sources.tmdb.client import BASE, LANGUAGE  # noqa: E402
from backend.sources.tmdb.parse import POSTER_BASE  # noqa: E402
from backend.storage.rescale import rescaled  # noqa: E402

OLD_DB = Path(r"E:\Files\Archive\Old Projects\Movie Picker\movie_picker"
              r"\movie_picker.db")

# Сколько карточек грузится разом. Каждая — это запрос идентичности, детальный
# ответ и обложка; пятёрка держит сеть занятой, не превращая перенос в наплыв.
AT_ONCE = 5

# Строка без `imdb_id` непереносима вовсе: мост между базами только он.
QUERY = (
    "SELECT m.imdb_id, m.title, r.updated_at, r.rating "
    "FROM user_ratings r JOIN movies m ON m.id = r.movie_id "
    "WHERE NOT m.is_tv "
    "AND m.imdb_id IS NOT NULL AND TRIM(m.imdb_id) <> ''"
)

# Исходы переноса одной строки. Пропуск отделён от неудачи: он работа по
# правилу, а сложенные вместе они прятали бы друг друга в итоговом счёте.
WRITTEN, SKIPPED, FAILED = "перенесено", "пропущено", "не вышло"

logger = logging.getLogger("import")


@dataclass(frozen=True, slots=True)
class Entry:
    """Строка старой базы: чем её опознать и что перенести."""

    imdb_id: str
    title: str
    when: datetime
    score: float


def old_entries(path: Path) -> list[Entry]:
    """Оценённые фильмы старой базы. Открывается она только на чтение: в
    переносе чужая база не участвует ничем, кроме ответов."""
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute(QUERY).fetchall()
    finally:
        connection.close()

    return [Entry(imdb_id, title, datetime.fromisoformat(when), float(score))
            for imdb_id, title, when, score in rows]


async def identity(http: SourceHttp, key: str, entry: Entry) -> CardView | None:
    """Кандидат для загрузчика — тот же тип, что приезжает из выдачи поиска.

    Ответ разбирается здесь, а не в клиенте источника: ручка `/find` нужна
    одному этому переносу, и в боевом клиенте она осталась бы мёртвой."""
    response = await http.get(f"{BASE}/find/{entry.imdb_id}",
                              params={"api_key": key, "language": LANGUAGE,
                                      "external_source": "imdb_id"})
    if not isinstance(response, httpx.Response) or response.status_code != 200:
        return None

    found = response.json().get("movie_results") or []
    if not found:
        return None

    row = found[0]
    poster = row.get("poster_path")
    return CardView(
        kind=Kind.MOVIE,
        source=Source.TMDB,
        source_id=str(row["id"]),
        title=row.get("title") or entry.title,
        poster_url=f"{POSTER_BASE}{poster}" if poster else "",
    )


async def imported(back, http: SourceHttp, key: str, entry: Entry) -> str:
    """Одна строка целиком: идентичность, загрузка карточки, оценка.

    Час берётся старый: по нему в новой базе сортируют, и проставленный
    временем переноса он схлопнул бы всю библиотеку в одну минуту."""
    candidate = await identity(http, key, entry)
    if candidate is None:
        logger.warning("не нашёлся у TMDB: %s (%s)", entry.title, entry.imdb_id)
        return FAILED

    item_id = await back.loader.ensure(candidate)
    if not isinstance(item_id, int):
        logger.warning("не загрузился: %s — %s", entry.title, item_id)
        return FAILED

    # Своя оценка спрашивается после загрузки, а не до: карточку в новой базе
    # опознаёт номер TMDB, а он приезжает только с разбором идентичности.
    # Пустой балл при живой строке — обычное дело: её заводит и рецензия.
    mine = await back.ratings.get(item_id)
    if mine is not None and mine.score is not None:
        logger.info("уже оценён, не трогаю: %s", entry.title)
        return SKIPPED

    score = rescaled(entry.score, back.scale)
    await back.ratings.set_score(item_id, score, entry.when)
    logger.info("перенесено: %s — %s", entry.title, score)
    return WRITTEN


async def transfer(back, http: SourceHttp, key: str,
                   entries: list[Entry]) -> Counter:
    """Все строки, по несколько разом."""
    turn = asyncio.Semaphore(AT_ONCE)

    async def one(entry: Entry) -> str:
        async with turn:
            return await imported(back, http, key, entry)

    return Counter(await asyncio.gather(*(one(entry) for entry in entries)))


def settings():
    """Настройки приложения: корневой `.env` побеждает, рабочий лежит в папке
    данных — тот же порядок, что у `main.py`."""
    load_dotenv()
    load_dotenv(load_config(os.environ, ROOT).data_dir / ".env")
    return load_config(os.environ, ROOT)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = settings()
    old = Path(sys.argv[1]) if len(sys.argv) > 1 else OLD_DB
    entries = old_entries(old)
    logger.info("в старой базе оценённых фильмов: %s", len(entries))

    back = await build_backend(config)
    http = SourceHttp("tmdb")
    try:
        done = await transfer(back, http, config.tmdb_key, entries)
    finally:
        await http.aclose()

    logger.info("из %s: %s", len(entries),
                ", ".join(f"{name} {count}"
                          for name, count in sorted(done.items())))
    logger.info("база %s, шкала %s ступеней", config.library_db, back.scale)


if __name__ == "__main__":
    asyncio.run(main())
