"""Перевод ответов Google Books в наши типы."""

from datetime import datetime

from bs4 import BeautifulSoup

from backend.model import (
    CompanyRole,
    ExternalId,
    IdSource,
    Credit,
    GenreSource,
    Item,
    Kind,
    PersonRole,
    SearchHit,
    Source,
    SourceCard,
)
from backend.publishers import named
from backend.titles import flattened
from backend.sources.convert import year
from backend.unique import unique

# Второй уровень пути, который ничего не уточняет: `Fiction / General` — это
# «художественная, и больше Google не сказал».
_GENERAL = "General"

# Ступени обложки в том порядке, в каком их стоит пробовать: сперва ближайшая к
# нашей мерке 500×750 сверху, потом крупнее, потом мельче. Замерено 23.08.2026
# на семи издательских томах: `small` — 300×423, `medium` — 575×812, `large` —
# 800×1129, `extraLarge` — до 2448×3116, `thumbnail` — 128×195.
#
# Ближайшая сверху, а не самая крупная: обрезка ужимает до 500×750 и не
# растягивает, так что `medium` даёт тот же итог, что `extraLarge`, а стоит
# впятеро меньше. Мельче нашей мерки ступени идут последними — ими приходится
# довольствоваться у русских изданий, где объявлен один `thumbnail`.
#
# `smallThumbnail` в список не входит вовсе: 47×80 у скана — это не обложка, а
# значок.
_COVERS = ("medium", "large", "extraLarge", "small", "thumbnail")

# Те же ступени по возрастанию размера — этим порядком выбирается запасная у
# скана. Отдельным набором, а не перевёрнутым `_COVERS`: тот упорядочен
# близостью к нашей мерке, и `small` стоит в нём после `extraLarge` не потому,
# что крупнее. `thumbnail` сюда не входит — до этого набора добираются только
# тогда, когда его нет вовсе.
_SMALLER_FIRST = ("small", "medium", "large", "extraLarge")

# Чем издательский том отличается от сканированного — прямо в адресе.
_PUBLISHER = "/books/publisher/content"


def _genre_mark(path: str) -> str:
    """Второй уровень пути BISAC, а где его нет или он `General` — первый.

    Третий слишком дробен: у одной книги разом `Hard Science Fiction` и
    `Space Exploration`. Первый слишком крупен: `Fiction` покрывает треть всех
    книг."""
    parts = [one.strip() for one in path.split("/") if one.strip()]
    if len(parts) > 1 and parts[1] != _GENERAL:
        return parts[1]
    return parts[0] if parts else ""


def _marks(info: dict) -> tuple[tuple[GenreSource, str], ...]:
    """Повторы снимаются: у «Задачи трёх тел» четыре пути BISAC и один и тот же
    второй уровень у всех четырёх — жанр встал бы в карточке четырьмя
    одинаковыми метками."""
    marks = [_genre_mark(path) for path in info.get("categories", [])]
    return tuple((GenreSource.GOOGLE_BOOKS, mark) for mark in unique(marks) if mark)


def covers(links: dict) -> list[str]:
    """Объявленные томом адреса обложки в порядке близости к нашей мерке."""
    return [links[name] for name in _COVERS if links.get(name)]


def _poster(info: dict) -> str:
    """Адрес обложки: ближайшая к нашей мерке ступень у издательского тома и
    `thumbnail` у сканированного.

    Разделение замеренное, 23.08.2026, на восемнадцати томах живой выдачи.
    Издательские адреса идут через `/books/publisher/content`, и у всех семи
    таких томов **любая** ступень — настоящая обложка: 300×423, 575×812,
    800×1129, до 2448×3116. Сканы идут через `/books/content`, и у трёх из пяти
    крупные ступени — **полоса страницы**: 300×48, 575×92, 800×128 при
    пропорции 6.25. `thumbnail` при этом обложка у всех до единого — 128×195,
    128×204, 128×219.

    Значит крупную ступень берём там, где ей можно верить, а у скана
    довольствуемся маленькой: она мелковата, зато это обложка, а не кусок
    страницы. Цена названа — у скана с честными ступенями (один из пяти) мы
    берём 128 вместо 575.

    Скан без `thumbnail` — случай краевой (замерено: объявлен у всех до
    единого), и запасной ему идёт **самая мелкая** из объявленных, а не
    последняя в лестнице: последняя у тома с одними `medium` и `large` — это
    `large` 800×1129, то есть ровно та крупная ступень, от которой ветка и
    защищает.

    Самая крупная не берётся нарочно, это решение пользователя того же дня:
    обрезка ужимает до 500×750 и не растягивает, поэтому `medium` 575×812 даёт
    тот же итог, что `extraLarge` 2448×3116, а весит впятеро меньше."""
    links = info.get("imageLinks", {})
    ladder = covers(links)
    if not ladder:
        return ""
    thumbnail = links.get("thumbnail", "")
    if _PUBLISHER in thumbnail:
        return ladder[0]
    return thumbnail or next(
        links[name] for name in _SMALLER_FIRST if links.get(name))


