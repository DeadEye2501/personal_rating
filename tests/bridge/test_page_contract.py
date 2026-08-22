"""Имена, которые страница и мост обязаны называть одинаково.

Своей проверки у этих пар нет ни с одной стороны: питон не читает `client/`,
Vitest не читает `bridge/`. Ломаются они по-разному, и тише всех — фильтры:
раздел, тип и критерий сортировки мост переводит в перечисления и на неизвестном
падает `ValueError`, а фильтры читает через `filters.get(name, ())`, где
разъехавшееся имя даёт не отказ, а фильтр, который молча не применился.

Читается исходник страницы, а не собранный бандл: сборки может не быть вовсе, а
имена обязаны совпадать и до неё."""

import re
from dataclasses import fields
from pathlib import Path

from backend.model import (
    Rating,
    TagExists,
    CompanyRole,
    GenreKind,
    IdSource,
    ItemExists,
    Kind,
    PersonRole,
    RatingSource,
    Section,
    Sort,
    Source,
)
from backend.config import FIVE, TEN
from bridge.answer import Domain, kebab
from bridge.api import Api
from bridge.feed import FILTER_FIELDS

WEB = Path(__file__).resolve().parents[2] / "client"
# Читается исходник, а не собранное: в `dist` лежат те же строки, и сверка по
# ним подтверждала бы сама себя вчерашней сборкой. Замерено: пути там есть, и от
# ложного согласия спасало только то, что минификатор пишет их обратными
# кавычками.
SKIPPED = {"node_modules", "dist"}

# Тело `chosen` — единственное место страницы, где имена фильтра пишутся.
CHOSEN = re.compile(r"export function chosen\(filters\) \{(.+?)\n\}", re.DOTALL)


def source(path: str) -> str:
    return (WEB / path).read_text(encoding="utf-8")


def named_in_chosen() -> set[str]:
    body = CHOSEN.search(source("state/filters.js"))
    assert body, "в client/state/filters.js больше нет функции chosen"
    return set(re.findall(r"^\s{4}(\w+):", body.group(1), re.MULTILINE))


def values_of(table: str, text: str) -> set[str]:
    """Значения `value:` внутри одной таблицы, до её закрывающей скобки.

    Скобка ищется после имени, а не литералом `= [`: таблица, зависящая от
    состояния, обёрнута в `$derived(...)`, и жёсткий литерал отставал бы от неё
    падением на месте вместо расхождения наборов."""
    start = text.index("[", text.index(f"const {table} = "))
    return set(re.findall(r"value: '(\w+)'", text[start:text.index("]", start)]))


def body_of(table: str, text: str) -> str:
    """Тело словаря `const ИМЯ = { ... }` вместе со скобками.

    Скобки считаются, а не ищутся первой закрывающей: `${...}` внутри шаблонной
    строки оборвал бы словарь на середине. Сами шаблоны выкидываются — иначе
    `https:` в адресе читается ключом."""
    opened = text.index("{", text.index(f"const {table} = {{"))
    depth, end = 0, len(text)
    for index in range(opened, len(text)):
        depth += {"{": 1, "}": -1}.get(text[index], 0)
        if not depth:
            end = index
            break
    return re.sub(r"`[^`]*`", "''", text[opened:end])


def keys_of(table: str, text: str) -> set[str]:
    return set(re.findall(r"[{,]\s*(\w+):", body_of(table, text)))


def strings_of(table: str, text: str) -> set[str]:
    """Значения плоского списка `const ИМЯ = ['a', 'b']`.

    Третий разборщик рядом с двумя: `values_of` ищет `value:` в таблице
    объектов, `keys_of` — ключи словаря, а этот список объявлен голыми
    строками."""
    start = text.index(f"const {table} = [")
    return set(re.findall(r"'(\w+)'", text[start:text.index("]", start)]))


def test_the_page_names_exactly_what_the_bridge_reads():
    assert named_in_chosen() == set(FILTER_FIELDS)


def test_the_page_offers_exactly_the_kinds_the_backend_knows():
    """Переключатель типа — кнопка на каждый тип, и каждая уезжает в
    `Kind`."""
    assert values_of("KINDS", source("app/Topbar.svelte")) == set(Kind)


