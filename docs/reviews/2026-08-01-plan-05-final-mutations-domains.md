# Итоговое ревью плана 5: мутации по доменам моста и отдаче страницы

Измерение — проверить мутациями, что тесты сторожат то, ради чего написаны.
Область: `bridge/library.py`, `marks.py`, `refs.py`, `feed.py`, `search.py`,
`world.py`, `covers.py`, `api.py`, `serve.py`, `window.py`.

Прогон: `pytest tests/bridge -q`, чистый код — **190 зелёных**.

## Что сделано

**79 мутаций**, по одной строке каждая, с откатом после прогона. Раскладка:
library 7, marks 9, refs 4, feed 9, search 9, world 10, covers 3, serve 17,
api 4, window 6.

Ломалось то, что легко сломать случайно: доводы одного типа местами, снятый
перевод в перечисление, снятый номер операции, подменённое имя метода бэкенда,
снятая проверка, перепутанные домены, изменённый код ответа HTTP.

**Молча прошло 11.** Каждая проверена вторым разом временной пробой: на чистом
коде проба зелёная, под мутацией красная. Из одиннадцати **десять — настоящие
дыры**, одна признана ненаблюдаемой по построению.

## Находки

### Critical (обязательно к правке)

**1. `bridge/window.py:44` — `open_window` не проверяется ни одним тестом, и
проверка движка молча снимается с фоновой функции.**

Сломано: `webview.start(func=_check_renderer, debug=debug)` → `webview.start(debug=debug)`.

Почему набор не заметил: `tests/bridge/test_window.py` открывается фразой «Окно
здесь не поднимается ни разу» и зовёт `_check_renderer()` **напрямую**. Что её
кто-то ставит фоновой функцией окна, не утверждает ничто. Тест
`test_a_foreign_engine_leaves_a_line_in_the_log` сам называет критерий приёмки:
«**отсутствие** этой строки в логе, поэтому сломанная проверка выглядит точно как
исправный движок» — и ровно этот случай не закрывает.

Чем кончится: нет среды WebView2 — pywebview молча уезжает на MSHTML, приложение
выглядит грубой подделкой, и в логе про это нет ни строки. Это тот самый дефект,
ради которого 31.07 менялся стек, и единственная строка, которая от него
защищает, ничем не сторожится.

Чинить: тест на `open_window` с подменёнными `webview.create_window` и
`webview.start`, утверждающий `started["func"] is _check_renderer`.

**2. `bridge/window.py:47` — закрытие потока бэкенда снимается молча.**

Сломано: `thread.close()` → `pass`.

Почему набор не заметил: то же — `open_window` не зовут.

Чем кончится: окно закрыли, а `Backend.aclose()` не позвался. Поток объявлен
`daemon=True`, поэтому процесс всё-таки завершится, но движок SQLAlchemy и шесть
клиентов `httpx` закрываются убийством потока на полуслове: без чекпойнта WAL и
с брошенными сокетами. Проектное решение про порядок закрытия («список живых
задач ведёт поток») при этом просто не исполняется.

Чинить: тем же тестом — `thread.close()` обязан быть позван после `webview.start`.

**3. `bridge/api.py:33` — домен, собранный не на том потоке, проходит молча.**

Сломано: `self.covers = Covers(thread)` → `self.covers = Covers(None)`.

Почему набор не заметил: `test_bridge_surface.py` проверяет имена на поверхности
(`test_the_bridge_shows_seven_domains_and_cancelling`) и то, что за семью именами
стоят семь разных классов (`test_each_name_hides_its_own_domain`), — обе половины
поймали подмену класса (M69, M70). Но **через собранный `Api` не зовётся ни один
домен**: что каждому достался живой поток, не утверждает никто.

Чем кончится: заливка обложки и проверка её наличия отвечают «непредвиденный сбой»
на каждый вызов — `AttributeError: 'NoneType' object has no attribute 'run'`,
завёрнутый оболочкой. При 190 зелёных тестах.

Это ровно тот класс, который проект уже ловил дважды: «сборка — самое опасное
место в плане» (план 4, `loader=None` при 909 зелёных).

