# Ревью повторов по картам — план «Книги и музыка», задача 2

Измерение: повторы по картам всего проекта (`module-map.md`, `data-map.md`,
`front-map.md`, `not-duplicates.md`), а не дифф. Код не закоммичен, диапазона
коммитов нет — смотрю рабочее дерево `git diff` только чтобы знать, что
появилось.

## Ход разбора

1. Прочитаны все три карты целиком и `not-duplicates.md` (243 строки — до
   раздела «Похоже в тестах, но проверяет разное» включительно и далее).
2. Прочитан `git status`/`git diff` по изменённым файлам: `backend/model/kinds.py`,
   `backend/sources/registry.py`, `client/app/App.svelte`, `client/app/Topbar.svelte`,
   `client/state/card.js`, `client/state/credits.js`, `client/state/genres.js`,
   `client/state/kinds.js`, `client/state/session.js`, `client/styles/palette.css`,
   `tests/backend/sources/test_registry.py`, `tests/backend/test_model.py`,
   `tests/backend/test_search.py`, `tests/bridge/test_bridge_marks.py`,
   `tests/bridge/test_page_contract.py`, `tests/fakes.py`, `tests/web/card.test.js`,
   `tests/web/session.test.js`.
3. Прочитаны сами файлы целиком: `backend/sources/registry.py`, `tests/fakes.py`,
   `client/state/kinds.js`, `client/state/genres.js`, `client/state/credits.js`,
   `client/state/card.js`, `client/app/Topbar.svelte`, `client/app/App.svelte`,
   `client/state/facts.js`, `bridge/refs.py`, `tests/web/card.test.js`,
   `tests/bridge/test_page_contract.py`, `migrations/versions/0002_genres.py`,
   `backend/sources/build.py`.

## Кандидаты, проверенные и отведённые

### Шесть таблиц по типу содержимого (`ROUTES`, `KINDS`, `NOUNS`, `GENRE_KINDS`, `ROLES`, `OWN`) — не повтор

Все шесть ключуются одним и тем же пятиэлементным доменом (`Kind`), но несут
разное содержимое и разных потребителей:

- `ROUTES` (`backend/sources/registry.py`) — кто отвечает за тип на стороне
  источников: каталоги, поиск по человеку, оценочные источники.
- `KINDS` (`client/app/Topbar.svelte`) — иконка и подпись кнопки переключателя.
- `NOUNS` (`client/state/kinds.js`) — тройка склонений для текста («3 книги»),
  и явно не совпадает с `KINDS.label` по значению: у музыки единица счёта —
  альбом («альбом», «альбома», «альбомов»), а не «музыка» — сам файл это
  объясняет в докстринге.
- `GENRE_KINDS` (`client/state/genres.js`) — в какой из четырёх наборов жанров
  попадает тип.
- `ROLES` (`client/state/credits.js`) — какие роли состава существуют и в какой
  полке (`people`/`companies`) живут; ключ у неё не `Kind`, а роль.
- `OWN` (`client/state/card.js`) — какие поля формы свои у типа.

Ни одна пара не говорит одно и то же под разными именами: проверено по тексту
каждой таблицы построчно. Пять из шести (`KINDS`, `NOUNS`, `GENRE_KINDS`,
`ROLES` через привязку роль→полка, `OWN` — косвенно через `shownFor`)
сторожатся тестами границы — `tests/bridge/test_page_contract.py`
(`test_the_page_offers_exactly_the_kinds_the_backend_knows`,
`test_the_page_has_a_word_form_for_every_kind`,
`test_the_page_maps_every_kind_to_a_genre_set_the_base_has` +
`test_every_reader_of_the_genre_table_reads_the_sworn_one`,
`test_the_card_shows_every_role_the_base_stores`,
`test_the_card_asks_the_right_two_shelves`) или тестами фронта
(`tests/web/card.test.js`). `ROUTES` сторожится `tests/backend/sources/test_registry.py`
(новые `test_every_kind_has_a_row_in_the_table`,
`test_a_kind_outside_the_table_is_refused_on_the_spot`,
`test_kinds_without_sources_ask_nobody`). Это ровно случай «таблица данных с
разными потребителями, разъезд которой сторожит тест» — не повтор.