def test_the_library_halves_match_the_sections_the_base_serves():
    """Поиска и статистики в `Section` нет намеренно: их база не отдаёт вовсе —
    поиск складывает две выдачи сам, статистика спрашивает гистограмму."""
    assert values_of("VIEWS", source("app/Topbar.svelte")) == set(Section)


def test_the_switch_offers_exactly_the_orders_the_base_supports():
    keys = set(re.findall(r"key: '?(\w+)'?,", source("state/sorting.js")))
    # `ADDED_AT` в таблице стоит именем константы, а не строкой.
    assert (keys - {"ADDED_AT"}) | {Sort.ADDED_AT} == set(Sort)


def test_every_rating_source_has_a_scale_and_a_name():
    """Оценки приезжают ключами `RatingSource`, а страница берёт по ним шкалу и
    подпись. Разъехавшись, они молчат вдвойне: неизвестная шкала уходит в
    запасную десятибалльную, неизвестное имя показывается сырым ключом."""
    page = source("state/sources.js")

    assert keys_of("MAX", page) == set(RatingSource)
    assert keys_of("NAMES", page) == set(RatingSource)


def test_every_card_source_has_a_name_on_the_page():
    """Подпись источника карточки живёт в своём пространстве — `Source`, а не
    `RatingSource`: совпадают они только тремя значениями из семи, и седьмой
    источник страница подписывала бы сырым ключом `old_games`.

    Ручной в таблице нет намеренно: окно карточки её подпись не показывает
    вовсе — там крестик вместо имени."""
    keys = keys_of("CARDS", source("state/sources.js"))

    assert keys == set(Source) - {Source.MANUAL}


def test_every_rating_source_has_a_place_in_the_row():
    """Порядок в ряду оценок назван списком, и в нём обязаны стоять все семь.
    Пропущенный уходит в конец — это задумано для восьмого, которого ещё нет, —
    и потому пропажа знакомого прошла бы молча, поменяв ряд местами."""
    page = source("state/sources.js")
    start = page.index("const ORDER = [")

    listed = re.findall(r"'([a-z]+)'", page[start:page.index("]", start)])

    assert set(listed) == set(RatingSource)
    assert len(listed) == len(set(listed))


def test_the_tmdb_link_is_built_for_kinds_the_backend_knows():
    """У TMDB фильмы и сериалы нумеруются порознь, и путь у них разный. Ключ,
    разъехавшийся с `Kind`, оставил бы карточку без ссылки — молча."""
    built = keys_of("TMDB_PATHS", source("state/sources.js"))

    assert built <= set(Kind)
    assert built == {Kind.MOVIE, Kind.SERIES}


def test_pages_are_built_only_for_ids_that_are_actually_stored():
    """Адрес собирается по чужому идентификатору, а чужими сегодня приезжают
    только IMDb и Кинопоиск: `IdSource` знает ещё Steam и GOG, но их не пишет
    ни один клиент. Строка про источник, которого в перечислении нет вовсе, —
    это ссылка в никуда."""
    built = keys_of("PAGES", source("state/sources.js"))

    assert built <= set(IdSource)
    assert built == {IdSource.IMDB, IdSource.KINOPOISK}


def test_the_card_shows_every_role_the_base_stores():
    """Строки состава на карточке перечислены своей таблицей. Переименованная
    роль отказа не даёт — строка просто исчезает со всех карточек разом, а
    заметить это можно только глазами и только зная, что она там была."""
    named = set(re.findall(r"role: '(\w+)'", source("state/credits.js")))

    assert named == set(PersonRole) | set(CompanyRole)


def test_the_page_names_the_same_three_aspects_as_the_base():
    """Три стороны оценки игры уезжают мосту именами полей: `wire.py` кладёт
    датакласс на провод как есть. Переименованная сторона отказа не даёт —
    строка шкалы гаснет на всех играх молча, а среднее считается по двум."""
    named = set(re.findall(r"key: '(\w+)'", source("state/scores.js")))
    stored = {field.name for field in fields(Rating)} - {"item_id", "score",
                                                         "review"}

    assert named == stored


