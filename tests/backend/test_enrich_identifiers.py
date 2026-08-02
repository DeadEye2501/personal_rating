"""Чем спрашивают агрегаторов и что запоминают из их ответа.

Отделено от проверок самих оценок, когда те упёрлись в предел файла: предмет тут
другой — идентификатор карточки, а не значение и его срок годности."""

from backend.model import (
    ExternalId,
    ExternalRating,
    Found,
    IdSource,
    Kind,
    Ratings,
    RatingSource,
)
from backend.storage.repository.external import ExternalIdsRepository
from backend.storage.repository.library import LibraryRepository
from tests.backend.enriching import FakeRatings, found, stored_ratings
from tests.conftest import MOMENT, an_item


async def test_the_identifier_is_taken_by_source_and_not_by_order(sessions,
                                                                  item_id,
                                                                  enrich):
    """Агрегаторы спрашивают по IMDb, и достать его надо по источнику, а не
    первым попавшимся.

    У карточки идентификаторов бывает несколько: Кинопоиск кладёт свой, и у
    карточки, известной ему и не известной IMDb, порядок строк решал бы, чей
    номер уедет в запрос. Наблюдается это только на карточке с двумя
    идентификаторами — в остальных проверках он один, и там перепутать нечего.

    Второй идентификатор от GOG, а не от Кинопоиска, и это не вкус: `ids_of`
    отдаёт строки `ORDER BY source`, `imdb` стоит раньше `kinopoisk` — и «взять
    первую строку», ровно та ошибка, ради которой проверка написана, дала бы тот
    же ответ. `gog` идёт раньше `imdb`, и подмена становится видна.

    Вторым заходом — карточка, у которой IMDb нет вовсе: спрашивать агрегаторов
    нечем, и чужой номер вместо своего наблюдается по тому, что запроса не было
    вовсе."""
    ids = ExternalIdsRepository(sessions)
    await ids.put(item_id, ExternalId(IdSource.GOG, "1207658930"))
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6)))

    await enrich(client).enrich(item_id, Kind.MOVIE)

    assert [one[0] for one in client.asked] == ["tt0816692"]

    only_foreign = await LibraryRepository(sessions).create(
        an_item("258687", "Только у Кинопоиска")
    )
    await ids.put(only_foreign, ExternalId(IdSource.KINOPOISK, "258687"))
    other = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6)))

    await enrich(other).enrich(only_foreign, Kind.MOVIE)

    assert other.asked == [], "спросили агрегатора чужим номером"


async def test_without_an_imdb_id_nobody_is_asked(sessions, enrich):
    """`imdb_id` есть только в детальном ответе — без него спрашивать нечем."""
    item_id = await LibraryRepository(sessions).create(
        an_item("1", "Без идентификатора")
    )
    client = FakeRatings((RatingSource.IMDB,), found((RatingSource.IMDB, 8.6)))

    await enrich(client).enrich(item_id, Kind.MOVIE)

    assert client.asked == []


async def test_a_found_identifier_is_kept(sessions, item_id, enrich):
    """Кинопоиск заодно сообщает свой id — дальше по нему ходить дешевле."""
    answer = Found(Ratings(
        values=(ExternalRating(RatingSource.KINOPOISK, 8.6, MOMENT),),
        external_ids=(ExternalId(IdSource.KINOPOISK, "258687"),),
    ))
    service = enrich(FakeRatings((RatingSource.KINOPOISK,), answer))

    await service.enrich(item_id, Kind.MOVIE)

    stored = await ExternalIdsRepository(sessions).ids_of(item_id)
    assert (IdSource.KINOPOISK, "258687") in [(e.source, e.value) for e in stored]


async def test_an_identifier_taken_by_another_card_is_logged_not_raised(
    sessions, item_id, enrich, caplog
):
    other_id = await LibraryRepository(sessions).create(
        an_item("27205", "Начало")
    )
    await ExternalIdsRepository(sessions).put(
        other_id, ExternalId(IdSource.KINOPOISK, "258687")
    )
    answer = Found(Ratings(
        values=(ExternalRating(RatingSource.KINOPOISK, 8.6, MOMENT),),
        external_ids=(ExternalId(IdSource.KINOPOISK, "258687"),),
    ))
    service = enrich(FakeRatings((RatingSource.KINOPOISK,), answer))

    with caplog.at_level("WARNING"):
        await service.enrich(item_id, Kind.MOVIE)

    assert "258687" in caplog.text
    # Оценка при этом записана: занятый чужой идентификатор её не отменяет.
    assert await stored_ratings(sessions, item_id) == {RatingSource.KINOPOISK: 8.6}
