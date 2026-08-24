"""Отбор ленты фильтрами: включённые, исключённые и их сочетания.

Отдельно от `test_sections.py`: тот про то, что раздел показывает и в каком
порядке, а этот — про то, чем набор сужают. Общего у них ровно запрос, и он
проверяется порознь: сортировка от фильтра не зависит вовсе."""

from dataclasses import replace

import pytest

from backend.model import Filters, Kind
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.tags import TagsRepository
from backend.storage.repository.wishlist import WishlistRepository
from tests.conftest import ACTION, ADVENTURE, DRAMA, MOMENT, RATED, WANTED, an_item


@pytest.fixture
async def library(sessions):
    return LibraryRepository(sessions)


async def test_a_tag_filter_narrows_the_section(sessions, library, sections):
    ratings = RatingsRepository(sessions)
    tags = TagsRepository(sessions)
    tagged_id = await library.create(an_item("1", "С меткой", year=2014))
    other_id = await library.create(an_item("2", "Без метки", year=2010))
    for item_id in (tagged_id, other_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(tagged_id, tag_id)

    found = await sections.ids(
        replace(RATED, filters=Filters(tag_ids=(tag_id,))), limit=50, offset=0
    )

    assert found == [tagged_id]


async def test_two_tags_are_joined_by_and(sessions, library, sections):
    """Решение пользователя 02.08.2026: каждая добавленная метка сужает набор,
    а не расширяет его. Раньше здесь было «или», и вторая метка приводила
    карточки, которых с первой не было."""
    ratings = RatingsRepository(sessions)
    tags = TagsRepository(sessions)
    both_id = await library.create(an_item("1", "С обеими", year=2014))
    one_id = await library.create(an_item("2", "С одной", year=2010))
    for item_id in (both_id, one_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    first_tag = await tags.create(Kind.MOVIE, "пересмотреть")
    second_tag = await tags.create(Kind.MOVIE, "с женой")
    stranger = await tags.create(Kind.MOVIE, "не выбирали")
    await tags.assign(both_id, first_tag)
    await tags.assign(both_id, second_tag)
    # Меток у второй карточки тоже две, и вторая не выбрана: со счётом без
    # отбора по выбранным «две любых» и «две эти» неразличимы, и фильтр по паре
    # тегов привёл бы карточку с двумя чужими.
    await tags.assign(one_id, first_tag)
    await tags.assign(one_id, stranger)

    found = await sections.ids(
        replace(RATED, filters=Filters(tag_ids=(first_tag, second_tag))),
        limit=50, offset=0,
    )

    assert found == [both_id]


async def test_a_genre_filter_narrows_the_section(sessions, reference, library,
                                                  sections):
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    drama_id = await library.create(an_item("1", "Драма", year=2014))
    other_id = await library.create(an_item("2", "Не драма", year=2010))
    for item_id in (drama_id, other_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    genre_ids = [DRAMA]
    await genres.set_for_item(drama_id, genre_ids)

    found = await sections.ids(
        replace(RATED, filters=Filters(genre_ids=tuple(genre_ids))),
        limit=50, offset=0,
    )

    assert found == [drama_id]


async def test_two_genres_are_joined_by_and(sessions, reference, library,
                                            sections):
    """Жанры сужают так же, как метки: выбрал боевик и приключения — получил то,
    что и то и другое разом.

    У одной карточки оба жанра, у другой только боевик: первая обязана пройти,
    вторая — нет."""
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    both_id = await library.create(an_item("1", "Боевик и приключения"))
    one_id = await library.create(an_item("2", "Только боевик"))
    for item_id in (both_id, one_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    pair = [ACTION, ADVENTURE]
    await genres.set_for_item(both_id, pair)
    await genres.set_for_item(
        one_id, [ACTION])

    found = await sections.ids(
        replace(RATED, filters=Filters(genre_ids=tuple(pair))),
        limit=50, offset=0,
    )

    assert found == [both_id]


async def test_a_tag_and_a_genre_are_joined_by_and(sessions, reference, library,
                                                   sections):
    """И между признаками, и внутри признака — «и»."""
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    tags = TagsRepository(sessions)
    both_id = await library.create(an_item("1", "И то и то", year=2014))
    only_tag_id = await library.create(an_item("2", "Только метка", year=2010))
    for item_id in (both_id, only_tag_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)

    genre_ids = [DRAMA]
    await genres.set_for_item(both_id, genre_ids)
    tag_id = await tags.create(Kind.MOVIE, "пересмотреть")
    await tags.assign(both_id, tag_id)
    await tags.assign(only_tag_id, tag_id)

    found = await sections.ids(
        replace(RATED, filters=Filters(tag_ids=(tag_id,),
                                       genre_ids=tuple(genre_ids))),
        limit=50, offset=0,
    )

    assert found == [both_id]


async def test_a_score_filter_takes_whole_columns(sessions, library, sections):
    """Фильтр по оценке говорит теми же столбцами, что и гистограмма, а те —
    теми же ступенями, что и карточка: 7.66 у игры — это столбец 8. Проба выше
    половины нарочно: на 7.33 округление вниз дало бы ту же семёрку."""
    ratings = RatingsRepository(sessions)
    eight_id = await library.create(an_item("1", "Восьмёрка", year=2014))
    nine_id = await library.create(an_item("2", "Девятка", year=2010))
    await ratings.set_score(eight_id, 7.66, now=MOMENT)
    await ratings.set_score(nine_id, 9.0, now=MOMENT)

    found = await sections.ids(
        replace(RATED, filters=Filters(scores=(8,))), limit=50, offset=0
    )

    assert found == [eight_id]


async def test_two_scores_stay_joined_by_or(sessions, library, sections):
    """Оценка — единственный признак, где «или» остаётся, и не по решению, а по
    устройству: она у карточки одна, и «семь и восемь разом» не бывает ни у
    чего. Переведи её на «и» — лента опустеет при любом выборе."""
    ratings = RatingsRepository(sessions)
    seven_id = await library.create(an_item("1", "Семёрка"))
    eight_id = await library.create(an_item("2", "Восьмёрка"))
    nine_id = await library.create(an_item("3", "Девятка"))
    for item_id, score in ((seven_id, 7.0), (eight_id, 8.0), (nine_id, 9.0)):
        await ratings.set_score(item_id, score, now=MOMENT)

    found = await sections.ids(
        replace(RATED, filters=Filters(scores=(7, 8))), limit=50, offset=0
    )

    assert sorted(found) == sorted([seven_id, eight_id])


async def test_an_excluded_tag_wins_over_an_included_genre(
    sessions, reference, library, sections
):
    """Исключённое вычитается последним и сильнее включённого: выбрал драму,
    исключил метку — карточка с обеими не покажется."""
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    tags = TagsRepository(sessions)

    both_id = await library.create(an_item("1", "И драма, и метка", year=2014))
    only_genre_id = await library.create(an_item("2", "Только драма", year=2010))
    for item_id in (both_id, only_genre_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
        await genres.set_for_item(item_id, [DRAMA])

    tag_id = await tags.create(Kind.MOVIE, "не хочу видеть")
    await tags.assign(both_id, tag_id)

    genre_ids = [DRAMA]
    found = await sections.ids(
        replace(RATED, filters=Filters(genre_ids=tuple(genre_ids),
                                       excluded_tag_ids=(tag_id,))),
        limit=50, offset=0,
    )

    assert found == [only_genre_id]


async def test_an_excluded_genre_removes_the_card(
    sessions, reference, library, sections
):
    ratings = RatingsRepository(sessions)
    genres = GenresRepository(sessions)
    drama_id = await library.create(an_item("1", "Драма", year=2014))
    plain_id = await library.create(an_item("2", "Без жанра", year=2010))
    for item_id in (drama_id, plain_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)

    genre_ids = [DRAMA]
    await genres.set_for_item(drama_id, genre_ids)

    found = await sections.ids(
        replace(RATED, filters=Filters(excluded_genre_ids=tuple(genre_ids))),
        limit=50, offset=0,
    )

    assert found == [plain_id]


async def test_two_excluded_mean_neither_of_them(sessions, library, sections):
    """Исключение осталось «ни одного из этих», а не «не все сразу»: карточка с
    одной из двух исключённых меток тоже уходит. На одной метке это неотличимо
    от включения, и подмена прошла бы молча."""
    ratings = RatingsRepository(sessions)
    tags = TagsRepository(sessions)
    one_id = await library.create(an_item("1", "С одной из"))
    clean_id = await library.create(an_item("2", "Ни с одной"))
    for item_id in (one_id, clean_id):
        await ratings.set_score(item_id, 8.0, now=MOMENT)
    first_tag = await tags.create(Kind.MOVIE, "скучное")
    second_tag = await tags.create(Kind.MOVIE, "не досмотрел")
    await tags.assign(one_id, first_tag)

    found = await sections.ids(
        replace(RATED,
                filters=Filters(excluded_tag_ids=(first_tag, second_tag))),
        limit=50, offset=0,
    )

    assert found == [clean_id]


async def test_an_excluded_score_removes_the_column(sessions, library, sections):
    """Оценка дробная, как у игры: исключается столбец, а не число. С ровной
    семёркой округление в этой ветке можно было бы потерять незаметно, а с
    оценкой ниже половины — потерять его направление."""
    ratings = RatingsRepository(sessions)
    eight_id = await library.create(an_item("1", "Восьмёрка", year=2014))
    nine_id = await library.create(an_item("2", "Девятка", year=2010))
    await ratings.set_score(eight_id, 7.66, now=MOMENT)
    await ratings.set_score(nine_id, 9.0, now=MOMENT)

    found = await sections.ids(
        replace(RATED, filters=Filters(excluded_scores=(8,))),
        limit=50, offset=0,
    )

    assert found == [nine_id]


async def test_an_excluded_score_does_not_empty_the_wishlist(
    sessions, library, sections
):
    """У отложенного, но не оценённого, score пуст, а `NULL NOT IN (7)` в SQL
    — это NULL, а не истина. Без защиты от NULL исключение по оценке выносит из
    раздела «Хочу посмотреть» вообще всё, и молча."""
    item_id = await library.create(an_item("1", "Отложенный", year=2014))
    await WishlistRepository(sessions).add(item_id, now=MOMENT)

    found = await sections.ids(
        replace(WANTED, filters=Filters(excluded_scores=(7,))),
        limit=50, offset=0,
    )

    assert found == [item_id]


async def test_nothing_included_changes_nothing(sessions, library, sections):
    """Пустой фильтр не должен превращаться в `IN ()`: такое условие в SQL ложно
    для всех строк, и лента опустела бы. Охраняют это `if` в `_included`.

    С исключениями наоборот, и потому они здесь не проверяются: `NOT IN ()`
    истинно для всех строк, так что снятие охраняющих `if` в `_excluded`
    наблюдаемого поведения не меняет вовсе."""
    ratings = RatingsRepository(sessions)
    item_id = await library.create(an_item("1", "Оценённый", year=2014))
    await ratings.set_score(item_id, 8.0, now=MOMENT)

    found = await sections.ids(RATED, limit=50, offset=0)

    assert found == [item_id]


async def test_a_scale_filter_takes_that_scale_alone(sessions, library, sections):
    """Отбор по шкале игры смотрит на саму шкалу, а не на выведенную из трёх
    общую. У обеих игр среднее ровно три, и общей оценкой они неразличимы:
    подмена шкалы на `score` прошла бы молча на любой другой паре."""
    ratings = RatingsRepository(sessions)
    fun_id = await library.create(an_item("1", "Играется", kind=Kind.GAME))
    pretty_id = await library.create(an_item("2", "Смотрится", kind=Kind.GAME))
    await ratings.set_aspects(fun_id, visual=2, narrative=2, gameplay=5,
                              now=MOMENT)
    await ratings.set_aspects(pretty_id, visual=5, narrative=2, gameplay=2,
                              now=MOMENT)

    found = await sections.ids(
        replace(RATED, kind=Kind.GAME, filters=Filters(gameplay=(5,))),
        limit=50, offset=0,
    )

    assert found == [fun_id]


async def test_two_steps_of_one_scale_stay_joined_by_or(sessions, library,
                                                        sections):
    """Внутри шкалы «или» по той же причине, что и у общей оценки: она у
    карточки одна, и «четыре и пять разом» не бывает ни у чего. Переведи её на
    «и» — лента опустеет при любом выборе двух ступеней."""
    ratings = RatingsRepository(sessions)
    four_id = await library.create(an_item("1", "Четвёрка", kind=Kind.GAME))
    five_id = await library.create(an_item("2", "Пятёрка", kind=Kind.GAME))
    three_id = await library.create(an_item("3", "Тройка", kind=Kind.GAME))
    for item_id, gameplay in ((four_id, 4), (five_id, 5), (three_id, 3)):
        await ratings.set_aspects(item_id, visual=3, narrative=3,
                                  gameplay=gameplay, now=MOMENT)

    found = await sections.ids(
        replace(RATED, kind=Kind.GAME, filters=Filters(gameplay=(4, 5))),
        limit=50, offset=0,
    )

    assert sorted(found) == sorted([four_id, five_id])


async def test_two_scales_are_joined_by_and(sessions, library, sections):
    """Между шкалами «и», как между любыми двумя признаками: «геймплей и
    нарратив равны 4 или 5» обязано оставить только то, где сошлись обе.

    Вторая игра проходит по нарративу и валится по геймплею, третья наоборот:
    со «или» между шкалами остались бы обе, и отбор по паре шкал расширял бы
    выдачу вместо сужения."""
    ratings = RatingsRepository(sessions)
    both_id = await library.create(an_item("1", "И то и то", kind=Kind.GAME))
    one_id = await library.create(an_item("2", "Только сюжет", kind=Kind.GAME))
    other_id = await library.create(an_item("3", "Только игра", kind=Kind.GAME))
    await ratings.set_aspects(both_id, visual=1, narrative=5, gameplay=4,
                              now=MOMENT)
    await ratings.set_aspects(one_id, visual=1, narrative=5, gameplay=2,
                              now=MOMENT)
    # Третья валится нарративом, а не геймплеем: без неё исход решала бы одна
    # шкала, и снятое условие второй прошло бы молча.
    await ratings.set_aspects(other_id, visual=1, narrative=2, gameplay=5,
                              now=MOMENT)

    found = await sections.ids(
        replace(RATED, kind=Kind.GAME,
                filters=Filters(narrative=(4, 5), gameplay=(4, 5))),
        limit=50, offset=0,
    )

    assert found == [both_id]


async def test_an_unset_scale_is_not_a_value(sessions, library, sections):
    """Невыставленная шкала — никакая, а не низшая и не равная общей оценке. У
    игры без геймплея среднее считается по двум сторонам и равно пяти, так что
    отбор, спутавший шкалу с общей оценкой, привёл бы её на «геймплей 5»."""
    ratings = RatingsRepository(sessions)
    played_id = await library.create(an_item("1", "С геймплеем", kind=Kind.GAME))
    untouched_id = await library.create(an_item("2", "Без", kind=Kind.GAME))
    await ratings.set_aspects(played_id, visual=5, narrative=5, gameplay=5,
                              now=MOMENT)
    await ratings.set_aspects(untouched_id, visual=5, narrative=5,
                              gameplay=None, now=MOMENT)

    found = await sections.ids(
        replace(RATED, kind=Kind.GAME, filters=Filters(gameplay=(5,))),
        limit=50, offset=0,
    )

    assert found == [played_id]


async def test_an_excluded_scale_keeps_the_unset_one(sessions, library,
                                                     sections):
    """`NULL NOT IN (5)` в SQL — это NULL, а не истина: без защиты исключение по
    шкале уносит из раздела все игры, у которых эта шкала не выставлена. А
    выставлять все три никто не обязан — среднее считается по заполненным."""
    ratings = RatingsRepository(sessions)
    played_id = await library.create(an_item("1", "С геймплеем", kind=Kind.GAME))
    untouched_id = await library.create(an_item("2", "Без", kind=Kind.GAME))
    await ratings.set_aspects(played_id, visual=5, narrative=5, gameplay=5,
                              now=MOMENT)
    await ratings.set_aspects(untouched_id, visual=5, narrative=5,
                              gameplay=None, now=MOMENT)

    found = await sections.ids(
        replace(RATED, kind=Kind.GAME, filters=Filters(excluded_gameplay=(5,))),
        limit=50, offset=0,
    )

    assert found == [untouched_id]


async def test_a_scale_filter_narrows_the_histogram_too(sessions, library,
                                                        sections):
    """Гистограмма и лента считают по одному набору, и шкала тут не исключение:
    отобрал по геймплею — увидел распределение общих оценок отобранного.
    Разойдись они, подвал говорил бы об одном наборе, а лента показывала другой."""
    ratings = RatingsRepository(sessions)
    fun_id = await library.create(an_item("1", "Играется", kind=Kind.GAME))
    dull_id = await library.create(an_item("2", "Не играется", kind=Kind.GAME))
    await ratings.set_aspects(fun_id, visual=6, narrative=6, gameplay=6,
                              now=MOMENT)
    await ratings.set_aspects(dull_id, visual=9, narrative=9, gameplay=1,
                              now=MOMENT)

    picture = await sections.histogram(Kind.GAME, Filters(gameplay=(6,)))

    assert picture.total == 1
    assert picture.average == 6.0


async def _one_high_each(library, ratings) -> dict[str, int]:
    """Три игры, у каждой высока ровно одна шкала. Средние у всех трёх равны,
    поэтому общей оценкой они неразличимы: отбор, спутавший колонку с соседней
    или с общей оценкой, на них обязан разойтись."""
    made = {}
    for number, (name, sides) in enumerate(
        (("visual", (5, 1, 1)), ("narrative", (1, 5, 1)),
         ("gameplay", (1, 1, 5))), start=1,
    ):
        item_id = await library.create(
            an_item(str(number), f"Сильна шкала {name}", kind=Kind.GAME))
        await ratings.set_aspects(item_id, *sides, now=MOMENT)
        made[name] = item_id
    return made


async def test_every_scale_filters_by_its_own_column(sessions, library,
                                                     sections):
    """Каждая колонка отбирает своей шкалой, а не соседней. Проверяются все три:
    с одной наблюдалась бы только она, и выпавшая из прохода шкала становилась
    бы мёртвым переключателем при зелёном наборе."""
    made = await _one_high_each(library, RatingsRepository(sessions))

    for name, item_id in made.items():
        found = await sections.ids(
            replace(RATED, kind=Kind.GAME, filters=Filters(**{name: (5,)})),
            limit=50, offset=0,
        )

        assert found == [item_id], name


async def test_every_scale_excludes_by_its_own_column(sessions, library,
                                                      sections):
    """Исключение ходит теми же колонками, что и включение, и тоже всеми тремя:
    вторая половина признака объявляется отдельным полем, и выпасть из прохода
    она может сама по себе."""
    made = await _one_high_each(library, RatingsRepository(sessions))

    for name, item_id in made.items():
        found = await sections.ids(
            replace(RATED, kind=Kind.GAME,
                    filters=Filters(**{f"excluded_{name}": (5,)})),
            limit=50, offset=0,
        )

        assert sorted(found) == sorted(set(made.values()) - {item_id}), name


async def test_a_scale_and_the_whole_score_narrow_together(sessions, library,
                                                           sections):
    """Единственное сочетание, где два условия считаются по-разному: общая
    оценка идёт ступенью с округлением, шкала — числом как есть.

    У обеих игр ступень общей оценки восьмая, и у первой она взялась
    округлением. Разъедься счёт — отбор либо потерял бы первую, либо оставил
    вторую, у которой геймплей шестой."""
    ratings = RatingsRepository(sessions)
    rounded_id = await library.create(an_item("1", "Округлилась", kind=Kind.GAME))
    dull_id = await library.create(an_item("2", "Скучная", kind=Kind.GAME))
    await ratings.set_aspects(rounded_id, visual=7, narrative=8, gameplay=8,
                              now=MOMENT)
    await ratings.set_aspects(dull_id, visual=9, narrative=9, gameplay=6,
                              now=MOMENT)

    found = await sections.ids(
        replace(RATED, kind=Kind.GAME,
                filters=Filters(scores=(8,), gameplay=(8,))),
        limit=50, offset=0,
    )

    assert found == [rounded_id]
