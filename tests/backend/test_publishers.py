"""Издательство книги: разбор строки и узнавание написаний.

Числа в проверках — из слепой разметки 23.08.2026: 111 написаний живой выдачи,
судья правил не видел.
"""

import pytest

from backend.model import CompanyRole, Credit, PersonRole
from backend.publishers import alike, named, publisher_key
from backend.storage.entity import COMPANIES, PEOPLE
from backend.storage.repository.credits import CreditRepository


@pytest.mark.parametrize("first, second", [
    ("Издательство АСТ", "АСТ"),
    ("АСТ", "Ast"),
    ("Издательство АСТ", "ACT"),
    ("ЛитРес", "Litres"),
    ("Litres", "LitRes"),
    ("Эксмо", "EKSMO"),
    ("Rosman", "Rosman Publishing"),
    ("Planet", "The Planet"),
    ("Games Workshop", "Games Workshop(uk)"),
    ("Издательство \"Азбука\"", "Азбука"),
    ("Wildside Press LLC", "Wildside"),
])
def test_one_publisher_in_two_spellings(first, second):
    assert publisher_key(first) == publisher_key(second)


@pytest.mark.parametrize("first, second", [
    ("Азбука-Аттикус", "Азбука"),
    ("Альпина Паблишер", "Альпина нон-фикшн"),
    ("Harper", "Harper Perennial"),
    ("Эксмо", "ЛитРес"),
    ("Planeta Publishing", "The Planet"),
])
def test_different_publishers_do_not_meet(first, second):
    """Импринты одной группы — разные издательства со своими каталогами, и
    склеить их значит потерять разницу, которую человек видит на обложке.

    Спрашивается близость, а не ключ: расходящиеся ключи ещё ничего не значат —
    близкими правило признаёт и разные написания, и вся его вторая половина
    (расстояние, костяк согласных) через ключи не видна вовсе."""
    assert not alike(first, second)


def test_a_latin_name_is_not_read_as_russian():
    """Подмена букв-двойников идёт только в слове, где двусмысленна каждая
    буква. Поймано замером: слепая подмена превращала `DirectMEDIA` в
    `direstmedia`, а `Publishing` — в `ruvlisning`."""
    assert publisher_key("DirectMEDIA") == "directmedia"
    assert publisher_key("Perfection Learning") == "perfection learning"


def test_a_string_names_several_publishers():
    """«ЛитРес, АСТ» — два разных издательства, решение пользователя
    23.08.2026."""
    assert named("ЛитРес, АСТ") == ("ЛитРес", "АСТ")
    assert named("ЛитРес, АСТ: CORPUS") == ("ЛитРес", "АСТ", "CORPUS")


def test_a_name_with_a_conjunction_stays_whole():
    """«Манн, Иванов и Фербер» — одно издательство из трёх фамилий."""
    assert named("Манн, Иванов и Фербер") == ("Манн, Иванов и Фербер",)


def test_a_legal_form_is_not_a_publisher():
    """Форма собственности стоит отдельной частью, но издательства не
    называет."""
    assert named("Бизнес-журнал, ЗАО") == ("Бизнес-журнал",)


def test_a_name_of_service_words_alone_names_nobody():
    """«ООО» и «Издательство» — не имена, и заводить под них студию незачем.

    А имя, которого приведение не знает целиком — японское, греческое,
    ивритское, — издательство называет, и вернуть его надо как есть: иначе у
    книги не осталось бы издателя вовсе."""
    assert named("ООО") == ()
    assert named("Издательство") == ()
    assert named("講談社") == ("講談社",)


def test_an_empty_string_names_nobody():
    assert named("") == ()
    assert named("   ") == ()


async def test_two_spellings_of_one_publisher_share_a_row(sessions):
    """Правило стоит на записи: иначе «Издательство АСТ» и «АСТ» заводят две
    студии, и книга одного издательства раскладывается по двум карточкам-родителям.

    Проверяется на студиях, а не на людях: у человека одно написание, а
    издательство приезжает как придётся."""
    studios = CreditRepository(sessions, COMPANIES)
    first = await studios.ensure(Credit(name="Издательство АСТ",
                                        role=CompanyRole.PUBLISHER))
    second = await studios.ensure(Credit(name="Ast", role=CompanyRole.PUBLISHER))

    assert first == second


