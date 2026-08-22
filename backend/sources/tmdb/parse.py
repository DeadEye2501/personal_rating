"""Перевод ответов TMDB в наши типы."""

from datetime import date, datetime

from backend.model import (
    Credit,
    ExternalRating,
    GenreSource,
    IdSource,
    Item,
    Kind,
    PersonHit,
    PersonRole,
    RatingSource,
    SearchHit,
    SeriesCounts,
    Source,
    SourceCard,
)
from backend.sources.convert import genres, identifier, rating, year
from backend.unique import unique_by

POSTER_BASE = "https://image.tmdb.org/t/p/w500"


class Incomplete(ValueError):
    """Источник ответил 200, но обещанного блока в ответе нет.

    Опечатка в `append_to_response` ошибки не даёт: приходит 200 и просто без
    блока. Поэтому полнота проверяется по содержимому, а не по коду.

    Наследник `ValueError`, а не `Exception`: неполное тело — это то же
    «ответил непонятно чем», и попадать оно должно в общий перечень
    `BROKEN_BY_PARSING`, а не во вторую ветку рядом с ним."""


def _released(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _poster(payload: dict) -> str:
    path = payload.get("poster_path")
    return f"{POSTER_BASE}{path}" if path else ""


def _genres(payload: dict) -> tuple[tuple[GenreSource, str], ...]:
    return genres(GenreSource.TMDB, payload.get("genres", []))


# Шкала оценки TMDB у нас стобалльная — решено пользователем 02.08.2026. Своё
# `vote_average` приезжает десятибалльным, а MDBList отдаёт ту же оценку сразу
# сотней; не приведи одно к другому — и в ленте рядом встанут «TMDB 8.4» и
# «TMDB 84», означающие одно и то же.
def _hundred(value: float | None) -> float | None:
    return None if value is None else value * 10


def _own_rating(payload: dict, now: datetime) -> tuple[ExternalRating, ...]:
    return rating(RatingSource.TMDB, _hundred(payload.get("vote_average")), now)


def _person(row: dict, role: PersonRole, position: int | None = None) -> Credit:
    """Идентификатор человека приезжает в том же ответе, что и состав. Без
    него два разных актёра-тёзки склеились бы в одну строку молча."""
    return Credit(
        name=row["name"],
        role=role,
        position=position,
        source=Source.TMDB,
        source_id=str(row["id"]),
    )


def _cast(rows: list[dict]) -> list[Credit]:
    return [
        _person(row, PersonRole.ACTOR, row.get("order", index))
        for index, row in enumerate(rows)
    ]


def _required(payload: dict, block: str) -> dict:
    """Блок, без которого карточку записывать нельзя.

    Проверяется наличие, а не непустота: у документалки состав пуст
    по-настоящему, и такая карточка обязана сохраниться."""
    found = payload.get(block)
    if found is None or "cast" not in found:
        raise Incomplete(f"в ответе TMDB нет {block}.cast")
    return found


_DIRECTOR = "Director"

# Чья это работа — решают те же роли, из-за которых человек попадает в состав
# карточки: ролей у нас три, и продюсера среди них нет вовсе. `Creator` — это
# шоураннер: замерено, что он совпадает с `created_by`, откуда его берёт
# `parse_series`. Режиссёр сериала в карточку не пишется, но сериал, который он
# снял, — его работа, и из выдачи по нему она не пропадает.
_CREDITED_JOBS = {
    Kind.MOVIE: (_DIRECTOR,),
    Kind.SERIES: (_DIRECTOR, "Creator"),
}

# Чем TMDB помечает камео «играет самого себя». Английские и в русской выдаче:
# локализация `character` не переводит — замерено 22.08.2026 на четырёх людях,
# `Self` встретился 172 раза, `Self (archive footage)` — 36, `Himself` — 4.
# Сравнивается начало строки: за пометкой идёт уточнение — `Self - Host`,
# `Self - Narrator (voice)`, `Self (archive footage)`.
_PLAYS_HIMSELF = ("self", "himself", "herself")


# У фильма название в title, у сериала — в name; поле даты тоже разное. Знание
# одно, и запись у него одна: отсюда ключи берут все три разборщика.
_KEYS = {
    Kind.MOVIE: ("title", "original_title", "release_date"),
    Kind.SERIES: ("name", "original_name", "first_air_date"),
}


def _item(payload: dict, kind: Kind, now: datetime, **extra) -> Item:
    """Девять полей, общих у фильма и сериала.

    Различаются они тремя ключами и тем, что дописывает вызывающий:
    длительностью у фильма, сезонами с сериями у сериала."""
    title_key, original_key, date_key = _KEYS[kind]
    return Item(
        id=0,
        kind=kind,
        source=Source.TMDB,
        source_id=str(payload["id"]),
        title=payload.get(title_key) or "",
        synced_at=now,
        original_title=payload.get(original_key) or "",
        year=year(payload.get(date_key)),
        released_at=_released(payload.get(date_key)),
        synopsis=payload.get("overview") or "",
        poster_url=_poster(payload),
        **extra,
    )


def parse_search(payload: dict, kind: Kind) -> list[SearchHit]:
    return _hits(payload.get("results", []), kind)


def parse_credits(payload: dict, kind: Kind) -> list[SearchHit]:
    """Фильмография человека. Разбираются оба списка: у режиссёра работы лежат
    в `crew`, у актёра — в `cast`, и у многих есть и то и другое.

    Из `crew` берутся не все строки: там лежит вся съёмочная группа, и работа,
    которую человек спродюсировал, снял оператором или где его лишь поблагодарили
    в титрах, — не его. Замерено 05.08.2026: по Нолану так приезжает тринадцать
    чужих фильмов из шестидесяти трёх, по Питту — шестьдесят шесть из ста
    семидесяти семи.

    Из `cast` — тоже не все: камео «играет самого себя» это не работа человека,
    а разговор о нём — документалки, телешоу, дорожки с архивной хроникой.
    Замерено 22.08.2026: у Нолана таких строк тридцать две из тридцати трёх, у
    Шварценеггера 104 из 171, у Тарантино 68 из 104. Решение пользователя того
    же дня; до него `cast` не фильтровался вовсе.

    Одна работа приезжает дважды, если человек на ней в двух ролях. Повторы
    снимаются по идентификатору работы, а не сравнением кандидатов целиком:
    целиком они совпадают лишь пока разбор не читает ничего ролевого — ни
    `character`, ни `order`, — и дедупликация ломалась бы от добавления любого
    из этих полей. `job` и `character` читаются здесь, до сборки, и в кандидата
    не попадают."""
    played = [row for row in payload.get("cast", [])
              if not _himself(row.get("character"))]
    made = [row for row in payload.get("crew", [])
            if row.get("job") in _CREDITED_JOBS[kind]]
    return unique_by(_hits([*played, *made], kind), lambda one: one.source_id)


def _himself(character: str | None) -> bool:
    return (character or "").strip().lower().startswith(_PLAYS_HIMSELF)


def parse_people(payload: dict) -> list[PersonHit]:
    """Найденные приезжают все — это и есть ответ на поиск по имени. Поиск у
    TMDB нечёткий, и близкие написания в ответе — тоже ответ."""
    return [PersonHit(source_id=str(row["id"]))
            for row in payload.get("results", [])]


def _hits(rows: list[dict], kind: Kind) -> list[SearchHit]:
    """Общее у выдачи поиска и у фильмографии: замерено, что строка там и там
    одна и та же — те же названия, дата, постер, жанры и оценка."""
    title_key, original_key, date_key = _KEYS[kind]

    hits = []
    for row in rows:
        hits.append(
            SearchHit(
                kind=kind,
                source=Source.TMDB,
                source_id=str(row["id"]),
                title=row.get(title_key) or "",
                original_title=row.get(original_key) or "",
                year=year(row.get(date_key)),
                synopsis=row.get("overview") or "",
                poster_url=_poster(row),
                genre_ext_ids=tuple(
                    (GenreSource.TMDB, str(genre_id))
                    for genre_id in row.get("genre_ids", [])
                ),
                source_rating=_hundred(row.get("vote_average") or None),
            )
        )
    return hits


def parse_movie(payload: dict) -> SourceCard:
    credits_block = _required(payload, "credits")
    people = _cast(credits_block["cast"])
    people += [
        _person(row, PersonRole.DIRECTOR)
        for row in credits_block.get("crew", [])
        if row.get("job") == _DIRECTOR
    ]

    now = datetime.now()
    return SourceCard(
        item=_item(payload, Kind.MOVIE, now,
                   runtime=payload.get("runtime") or None),
        genre_ext_ids=_genres(payload),
        people=tuple(people),
        external_ids=identifier(IdSource.IMDB, payload.get("imdb_id")),
        ratings=_own_rating(payload, now),
    )


def parse_series_counts(payload: dict) -> SeriesCounts:
    """Оба числа лежат в ответе /tv/{id} без единого довеска.

    Считать сезоны по длине seasons[] нельзя: нулевой сезон — спецматериалы, и у
    «Andor» вышло бы три вместо двух."""
    return SeriesCounts(seasons=payload.get("number_of_seasons"),
                        episodes=payload.get("number_of_episodes"))


def parse_series(payload: dict) -> SourceCard:
    people = _cast(_required(payload, "aggregate_credits")["cast"])
    people += [
        _person(row, PersonRole.SHOWRUNNER) for row in payload.get("created_by", [])
    ]

    counts = parse_series_counts(payload)
    now = datetime.now()
    return SourceCard(
        item=_item(payload, Kind.SERIES, now,
                   seasons_count=counts.seasons,
                   episodes_count=counts.episodes),
        genre_ext_ids=_genres(payload),
        people=tuple(people),
        # У сериала на верхнем уровне `imdb_id` нет вовсе — он в довеске.
        external_ids=identifier(
            IdSource.IMDB, (payload.get("external_ids") or {}).get("imdb_id")),
        ratings=_own_rating(payload, now),
    )

