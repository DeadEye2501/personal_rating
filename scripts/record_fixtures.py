"""Разовая запись живых ответов источников в tests/fixtures/.

Запуск: pipenv run python -m scripts.record_fixtures
Ключи берутся из .env. Пишутся только те источники, чьи ключи заполнены.
"""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from backend.config import load_config
from backend.sources.http import USER_AGENT
from backend.sources.steam.client import CARD_WANTED, SIFT_WANTED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures"
HEADERS = {"User-Agent": USER_AGENT}

# Каталог коммитится: из заголовков берём только то, что нужно разбору.
# Всё остальное — Set-Cookie, ключи, служебное — не наше дело.
KEEP_HEADERS = ("content-type", "retry-after", "x-ratelimit-limit",
                "x-ratelimit-remaining", "x-ratelimit-reset")

INTERSTELLAR_TMDB = 157336
ANDOR_TMDB = 83867
INTERSTELLAR_IMDB = "tt0816692"
WITCHER_APPID = 292030

# Четыре игры, у которых разошёлся и род товара, и форма имени обложки: игра с
# хешем в имени файла, инструмент с голым именем, игра с `portrait.png` и без
# `library_capsule_2x` вовсе, и playtest. На одном appid отсева не наблюдается.
REDKIT_APPID = 2684660
ARCANUM_APPID = 500810
PLAYTEST_APPID = 4926960

# Режиссёр и актёр: у первого работы лежат в crew, у второго в cast, и разбор
# обязан видеть оба списка.
NOLAN_TMDB = 525
MURPHY_TMDB = 2037

# Шоураннер: у него в сериальном crew есть и `Creator`, и `Executive Producer`,
# а у Нолана этот список пуст вовсе — на нём отбор ролей не наблюдается.
GILLIGAN_TMDB = 66633

# Том с полным путём BISAC: у него два пути, и у первого есть второй уровень —
# ровно то, чем справочник книг и пользуется.
THREE_BODY_GB = "-u8-DwAAQBAJ"
# Том без обложки и без издательства: у четверти книг обложки нет, и строка
# выдачи обязана пережить это, а не исчезнуть.
NO_COVER_GB = "vDkkMwEACAAJ"
# Том без автора: у Google `authors` бывает пуст, и состав карточки тогда пуст.
NO_AUTHOR_GB = "0pkiAQAAIAAJ"
# Годный по форме, но несуществующий том: отвечает 404 с телом. Негодный по
# форме отвечает 503, и это занятость, а не отсутствие.
ABSENT_GB = "zzzzzzzzzzzz"
MALFORMED_GB = "нетТакого123"

# «Группа крови»: одиннадцать треков, у всех `track_position` пуст, жанр один.
BLOOD_TYPE_DEEZER = 54717452
# Альбом без жанра вовсе: замерено, что таких у Deezer 12 из 57.
NO_GENRE_DEEZER = 5752371
KINO_DEEZER = 4505880

# Занятость Google: тот же код, что у old-games.ru, и лечится так же.
BUSY_GB = 503