def test_the_card_asks_the_right_two_shelves():
    """Люди и студии лежат в разных репозиториях, и мост зовёт их по имени
    домена. Перепутанные местами, они дали бы режиссёра среди студий — ровно та
    ошибка, которую проект уже ловил мутациями в сборке бэкенда.

    Сверяется **привязка**, а не набор из двух имён: набор переживает обмен
    ролей местами, и до 01.08.2026 этот докстринг обещал больше, чем проверял.
    Кто где лежит, питон знает сам — по `PersonRole` и `CompanyRole`."""
    asked = re.findall(r"role: '(\w+)', +domain: '(\w+)'",
                       source("state/credits.js"))
    shelves = {role: shelf
               for shelf, roles in (("people", PersonRole),
                                    ("companies", CompanyRole))
               for role in roles}

    assert asked, "в client/state/credits.js больше нет таблицы ролей"
    assert dict(asked) == {role: shelves[role] for role, _ in asked}


def test_sorting_is_offered_exactly_where_the_base_can_sort():
    """Круг состояний заведён ровно тем разделам, которые база и сортирует.
    Разойдясь, они дали бы либо кнопку, которая ничего не меняет, либо раздел с
    порядком, но без переключателя."""
    cycles = re.search(r"const CYCLES = \{(.+?)\n\}", source("state/sorting.js"),
                       re.DOTALL)
    assert cycles, "в client/state/sorting.js больше нет таблицы CYCLES"
    assert set(re.findall(r"^\s{2}(\w+):", cycles.group(1),
                          re.MULTILINE)) == set(Section)


def test_the_page_maps_every_kind_to_a_genre_set_the_base_has():
    """Наборов жанров четыре на пять типов содержимого: игры, книги и музыка
    берут каждый свой, кино и сериалы делят оставшийся. Разъехавшись, таблица привезла бы во вкладку
    «Фильмы» игровые жанры — отказа тут не будет, отбор просто уйдёт номерами,
    которых у типа не бывает.

    Привязка выводится из перечислений, а не переписывается списком: список в
    тесте расходится не с ожидаемым, а с самим собой. Тип, чьё имя есть и среди
    наборов жанров, берёт одноимённый; остальным достаётся единственный
    оставшийся."""
    table = keys_and_values("GENRE_KINDS", source("state/genres.js"))
    own = {kind for kind in Kind if kind in set(GenreKind)}
    shared, = set(GenreKind) - {GenreKind(kind) for kind in own}

    assert set(table) == set(Kind)
    assert {table[kind] for kind in own} == {kind for kind in own}
    assert {table[kind] for kind in set(Kind) - own} == {shared}


def test_every_reader_of_the_genre_table_reads_the_sworn_one():
    """Сверка таблицы не замечает, что её перестали читать: `GENRE_KINDS[kind]`,
    заменённое на голый `kind`, оставляет и её, и весь набор зелёными, а модалка
    жанров начинает спрашивать справочник несуществующим `movie`.

    Читателей двое — модалка фильтров и окно карточки, — и сверена ровно одна
    таблица. Объяви кто-нибудь свою рядом, сверка осталась бы зелёной, а
    вкладка «Фильмы» привезла бы игровые жанры: поэтому проверяется, что
    объявление одно и каждый читатель берёт его импортом.

    Исходником, а не следствием: следствие живёт в разметке, а разметка по
    решению проекта не проверяется вовсе."""
    readers, declared = set(), set()
    for path in WEB.rglob("*"):
        if path.suffix not in {".js", ".svelte"} or SKIPPED & set(path.parts):
            continue
        body = path.read_text(encoding="utf-8")
        if "GENRE_KINDS[" in body:
            readers.add(path)
        if "GENRE_KINDS =" in body:
            declared.add(path.name)

    assert readers, "страница больше не читает таблицу наборов жанров"
    assert declared == {"genres.js"}
    for path in readers:
        assert "GENRE_KINDS } from '$state/genres.js'" in path.read_text(
            encoding="utf-8"), f"{path.name} читает чужую таблицу"


