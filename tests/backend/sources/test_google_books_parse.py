"""Разбор ответов Google Books: строка выдачи, карточка тома, жанры и обложка.

Отдельным модулем от разговора по сети: там ключи, квота и занятость, здесь
чистый разбор записанных тел. Разошлись они по этому шву, когда файл перевалил
предел в пятьсот строк.
"""

from backend.model import (
    CompanyRole,
    GenreSource,
    IdSource,
    Kind,
    PersonRole,
    Source,
)
from backend.sources.google_books.parse import (
    parse_by_author,
    parse_card,
    parse_search,
)


def test_the_search_gives_a_row_for_every_volume(fixture):
    """Строк ровно столько, сколько томов в `items`: обрезанная выдача выглядела
    бы как бедный каталог, а не как поломка разбора."""
    payload = fixture("google_books/search_dune.json")

    hits = parse_search(payload)

    assert len(hits) == len(payload["items"])
    assert len(hits) > 1, "фикстура с одной строкой ничего не сторожит"


def test_a_search_row_carries_what_the_volume_shows(fixture):
    """Название, номер тома и год — из строки выдачи. Тип и источник ставит
    разбор: перепутай их, и книга уехала бы в чужую вкладку."""
    hits = parse_search(fixture("google_books/search_dune.json"))

    first = hits[0]
    assert (first.kind, first.source) == (Kind.BOOK, Source.GOOGLE_BOOKS)
    assert first.source_id == "4kbYExSCa6oC"
    assert first.title == "The Science of Dune"
    assert first.year == 2007


def test_a_volume_without_a_cover_still_becomes_a_row():
    """Обложки нет у части книг, и строка без неё обязана остаться в выдаче —
    иначе кусок каталога исчезает молча."""
    without = {"items": [{"id": "x", "volumeInfo": {"title": "Без обложки"}}]}

    assert parse_search(without)[0].poster_url == ""


def test_a_row_takes_the_only_level_the_search_gives(fixture):
    """Выдача обрезает путь BISAC до верхушки — замерено: у «Задачи трёх тел»
    там `Fiction`, а полный путь отдаёт только карточка. Верхний уровень
    справочник знает (`Fiction` — это `Проза`), и терять его незачем: без метки
    строка выдачи стоит без жанра вовсе."""
    hits = parse_search(fixture("google_books/search_dune.json"))

    first = hits[0]
    assert first.genre_ext_ids == ((GenreSource.GOOGLE_BOOKS, "Social Science"),)


def test_the_genre_comes_from_the_second_level_of_the_path(fixture):
    """Спека требует второй уровень BISAC: первый — `Fiction` — покрывает треть
    всех книг, третий дробен до `Space Exploration`. Наблюдается меткой,
    уехавшей в `genre_ext_ids`, а не разбором строки: справочник сверяет
    именно её."""
    card = parse_card(fixture("google_books/volume_three_body.json"))

    assert (GenreSource.GOOGLE_BOOKS, "Science Fiction") in card.genre_ext_ids
    assert (GenreSource.GOOGLE_BOOKS, "Fiction") not in card.genre_ext_ids


def test_four_paths_of_one_book_give_one_genre(fixture):
    """У «Задачи трёх тел» четыре пути BISAC, и второй уровень у всех четырёх
    один и тот же. Не сними повтор — и книга получит четыре одинаковых жанра:
    в карточке они встанут в ряд четырьмя одинаковыми метками."""
    payload = fixture("google_books/volume_three_body.json")

    card = parse_card(payload)

    assert len(payload["volumeInfo"]["categories"]) == 4
    assert card.genre_ext_ids == ((GenreSource.GOOGLE_BOOKS, "Science Fiction"),)


def test_a_general_second_level_falls_back_to_the_first():
    """`Fiction / General` — это «художественная, и больше Google не сказал».
    Второй уровень тут пустышка, и жанром обязан стать первый."""
    payload = {"id": "x",
               "volumeInfo": {"title": "Т", "categories": ["Fiction / General"]}}

    assert parse_card(payload).genre_ext_ids == (
        (GenreSource.GOOGLE_BOOKS, "Fiction"),)


def test_a_volume_without_categories_gets_no_genre(fixture):
    """У части книг `categories` нет вовсе — замерено, у `Sapiens`. Пустая
    метка уехала бы в справочник и не совпала бы ни с одним правилом, зато
    заняла бы строку в базе."""
    card = parse_card(fixture("google_books/volume_no_cover.json"))

    assert card.genre_ext_ids == ()