def save(source: str, case: str, response: httpx.Response) -> None:
    folder = OUT / source
    folder.mkdir(parents=True, exist_ok=True)
    try:
        body = folder / f"{case}.json"
        body.write_text(
            json.dumps(response.json(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except ValueError:
        # Сюда попадает один ответ из тридцати восьми: битый `input_json` у
        # тегов Steam отдаёт страницу ошибки HTML. Остальные пять источников
        # отвечают JSON даже на отказ.
        body = folder / f"{case}.txt"
        body.write_text(response.text, encoding="utf-8")

    kept = {k: v for k, v in response.headers.items() if k.lower() in KEEP_HEADERS}
    (folder / f"{case}.meta.json").write_text(
        json.dumps({"status": response.status_code, "headers": kept},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  {source}/{body.name}  {response.status_code}  {len(response.content)} б")


async def record_tmdb(client: httpx.AsyncClient, key: str) -> None:
    print("TMDB")
    base = "https://api.themoviedb.org/3"
    common = {"api_key": key, "language": "ru-RU"}

    save("tmdb", "search_movie", await client.get(
        f"{base}/search/movie", params={**common, "query": "Интерстеллар"}))
    save("tmdb", "search_tv", await client.get(
        f"{base}/search/tv", params={**common, "query": "Andor"}))
    save("tmdb", "movie_detail", await client.get(
        f"{base}/movie/{INTERSTELLAR_TMDB}",
        params={**common, "append_to_response": "credits"}))
    save("tmdb", "tv_detail", await client.get(
        f"{base}/tv/{ANDOR_TMDB}",
        params={**common, "append_to_response": "aggregate_credits,external_ids"}))
    # Опечатка в довеске: ответ 200 и просто без блока — отсюда правило
    # проверять содержимое, а не код.
    save("tmdb", "movie_detail_typo_append", await client.get(
        f"{base}/movie/{INTERSTELLAR_TMDB}",
        params={**common, "append_to_response": "credtis"}))
    save("tmdb", "person_credits_movie", await client.get(
        f"{base}/person/{NOLAN_TMDB}/movie_credits", params=common))
    save("tmdb", "person_credits_tv", await client.get(
        f"{base}/person/{NOLAN_TMDB}/tv_credits", params=common))
    save("tmdb", "person_credits_actor", await client.get(
        f"{base}/person/{MURPHY_TMDB}/movie_credits", params=common))
    save("tmdb", "person_credits_showrunner", await client.get(
        f"{base}/person/{GILLIGAN_TMDB}/tv_credits", params=common))
    save("tmdb", "search_person", await client.get(
        f"{base}/search/person", params={**common, "query": "Christopher Nolan"}))
    save("tmdb", "search_person_empty", await client.get(
        f"{base}/search/person", params={**common, "query": "щщщ ыыы ъъъ"}))
    save("tmdb", "not_found", await client.get(
        f"{base}/movie/99999999", params=common))
    save("tmdb", "bad_key", await client.get(
        f"{base}/movie/{INTERSTELLAR_TMDB}", params={"api_key": "мусор"}))


async def record_steam(client: httpx.AsyncClient) -> None:
    print("Steam")
    save("steam", "search", await client.get(
        "https://steamcommunity.com/actions/SearchApps/The Witcher 3 Wild Hunt"))
    save("steam", "search_empty", await client.get(
        "https://steamcommunity.com/actions/SearchApps/zzqqxxnotagame123"))
    save("steam", "appdetails", await client.get(
        "https://store.steampowered.com/api/appdetails",
        params={"appids": WITCHER_APPID, "l": "russian"}))
    save("steam", "appdetails_missing", await client.get(
        "https://store.steampowered.com/api/appdetails",
        params={"appids": 999999999, "l": "russian"}))
    save("steam", "appdetails_broken", await client.get(
        "https://store.steampowered.com/api/appdetails", params={"l": "russian"}))


async def record_steam_items(client: httpx.AsyncClient) -> None:
    """Ответы `GetItems`: в `appdetails` нет ни тегов, ни рода товара, ни
    настоящего имени файла обложки. `country_code` только US — с RU ответ
    приходит пустым, с `visible: false`."""
    print("Steam, GetItems")
    tags = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"

    def ask(appids: list[int], wanted: dict) -> str:
        return json.dumps({
            "ids": [{"appid": one} for one in appids],
            "context": {"language": "russian", "country_code": "US",
                        "steam_realm": 1},
            "data_request": wanted,
        })

    of_tags = {"include_tag_count": 20}
    save("steam", "store_items", await client.get(
        tags, params={"input_json": ask([WITCHER_APPID], of_tags)}))
    save("steam", "store_items_missing", await client.get(
        tags, params={"input_json": ask([999999999], of_tags)}))
    save("steam", "store_items_empty", await client.get(
        tags, params={"input_json": ask([], of_tags)}))
    # Единственный ответ за весь прогон, который не JSON: страница ошибки.
    save("steam", "store_items_broken", await client.get(
        tags, params={"input_json": "{не json"}))
    # Дальше — то, что спрашивает боевой клиент, и просимое берётся у него же.
    # Списанное руками разошлось молча: `include_release` появился в коде, а
    # здесь нет, и первый же перезапуск стёр бы годы из `store_items_many`,
    # уронив три проверки с видом «Steam перестал отдавать дату».
    #
    # Выдача и карточка записываются порознь, потому что на пару Steam мог бы
    # ответить иначе, чем на каждое порознь.
    save("steam", "store_items_many", await client.get(
        tags, params={"input_json": ask(
            [WITCHER_APPID, REDKIT_APPID, ARCANUM_APPID, PLAYTEST_APPID],
            SIFT_WANTED)}))
    save("steam", "store_items_card", await client.get(
        tags, params={"input_json": ask([WITCHER_APPID], CARD_WANTED)}))


async def record_gog(client: httpx.AsyncClient) -> None:
    print("GOG")
    save("gog", "catalog", await client.get(
        "https://catalog.gog.com/v1/catalog",
        params={"query": "like:Baldur's Gate", "locale": "ru-RU"}))
    # Тот же запрос с отсевом дополнений. Пара с `catalog` выше нужна целиком:
    # порознь не видно, что именно ушло.
    save("gog", "catalog_filtered", await client.get(
        "https://catalog.gog.com/v1/catalog",
        params={"query": "like:Baldur's Gate", "locale": "ru-RU",
                "productType": "in:game,pack"}))
    # Заведомая бессмыслица: приедет 200 и десятка два несвязанных игр.
    save("gog", "catalog_nonsense", await client.get(
        "https://catalog.gog.com/v1/catalog",
        params={"query": "like:zzqqxxnotagame123", "locale": "ru-RU"}))
    # Товарная ручка: она переводит номер в название, потому что каталог по
    # числу не находит ничего. Номер взят из ответа каталога выше — цепочка
    # «номер → название → каталог» иначе не проверяется целиком.
    save("gog", "product", await client.get(
        "https://api.gog.com/products/1456460669"))
    # Единственное место, где GOG умеет сказать «такого продукта нет». Номер
    # заведомо несуществующий: у `products/1` лежит настоящая игра.
    save("gog", "product_missing", await client.get(
        "https://api.gog.com/products/999999999"))


async def record_mdblist(client: httpx.AsyncClient, key: str) -> None:
    print("MDBList")
    # Ответ /user не записываем: он про учётную запись, а не про разбор.
    save("mdblist", "found", await client.get(
        f"https://api.mdblist.com/imdb/movie/{INTERSTELLAR_IMDB}",
        params={"apikey": key}))
    save("mdblist", "bad_key", await client.get(
        f"https://api.mdblist.com/imdb/movie/{INTERSTELLAR_IMDB}",
        params={"apikey": "мусор"}))
    save("mdblist", "no_key", await client.get(
        f"https://api.mdblist.com/imdb/movie/{INTERSTELLAR_IMDB}"))


async def record_omdb(client: httpx.AsyncClient, key: str) -> None:
    print("OMDB")
    save("omdb", "found", await client.get(
        "https://www.omdbapi.com/",
        params={"apikey": key, "i": INTERSTELLAR_IMDB}))
    save("omdb", "not_found", await client.get(
        "https://www.omdbapi.com/", params={"apikey": key, "i": "tt0000000"}))
    save("omdb", "bad_id", await client.get(
        "https://www.omdbapi.com/", params={"apikey": key, "i": "мусор"}))
    save("omdb", "bad_key", await client.get(
        "https://www.omdbapi.com/", params={"apikey": "мусор", "i": INTERSTELLAR_IMDB}))
    save("omdb", "no_key", await client.get(
        "https://www.omdbapi.com/", params={"i": INTERSTELLAR_IMDB}))


async def record_kinopoisk_unofficial(client: httpx.AsyncClient, key: str) -> None:
    print("Кинопоиск, unofficial")
    # Негодный ключ тут латиницей: у Кинопоиска он ездит заголовком, а заголовок
    # httpx кодирует в ASCII и на кириллице падает, не дойдя до сети.
    wrong = "not-a-real-key"
    # Ответ /api_keys/{key} не записываем: ключ стоит прямо в пути.
    base = "https://kinopoiskapiunofficial.tech/api/v2.2/films"
    save("kinopoisk", "unofficial_found", await client.get(
        base, params={"imdbId": INTERSTELLAR_IMDB}, headers={"X-API-KEY": key}))
    save("kinopoisk", "unofficial_not_found", await client.get(
        base, params={"imdbId": "tt0000000"}, headers={"X-API-KEY": key}))
    save("kinopoisk", "unofficial_bad_key", await client.get(
        base, params={"imdbId": INTERSTELLAR_IMDB}, headers={"X-API-KEY": wrong}))
    # «Гражданин-мститель»: в списке оценки нет, в карточке по номеру она есть.
    # У «Интерстеллара» в списке она стоит, и на нём этот случай не наблюдается.
    save("kinopoisk", "unofficial_list_without_rating", await client.get(
        base, params={"imdbId": "tt35309713"}, headers={"X-API-KEY": key}))
    save("kinopoisk", "unofficial_card", await client.get(
        f"{base}/6943602", headers={"X-API-KEY": key}))


async def record_oldgames(client: httpx.AsyncClient) -> None:
    """Единственный источник без API: пишутся страницы, а не ответы ручек.

    «Dune» взята потому, что у неё есть всё сразу — обложка, описание, оценка;
    «Dedale» — потому что обложки у неё нет, и вместо адреса приезжает заглушка
    `nocover-rus.gif`. Несуществующий номер даёт страницу ошибки: единственный
    ответ сайта, который не таблица и не карточка."""
    print("old-games.ru")
    base = "https://www.old-games.ru"
    save("oldgames", "search_dune", await client.get(
        f"{base}/catalog/", params={"gamename": "dune"}))
    save("oldgames", "search_nothing", await client.get(
        f"{base}/catalog/", params={"gamename": "щукапцхжэ"}))
    save("oldgames", "card_dune", await client.get(f"{base}/game/25.html"))
    save("oldgames", "card_without_cover", await client.get(f"{base}/game/4000.html"))
    save("oldgames", "missing_game", await client.get(f"{base}/game/99999999.html"))


async def record_google_books(client: httpx.AsyncClient, key: str) -> None:
    """Ответы боевой ручки v1, с ключом.

    Поиск перепрашивается: Google душит очередь запросов и отвечает 503 на
    половину из них. Замерено — повтор поднимает пять успешных из десяти до
    восьми, а пауза не даёт ничего."""
    print("Google Books")
    base = "https://www.googleapis.com/books/v1/volumes"

    async def asked(params: dict) -> httpx.Response:
        for _ in range(4):
            answer = await client.get(base, params={**params, "key": key})
            if answer.status_code != BUSY_GB:
                return answer
        return answer

    save("google_books", "search_dune", await asked(
        {"q": "dune", "maxResults": 20, "startIndex": 0}))
    save("google_books", "search_dune_page2", await asked(
        {"q": "dune", "maxResults": 20, "startIndex": 20}))
    save("google_books", "inauthor_herbert", await asked(
        {"q": 'inauthor:"Frank Herbert"', "maxResults": 20}))

    for case, volume in (("volume_three_body", THREE_BODY_GB),
                         ("volume_no_cover", NO_COVER_GB),
                         ("volume_no_author", NO_AUTHOR_GB),
                         ("absent", ABSENT_GB),
                         ("busy", MALFORMED_GB)):
        save("google_books", case,
             await client.get(f"{base}/{volume}", params={"key": key}))

    # Без ключа суточная квота безымянного проекта равна нулю: 429 на первый
    # же запрос. С негодным ключом ответ другой — 400.
    save("google_books", "quota", await client.get(base, params={"q": "dune"}))
    save("google_books", "bad_key", await client.get(
        base, params={"q": "dune", "key": "мусор"}))


async def record_deezer(client: httpx.AsyncClient) -> None:
    """Ключа Deezer не требует вовсе.

    Отказа по частоте здесь нет: он приходит под кодом 200 с телом
    `{"error": {"code": 4}}`, и вызвать его можно только волной запросов —
    такую фикстуру пишут руками, а не бьют по чужому сервису."""
    print("Deezer")
    base = "https://api.deezer.com"

    save("deezer", "search_album_kino", await client.get(
        f"{base}/search/album", params={"q": "Кино Группа крови"}))
    save("deezer", "search_album_page2", await client.get(
        f"{base}/search/album", params={"q": "rock", "index": 5, "limit": 5}))
    save("deezer", "album_blood_type", await client.get(
        f"{base}/album/{BLOOD_TYPE_DEEZER}"))
    save("deezer", "album_no_genre", await client.get(
        f"{base}/album/{NO_GENRE_DEEZER}"))
    save("deezer", "absent", await client.get(f"{base}/album/999999999999"))
    save("deezer", "search_artist_kino", await client.get(
        f"{base}/search/artist", params={"q": "Кино"}))
    save("deezer", "artist_albums_kino", await client.get(
        f"{base}/artist/{KINO_DEEZER}/albums", params={"limit": 5}))


async def main() -> None:
    load_dotenv(ROOT / ".env")
    config = load_config(os.environ, ROOT)
    async with httpx.AsyncClient(headers=HEADERS, timeout=30,
                                 follow_redirects=True) as client:
        await record_steam(client)
        await record_steam_items(client)
        await record_gog(client)
        await record_oldgames(client)
        await record_deezer(client)

        pairs = (
            ("TMDB", config.tmdb_key, record_tmdb),
            ("MDBList", config.mdblist_key, record_mdblist),
            ("OMDB", config.omdb_key, record_omdb),
            ("Кинопоиска", config.kinopoisk_unofficial_key,
             record_kinopoisk_unofficial),
            ("Google Books", config.google_books_key, record_google_books),
        )
        for name, key, recorder in pairs:
            if not key:
                print(f"ключ {name} пуст — пропускаю")
                continue
            await recorder(client, key)


if __name__ == "__main__":
    asyncio.run(main())
