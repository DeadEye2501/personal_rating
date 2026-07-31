"""Перевод значений границы в то, что переживёт `json.dumps` без своего
кодировщика: его у pywebview нет."""

import json
from datetime import date, datetime, timedelta

import pytest

from backend.model import (
    CardView,
    ExternalRating,
    Genre,
    GenreKind,
    Kind,
    Missing,
    Rating,
    RatingSource,
    Reason,
    Refusal,
    Source,
    Tag,
)
from bridge.wire import outcome, to_wire


def test_a_moment_travels_as_iso_with_a_t():
    """Именно ISO, а не `str(datetime)`: тот даёт пробел вместо «T», и разбор
    на стороне страницы молча получает `Invalid Date`."""
    assert to_wire(datetime(2026, 7, 31, 14, 5, 6)) == "2026-07-31T14:05:06"


def test_a_date_travels_as_iso():
    assert to_wire(date(2014, 11, 5)) == "2014-11-05"


def test_a_delay_travels_as_seconds():
    """`Refusal.retry_after` приезжает при каждом отказе источника.

    Сутки проверяются отдельно: срок приходит числом от чужого сервера, а у
    `timedelta` есть поле `seconds`, которое дни отбрасывает — на суточном
    отказе оно ответило бы «ноль секунд»."""
    assert to_wire(timedelta(minutes=2, seconds=30)) == 150.0
    assert to_wire(timedelta(days=1)) == 86400.0


def test_a_dataclass_travels_as_a_dictionary():
    assert to_wire(Tag(id=3, name="пересмотреть")) == {"id": 3,
                                                       "name": "пересмотреть"}


def test_an_enum_travels_as_a_plain_string():
    assert to_wire(Kind.SERIES) == "series"
    assert type(to_wire(Kind.SERIES)) is str


def test_a_tuple_travels_as_an_array():
    genres = (Genre(id=1, name="Драма", kind=GenreKind.FILM),)
    assert to_wire(genres) == [{"id": 1, "name": "Драма", "kind": "film"}]


def test_the_whole_card_survives_json():
    """Основной тип ленты и самый глубокий: три уровня, шесть кортежей
    датаклассов, `datetime` внутри вложенного."""
    view = CardView(
        kind=Kind.MOVIE,
        source=Source.TMDB,
        source_id="157336",
        title="Интерстеллар",
        item_id=4,
        synced_at=datetime(2026, 7, 31, 12, 0),
        genres=(Genre(id=1, name="Драма", kind=GenreKind.FILM),),
        tags=(Tag(id=2, name="пересмотреть"),),
        external=(ExternalRating(source=RatingSource.IMDB, value=8.7,
                                 fetched_at=datetime(2026, 7, 30, 9, 0)),),
        rating=Rating(item_id=4, score=9.0),
    )

    back = json.loads(json.dumps(to_wire(view), allow_nan=False))

    assert back["title"] == "Интерстеллар"
    assert back["synced_at"] == "2026-07-31T12:00:00"
    assert back["external"][0]["fetched_at"] == "2026-07-30T09:00:00"
    assert back["rating"]["score"] == 9.0
    assert back["genres"][0]["kind"] == "film"


def test_a_dictionary_travels_with_string_keys_and_translated_values():
    """Через эту ветвь пойдёт каждый ответ источника: `outcome` отдаёт словарь,
    а ключ в JSON строкой быть обязан."""
    assert to_wire({1: datetime(2026, 7, 31, 12, 0)}) == {
        "1": "2026-07-31T12:00:00"}


def test_not_a_number_becomes_nothing():
    """`json.dumps` печатает `NaN`, а `JSON.parse` его не принимает — упало бы
    разбором всего ответа, а не одного поля."""
    assert to_wire(float("nan")) is None
    assert to_wire(float("inf")) is None


def test_bytes_are_refused():
    """Байты через мост не ходят вовсе: результат вклеивается в текст скрипта.
    Обложка едет своей ручкой, и молчаливого запасного пути у неё нет."""
    with pytest.raises(TypeError, match="байты"):
        to_wire(b"\x89PNG")


def test_an_unknown_type_is_refused():
    """Отказ громкий, а не `default=str`: подставленная строка вместо объекта
    доедет до страницы и сломается там, где искать её будет некому."""
    with pytest.raises(TypeError):
        to_wire(object())


def test_missing_is_told_apart_from_anything_empty():
    """После разбора `Missing` — это `{}`. Метку приклеивает мост: различать
    исходы по набору ключей нельзя, пустое неотличимо от пустого."""
    assert outcome(Missing()) == {"outcome": "missing"}


def test_a_refusal_carries_its_reason():
    refusal = Refusal(source="tmdb", reason=Reason.QUOTA,
                      retry_after=timedelta(seconds=60), detail="квота")
    assert outcome(refusal) == {
        "outcome": "refusal",
        "refusal": {"source": "tmdb", "reason": "quota",
                    "retry_after": 60.0, "detail": "квота"},
    }


def test_a_value_is_wrapped_the_same_way():
    """Форма ответа одна на все три исхода: ветка на стороне страницы одна."""
    assert outcome(7) == {"outcome": "found", "value": 7}


def test_a_refusal_travels_whole():
    """Отказ источника приезжает на плашку целиком, вместе со сроком: он
    единственный тип границы, у которого поле — `timedelta`."""
    refusal = Refusal(source="tmdb", reason=Reason.QUOTA,
                      retry_after=timedelta(seconds=60), detail="квота")

    assert to_wire(refusal) == {"source": "tmdb", "reason": "quota",
                                "retry_after": 60.0, "detail": "квота"}
