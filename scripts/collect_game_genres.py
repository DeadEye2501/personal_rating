"""Разовый сбор игровых жанров: справочника в документации нет ни у Steam, ни у
GOG, но каждый отдаёт свой список отдельной ручкой.

Запуск: pipenv run python scripts/collect_game_genres.py
"""

import asyncio
import json

import httpx

HEADERS = {"User-Agent": "PersonalRating/0.1 (personal library app)"}

# Витрина отдаёт имена без числовых идентификаторов, а карточка игры — с ними.
# Поэтому список берётся из витрины, а номера добираются по играм-примерам.
STEAM_MENU = "https://store.steampowered.com/api/getgenrelist/"
STEAM_APP = "https://store.steampowered.com/api/appdetails"
GOG_CATALOG = "https://catalog.gog.com/v1/catalog"

EXAMPLES_PER_GENRE = 2


def example_appids(menu: list[dict]) -> list[int]:
    """Игры-примеры из витрины. У платформенных строк вместо списка лежит false."""
    appids = []
    for genre in menu:
        items = genre.get("items")
        if isinstance(items, list):
            appids.extend(item["id"] for item in items[:EXAMPLES_PER_GENRE])
    return list(dict.fromkeys(appids))


async def app_genres(client: httpx.AsyncClient, appid: int) -> list[dict]:
    response = await client.get(STEAM_APP, params={"appids": appid, "l": "russian"})
    if response.status_code != 200:
        # Иначе на троттлинге скрипт свалится с JSONDecodeError.
        print(f"steam {appid}: код {response.status_code}, пропущено")
        return []
    payload = response.json().get(str(appid), {})
    if not payload.get("success"):
        print(f"steam {appid}: success=false, пропущено")
        return []
    return payload["data"].get("genres", [])


async def steam_genres(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.get(STEAM_MENU, params={"l": "russian"})
    menu = response.json()["genres"]
    print(f"витрина Steam: {len(menu)} строк")

    found: dict[str, str] = {}
    for appid in example_appids(menu):
        for genre in await app_genres(client, appid):
            found[str(genre["id"])] = genre["description"]
        await asyncio.sleep(0.3)
    return found


async def gog_genres(client: httpx.AsyncClient) -> dict[str, str]:
    """Полный список отдаётся фасетом каталога — выборка по играм не нужна."""
    response = await client.get(GOG_CATALOG, params={"limit": "1", "locale": "ru-RU"})
    found: dict[str, str] = {}
    for genre in response.json()["filters"]["fullGenresList"]:
        found.setdefault(genre["slug"], genre["name"])
    return found


async def main() -> None:
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
        steam = await steam_genres(client)
        gog = await gog_genres(client)

    print(json.dumps({"steam": steam, "gog": gog}, ensure_ascii=False, indent=2))
    print(f"\nSteam: {len(steam)} жанров, GOG: {len(gog)} жанров")


if __name__ == "__main__":
    asyncio.run(main())