async def test_a_name_the_rule_cannot_read_still_finds_its_row(sessions):
    """Точное совпадение имени ищется **до** близости, а не вместо неё.

    У приведения есть имена, на которых оно даёт пустой ключ: письменность,
    которой оно не знает («講談社»), и имя из одних служебных слов («Media»). А
    пустой ключ близким не считается никогда — значит без точного поиска каждая
    книга такого издательства заводила бы новую студию, и «講談社» размножилось
    бы по числу книг."""
    studios = CreditRepository(sessions, COMPANIES)

    for name in ("講談社", "Media"):
        first = await studios.ensure(Credit(name=name,
                                            role=CompanyRole.PUBLISHER))
        second = await studios.ensure(Credit(name=name,
                                             role=CompanyRole.PUBLISHER))
        assert first == second, f"{name}: завелось второй строкой"


def test_a_replaced_vowel_at_the_start_is_another_name():
    """Костяк согласных меняет гласную на гласную, и без первой из них
    `Vintage Books` встаёт одной строкой с `Vantage Press` — поймано ревью
    23.08.2026 перебором 107 имён, единственная ложная склейка на 5671 пару.

    Схемы транслитерации расходятся на конце имени, а не на первом слоге:
    `Rosman` и `Rossmen` начинаются одинаково, и их правило по-прежнему
    сводит."""
    assert not alike("Vintage Books", "Vantage Press")
    assert alike("Rosman", "Rossmen"), "своё же правило перестало работать"


async def test_different_publishers_keep_their_rows(sessions):
    """Импринты одной группы — разные издательства: «Азбука-Аттикус» и «Азбука»
    ведут свои каталоги, и склеить их значит потерять разницу."""
    studios = CreditRepository(sessions, COMPANIES)
    first = await studios.ensure(Credit(name="Азбука-Аттикус",
                                        role=CompanyRole.PUBLISHER))
    second = await studios.ensure(Credit(name="Азбука", role=CompanyRole.PUBLISHER))

    assert first != second


async def test_two_people_with_alike_names_are_not_merged(sessions):
    """Приведение издательств людей не касается: у человека имя пишут одним
    способом, а «Иванов, ООО» — не форма собственности, а фамилия."""
    people = CreditRepository(sessions, PEOPLE)
    first = await people.ensure(Credit(name="Rosman", role=PersonRole.ACTOR))
    second = await people.ensure(Credit(name="Rossmen", role=PersonRole.ACTOR))

    assert first != second, "правило издательств добралось до людей"
    assert alike("Rosman", "Rossmen"), "свидетель перестал быть свидетелем"


def test_a_misspelling_of_one_name_is_the_same_publisher():
    """Написания сравниваются расстоянием, а не равенством: «ДиректМедиа» и
    `DirectMEDIA` расходятся одной буквой — латинское `c` против `к`, — и
    равенство ключей их не свело бы."""
    assert alike("ДиректМедиа", "DirectMEDIA")
    assert alike("ООО ДиректМедиа", "DirectMEDIA")


def test_another_scheme_of_transliteration_is_the_same_name():
    """«Росмэн» пишут и `Rosman`, и `Rossmen`: гласная **заменена**, костяк
    согласных тот же. Расстоянием такое не берётся — в шестибуквенном имени две
    правки, — поэтому у близости второй путь: тот же костяк при том же числе
    гласных."""
    assert alike("Rosman Publishing", "Rossmen")


def test_an_added_vowel_makes_another_name():
    """Добавленная гласная — уже другое имя, и число гласных их разводит:
    `Planet` против `Planeta`. Замерено 23.08.2026: без счёта гласных костяк
    склеивал эту пару, а издательства разные."""
    assert not alike("The Planet", "Planeta Publishing")