def test_the_author_is_a_person_and_the_publisher_is_a_company(fixture):
    """Роли не должны разъехаться: автор идёт туда же, где режиссёр, а
    издательство — туда, где студия. Перепутанные местами роли — тот самый
    дефект, который однажды прошёл шесть мутаций молча."""
    card = parse_card(fixture("google_books/volume_three_body.json"))

    assert [one.name for one in card.people] == ["Лю Цысинь"]
    assert [one.role for one in card.people] == [PersonRole.AUTHOR]
    assert [one.name for one in card.companies] == ["Эксмо"]
    assert [one.role for one in card.companies] == [CompanyRole.PUBLISHER]


def test_an_author_comes_without_any_identity(fixture):
    """У Google `authors` — голые строки, идентичности автора нет вовсе.
    Выдуманный суррогат склеил бы двух разных Ивановых в одну строку навсегда:
    таких склеивают по имени, как студии магазинов."""
    card = parse_card(fixture("google_books/volume_three_body.json"))

    assert card.people[0].source is None
    assert card.people[0].source_id is None


def test_a_volume_without_authors_still_becomes_a_card(fixture):
    """У сборников и трудов конференций автора нет — замерено. Карточка обязана
    собраться: иначе такая книга не заводится вовсе, а издательство у неё есть."""
    card = parse_card(fixture("google_books/volume_no_author.json"))

    assert card.people == ()
    assert card.companies


def test_the_rating_never_reaches_the_card(fixture):
    """Замер: оценка есть у четырёх томов из двенадцати, и у всех четырёх от
    одного до четырёх голосов при значениях 5, 5, 5 и 4. Рядом с «IMDb 8.4»
    такая пятёрка читалась бы как мнение публики и врала бы."""
    payload = fixture("google_books/volume_three_body.json")

    assert payload["volumeInfo"]["averageRating"], "фикстура без оценки не сторожит"
    assert parse_card(payload).ratings == ()


def test_a_card_carries_the_title_year_and_synopsis(fixture):
    """Три поля, ради которых карточка и запрашивается вторым запросом: в
    выдаче года и синопсиса может не быть вовсе, а в базу они уезжают
    навсегда."""
    card = parse_card(fixture("google_books/volume_three_body.json"))

    assert card.item.kind is Kind.BOOK
    assert card.item.source_id == "-u8-DwAAQBAJ"
    assert card.item.title == "Задача трех тел"
    assert card.item.year == 2017
    assert "Они придут" in card.item.synopsis


def test_the_synopsis_comes_without_markup(fixture):
    """Замерено: у «Задачи трёх тел» описание приходит абзацами HTML — весь
    текст обёрнут в `<p>`. Страница показывает синопсис текстом и экранирует
    его, так что теги приехали бы человеку дословно и уехали бы в базу
    навсегда: перезапрос карточки идёт раз в месяц."""
    payload = fixture("google_books/volume_three_body.json")

    card = parse_card(payload)

    assert "<p>" in payload["volumeInfo"]["description"], "фикстура без разметки"
    assert "<" not in card.item.synopsis
    assert card.item.synopsis.startswith("Они придут")


def test_a_category_of_nothing_but_separators_becomes_no_mark():
    """Путь BISAC из одних разделителей жанра не даёт. Пропусти его — и в
    справочник уехала бы метка без имени, то есть жанр, которого у источника не
    существует; в карточке он встал бы пустой строкой."""
    payload = {"id": "1", "volumeInfo": {
        "title": "Дюна",
        "categories": ["/ /", "Fiction / Science Fiction / Hard Science Fiction"]}}

    assert parse_card(payload).genre_ext_ids == (
        (GenreSource.GOOGLE_BOOKS, "Science Fiction"),)


