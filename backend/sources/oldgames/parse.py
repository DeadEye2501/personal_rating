"""Перевод страниц old-games.ru в наши типы.

Единственный источник без API: разбирается HTML. Отсюда правило, которого у
остальных шести нет — **разбор ломается громко**. Не нашлось того, на чём стоит
страница, — исключение, а не пустая карточка: перезапроса у игр не бывает, и
обеднённая строка легла бы в базу навсегда.

Разбирает `beautifulsoup4`. Токенизатор при этом тот же `html.parser` из
стандартной библиотеки — берётся у bs4 древостроитель, который восстанавливает
неявно закрытые теги: на выдаче по «dune» 27 открывающих `<tr>` и 21
закрывающий. Самодельный разборщик со счётчиком глубины на этой же странице
молча вернул одну строку из семи, и это худший вид поломки.
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from backend.sources.convert import year_in_text

from backend.language import by_language
from backend.model import (
    CompanyRole,
    Credit,
    GenreSource,
    Item,
    Kind,
    SearchHit,
    Source,
    SourceCard,
)

# Ссылка на саму игру. Рядом в той же ячейке лежат `/game/video/N.html`,
# `/game/screenshots/N.html` и ещё три таких же — по номеру их не различить.
GAME_HREF = re.compile(r"^/game/(\d+)\.html$")

# Своя заглушка сайта вместо отсутствующей обложки. Записать её адресом значит
# завести карточку с картинкой «обложки нет» навсегда.
NOCOVER = "nocover-rus.gif"

# Микроразметка игры. Первый `itemprop="name"` на странице — имя самого сайта,
# второй — «Каталог игр», и только третий лежит здесь.
GAME_SCOPE = '[itemtype*="SoftwareApplication"]'

# Чем сайт подписывает автора обзора. Хвост отрезается: это не часть синопсиса, а
# подпись под ним, и в карточке она выглядела бы концом описания игры.
BY = "Автор обзора:"

# Второе имя игры на странице карточки. В выдаче оно лежит иначе — там
# `div.alt-titles-list`, — и общего селектора у двух страниц нет.
ALT_NAMES = "span.game_alt_names"

# «Разработчик неизвестен» оформлен у сайта настоящей компанией с именем `-`.
# Взятая как есть, она стала бы одной кликабельной студией на все такие игры.
UNKNOWN = "-"


def _soup(page: str) -> BeautifulSoup:
    return BeautifulSoup(page, "html.parser")


def _text(node: Tag | None) -> str:
    """Текст узла одной строкой. Пробел разделителем обязателен: название
    разбито на `<b>Dune</b> II: ...`, и без него склеится в «DuneII»."""
    return node.get_text(" ", strip=True) if node is not None else ""


def _hit(row: Tag) -> SearchHit:
    """Строка выдачи в кандидата.

    Платформа и издатель со страницы не берутся: у `SearchHit` для них нет
    поля. Обложки в выдаче нет вовсе — её добирает карточка.

    Название берётся из атрибута `title` ссылки, а не из её текста: текст разбит
    тегами (`<b>Dune</b>: Keep The Secret`), и склейка через пробел даёт лишний —
    «Dune : Keep The Secret». В атрибуте оно записано целиком."""
    cells = row.find_all("td", recursive=False)
    link = row.find("a", href=GAME_HREF)
    if link is None:
        raise ValueError(f"в строке {row.get('id')} нет ссылки на игру")

    genre = _text(cells[1]) if len(cells) > 1 else ""
    return SearchHit(
        kind=Kind.GAME,
        source=Source.OLD_GAMES,
        source_id=GAME_HREF.match(link["href"]).group(1),
        title=link.get("title") or _text(link),
        # Второе написание ищется внутри своей ячейки, а не от ссылки вперёд:
        # `find_next` идёт по всему документу, и строка без своего второго
        # названия забирала бы его у следующей. Замерено на записанной выдаче —
        # три строки из семи получали чужое.
        original_title=_text(cells[0].find("div", class_="alt-titles-list")),
        year=year_in_text(_text(cells[2])) if len(cells) > 2 else None,
        genre_ext_ids=((GenreSource.OLD_GAMES, genre),) if genre else (),
    )


def parse_search(page: str) -> list[SearchHit]:
    """Выдача каталога. Ноль строк — честный отрицательный ответ, в отличие от
    GOG: страница при этом настоящая, игр в ней нет.

    Что это вообще выдача, а не страница ошибки, видно по форме поиска: на
    ошибке её нет. Без этой проверки чужая страница читалась бы как «ничего не
    нашлось», то есть как отрицательный факт."""
    soup = _soup(page)
    if soup.find("input", attrs={"name": "gamename"}) is None:
        raise ValueError("страница не похожа на выдачу каталога")
    return [_hit(row) for row in soup.select('tr[id^="game_"]')]


def _labelled(scope: Tag, label: str) -> str:
    """Значение поля по его подписи: `<td>Подпись:</td><td>значение</td>`.

    Подписью, а не порядком ячеек: строк у разных игр разное число — у одной
    есть «Локализация», у другой нет, — и счёт по номеру уехал бы."""
    head = scope.find("td", string=re.compile(rf"^\s*{label}\s*:"))
    return _text(head.find_next_sibling("td")) if head is not None else ""


def _companies(scope: Tag) -> tuple[Credit, ...]:
    return tuple(
        Credit(name=name, role=role)
        for role, label in ((CompanyRole.DEVELOPER, "Разработчик"),
                            (CompanyRole.PUBLISHER, "Издатель"))
        if (name := _labelled(scope, label)) and name != UNKNOWN
    )


def _synopsis(soup: BeautifulSoup) -> str:
    """Описание из тела страницы, без подписи автора обзора."""
    return _text(soup.find(id="reviewtext")).split(BY)[0].strip()


def _cover(soup: BeautifulSoup) -> str:
    picture = soup.find("meta", attrs={"property": "og:image"})
    address = picture.get("content", "") if picture is not None else ""
    return "" if NOCOVER in address else address


def parse_card(page: str, source_id: str) -> SourceCard:
    """Карточка игры.

    Описание берётся из тела страницы, а не из микроразметки: в `description`
    там лежит огрызок «Dune, Год выхода: 1992», а настоящий текст — несколько
    тысяч знаков по-русски — стоит отдельным блоком."""
    soup = _soup(page)
    scope = soup.select_one(GAME_SCOPE)
    if scope is None:
        raise ValueError(f"на странице {source_id} нет разметки карточки игры")

    title = _text(scope.select_one('[itemprop="name"]'))
    if not title:
        raise ValueError(f"у карточки {source_id} нет названия")
    title, original_title = by_language(
        [title, *(_text(one) for one in scope.select(ALT_NAMES))])

    genre = _text(scope.select_one('[itemprop="applicationSubCategory"]'))
    return SourceCard(
        item=Item(
            id=0,
            kind=Kind.GAME,
            source=Source.OLD_GAMES,
            source_id=source_id,
            title=title,
            synced_at=datetime.now(),
            original_title=original_title,
            year=year_in_text(_labelled(scope, "Год выхода")),
            synopsis=_synopsis(soup),
            poster_url=_cover(soup),
        ),
        genre_ext_ids=((GenreSource.OLD_GAMES, genre),) if genre else (),
        companies=_companies(scope),
    )
