"""Собрать таблицу: как одна и та же игра выглядит в Steam, GOG и old-games.ru.

Материал для разбора правил дедупликации. Пишет JSON, ничего не решает.
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

STEAM_SEARCH = "https://steamcommunity.com/actions/SearchApps"
STEAM_CARD = "https://store.steampowered.com/api/appdetails"
GOG_CATALOG = "https://catalog.gog.com/v1/catalog"
OG_CATALOG = "https://www.old-games.ru/catalog/"

BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/150.0.0.0 Safari/537.36"}
OUT = Path(__file__).parent / "pairs.json"

ROW = re.compile(r'<tr[^>]*id="game_(\d+)"(.*?)(?=<tr[^>]*id="game_|</table>)',
                 re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAGS = re.compile(r"<[^>]+>")
ALT = re.compile(r'<div class="alt-titles-list">(.*?)</div>', re.S)
ALT_BLOCK = re.compile(r'<div class="alt-titles-list">.*?</div>', re.S)


def plain(chunk):
    return " ".join(TAGS.sub(" ", chunk).replace("&quot;", '"')
                    .replace("&amp;", "&").split())


async def steam(http, query):
    found = await http.get(f"{STEAM_SEARCH}/{quote(query, safe='')}")
    out = []
    for row in (found.json() or [])[:3]:
        appid = str(row["appid"])
        card = await http.get(STEAM_CARD, params={"appids": appid,
                                                  "l": "english", "cc": "us"})
        data = ((card.json() or {}).get(appid) or {}).get("data") or {}
        out.append({
            "id": appid,
            "title": row.get("name"),
            "year": (data.get("release_date") or {}).get("date"),
            "developers": data.get("developers"),
            "publishers": data.get("publishers"),
            "genres": [g["description"] for g in data.get("genres", [])],
        })
    return out


async def gog(http, query):
    found = await http.get(GOG_CATALOG, params={
        "query": f"like:{query}", "locale": "en-US",
        "productType": "in:game,pack"})
    return [{
        "id": product.get("id"),
        "title": product.get("title"),
        "slug": product.get("slug"),
        "year": (product.get("releaseDate") or "")[:10],
        "developers": product.get("developers"),
        "publishers": product.get("publishers"),
        "genres": [g.get("slug") for g in product.get("genres") or []],
    } for product in ((found.json() or {}).get("products") or [])[:3]]


async def oldgames(http, query):
    found = await http.get(OG_CATALOG, params={"gamename": query})
    out = []
    for gid, body in ROW.findall(found.text)[:3]:
        cells = [plain(cell) for cell in CELL.findall(body)]
        alt = ALT.search(body)
        head = ALT_BLOCK.sub("", body).split("</a>")[0]
        out.append({
            "id": gid,
            "title": plain(head),
            "alt": plain(alt.group(1)) if alt else None,
            "genre": cells[1] if len(cells) > 1 else None,
            "year": cells[2] if len(cells) > 2 else None,
            "platform": cells[3] if len(cells) > 3 else None,
            "publisher": cells[4] if len(cells) > 4 else None,
        })
    return out


async def one(http, query):
    results = await asyncio.gather(steam(http, query), gog(http, query),
                                   oldgames(http, query),
                                   return_exceptions=True)
    named = zip(("steam", "gog", "oldgames"), results, strict=True)
    return {"query": query,
            **{source: (rows if isinstance(rows, list)
                        else f"сорвалось: {type(rows).__name__}")
               for source, rows in named}}


async def main(titles):
    collected = []
    async with httpx.AsyncClient(timeout=60, headers=BROWSER,
                                 follow_redirects=True) as http:
        for number, title in enumerate(titles, 1):
            collected.append(await one(http, title))
            if number % 10 == 0:
                print(f"  {number}/{len(titles)}")
    OUT.write_text(json.dumps(collected, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"записано {len(collected)} запросов в {OUT}")


if __name__ == "__main__":
    names = Path(sys.argv[1]).read_text(encoding="utf-8").split("\n")
    asyncio.run(main([name.strip() for name in names if name.strip()]))