def test_the_cover_of_a_publisher_volume_takes_the_step_nearest_our_size():
    """У издательского тома верна любая ступень — замерено 23.08.2026 на семи
    таких томах, — и берётся ближайшая к нашей мерке 500×750 сверху: `medium`
    575×812. Самая крупная не берётся нарочно: обрезка ужимает до 500×750 и не
    растягивает, так что `extraLarge` 2448×3116 дал бы тот же итог за впятеро
    больший вес."""
    publisher = "http://books.google.com/books/publisher/content?id=1"
    payload = {"id": "1", "volumeInfo": {"title": "Дюна", "imageLinks": {
        "smallThumbnail": f"{publisher}&zoom=5",
        "thumbnail": f"{publisher}&zoom=1",
        "small": f"{publisher}&w=300",
        "medium": f"{publisher}&w=575",
        "large": f"{publisher}&w=800",
        "extraLarge": f"{publisher}&w=1800",
    }}}

    assert parse_card(payload).item.poster_url == f"{publisher}&w=575"


def test_the_cover_of_a_scan_takes_the_thumbnail_and_no_bigger():
    """У сканированного тома крупные ступени бывают полосой страницы: 300×48,
    575×92, 800×128 при пропорции 6.25 — замерено 23.08.2026 на трёх сканах из
    пяти. `thumbnail` при этом обложка у всех до единого, и берётся он.

    Отличает скан сам адрес: `/books/content` против
    `/books/publisher/content` у издательского."""
    scan = "http://books.google.com/books/content?id=1"
    payload = {"id": "1", "volumeInfo": {"title": "Скан", "imageLinks": {
        "thumbnail": f"{scan}&zoom=1",
        "medium": f"{scan}&zoom=3",
        "extraLarge": f"{scan}&zoom=6",
    }}}

    assert parse_card(payload).item.poster_url == f"{scan}&zoom=1"


def test_a_scan_without_a_thumbnail_falls_back_to_the_smallest_step():
    """Запасная ступень у скана — самая мелкая из объявленных, а не последняя в
    лестнице: лестница упорядочена близостью к нашей мерке, и `small` стоит в
    ней после `extraLarge`. Возьми последнюю, и том, у которого объявлены
    только `medium` и `large`, получил бы 800×1129 — ровно ту крупную ступень,
    от которой ветка и защищает.

    Случай краевой: `thumbnail` замерен у всех до единого. Написано так, как
    объяснено в самом разборе — «у скана довольствуемся маленькой»."""
    scan = "http://books.google.com/books/content?id=1"
    links = {"medium": f"{scan}&zoom=3", "large": f"{scan}&zoom=4"}
    volume = {"id": "1", "volumeInfo": {"title": "Скан", "imageLinks": links}}

    assert parse_card(volume).item.poster_url == f"{scan}&zoom=3"

    # Со `small` мельче становится он: без этой половины набор мог бы стоять в
    # любом порядке, лишь бы крупная не была первой.
    links["small"] = f"{scan}&w=300"
    assert parse_card(volume).item.poster_url == f"{scan}&w=300"


def test_the_cover_falls_back_to_what_is_there():
    """Ступеней у тома бывает две: в строке выдачи Google объявляет только
    `thumbnail` и `smallThumbnail`, а у сканированных томов и в карточке нет ни
    одной. Замерено 23.08.2026 на живых данных."""
    thumbnail = {"id": "1", "volumeInfo": {
        "title": "Дюна", "imageLinks": {"thumbnail": "http://g/t?zoom=1"}}}
    without = {"id": "2", "volumeInfo": {"title": "Скан"}}

    hits = parse_search({"items": [thumbnail, without]})

    assert [hit.poster_url for hit in hits] == ["http://g/t?zoom=1", ""]


def test_the_cover_of_a_volume_is_not_rebuilt_by_hand(fixture):
    """Адрес уезжает как есть: у части томов в хвосте стоит токен `imgtk`, без
    которого картинка не отдаётся."""
    payload = fixture("google_books/volume_three_body.json")

    card = parse_card(payload)

    assert card.item.poster_url in payload["volumeInfo"]["imageLinks"].values()
    assert "zoom=3" not in card.item.poster_url


def test_the_works_of_an_author_are_only_those_that_have_him():
    """Ручки людей у Google нет вовсе, и `inauthor:` он понимает как пожелание:
    замерено 23.08.2026 живьём — по `inauthor:"задача трех тел"` приезжают
    «The Three-Body Problem» Валтонена и Марчала, то есть чужие книги под
    видом работ автора.

    Поэтому автор проверяется по ответу: у тома он обязан быть."""
    payload = {"items": [
        {"id": "1", "volumeInfo": {"title": "Дюна",
                                   "authors": ["Фрэнк Герберт"]}},
        {"id": "2", "volumeInfo": {"title": "The Three-Body Problem",
                                   "authors": ["Mauri J. Valtonen"]}},
        {"id": "3", "volumeInfo": {"title": "Новая литература"}},
    ]}

    assert [hit.title for hit in parse_by_author(payload, "Фрэнк Герберт")] \
        == ["Дюна"]