def _owned_by(asked: set[str], authors: list[str]) -> bool:
    """Есть ли у тома спрошенный автор. Хватает части имени: человек набирает
    «толкин», а Google пишет «Джон Рональд Руэл Толкин», и требовать совпадения
    целиком значило бы не находить по фамилии вовсе."""
    return any(asked <= set(flattened(one).split()) for one in authors)


def parse_by_author(payload: dict, name: str) -> list[SearchHit]:
    """Работы автора: те тома ответа, у которых он правда есть.

    Проверка нужна потому, что ручки людей у Google нет вовсе, а `inauthor:` он
    понимает как пожелание. Замерено 23.08.2026 живьём: по
    `inauthor:"задача трех тел"` приезжают «The Three-Body Problem» Валтонена и
    Марчала — чужие книги под видом работ автора, и до экрана они доезжали, ведь
    работы тёзок общий отсев по запросу не трогает: там запрос — имя, а строки —
    книги.

    Цена замерена в тот же день: у «Фрэнка Герберта» из двадцати строк остаётся
    девятнадцать (уходит транслитерация `Frenk Gerbert`), у «Стивена Кинга» —
    семнадцать, и уходят книги **про** него.

    Приведение имени берётся то же, что у склейки и отсева: своё разошлось бы с
    ним молча."""
    asked = set(flattened(name).split())
    if not asked:
        return []
    return parse_search({"items": [
        one for one in payload.get("items", [])
        if _owned_by(asked, one.get("volumeInfo", {}).get("authors", []))
    ]})


def _isbn(info: dict) -> tuple[ExternalId, ...]:
    """ISBN тома: тринадцатизначный, а если его нет — десятизначный.

    Нужен запасному источнику обложек: у Google картинки нет у большинства
    бумажных русских изданий — замерено 23.08.2026, у 15 томов из 38 с ISBN, —
    и обложку ищут в чужом каталоге по этому номеру.

    Пустой список — обычное дело: у сканов и журналов ISBN нет вовсе."""
    numbers = {one.get("type"): one.get("identifier", "")
               for one in info.get("industryIdentifiers", [])}
    found = numbers.get("ISBN_13") or numbers.get("ISBN_10") or ""
    return (ExternalId(source=IdSource.ISBN, value=found),) if found else ()


def _plain(value: str | None) -> str:
    """Синопсис без разметки: замерено, у «Задачи трёх тел» весь текст обёрнут
    в `<p>`. Страница показывает синопсис текстом и экранирует его — теги
    приехали бы человеку дословно.

    Разбирает `bs4`, как и страницы old-games.ru: свой отрезатель регуляркой не
    знает про сущности вроде `&nbsp;`."""
    if not value:
        return ""
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def _info(payload: dict) -> dict:
    """Всё о томе лежит одним блоком, и он же приезжает строкой выдачи."""
    return payload.get("volumeInfo") or {}


def parse_search(payload: dict) -> list[SearchHit]:
    """Строка выдачи несёт всё, кроме полного пути жанра: его обрезает сам
    Google до верхушки — замерено, у «Задачи трёх тел» в выдаче `Fiction`, а в
    карточке `Fiction / Science Fiction / Hard Science Fiction`."""
    hits = []
    for row in payload.get("items", []):
        info = _info(row)
        hits.append(
            SearchHit(
                kind=Kind.BOOK,
                source=Source.GOOGLE_BOOKS,
                source_id=str(row["id"]),
                title=info.get("title") or "",
                year=year(info.get("publishedDate")),
                synopsis=_plain(info.get("description")),
                poster_url=_poster(info),
                genre_ext_ids=_marks(info),
                external_ids=_isbn(info),
            )
        )
    return hits


def parse_card(payload: dict) -> SourceCard:
    """Идентичности у автора нет вовсе: `authors` — голые строки, и суррогат
    склеил бы двух тёзок в одну строку навсегда. Таких склеивают по имени — и
    только по точному: близость написаний заведена для студий, а у человека имя
    пишут одним способом.

    `original_title` остаётся пустым: второго названия у Google нет ни одного."""
    info = _info(payload)
    publisher = info.get("publisher")
    now = datetime.now()
    return SourceCard(
        item=Item(
            id=0,
            kind=Kind.BOOK,
            source=Source.GOOGLE_BOOKS,
            source_id=str(payload["id"]),
            title=info.get("title") or "",
            synced_at=now,
            year=year(info.get("publishedDate")),
            synopsis=_plain(info.get("description")),
            poster_url=_poster(info),
        ),
        genre_ext_ids=_marks(info),
        people=tuple(Credit(name=name, role=PersonRole.AUTHOR)
                     for name in info.get("authors", [])),
        # Издательств в строке бывает несколько: «ЛитРес, АСТ» — два разных,
        # семь строк на 260 в замере 23.08.2026. Разбирает их `named`, там же
        # и оговорки: союз не режется, форма собственности не издательство.
        companies=tuple(Credit(name=one, role=CompanyRole.PUBLISHER)
                        for one in named(publisher)),
    )