`ACCENTS` (`client/app/App.svelte`) тестами не сторожится, но это
согласуется с решением проекта не проверять компоненты/сборку — тем же
необорудован и весь остальной `App.svelte`, и это не новый пробел этого
слайса.

### `FakeSources.NOBODY` (`tests/fakes.py`) vs `Sources.ROUTES` (`backend/sources/registry.py`) — повтор с доводом, довод принят

`NOBODY = frozenset({Kind.BOOK, Kind.MUSIC})` действительно повторяет руками
то же самое знание, что уже записано в `ROUTES` (пустые каталоги/поиск/оценки
у книг и музыки). Комментарий у поля прямо это признаёт: «Правило повторяется
отсюда нарочно, по тому же доводу, что и «у игр — никто»: само оно живёт в
`Sources.ROUTES`, а здесь проверяется послушание сервиса».

Проверил довод по прецеденту: до этого слайса `FakeSources.people_for` и
`rating_sources` уже вручную повторяли «у игр — никто» (`kind is Kind.GAME`)
без какой-либо сверки с `Sources` — тот же приём, тот же файл, тот же
рецензируемый и принятый ранее код. `NOBODY` — механическое расширение уже
принятого паттерна на два новых типа, а не новая архитектурная дыра.
Обоснование в комментарии совпадает по форме и по существу с тем, что уже
было принято проектом: `FakeSources` — тестовый двойник, а не источник
истины, и он должен воспроизводить контракт `Sources` ровно настолько, чтобы
проверить, что *сервис* его слушается; сверки с `ROUTES` тестом нет — как не
было её и для `Kind.GAME` — но это тот же принятый риск, а не новый.
Довод принимаю, находкой не считаю.

### `tests/web/card.test.js:KINDS` — литерал, но не новый повтор

`const KINDS = ['movie', 'series', 'game', 'book', 'music']` — литеральный
список типов содержимого в теле теста. По диффу видно, что константа
существовала до слайса (`['movie', 'series', 'game']`) и в этом слайсе
только расширена двумя новыми значениями, а не заведена заново. Второго
такого списка нигде в тестах или на странице не появилось — второй
кандидат, `tests/backend/test_model.py:SCHEMA`, существовал до слайса и не
про список типов, а про полный алфавит каждого перечисления (`Kind`,
`Source`, `IdSource`, `RatingSource`, `PersonRole`, `CompanyRole`,
`GenreKind`, `GenreSource`) — это не пара к первому, а самостоятельная
таблица с другим назначением. Тела тестов в сравнение повторов не входят по
решению проекта, а сама константа — не боевой код и не имеет второй копии
где-либо ещё. Не повтор.

### `bridge/refs.py:Refs.genres` — не проверял как повтор, но нашёл побочно

Докстринг `def genres(...)` всё ещё говорит «Наборов два: кино и игры» — это
стало неправдой ещё в задаче 2 (у `GenreKind` теперь четыре набора, и
`backend/model/kinds.py` это уже отражает своим докстрингом). Это не повтор
данных (соответствие Kind→GenreKind нигде в `refs.py` не продублировано —
таблицы там нет), а устаревшая прозаическая фраза. Вне моего измерения
(повторы по картам), поэтому в «Находки» не выношу, а фиксирую здесь как
наблюдение для рецензента по манифесту/правилу 11.

## Находки

Critical: 0
Important: 0
Minor: 0

Ни одна проверенная пара не подтвердилась как повтор, требующий правки.

## Вердикт

**Готово к коммиту** — по измерению «повторы по картам». Шесть таблиц по
типу содержимого — законное разделение ответственности с разными
потребителями, пять из шести застрахованы тестами границы. Единственный
намеренный повтор (`FakeSources.NOBODY`) сопровождён доводом, который
проверяется прецедентом того же файла и принимается. Литеральный список
типов в `tests/web/card.test.js` — не новый и не имеет пары.