Чинить: прогнать через собранный `Api` по одному вызову на домен — семь строк,
которые заодно закроют и подмену потока, и подмену класса.

### Important (следует поправить)

**4. `bridge/world.py:103` — `Kind(kind)` у числа ожидаемых оценок не сторожится:
сравнение идёт `==`, а `Kind` — `StrEnum`.**

Сломано: `back.enricher.expected(Kind(kind))` → `back.enricher.expected(kind)`.

Почему набор не заметил: `test_expected_sources_are_known_before_the_network`
пишет `assert seen == [Kind.MOVIE]`, а `Kind.MOVIE == "movie"` истинно.
Соседний тест того же файла — `test_enriching_answers_with_what_arrived` — это
знает и пишет `is`, с докстрингом «`==` пропустило бы сырую строку, а реестр
источников различает его `is`». В `expected` тот же приём не применён.

Чем кончится: `SourceRegistry.rating_sources` сравнивает `if kind is Kind.GAME`.
Сырая строка `"game"` тождеством не совпадёт, и для игры вернутся три оценочных
клиента вместо пустого списка. На карточке игры нарисуются три кружка под оценки
агрегаторов, которые не приедут никогда.

Чинить: `assert seen[0] is Kind.GAME`, и типом содержимого взять именно игру —
на фильме следствие не наблюдается.

**5. `bridge/marks.py:36` — то же у заведения тега.**

Сломано: `back.tags.create(Kind(kind), name)` → `back.tags.create(kind, name)`.

Почему набор не заметил: `test_a_new_tag_belongs_to_one_kind` пишет
`assert args == (Kind.SERIES, "пересмотреть")` — равенство на `StrEnum`. Теста
«неизвестный тип содержимого — это отказ» у этого метода нет вовсе, хотя у
жанров он есть (`test_an_unknown_set_of_genres_is_a_failure_too`).

Чем кончится: колонка `tag.kind` — обычный `Text`, ограничения на значения нет.
Опечатка на стороне страницы молча положит в базу тег с чужим типом, и он станет
невидим во всех трёх вкладках — навсегда, потому что удалить его тоже неоткуда.
Соседние методы того же домена (`tags.list_for_kind`, `tags.reorder`) сторожатся
тождеством, то есть приём в файле уже принят и просто не доведён до конца.

Чинить: `assert args[0] is Kind.SERIES` плюс тест на неизвестный тип с
`assert log == []`.

**6. `bridge/covers.py:34` — строгость разбора base64 не сторожится.**

Сломано: `base64.b64decode(data, validate=True)` → `validate=False`.

Почему набор не заметил: `test_broken_base64_does_not_reach_the_backend` кормит
строку `"не base64!"`. Кириллица в `b64decode` падает раньше проверки алфавита —
строка кодируется в ascii, — поэтому отказ приходит и без `validate`. Строку
подобрали такую, что свойство, ради которого написан тест, ею не наблюдается.

Чем кончится: мусор вокруг годного base64 (`"!!! ***iVBORw0KGho="`) при
`validate=False` тихо отбрасывается, и до бэкенда доезжают байты, которых
страница не посылала. Гарантия самого теста — `assert log == []` — держится не
кодом, а удачным выбором строки.

Чинить: кормить ascii-мусором вокруг годного base64, а не кириллицей.

### Minor (по возможности)

**7. `bridge/library.py:36` — `Kind(kind)` у поиска тёзок по названию.**

Сломано: `find_by_title(Kind(kind), title)` → `find_by_title(kind, title)`.
Не заметил `test_the_same_title_check_stays_inside_one_kind`: `args ==
(Kind.MOVIE, "Одиссея")` — то же равенство на `StrEnum`.

Чем кончится: мягче, чем у 4 и 5 — неизвестный тип перестаёт быть отказом и
уезжает в `where`, где ничему не соответствует. Предупреждение о совпадении
названия молча не покажется. Своё решение («частичной карточки в базе не бывает»)
это не задевает.

Чинить: `assert args[0] is Kind.MOVIE`.

**8. `bridge/world.py:109` — `https://` сужается до `http` молча.**