def keys_and_values(table: str, text: str) -> dict[str, str]:
    """Словарь строковых значений `const ИМЯ = { ключ: 'значение' }`.

    Тело берётся общим `body_of`: наивный поиск первой закрывающей скобки уже
    однажды обрывал словарь на середине, и заводить его второй раз незачем."""
    return dict(re.findall(r"(\w+): '(\w+)'", body_of(table, text)))


def test_the_page_knows_the_refusals_it_tells_apart():
    """Два отказа страница разбирает по роду, потому что они штатные и говорят
    о них иначе, чем о поломке: занятое имя тега и занятая ссылка. Разъехавшись,
    «Такой тег уже есть» молча станет «Не удалось завести тег», а «Эта карточка
    уже есть» — «Не удалось привязать».

    Род берётся из имени класса, и оба имени живут в питоне: страница их только
    повторяет, и сверять надо повторение."""
    named = re.search(r"const TAG_EXISTS = '([\w-]+)'", source("app/tags.js"))
    taken = re.search(r"const TAKEN = '([\w-]+)'", source("app/LinkField.svelte"))

    assert named, "в client/app/tags.js больше нет константы TAG_EXISTS"
    assert taken, "в client/app/LinkField.svelte больше нет константы TAKEN"
    assert named.group(1) == kebab(TagExists.__name__)
    assert taken.group(1) == kebab(ItemExists.__name__)


def test_the_page_calls_a_hand_made_card_what_the_base_calls_it():
    """Ручная карточка помечена источником `manual`, и по нему окно решает,
    показывать поле ссылки или имя источника с крестиком. Разъехавшись, оно
    предложит привязать уже привязанную и не даст отвязать — молча."""
    named = re.search(r"const MANUAL = '(\w+)'", source("state/sources.js"))

    assert named, "в client/state/sources.js больше нет константы MANUAL"
    assert named.group(1) == Source.MANUAL


# Путь до моста страница называет строкой, и опечатка в нём не роняет ни сборку,
# ни один тест фронта: промис отклоняется уже в бегущем приложении.
#
# Ищется **любой** строковый литерал вида «слово.слово», а не только стоящий
# прямо в `call(...)`: страница зовёт мост и тернарником, и через производную, и
# через свою обёртку — привязка к имени вызова оставляла четыре живых пути вне
# сверки, и среди них весь круг обогащения видимой карточки. Лишнее отсекается
# доменом: пара считается путём, только если её первое слово — домен моста.
CALLED = re.compile(r"'(\w+)\.(\w+)'")


def paths_of_the_page(domains: set[str]) -> set[tuple[str, str]]:
    found = set()
    for path in WEB.rglob("*"):
        if path.suffix not in {".js", ".svelte"} or SKIPPED & set(path.parts):
            continue
        found |= {pair for pair in CALLED.findall(path.read_text(encoding="utf-8"))
                  if pair[0] in domains}
    return found


def test_every_path_the_page_calls_exists_on_the_bridge():
    """Обратная половина `test_bridge_surface.py`: тот сверяет «мост → бэкенд»,
    этот — «страница → мост». Без него `marks.tag_usage`, написанное как
    `marks.tag_uses`, оставляет оба набора зелёными, а удаление тега перестаёт
    спрашивать про носителей — молча."""
    sides = {domain: side for domain, side in vars(Api(None)).items()
             if isinstance(side, Domain)}
    surface = {(domain, method)
               for domain, side in sides.items()
               for method in dir(side) if not method.startswith("_")}
    called = paths_of_the_page(set(sides))

    assert called, "страница больше не зовёт мост ни одним путём"
    assert called <= surface, f"страница зовёт то, чего у моста нет: {called - surface}"
    # Число, а не только вложенность: сверка ничего не стоит, если находить
    # пути перестал сам поиск. Оно и ловило четыре пути, потерянных прежним
    # выражением — те, что страница зовёт не прямо.
    assert len(called) >= 41, f"путей найдено меньше, чем есть: {len(called)}"


