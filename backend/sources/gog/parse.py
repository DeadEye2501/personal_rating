"""Перевод ответов GOG в наши типы."""

from datetime import datetime

from backend.model import (
    GenreSource,
    Item,
    Kind,
    RatingSource,
    SearchHit,
    Source,
    SourceCard,
)
from backend.sources.convert import companies, genres, rating, year
from backend.unique import unique


# Одно и то же у GOG пишется по-разному в жанрах и в тегах, а метка в
# справочнике одна. Приводится здесь, а не там: сочетание `action` + `rpg` иначе
# не сработало бы на игре, у которой ролевая приехала жанром `role-playing`.
#
# Строк пять, а не восемь: у спеки в таблице написаний есть ещё `real-time`,
# `sci-fi` и `turn-based`, но ни одного из этих слагов справочник не знает ни в
# каком написании — приводить их не для кого.
SPELLING = {
    "point-and-click": "pointandclick",
    "team-sport": "teamsport",
    "virtual-life": "virtuallife",
    # Опечатка самого GOG в жанре, проверено живьём.
    "roguelike": "rougelike",
    "role-playing": "rpg",
}


def _marks(row: dict) -> tuple[tuple[GenreSource, str], ...]:
    """Жанры и теги приезжают одним ответом и сливаются в одно пространство:
    решение пользователя 02.08.2026 — «смешиваем их в один список, попутно
    убирая дубликаты».

    Сопоставляем по слагу, а не по названию: название GOG переводит, слаг нет."""
    marked = genres(GenreSource.GOG, row.get("genres", []), key="slug") + genres(
        GenreSource.GOG, row.get("tags", []), key="slug"
    )
    return tuple(unique(
        (space, SPELLING.get(slug, slug)) for space, slug in marked
    ))


def parse_catalog(payload: dict) -> list[SourceCard]:
    """У GOG поиск и карточка — один запрос: отдельный детальный не нужен."""
    now = datetime.now()
    return [
        SourceCard(
            item=Item(
                id=0,
                kind=Kind.GAME,
                source=Source.GOG,
                source_id=str(row["id"]),
                # Локализованы у GOG только жанры: название английское.
                title=row.get("title") or "",
                synced_at=now,
                year=year(row.get("releaseDate")),
                poster_url=row.get("coverVertical") or "",
            ),
            genre_ext_ids=_marks(row),
            companies=companies(row),
            # Оценка игроков лежит в `reviewsRating`; `ratings` у GOG — это
            # возрастные рейтинги, PEGI и ESRB, и оценкой игры они не являются.
            ratings=rating(RatingSource.GOG, row.get("reviewsRating"), now),
        )
        for row in payload.get("products", [])
    ]


def to_hit(card: SourceCard) -> SearchHit:
    """Наружу поиск отдаёт кандидатов, как TMDB и Steam."""
    return SearchHit(
        kind=card.item.kind,
        source=card.item.source,
        source_id=card.item.source_id,
        title=card.item.title,
        year=card.item.year,
        poster_url=card.item.poster_url,
        genre_ext_ids=card.genre_ext_ids,
        source_rating=card.ratings[0].value if card.ratings else None,
    )


def find_slug(payload: dict, slug: str) -> str | None:
    """Совпадение строгое. Поиск GOG никогда не отвечает «не найдено»: на
    заведомую бессмыслицу приходит 200 и два десятка несвязанных игр. Брать
    похожее по названию значит молча привязать не ту игру."""
    for row in payload.get("products") or []:
        if row.get("slug") == slug:
            return str(row["id"])
    return None


def title_of(payload: dict) -> str:
    """Название товара строкой — им спрашивают каталог, когда на руках только
    номер.

    Пустое и `null` считаются неразобранным ответом, а не названием: пустой
    запрос каталог понимает буквально и отдаёт весь каталог, шесть с лишним
    тысяч наименований, из которых нужного может и не оказаться на первой
    странице."""
    title = payload["title"]
    if not isinstance(title, str) or not title:
        raise ValueError(f"название товара не строка: {title!r}")
    return title