Сломано: `url.startswith("https://")` → `url.startswith("http")`.
`test_a_foreign_scheme_is_refused` кормит `file:///C:/Windows/system32`, второй
тест — `https://…`. Между ними ничего не различает `http://`.

Чем кончится: страница источника откроется по незащищённому адресу. Опасной
схемы (`file:`, `javascript:`) префикс `http` всё ещё не пускает, поэтому
следствие — расхождение с записанным решением, а не дыра в правах.

Чинить: добавить `http://` третьим случаем в тест отказа.

**9. `bridge/window.py:38–41` — размеры окна не наблюдаются ничем.**

Сломано отдельно: `min_size=(MIN_WIDTH, MIN_HEIGHT)` → перевёрнуто; стартовый
размер → сведён к минимуму. Обе молчат по той же причине, что 1 и 2, —
`open_window` не зовут.

Чем кончится: перевёрнутый минимум даёт окно, которое тянется по ширине до 600 и
по высоте до 900, то есть уже собственной шапки; стартовый размер меньше — окно
открывается подтянутым, ровно то, что комментарий в коде обещает не допускать.

Чинить: тем же тестом на `open_window`, что и 1 с 2, — четыре утверждения на
одном подменённом `create_window`.

### Ненаблюдаемое по построению (не находка)

**M68. `bridge/serve.py:119` — `return None` → `return b""` в `_fetched`.**
Проверено пробой: отличить нельзя ничем. Обе величины отсекает один и тот же
сторож `not isinstance(picture, bytes | bytearray) or not picture`, и оба пути
дают `404` с одинаковыми заголовками и пустым телом. Мутант эквивалентный —
дырой не является.

## Таблица всех мутаций

