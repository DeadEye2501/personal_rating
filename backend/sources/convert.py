"""Куски чужого ответа, которые все источники переводят одинаково."""

from datetime import datetime

from backend.model import (
    CompanyRole,
    Credit,
    ExternalId,
    ExternalRating,
    GenreSource,
    IdSource,
    RatingSource,
    Source,
)


def identifier(source: IdSource, value) -> tuple[ExternalId, ...]:
    """Один чужой идентификатор или ни одного.

    Отбрасывается по `is None`, а не по ложности: у Кинопоиска номер приезжает
    числом, и ноль идентификатором не бывает — а вот пустая строка от TMDB
    означает ровно «не дал», поэтому её здесь тоже нет.

    Число приводится к строке: в базе колонка текстовая, и два пути записи
    разошлись бы типом."""
    if value is None or value == "":
        return ()
    return (ExternalId(source=source, value=str(value)),)


def genres(
    space: GenreSource, rows: list[dict], key: str = "id"
) -> tuple[tuple[GenreSource, str], ...]:
    """Метки в детальном ответе — объекты с именем, а идентификатор лежит
    внутри. Имя нам не нужно: наш жанр выводят правила справочника, и смотрят
    они на идентификатор. У GOG он слаг, а не число, отсюда `key`.

    Приведением метки к тому написанию, которое знает справочник, эта функция не
    занимается — оно своё у каждого источника и живёт в его разборе."""
    return tuple((space, str(row[key])) for row in rows)


def year(value: str | None) -> int | None:
    """Год из даты, которая с него начинается: `2014-11-05` у TMDB,
    `2023.08.03` у GOG. У необъявленного к выходу дата приходит пустой."""
    head = (value or "")[:4]
    return int(head) if head.isdigit() else None


def companies(payload: dict) -> tuple[Credit, ...]:
    """Магазины отдают студии голыми строками: идентичности у них нет, и
    выдумывать суррогат незачем — таких склеивают по имени."""
    return tuple(
        Credit(name=name, role=role)
        for role, key in (
            (CompanyRole.DEVELOPER, "developers"),
            (CompanyRole.PUBLISHER, "publishers"),
        )
        for name in payload.get(key, [])
    )


# У кого оценка приезжает даром вместе с выдачей поиска. У Steam в поиске оценки
# нет вовсе, поэтому его тут и нет. Знание об источниках, поэтому лежит здесь:
# седьмой источник добавляется новой папкой и этой таблицей, а не типом границы.
FREE_IN_SEARCH = {
    Source.TMDB: RatingSource.TMDB,
    Source.GOG: RatingSource.GOG,
}


def from_search(source: Source, value: float | None,
                now: datetime) -> tuple[ExternalRating, ...]:
    """Оценка кандидата выдачи — или ни одной, если этот источник её не даёт."""
    own = FREE_IN_SEARCH.get(source)
    return () if own is None else rating(own, value, now)


def rating(
    source: RatingSource, value: float | int | None, now: datetime
) -> tuple[ExternalRating, ...]:
    """Одна оценка или ни одной.

    Ноль считается отсутствием: у TMDB `vote_average` равен нулю, пока фильм не
    оценил никто, и записать его значило бы объявить, что фильм оценили в ноль."""
    if not value:
        return ()
    return (ExternalRating(source=source, value=float(value), fetched_at=now),)
