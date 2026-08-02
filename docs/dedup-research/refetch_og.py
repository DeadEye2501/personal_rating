"""Пересобрать половину old-games: прежний разбор ячеек был неверен."""
import asyncio, json
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

CATALOG = "https://www.old-games.ru/catalog/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/150.0.0.0 Safari/537.36"}
FILE = Path(__file__).parent / "pairs.json"


def read(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for row in soup.select('tr[id^="game_"]')[:3]:
        cells = row.find_all("td", recursive=False)
        link = row.find("a", href=lambda h: h and "/game/" in h)
        alt = row.find("div", class_="alt-titles-list")
        text = [" ".join(c.get_text(" ").split()) for c in cells]
        out.append({
            "id": row["id"][5:],
            "title": link.get_text(" ", strip=True) if link else "",
            "alt": " ".join(alt.get_text(" ").split()) if alt else None,
            "genre": text[1] if len(text) > 1 else None,
            "year": text[2] if len(text) > 2 else None,
            "platform": text[3] if len(text) > 3 else None,
            "publisher": text[4] if len(text) > 4 else None,
        })
    return out


async def main():
    rows = json.loads(FILE.read_text(encoding="utf-8"))
    async with httpx.AsyncClient(timeout=60, headers=HEADERS,
                                 follow_redirects=True) as http:
        for number, row in enumerate(rows, 1):
            found = await http.get(CATALOG, params={"gamename": row["query"]})
            row["oldgames"] = read(found.text)
            if number % 50 == 0:
                print(f"  {number}/{len(rows)}")
    FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    got = [one for row in rows for one in row["oldgames"]]
    years = [one for one in got if (one["year"] or "").strip().isdigit()]
    print(f"строк old-games {len(got)}, с годом {len(years)}")
    print("пример:", got[0] if got else "нет")


asyncio.run(main())