| № | Файл | Что сломано | Итог | Кто поймал |
|---|---|---|---|---|
| M01 | library | незаполненные поля формы едут в бэкенд | RED | `test_an_empty_field_does_not_reach_the_backend` |
| M02 | library | дата не переводится из строки | RED | `test_a_release_date_arrives_as_a_date` |
| M03 | library | тип содержимого не переводится у поиска тёзок | **SILENT** | — (находка 7) |
| M04 | library | у правки доводы местами | RED | `test_editing_names_the_card_and_keeps_the_fields` |
| M05 | library | отвязка зовёт сводку удаления | RED | `test_unlinking_names_the_card` |
| M06 | library | удаление мимо `delete_card`, прямо в репозиторий | RED | `test_deletion_goes_through_the_backend_method` |
| M07 | library | заведение не переводит `Kind` | RED | `test_a_manual_card_is_built_by_the_bridge` |
| M08 | marks | у назначения тега доводы местами | RED | `test_assigning_names_the_card_first_then_the_tag` |
| M09 | marks | перепутаны `visual` и `narrative` | RED | `test_aspects_go_to_their_own_scales` |
| M10 | marks | перепутаны `narrative` и `gameplay` | RED | `test_aspects_go_to_their_own_scales` |
| M11 | marks | оценка пишется как рецензия | RED | `test_setting_a_score_carries_the_moment` |
| M12 | marks | заведение тега не переводит `Kind` | **SILENT** | — (находка 5) |
| M13 | marks | снятие тега назначает его | RED | `test_unassigning_goes_the_same_way_round` |
| M14 | marks | счёт носителей тега зовёт удаление | RED | `test_the_number_of_carriers_is_asked_before_deleting` |
| M15 | marks | у порядка тегов доводы местами | RED | `test_reordering_survives_as_the_page_sent_it` |
| M16 | marks | закладка теряет момент | RED | `test_wishing_carries_the_moment` |
| M17 | refs | справочник всегда люди | RED | `test_the_domain_chooses_the_repository[companies]` |
| M18 | refs | подсказка заводит нового вместо поиска | RED | `test_the_domain_chooses_the_repository` |
| M19 | refs | снята проверка имени справочника | RED | `test_an_unknown_domain_is_a_failure_not_a_crash` |
| M20 | refs | жанры не переводятся в `GenreKind` | RED | `test_genres_come_for_the_asked_set` |
| M21 | feed | у страницы ленты снят номер операции | RED | `test_all_three_ways_into_the_feed_carry_the_number` |
| M22 | feed | у точечного чтения снят номер операции | RED | `test_all_three_ways_into_the_feed_carry_the_number` |
| M23 | feed | у гистограммы снят номер операции | RED | `test_all_three_ways_into_the_feed_carry_the_number` |
| M24 | feed | раздел не переводится в `Section` | RED | `test_the_request_is_assembled_from_what_the_page_holds` |
| M25 | feed | критерий сортировки не переводится в `Sort` | RED | то же |
| M26 | feed | сторона сортировки перевёрнута | RED | то же |
| M27 | feed | из перечня фильтров выпали исключённые оценки | RED | `test_all_six_kinds_of_filter_reach_the_backend` |
| M28 | feed | жанры подменены исключёнными жанрами | RED | то же |
| M29 | feed | гистограмма не переводит тип содержимого | RED | `test_the_histogram_uses_the_same_filters` |
| M30 | search | у своего поиска снят номер операции | RED | `test_both_halves_carry_the_number` |
| M31 | search | выдача своего поиска не запоминается | RED | 8 тестов, в т.ч. `test_external_is_merged_with_what_was_shown` |
| M32 | search | память не обновляется после складывания | RED | `test_a_candidate_from_the_outer_half_can_be_added_too` |
| M33 | search | кандидат ищется только по идентификатору | RED | `test_a_candidate_is_added_by_its_pair` |
| M34 | search | у внешнего снята проверка устаревания | RED | `test_a_stale_number_gets_nothing` |
| M35 | search | складывание идёт чужим вперёд | RED | `test_external_is_merged_with_what_was_shown` |
| M36 | search | у заведения кандидата снят номер операции | RED | `test_a_candidate_is_added_by_its_pair` |
| M37 | search | у внешнего поиска снят номер операции | RED | `test_both_halves_carry_the_number` |
| M38 | search | свой поиск не переводит тип содержимого | RED | `test_an_unknown_kind_is_a_failure_not_a_crash` |
| M39 | world | у обогащения снят номер операции | RED | `test_enriching_answers_with_what_arrived` |
| M40 | world | чужая схема адреса сужена до `http` | **SILENT** | — (находка 8) |
| M41 | world | непохожее на ссылку не становится отказом | RED | `test_an_unparsable_link_never_reaches_the_network` |
| M42 | world | карточка по ссылке не запоминается | RED | `test_the_card_for_a_link_is_kept_not_sent_back` |
| M43 | world | галочка перезаписи перевёрнута | RED | `test_the_overwrite_box_reaches_the_backend` |
| M44 | world | подсказка тумблера не доезжает до разбора | RED | `test_an_unknown_kind_never_reaches_the_parser` |
| M45 | world | у привязки снята проверка устаревания | RED | `test_linking_without_a_kept_card_is_stale` |
| M46 | world | у перезапроса сериала снят номер операции | RED | `test_refreshing_a_series_is_silent_when_nothing_was_needed` |
| M47 | world | у карточки по ссылке снят номер операции | RED | `test_the_card_for_a_link_is_kept_not_sent_back` |
| M48 | world | число ожидаемых оценок не переводит тип | **SILENT** | — (находка 4) |
| M49 | covers | base64 разбирается без проверки алфавита | **SILENT** | — (находка 6) |
| M50 | covers | у заливки доводы местами | RED | `test_an_uploaded_picture_arrives_as_bytes` |
| M51 | covers | битая картинка ловится не тем родом | RED | `test_broken_base64_does_not_reach_the_backend` |
| M52 | serve | снята проверка выхода за корень | RED | `test_a_way_out_of_the_root_is_refused` |
| M53 | serve | на неприехавшей обложке 200 вместо 404 | RED | `test_a_cover_that_did_not_arrive_is_not_found` |
| M53b | serve | пустые байты отдаются как обложка | RED | `test_an_empty_picture_is_not_a_picture_either` |
| M54 | serve | снят кеш обложки | RED | `test_a_cover_of_a_library_card_is_taken_by_its_number` |
| M55 | serve | у модуля подменён тип содержимого | RED | `test_a_module_gets_the_script_type` |
| M56 | serve | у шрифта подменён тип содержимого | RED | `test_a_font_gets_its_own_type` |
| M57 | serve | ручка обложки переименована | RED | 6 тестов обложек |
| M58 | serve | корень не разворачивается в `index.html` | RED | `test_the_root_gives_the_page` |
| M59 | serve | PNG опознаётся как JPEG | RED | `test_a_cover_of_a_library_card_is_taken_by_its_number` |
| M60 | serve | неполный запрос отвечает 404 вместо 400 | RED | `test_a_cover_asked_without_anything_is_refused` |
| M61 | serve | нечисловой номер не отсеивается | RED | `test_a_number_that_is_not_a_number_is_a_bad_request` |
| M62 | serve | у своей карточки источник и адрес местами | RED | `test_a_cover_of_a_library_card_is_taken_by_its_number` |
| M63 | serve | обложка кандидата сохраняется под номером 0 | RED | `test_a_cover_of_a_candidate_is_taken_by_its_address` |
| M64 | serve | источник не переводится в перечисление | RED | то же (`args[1] is Source.TMDB`) |
| M65 | serve | снят `Content-Length` | RED | `test_the_root_gives_the_page` |
| M66 | serve | неизвестное расширение отдаётся как html | RED | `test_an_unknown_extension_travels_as_bytes` |
| M67 | serve | сбой обложки ловится только как `OSError` | RED | `test_a_thread_that_refused_gives_a_place_for_the_stub` |
| M68 | serve | нет карточки — пустые байты вместо `None` | **SILENT** | эквивалентный мутант |
| M69 | api | под именем `marks` стоит домен карточки | RED | `test_each_name_hides_its_own_domain` |
| M70 | api | под именем `search` стоит лента | RED | то же |
| M71 | api | отмена не доносит номера до потока | RED | `test_cancelling_reaches_the_thread` |
| M72 | api | домен собран на пустом потоке (`Covers(None)`) | **SILENT** | — (находка 3) |
| M73 | window | проверка рендерера инвертирована | RED | 5 тестов `test_window.py` |
| M74 | window | жалоба пишется на своём движке | RED | `test_a_foreign_engine_leaves_a_line_in_the_log` |
| M75 | window | минимальный размер окна перевёрнут | **SILENT** | — (находка 9) |
| M76 | window | проверка движка не ставится фоновой функцией | **SILENT** | — (находка 1) |
| M77 | window | поток не закрывается после закрытия окна | **SILENT** | — (находка 2) |
| M78 | window | стартовый размер сведён к минимуму | **SILENT** | — (находка 9) |

