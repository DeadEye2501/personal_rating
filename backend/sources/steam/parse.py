"""Перевод ответов Steam в наши типы."""

import re
from datetime import datetime

from backend.model import (
    ExternalRating,
    GenreSource,
    Item,
    Kind,
    RatingSource,
    SearchHit,
    Source,
    SourceCard,
)
from backend.sources.convert import companies, genres, rating

ASSETS = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps"

YEAR = re.compile(r"(?:19|20)\d{2}")


def poster_url(appid: str) -> str:
    """Вертикальной обложки в ответе API нет, но она лежит по предсказуемому
    адресу. Вариант без `_2x` отдаёт 300×450, вдвое меньше своего имени."""
    return f"{ASSETS}/{appid}/library_600x900_2x.jpg"


def parse_search(payload: list[dict]) -> list[SearchHit]:
    return [
        SearchHit(
            kind=Kind.GAME,
            source=Source.STEAM,
            source_id=str(row["appid"]),
            title=row.get("name") or "",
            poster_url=poster_url(str(row["appid"])),
        )
        for row in payload
    ]


def _year(value: str | None) -> int | None:
    """Дата приходит как её написал человек и на языке запроса: «18 мая.
    2015 г.», «26 Nov, 2015», «Coming soon». Год ищется в строке, а не
    отрезается с конца: по-русски там стоит «г.», и хвост из четырёх знаков
    даёт «5 г.»."""
    found = YEAR.search(value or "")
    return int(found.group()) if found else None


def _metascore(data: dict, now: datetime) -> tuple[ExternalRating, ...]:
    """Metascore принадлежит Metacritic, а не Steam: у Valve с ними лицензия."""
    return rating(
        RatingSource.METACRITIC, (data.get("metacritic") or {}).get("score"), now
    )


def parse_card(data: dict) -> SourceCard:
    """Принимает блок `data` уже сверенного ответа, а не весь ответ: сверку
    ключа с запрошенным appid делает клиент."""
    appid = str(data["steam_appid"])
    now = datetime.now()
    return SourceCard(
        item=Item(
            id=0,
            kind=Kind.GAME,
            source=Source.STEAM,
            source_id=appid,
            title=data.get("name") or "",
            synced_at=now,
            synopsis=data.get("short_description") or "",
            poster_url=poster_url(appid),
            year=_year((data.get("release_date") or {}).get("date")),
        ),
        genre_ext_ids=genres(GenreSource.STEAM, data.get("genres", [])),
        companies=companies(data),
        ratings=_metascore(data, now),
    )


def parse_tags(payload: dict) -> tuple[tuple[GenreSource, str], ...]:
    """Теги игры из отдельного ответа. Приезжают номерами с весами; вес нам не
    нужен — нужен сам номер."""
    items = (payload.get("response") or {}).get("store_items") or [{}]
    return genres(GenreSource.STEAM_TAG, items[0].get("tags", []), key="tagid")
