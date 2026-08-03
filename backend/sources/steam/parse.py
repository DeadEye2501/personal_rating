"""Перевод ответов Steam в наши типы."""

from dataclasses import replace
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
from backend.sources.convert import companies, genres, rating, year_in_text

ASSETS = "https://shared.akamai.steamstatic.com/store_item_assets/"

# Род товара числом: `0` игра, `4` дополнение, `6` инструмент, `12` playtest.
# `appdetails` его не различает вовсе — у REDkit там `type: 'game'`, то есть по
# карточке инструмент от игры не отличить.
TYPE_GAME = 0

# Ответ про товар, а не отговорка. Число, а не флаг: `15` истинно.
ANSWERED = 1

# Жанр магазина и его тег нумеруются порознь и сталкиваются числами: жанр `9` —
# это «Гонки», а тег `9` — «Стратегия». В справочнике пространство одно, и жанр
# приводится к номеру тега-двойника здесь: дальше происхождение метки неизвестно,
# и общей таблицей написаний это уже не починить — она превратила бы тег `9` в
# «Гонки» у каждой стратегии.
#
# Жанр без двойника отбрасывается: жанр несут ровно эти восемь из двенадцати,
# остальные четыре — «Инди», «Казуальные», «Ранний доступ» и «Бесплатно».
GENRE_TWIN = {
    "1": "19",  # Action
    "2": "9",  # Strategy
    "3": "122",  # RPG
    "9": "699",  # Racing
    "18": "701",  # Sports
    "25": "21",  # Adventure
    "28": "599",  # Simulation
    "29": "128",  # Massively Multiplayer
}


def poster_url(appid: str) -> str:
    """Запасной адрес вертикальной обложки: настоящее имя файла приезжает в
    `assets`, а без него остаётся угаданное. Оно верно в 62% случаев — лучше,
    чем обложки нет вовсе.

    Вариант без `_2x` отдаёт 300×450, вдвое меньше своего имени."""
    return f"{ASSETS}steam/apps/{appid}/library_600x900_2x.jpg"


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


def _store_items(payload: dict) -> list[dict]:
    """Строки ответа `GetItems`.

    Без `store_items` Steam отвечает на пустой `ids` — это наш промах, а не
    «ничего не нашлось», и молча принять его за пустоту нельзя ни одному из двух
    потребителей: у карточки так пропали бы теги, у выдачи — отсев."""
    items = (payload.get("response") or {}).get("store_items")
    if not items:
        raise ValueError("ответ без store_items")
    return items


def _poster(row: dict, appid: str) -> str:
    """Настоящее имя файла обложки лежит в `assets`, и одним шаблоном его формы
    не покрываются: голое `library_600x900_2x.jpg`, `portrait.png`,
    `<хеш>/library_capsule_2x.jpg` и локализованное
    `<хеш>/library_600x900_russian_2x.jpg`. Замерено, что угаданный адрес не
    отвечает у 38% строк.

    `library_capsule_2x` есть не у всех: у «Arcanum» только одинарный
    `portrait.png`. Двойной предпочитается ему, а не наоборот, — одинарный
    вдвое меньше."""
    assets = row.get("assets") or {}
    name = assets.get("library_capsule_2x") or assets.get("library_capsule")
    template = assets.get("asset_url_format")
    if not name or not template:
        return poster_url(appid)
    return ASSETS + template.replace("${FILENAME}", name)


def _answered(payload: dict) -> dict[str, dict]:
    """Строки ответа по appid, о котором они, — и только те, что о товаре.

    Отговорку от ответа отличает `success`, а не наличие полей. Замерено
    03.08.2026: на живой «Ведьмак 3» при `country_code: RU` приезжает
    `success: 15`, `visible: false` и **`type` отсутствует вовсе**. Считать это
    «род не игра» значит выбросить из выдачи настоящую игру — а при неверном
    контексте сразу все, потому что так Steam отвечает про каждую."""
    return {str(row["appid"]): row for row in _store_items(payload)
            if row.get("success") == ANSWERED}