## Вердикт

**Готово к слиянию? С правками.**

Семь доменов моста и отдача страницы сторожатся плотно: 68 мутаций из 79 упали
сразу, и по большей части одним точным тестом, а не лавиной. Перепутанные доводы,
снятые номера операций, подменённые имена методов, коды HTTP, память выдачи и
пара «источник + идентификатор» — всё это набор различает. Ни одной ошибки
поведения в боевом коде мутации не нашли.

Дыры — в двух местах, и оба узнаваемы по прежним ревью проекта:

- **Сборка и точка входа не проверяются.** `open_window` не зовётся ни разу, и
  четыре мутации по нему молчат — включая ту, что отключает единственную защиту
  от чужого движка, ради которой менялся стек. `Api` собирается, но через него
  не зовут ни одного домена, и домен на пустом потоке проходит молча. Это тот же
  дефект, что `loader=None` в плане 4.
- **Перевод в перечисление сторожится равенством, а `Kind` — это `StrEnum`.**
  Три места из шести пишут `==` вместо `is`, и в одном из них (`expected`)
  следствие настоящее: игровая карточка нарисует три кружка под оценки, которых
  не будет. Проект этот приём знает — соседний тест в том же файле пишет `is` и
  объясняет почему.

Правки нужны только в тестах: боевой код во всех девяти находках прав. Три
Critical (тест на `open_window`, семь вызовов через собранный `Api`) и три
Important (`is` вместо `==` в трёх местах плюс ascii-мусор в пробе base64) —
обязательны до слияния; три Minor закрываются теми же тестами попутно.