def test_a_namesake_of_the_author_does_not_own_his_book():
    """Часть имени — не любая её часть: совпасть обязано **всё** спрошенное.

    Замерено 23.08.2026: по «Frank Herbert» в двадцати строках приезжает и
    `Brian Herbert` — фамилия та же, человек другой. Хватай клиент пересечение
    вместо вхождения, и к Гербертам ехали бы книги сына, а к «Ивану Иванову» —
    половина каталога."""
    payload = {"items": [
        {"id": "1", "volumeInfo": {"title": "Дюна",
                                   "authors": ["Фрэнк Герберт"]}},
        {"id": "2", "volumeInfo": {"title": "Дом Атрейдесов",
                                   "authors": ["Брайан Герберт"]}},
    ]}

    kept = parse_by_author(payload, "Фрэнк Герберт")

    assert [hit.title for hit in kept] == ["Дюна"]


def test_a_part_of_the_name_is_enough_to_own_the_book():
    """Человек набирает «толкин», а Google пишет его полным именем. Требовать
    совпадения целиком значило бы не находить по фамилии вовсе."""
    payload = {"items": [
        {"id": "1", "volumeInfo": {"title": "Властелин колец",
                                   "authors": ["Джон Рональд Руэл Толкин"]}},
    ]}

    assert [hit.title for hit in parse_by_author(payload, "толкин")] \
        == ["Властелин колец"]


def test_a_string_of_publishers_becomes_several_companies():
    """Google кладёт в `publisher` то одно издательство, то перечень: «ЛитРес,
    АСТ» встречается семь раз на 260 строк живой выдачи. Это два разных
    издательства — решение пользователя 23.08.2026, — и строкой они в базу
    попадать не должны: тогда книга АСТ и книга «ЛитРес, АСТ» лежат под разными
    издателями."""
    payload = {"id": "1", "volumeInfo": {"title": "Дюна",
                                         "publisher": "ЛитРес, АСТ"}}

    names = [one.name for one in parse_card(payload).companies]

    assert names == ["ЛитРес", "АСТ"]


def test_a_publisher_with_a_conjunction_stays_one_company():
    """«Манн, Иванов и Фербер» — одно издательство из трёх фамилий."""
    payload = {"id": "1", "volumeInfo": {
        "title": "Дюна", "publisher": "Манн, Иванов и Фербер"}}

    assert [one.name for one in parse_card(payload).companies] \
        == ["Манн, Иванов и Фербер"]


def test_the_isbn_of_a_volume_travels_with_the_row():
    """ISBN нужен запасному источнику обложек: по нему ищут издание, и им же
    сверяют, что нашлось то самое. Берётся тринадцатизначный, а при его
    отсутствии десятизначный — у Google бывают оба."""
    payload = {"items": [{"id": "1", "volumeInfo": {
        "title": "Пикник на обочине",
        "industryIdentifiers": [{"type": "ISBN_10", "identifier": "5170829833"},
                                {"type": "ISBN_13", "identifier": "9785170829835"}],
    }}]}

    hit = parse_search(payload)[0]

    assert [(one.source, one.value) for one in hit.external_ids] \
        == [(IdSource.ISBN, "9785170829835")]

    # Отступление наблюдается томом, у которого тринадцатизначного нет вовсе:
    # с обоими номерами снятие запасного пути прошло бы молча, а у таких томов
    # обложку искать было бы нечем.
    only_ten = {"items": [{"id": "2", "volumeInfo": {
        "title": "Понедельник начинается в субботу",
        "industryIdentifiers": [{"type": "ISBN_10", "identifier": "5170829833"}],
    }}]}

    assert [one.value for one in parse_search(only_ten)[0].external_ids] \
        == ["5170829833"]


def test_a_volume_without_an_isbn_carries_nothing():
    """У сканов и журналов ISBN нет вовсе — замерено, у восьми томов из десяти
    он есть, у двух нет."""
    payload = {"items": [{"id": "1", "volumeInfo": {"title": "Скан"}}]}

    assert parse_search(payload)[0].external_ids == ()