def test_the_page_reads_exactly_what_the_summary_of_a_deletion_holds():
    """Сводка удаления — единственная величина границы без своего класса: это
    словарь, собранный литералами в репозитории. Переименуй в нём `in_wishlist`,
    и закладка молча пропадёт из предупреждения перед необратимым — оба набора
    останутся зелёными, а человек согласится, не зная, что теряет.

    Читаются оба тела разом: имя, которого сторона не назвала, и есть
    расхождение, в какую бы сторону оно ни случилось."""
    given = re.search(r"async def deletion_summary\(.+?return \{(.+?)\n\s+\}",
                      (Path(__file__).resolve().parents[2]
                       / "backend/storage/repository/library.py")
                      .read_text(encoding="utf-8"), re.DOTALL)

    assert given, "у репозитория больше нет deletion_summary со словарём"
    assert set(re.findall(r'"(\w+)":', given.group(1))) == set(
        re.findall(r"summary\.(\w+)", source("state/removal.js")))


def test_the_page_sends_the_three_scales_in_the_order_the_bridge_reads_them():
    """Три шкалы игры уезжают позиционными доводами, и мост читает их по месту:
    переставь местами `visual` и `narrative` на любой стороне — оценка визуала
    молча ляжет в нарратив, а обе стороны останутся зелёными. Сторож путей это
    не ловит: путь тот же, число доводов то же.

    Сверяются имена доводов моста с тем порядком, в каком их собирает страница.
    Первый довод у моста — номер карточки, и шкалы идут за ним."""
    named = re.search(r"const ASPECT_KEYS = \[(.+?)\]", source("app/marks.js"))
    assert named, "в client/app/marks.js больше нет списка ASPECT_KEYS"

    bridge = (Path(__file__).resolve().parents[2] / "bridge/marks.py")
    signature = re.search(r"def aspects\(self, item_id: int, (.+?)\) -> dict",
                          bridge.read_text(encoding="utf-8"), re.DOTALL)
    assert signature, "у моста больше нет метода aspects с тремя шкалами"

    assert re.findall(r"'(\w+)'", named.group(1)) == re.findall(
        r"(\w+): int \| None", signature.group(1))


def test_the_page_has_a_word_form_for_every_kind():
    """Формы склонения — по одной тройке на тип содержимого. Пропуск роняет
    `plural` на `undefined` прямо в подтверждении удаления тега, а лишний ключ
    остаётся мёртвым: набор типов задаёт `Kind`, а не этот файл."""
    forms = re.search(r"export const NOUNS = \{(.+?)\n\}",
                      source("state/kinds.js"), re.DOTALL)

    assert forms, "в client/state/kinds.js больше нет таблицы NOUNS"
    assert set(re.findall(r"^  (\w+):", forms.group(1), re.MULTILINE)) == set(Kind)


def test_the_page_draws_every_scale_the_settings_can_ask_for():
    """Шкал две, и обе объявлены на странице своей нотацией.

    Разъехавшись, они молчат: `SCALE_X2=0` дал бы питону пятёрку, а странице
    неизвестную шкалу — то есть ряд звёзд без ярлыков и без цветов, потому что
    поиск в пропавшей таблице отдаёт `undefined`, а не отказ."""
    notation = re.search(r"const NOTATION = \{(.+?)\n\}\n",
                         source("state/scores.js"), re.DOTALL)

    assert notation, "в client/state/scores.js больше нет таблицы NOTATION"
    known = {int(one) for one in re.findall(r"^  (\d+): \{",
                                            notation.group(1), re.MULTILINE)}
    assert known == {TEN, FIVE}


def test_the_page_asks_the_bridge_for_the_scale():
    """Не спросив, страница нарисует десять звёзд на пятибалльной базе, и
    молча: умолчание нотации совпадает с прежней шкалой, а число столбцов
    приезжает от базы — расхождение видно только глазами."""
    assert ("refs", "scale") in paths_of_the_page({"refs"})


def test_the_page_offers_a_link_field_only_where_a_catalog_exists():
    """Поле вставки ссылки у типа без источника разбирать нечего: любая
    вставленная строка ответила бы отказом. Список на странице свой, и разойтись
    с реестром он может молча — до второго этапа, когда книжный клиент приедет и
    поле должно вернуться само."""
    from backend.sources.registry import ROUTES

    with_catalog = {kind.value for kind, route in ROUTES.items() if route.catalogs}

    assert strings_of("LINKED", source("state/sources.js")) == with_catalog