def test_a_short_name_is_not_recognised_by_its_bones():
    """У короткого имени костяк ничего не значит: «Дом» и «Дым» — тот же костяк
    и то же число гласных, а издательства разные. Правило включается с шести
    букв, ровно с длины `rosman`."""
    assert not alike("Дом", "Дым")
    assert not alike("АСТ", "АСТА")


def test_an_empty_name_is_alike_to_nobody():
    """Пустое приведение — это не имя, и совпадать ему не с чем: иначе строка
    из одних знаков склеилась бы с любой такой же."""
    assert not alike("", "Эксмо")
    assert not alike("!!!", "???")


def test_a_name_in_quotes_is_the_whole_name():
    """Кавычки для того и стоят, чтобы отделить имя от служебных слов вокруг:
    «Издательский дом "Питер"», `Izd-Vo "Mik"`. Замерено 23.08.2026 на
    проверочной выборке — такие написания правило не узнавало."""
    assert alike("Питер", 'Издательский дом "Питер"')
    assert alike("Mik", 'Izd-Vo "Mik"')


def test_a_latin_word_of_lookalikes_is_not_read_as_russian():
    """Подмена букв-двойников бьёт только по короткой аббревиатуре капсом.

    Иначе она ловит настоящие английские слова, целиком сложенные из двойников,
    и коверкает их обратной транслитерацией: `Hachette` становилась `nasnette`,
    `Focus Home` — `focus nome`. Поймано ревью 23.08.2026."""
    assert publisher_key("Hachette") == "hachette"
    assert publisher_key("Focus Home Interactive") == "focus home interactive"
    assert publisher_key("Thomas Cook") == "thomas cook"
    assert publisher_key("Издательство АСТ") == publisher_key("ACT")


def test_a_service_word_in_latin_is_still_stripped():
    """Служебные слова из одних двойников — `Co`, `Pty`, `Book` — прежде
    коверкались подменой и потому не снимались вовсе: `Doubleday & Co`
    расходился с `Doubleday`, `Allen & Unwin Pty Ltd` с `Allen & Unwin`.
    Замерено ревью 23.08.2026 на всех трёх."""
    assert alike("Doubleday & Co", "Doubleday")
    assert alike("Allen & Unwin Pty Ltd", "Allen & Unwin")
    assert alike("Peter Book", "Peter Books")


def test_a_foreign_legal_form_is_a_legal_form_too():
    """Чешская `s.r.o.`, индийская `Pvt Limited`: форма собственности — она и
    в Африке форма, а не часть имени."""
    assert alike("e-artnow", "e-artnow sro")
    assert alike("Manjul Publishing", "Manjul Publishing House Pvt Limited")


def test_a_service_word_is_stripped_in_both_scripts():
    """Порядок в приведении: сперва письменность, потом шелуха. Обратный ловил
    «Издательство АСТ», но пропускал `Izdatel'stvo Ast` — то же слово латиницей.
    Поймано третьей выборкой 23.08.2026."""
    assert alike("Izdatel'stvo Ast", "Издательство АСТ")
    assert alike("Izdatelstvo Eksmo", "ООО Эксмо")


def test_a_name_where_the_service_word_is_its_own():
    """У части имён служебное слово — часть имени: `Penguin Group` это не
    «Penguin», `Signal Books` не «Signal», а `Ardis Publishers` (Анн-Арбор) не
    российский «АРДИС». Все три пары нашла слепая разметка 23.08.2026, и все
    три — разные издательства."""
    assert not alike("Penguin", "Penguin Group")
    assert not alike("Signal", "Signal Books")
    assert not alike("Ardis Publishers", "АРДИС")


def test_the_list_of_exceptions_does_not_touch_the_rest():
    """Исключение защищает названное имя, а не слово вообще: `Vintage Books` и
    `Penguin Books` по-прежнему сходятся со своими короткими написаниями."""
    assert alike("Vintage", "Vintage Books")
    assert alike("Penguin Books", "Penguin")
