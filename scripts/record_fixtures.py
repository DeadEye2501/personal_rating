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

# Режиссёр и актёр: у первого работы лежат в crew, у второго в cast, и разбор
# обязан видеть оба списка.
NOLAN_TMDB = 525
MURPHY_TMDB = 2037


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
    # Теги живут отдельно: в appdetails их нет вовсе. `country_code` только US —
    # с RU ответ приходит пустым, с `visible: false`.
    tags = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"

    def ask(ids: list[dict]) -> str:
        return json.dumps({
            "ids": ids,
            "context": {"language": "russian", "country_code": "US",
                        "steam_realm": 1},
            "data_request": {"include_tag_count": 20},
        })

    save("steam", "store_items", await client.get(
        tags, params={"input_json": ask([{"appid": WITCHER_APPID}])}))
    save("steam", "store_items_missing", await client.get(
        tags, params={"input_json": ask([{"appid": 999999999}])}))
    save("steam", "store_items_empty", await client.get(
        tags, params={"input_json": ask([])}))
    # Единственный ответ за весь прогон, который не JSON: страница ошибки.
    save("steam", "store_items_broken", await client.get(
        tags, params={"input_json": "{не json"}))


async def record_gog(client: httpx.AsyncClient) -> None:
    print("GOG")
    save("gog", "catalog", await client.get(
        "https://catalog.gog.com/v1/catalog",
        params={"query": "like:Baldur's Gate", "locale": "ru-RU"}))
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


async def main() -> None:
    load_dotenv(ROOT / ".env")
    config = load_config(os.environ, ROOT)
    async with httpx.AsyncClient(headers=HEADERS, timeout=30,
                                 follow_redirects=True) as client:
        await record_steam(client)
        await record_gog(client)

        pairs = (
            ("TMDB", config.tmdb_key, record_tmdb),
            ("MDBList", config.mdblist_key, record_mdblist),
            ("OMDB", config.omdb_key, record_omdb),
            ("Кинопоиска", config.kinopoisk_unofficial_key,
             record_kinopoisk_unofficial),
        )
        for name, key, recorder in pairs:
            if not key:
                print(f"ключ {name} пуст — пропускаю")
                continue
            await recorder(client, key)


if __name__ == "__main__":
    asyncio.run(main())
