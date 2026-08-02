"""Дописать в собранное русские названия GOG: в бою локаль `ru-RU`, а не `en-US`."""

import asyncio
import json
from pathlib import Path

import httpx

CATALOG = "https://catalog.gog.com/v1/catalog"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/150.0.0.0 Safari/537.36"}
FILE = Path(__file__).parent / "pairs.json"


async def russian(http, query):
    found = await http.get(CATALOG, params={
        "query": f"like:{query}", "locale": "ru-RU",
        "productType": "in:game,pack"})
    return {product.get("id"): product.get("title")
            for product in ((found.json() or {}).get("products") or [])}


def gog_rows(rows):
    for row in rows:
        for one in row.get("gog") or []:
            if isinstance(one, dict):
                yield one


async def main():
    rows = json.loads(FILE.read_text(encoding="utf-8"))
    async with httpx.AsyncClient(timeout=60, headers=HEADERS,
                                 follow_redirects=True) as http:
        for number, row in enumerate(rows, 1):
            names = await russian(http, row["query"])
            for one in row.get("gog") or []:
                if isinstance(one, dict):
                    one["title_ru"] = names.get(one["id"])
            if number % 50 == 0:
                print(f"  {number}/{len(rows)}")

    FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    total = list(gog_rows(rows))
    differ = [one for one in total
              if one.get("title_ru") and one["title_ru"] != one["title"]]
    print(f"строк GOG {len(total)}, русское название отличается у {len(differ)}")
    for one in differ[:8]:
        print(f"    {one['title']}  →  {one['title_ru']}")


if __name__ == "__main__":
    asyncio.run(main())
