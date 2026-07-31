"""Мост: карточка целиком — заведение, правка, отвязка, удаление."""

from backend.model import Kind, Source
from bridge.library import Library


def test_a_manual_card_is_built_by_the_bridge(spy, asked):
    """Страница присылает поля формы, а не `Item`: собрать датакласс обратно из
    JSON нечем, а `new_manual_item` уже умеет и источник, и свой идентификатор,
    и момент создания."""
    answers, log = asked
    answers["library.create"] = 12

    assert Library(spy).create({"kind": "movie", "title": "Одиссея",
                                "year": 1997}) == {"ok": 12}

    name, args, _ = log[0]
    assert name == "library.create"
    item = args[0]
    assert item.source is Source.MANUAL
    assert item.source_id
    assert item.kind is Kind.MOVIE
    assert item.title == "Одиссея"
    assert item.year == 1997


def test_an_empty_field_does_not_reach_the_backend(spy, asked):
    """Незаполненное в форме — это «не знаю», а не «пусто»: обязательно только
    название.

    Наблюдается на `synopsis`, а не на `year`, нарочно: у года умолчание и так
    `None`, и на нём тест зеленел бы даже без отбора. У строковых полей
    умолчание — пустая строка, и незаполненное поле формы прописало бы туда
    `None`."""
    answers, log = asked
    answers["library.create"] = 12

    Library(spy).create({"kind": "movie", "title": "Одиссея",
                         "synopsis": None})

    _, args, _ = log[0]
    assert args[0].synopsis == ""


def test_a_broken_field_answers_instead_of_raising(spy, asked):
    """Разбор полей формы идёт внутри заявки, а не до неё. Снаружи оболочки
    исключение пересекло бы границу потоков и ушло в pywebview, где ловить его
    некому, — а мост обещает, что наружу летит только ответ."""
    answers, _ = asked
    answers["library.create"] = 12

    answer = Library(spy).create({"kind": "movie", "title": "Одиссея",
                                  "released_at": "не дата"})

    assert answer["fail"] == "broken"


def test_a_release_date_arrives_as_a_date(spy, asked):
    """Через JSON дата едет строкой, а `Item.released_at` — это `date`."""
    answers, log = asked
    answers["library.create"] = 12

    Library(spy).create({"kind": "movie", "title": "Одиссея",
                         "released_at": "1997-05-18"})

    _, args, _ = log[0]
    assert args[0].released_at.year == 1997


def test_editing_names_the_card_and_keeps_the_fields(spy, asked):
    """Правка идёт по номеру строки, а поля собираются тем же путём, что у
    заведения."""
    answers, log = asked
    answers["library.replace_fields"] = None

    Library(spy).replace(12, {"kind": "movie", "title": "Одиссея"})

    name, args, _ = log[0]
    assert name == "library.replace_fields"
    assert args[0] == 12
    assert args[1].title == "Одиссея"


def test_unlinking_names_the_card(spy, asked):
    answers, log = asked
    answers["library.unlink"] = None

    Library(spy).unlink(12)

    assert log[0] == ("library.unlink", (12,), {})


def test_the_same_title_check_stays_inside_one_kind(spy, asked):
    """Фильм «Ведьмак» и игра «Ведьмак» — не дубли."""
    answers, log = asked
    answers["library.find_by_title"] = []

    Library(spy).same_title("movie", "Одиссея")

    name, args, _ = log[0]
    assert name == "library.find_by_title"
    # Тождеством, а не равенством: тип содержимого — строковое перечисление,
    # и `==` пропустило бы сырую строку, а живой отбор различает его `is`.
    assert args[0] is Kind.MOVIE
    assert args[1] == "Одиссея"


def test_deletion_goes_through_the_backend_method(spy, asked):
    """`library.delete` обходит порядок двух файлов базы: обложка обязана
    уходить первой, иначе `id` SQLite выдаст повторно и следующая карточка
    получит чужую обложку."""
    answers, log = asked
    answers["delete_card"] = None

    assert Library(spy).delete(12) == {"ok": None}
    assert [name for name, _, _ in log] == ["delete_card"]


def test_the_summary_travels_as_a_flat_dictionary(spy, asked):
    answers, log = asked
    answers["library.deletion_summary"] = {"tags": 2, "has_rating": True}

    assert Library(spy).deletion_summary(12) == {"ok": {"tags": 2,
                                                        "has_rating": True}}
    assert log[0] == ("library.deletion_summary", (12,), {})
