"""Мост: свои отметки — оценки, теги, закладки.

Момент везде зажат между двумя замерами вокруг вызова, а не проверен на
`year >= 2026`: тот прошёл бы и для литерала `datetime(2026, 1, 1)`, то есть не
отличил бы взятое время от записанного руками."""

from datetime import datetime

from backend.model import Kind, TagExists
from bridge.marks import Marks


def test_setting_a_score_carries_the_moment(spy, asked):
    """Часы внутри бэкенда не берутся — это его правило. Страница о них не
    знает, момент подставляет мост."""
    answers, log = asked
    answers["ratings.set_score"] = None

    before = datetime.now()
    Marks(spy).score(12, 9.0)
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "ratings.set_score"
    assert args[:2] == (12, 9.0)
    assert before <= args[2] <= after


def test_aspects_go_to_their_own_scales(spy, asked):
    """Три шкалы у игры разные, и перепутанные местами дают другую карточку —
    а сумма и среднее у них те же. Набор доводов этого не различает, привязка
    различает."""
    answers, log = asked
    answers["ratings.set_aspects"] = 7.0

    before = datetime.now()
    Marks(spy).aspects(12, visual=9, narrative=8, gameplay=4)
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "ratings.set_aspects"
    assert args[0] == 12
    assert args[1:4] == (9, 8, 4)
    assert before <= args[4] <= after


def test_aspects_answer_with_the_derived_score(spy, asked):
    """У игр оценка — среднее трёх шкал, и считает его база: карточке надо
    показать новое число сразу, не перечитывая её целиком."""
    answers, _ = asked
    answers["ratings.set_aspects"] = 7.333333333333333

    assert Marks(spy).aspects(12, 8, 7, 7) == {"ok": 7.333333333333333}


def test_clearing_a_rating_keeps_the_card(spy, asked):
    answers, log = asked
    answers["ratings.clear"] = None

    Marks(spy).clear_rating(12)

    assert [name for name, _, _ in log] == ["ratings.clear"]


def test_a_review_goes_to_the_right_card_with_a_moment(spy, asked):
    answers, log = asked
    answers["ratings.set_review"] = None

    before = datetime.now()
    Marks(spy).review(12, "пересмотрел, всё ещё держит")
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "ratings.set_review"
    assert args[:2] == (12, "пересмотрел, всё ещё держит")
    assert before <= args[2] <= after


def test_tags_come_for_the_asked_kind(spy, asked):
    """Наборы тегов у трёх типов независимы."""
    answers, log = asked
    answers["tags.list_for_kind"] = []

    Marks(spy).tags("game")

    name, args, _ = log[0]
    assert name == "tags.list_for_kind"
    assert args[0] is Kind.GAME


def test_reordering_survives_as_the_page_sent_it(spy, asked):
    """Ручной порядок обязан пережить перезапуск — за это отвечает `position`, а
    мост обязан не переставить список по дороге."""
    answers, log = asked
    answers["tags.reorder"] = None

    Marks(spy).reorder_tags("movie", [5, 2, 9])

    name, args, _ = log[0]
    assert name == "tags.reorder"
    assert args[0] is Kind.MOVIE
    assert args[1] == [5, 2, 9]


def test_a_new_tag_belongs_to_one_kind(spy, asked):
    """Наборы тегов у трёх типов независимы, и заведённый не тому типу тег
    оказался бы невидим там, где его завели."""
    answers, log = asked
    answers["tags.create"] = 7

    assert Marks(spy).create_tag("series", "пересмотреть") == {"ok": 7}

    name, args, _ = log[0]
    assert name == "tags.create"
    assert args == (Kind.SERIES, "пересмотреть")


def test_a_taken_tag_name_is_a_kind_of_failure(spy, asked):
    """Переименовал в занятое — нормальный ход событий, а не сбой."""
    answers, _ = asked
    answers["tags.rename"] = TagExists("драма")

    assert Marks(spy).rename_tag(3, "драма")["fail"] == "tag-exists"


def test_the_number_of_carriers_is_asked_before_deleting(spy, asked):
    """У тега с носителями удаление подтверждают, называя их число; ничей тег
    уходит молча."""
    answers, log = asked
    answers["tags.usage"] = 3

    assert Marks(spy).tag_usage(3) == {"ok": 3}

    name, args, _ = log[0]
    assert name == "tags.usage"
    assert args == (3,)


def test_deleting_a_tag_names_the_tag_not_the_card(spy, asked):
    """У удаления тега и снятия тега с карточки доводы разного рода, и
    перепутать их — значит стереть тег у всей библиотеки вместо одной строки."""
    answers, log = asked
    answers["tags.delete"] = None

    Marks(spy).delete_tag(3)

    name, args, _ = log[0]
    assert name == "tags.delete"
    assert args == (3,)


def test_assigning_names_the_card_first_then_the_tag(spy, asked):
    """Оба довода — числа, и переставленные местами они молча пройдут до базы.
    Порядок и есть то, что тут сторожится."""
    answers, log = asked
    answers["tags.assign"] = None

    Marks(spy).assign(12, 3)

    name, args, _ = log[0]
    assert name == "tags.assign"
    assert args == (12, 3)


def test_unassigning_goes_the_same_way_round(spy, asked):
    answers, log = asked
    answers["tags.unassign"] = None

    Marks(spy).unassign(12, 3)

    name, args, _ = log[0]
    assert name == "tags.unassign"
    assert args == (12, 3)


def test_wishing_carries_the_moment(spy, asked):
    """Порядок по умолчанию в «Хочу посмотреть» — по дате добавления, и берётся
    она отсюда."""
    answers, log = asked
    answers["wishlist.add"] = None

    before = datetime.now()
    Marks(spy).wish(12)
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "wishlist.add"
    assert args[0] == 12
    assert before <= args[1] <= after


def test_unwishing_needs_no_moment(spy, asked):
    """Снятие закладки момента не требует: строка уходит целиком."""
    answers, log = asked
    answers["wishlist.remove"] = None

    Marks(spy).unwish(12)

    assert log[0] == ("wishlist.remove", (12,), {})