def sifted(hits: list[SearchHit], payload: dict) -> list[SearchHit]:
    """Выдача, из которой убрано всё, что магазин назвал не игрой, и с
    настоящим адресом обложки. И то, и другое — из одного ответа `GetItems`.

    Строка, про которую Steam не ответил, остаётся. Убирается только то, про что
    он ответил прямо, — отсюда и `TYPE_GAME` умолчанием: ответ без рода товара
    это молчание о роде, а не «род не игра», и обойтись с ним надо так же.
    Потерять настоящую игру хуже, чем показать лишнее дополнение."""
    known = _answered(payload)
    kept = []
    for hit in hits:
        row = known.get(hit.source_id)
        if row is None:
            kept.append(hit)
        elif row.get("type", TYPE_GAME) == TYPE_GAME:
            kept.append(replace(hit, poster_url=_poster(row, hit.source_id)))
    return kept


def cover_of(payload: dict, appid: str) -> str:
    """Настоящий адрес обложки одной игры — для карточки, а не для выдачи.

    Пустая строка значит «Steam про неё не ответил»: подставлять сюда угаданный
    адрес нельзя, он у карточки уже стоит, и разобрать, откуда он взялся, было
    бы негде."""
    row = _answered(payload).get(appid)
    return _poster(row, appid) if row else ""


def _genres(data: dict) -> tuple[tuple[GenreSource, str], ...]:
    """Жанры карточки — номерами тегов-двойников: пространство меток у Steam
    одно на весь справочник."""
    marked = genres(GenreSource.STEAM, data.get("genres", []))
    return tuple((space, GENRE_TWIN[ext_id]) for space, ext_id in marked
                 if ext_id in GENRE_TWIN)


def _metascore(data: dict, now: datetime) -> tuple[ExternalRating, ...]:
    """Metascore принадлежит Metacritic, а не Steam: у Valve с ними лицензия."""
    return rating(
        RatingSource.METACRITIC, (data.get("metacritic") or {}).get("score"), now
    )


def parse_card(data: dict) -> SourceCard:
    """Принимает блок `data` уже сверенного ответа, а не весь ответ: у карточки
    ответ приходит словарём, и сверка ключа с запрошенным appid стоит клиенту
    одного обращения — залезать в тело незачем.

    У тегов сверка живёт в разборе, и это не разнобой: там ответ приходит
    списком, и достать из него номер можно только зная форму `store_items[0]`."""
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
            year=year_in_text((data.get("release_date") or {}).get("date")),
        ),
        genre_ext_ids=_genres(data),
        companies=companies(data),
        ratings=_metascore(data, now),
    )


def parse_tags(payload: dict, appid: str) -> tuple[tuple[GenreSource, str], ...]:
    """Теги игры из отдельного ответа. Приезжают номерами с весами; вес нам не
    нужен — нужен сам номер.

    Ответов у ручки три, и два из них — наш промах, а не «тегов нет»: без
    `store_items` Steam отвечает на пустой `ids`, а `success` не единицей — на
    несуществующую игру **и на существующую при неверном `country_code`**.
    Промахом, а не отсутствием: теги спрашивают после того, как карточка уже
    приехала, то есть игра заведомо есть.

    Карточку это не меняет — `_tags` ловит исключение и отдаёт пустой набор, как
    и прежде, — меняется наблюдаемость. Правил у Steam в справочнике 219, и без
    тегов сработать могут девять: своих жанров у магазина двенадцать на весь
    каталог, и жанр несут восемь. Обеднённая игра ложится в базу навсегда —
    перезапроса у игр не бывает вовсе, только удалить и завести заново, — и без
    записи в лог такая карточка выглядит исправной.

    `success` тут число, а не флаг: `15` истинно, и проверка на истинность
    посчитала бы несуществующую игру найденной. Отсюда и `ANSWERED` именем, а не
    единицей по месту."""
    item = _store_items(payload)[0]
    if item.get("success") != ANSWERED:
        raise ValueError(f"ответ на теги под success {item.get('success')}")
    # Запрос уходит списком, и ответ на список — тоже список: без сверки в жанры
    # игры уехали бы теги соседней. Сверка здесь, а не в клиенте, как у карточки:
    # форму `store_items[0]` знает только разбор, и клиенту пришлось бы залезть
    # в неё второй раз.
    #
    # Числами, а не строками: в запрос уходит `int(appid)`, и сравнение строк
    # разошлось бы на ведущем нуле.
    if item.get("appid") != int(appid):
        raise ValueError(f"теги не про {appid}, а про {item.get('appid')}")

    return genres(GenreSource.STEAM, item.get("tags", []), key="tagid")
