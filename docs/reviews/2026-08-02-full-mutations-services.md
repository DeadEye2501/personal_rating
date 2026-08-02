# Мутации по сервисам, сборке и мосту — 02.08.2026

Измерение: `backend/service/`, `backend/app.py`, `bridge/`. Работа шла в
отдельном рабочем дереве `agent-a8e9c9f7bcd731bfe` на коммите `d6a37c4`.

**Внесено 130 мутаций, поймано 125, прошло молча 5.**

По областям: сборка `backend/app.py` — 24 мутации, 1 молча; `bridge/` — 48
мутаций, 2 молча; `backend/service/` — 58 мутаций, 2 молча. Треть работы отдана
сборке, как и просило задание.

Набор до мутаций зелёный: **1288 тестов**, `.env` скопирован из основного дерева.
Каждая мутация — одна изменённая строка, вносилась по одной, откат сразу же.
Быстрый прогон шёл по своей половине области (`tests/bridge` — 2.5 с, backend-часть
— 22 с), **каждая молчаливая переспрашивалась всей областью (602 теста), а потом
всем набором (1288)** — все пять молчат и там.

Каждая молчаливая проверена временной пробой: зелёной на чистом коде, красной под
мутацией. Проба удалена, дерево чисто.

## Сильные стороны

- **Сборка больше не самое дырявое место проекта.** Из 24 мутаций по `app.py`
  поймано 23. Ловят их два теста, написанных именно за этим —
  `test_the_assembly_wires_the_three_services_nobody_asked_about` и
  `test_the_assembly_wires_the_click_on_a_name`, — и весь `test_offline.py`
  вокруг них. Пойманы **все** перестановки людей со студиями (три места:
  `card_parts`, поверхность `Backend`, `PeopleSearch`), **все** четыре `=None`,
  **все** три незакрытых ресурса, оба недоехавших транспорта, репозиторий не того
  типа в четырёх местах. Это ровно тот список, который раньше проходил молча.
- **Отказ моста сторожится по роду, а не по факту отказа.** Пять подмен рода
  (`stale`→`cancelled`, `timeout`→`broken`, `closed`→`broken`,
  `cancelled`→`closed`, `kebab` без дефиса) пойманы все пять. Свойство «плашка
  говорит разное» держится не тем, что ответ пришёл, а тем, что он назван.
- **Граница потоков проверена на состояниях, а не на счастливом пути.**
  Неразрешённый фьючерс ловится тремя разными тестами (заявка после закрытия,
  развалившаяся заявка, закрытие под живой задачей), номер операции — четырьмя,
  причём `op=op`→`op=None` в оболочке ловится сразу девятью тестами через
  `Watched.ops`.
- **`to_wire` и `outcome` закрыты полностью** — 5 из 5, включая порядок ветвей
  (`Enum` перед примитивом) и громкий отказ на байтах.
- **Отмена, откат и порядок двух файлов базы у писателя карточки пойманы все.**
  `S19` (снята ветка `CancelledError`), `S20` (откат мимо хранилища обложек),
  `S35` (обратный порядок удаления) — три места, которые проект однажды находил
  ревью, а не мутациями; теперь их держат тесты.
- **Ни одна из 130 мутаций не нашла ошибки поведения в боевом коде.** Все пять
  молчаливых — про тесты и про лишний код, а не про поломку.

## Находки

### Critical

#### 1. Боевой `Loader` не наблюдается ничем — ни один тест не звал `ensure` через собранный бэкенд

- **Где:** `backend/app.py:165–166`, поле `loader=Loader(..., posters=posters)`.
- **Мутация A23:** `posters=posters` → `posters=PosterService({}, store)`.
- **Гонялось:** быстрый набор — 602 теста; переспрошено всем набором — **1288
  тестов зелёные**.
- **Свойство без сторожа:** загрузчику досталась та же служба обложек, что и
  писателю карточки. Сегодня это не утверждает ничто.
- **Чем это кончится:** `Loader.ensure` первым делом идёт
  `self._posters.fetch(view.source, view.poster_url)`, и у службы без клиентов
  это `Refusal(BROKEN, "нет клиента для tmdb")`. Дальше стоит
  `if isinstance(poster, Refusal): return poster` — **завести найденную в поиске
  карточку было бы нельзя вовсе, ни одну, ни разу**, при 1288 зелёных тестах.
  Это буквально тот же дефект, что `loader=None` (909 тестов зелёные) и сломанный
  целиком GOG: приложение «работает», а главный сценарий мёртв.
- **Почему прошло:** единственный тест, который трогает боевой `loader`, —
  `test_the_assembly_wires_the_three_services_nobody_asked_about`, и он зовёт
  `card_for_link`, а этот путь обложек не касается вовсе. `ensure` через
  собранный бэкенд не зовётся нигде; тесты `test_loading.py` собирают `Loader`
  сами, своим набором частей.
- **Как наблюдать** (проба зелёная на чистом коде, красная под мутацией):

  ```python
  async def test_the_loader_got_the_real_poster_service(offline):
      candidate = CardView(kind=Kind.MOVIE, source=Source.TMDB,
                           source_id="157336", title="Интерстеллар",
                           poster_url="https://image.tmdb.org/p.jpg")

      answer = await offline.loader.ensure(candidate)

      assert isinstance(answer, Refusal)
      assert answer.reason is Reason.NETWORK
  ```

  Причина различает два случая, как и у соседнего
  `test_every_poster_source_got_its_own_named_client`: у настоящей службы клиент
  есть, и мёртвая сеть даёт `NETWORK`; у пустой клиента нет, и это `BROKEN`.
  Место — `tests/backend/test_offline.py`, рядом с двумя сборочными тестами.

### Important

#### 2. `Enricher._imdb_id` берёт идентификатор по порядку, а не по источнику

- **Где:** `backend/service/enrich.py:96–99`.
- **Мутация S14:** снята проверка `if external.source is IdSource.IMDB`.
- **Гонялось:** быстрый набор — 361 тест; область — 602; весь набор — **1288
  зелёные**.
- **Свойство без сторожа:** агрегаторов спрашивают **именно** номером IMDb.
  Сегодня проверяется только то, что у карточки с одним-единственным IMDb-номером
  этот номер доехал, — то есть набор, а не привязка. Это ровно тот класс, который
  проект ловил уже трижды: «тест проверял набор меток, а не привязку метки к
  источнику».
- **Чем это кончится:** у карточки, известной Кинопоиску и не известной IMDb
  (обычное дело для нашего кино), в `mdblist`/`omdb` уехал бы номер Кинопоиска.
  Ответ на чужой номер — это либо `Missing`, и тогда в базу на неделю ляжет
  пустая строка «у источника нет оценки», либо **чужая оценка на своей карточке**.
  Отдельно: сегодня такая карточка обязана выйти из обогащения по ветке «без
  imdb_id: агрегаторов спросить нечем», и эта ветка тоже не сторожится.
- **Как наблюдать:**

  ```python
  async def test_only_an_imdb_identifier_is_asked_with(sessions, enrich):
      item_id = ...  # карточка без IMDb
      await ExternalIdsRepository(sessions).put(
          item_id, ExternalId(IdSource.KINOPOISK, "258687"))
      client = FakeRatings((RatingSource.IMDB,), Missing())

      await enrich(client).enrich(item_id, Kind.MOVIE)

      assert client.asked == []
  ```

  Место — `tests/backend/test_enrich.py`. Фикстура `item_id` там кладёт ровно
  один идентификатор и ровно IMDb; нужен второй случай, а не второе поле.

#### 3. Проверка типов границы красна или зелена по порядку сбора — и это не мутация, а состояние набора

- **Где:** `tests/backend/test_model.py:67–83`,
  `test_every_boundary_type_is_named_on_the_surface`.
- **Найдено до первой мутации**, при попытке прогнать область в другом порядке.
- **Воспроизведение, минимальное:**

  ```
  pytest -q tests/bridge/test_bridge_world.py tests/backend/test_model.py
  → 2 failed, 84 passed
  pytest -q tests/backend/test_model.py tests/bridge/test_bridge_world.py
  → 84 passed
  ```

- **Причина:** `boundary_denials()` отдаёт `Denied.__subclasses__()` **на сборе**,
  а `bridge/world.py` объявляет `BadLink` и `ForeignScheme` наследниками `Denied`
  — намеренно, и в докстринге написано зачем. Проверка требует, чтобы каждый
  наследник лежал в `backend.model.__all__`, а отказам моста там не место по
  определению: `backend/` про `bridge/` не знает.
- **Почему сегодня зелено:** `testpaths = tests`, и `tests/backend` собирается
  раньше `tests/bridge` по алфавиту. Держится это порядком имён папок, а не
  кодом. Красным станет от чего угодно: прогона `tests/bridge` первым, случайного
  порядка, `-n auto`, переименования папки.
- **Что чинить:** проверка обязана различать отказы модели и отказы моста.
  Например, отбирать наследников по `__module__.startswith("backend.model")` —
  тогда своё она сторожит по-прежнему, а чужое не подбирает. Второй, более
  ценный, вариант: завести парную проверку **со стороны моста** — «каждый
  `Denied` моста доезжает до страницы своим родом», — и тогда правило будет
  сторожиться на обеих сторонах, а не падать на одной.

### Minor

#### 4. `Search._outer`: страж, чьё свойство держит соседний модуль

- **Где:** `bridge/search.py:76–80`.
- **Мутация B27:** снята проверка `if self._kept.taken(op) is not None:` перед
  `self._kept.put(op, merged)`. Молчит на 1288 тестах.
- **Это не дыра в тестах.** То же свойство держит `Kept.put` собственной
  проверкой `op < self._op`, и оно **сторожится**: мутация B10 (снять проверку в
  `Kept`) падает на
  `tests/bridge/test_kept.py::test_a_late_answer_does_not_take_the_cell_from_a_newer_one`.
- **Ветка недостижима как различающая — правило 8.** В `_outer` можно попасть
  только через `external(op)`, а тот уже вышел `stale()`, если `taken(op)` пуст,
  — значит на входе `Kept._op == op`. Пока летит ответ, ячейку может занять
  только больший номер (`Kept` меньший не пускает), и тогда `put(op, merged)`
  отвергается самим `Kept`. При `_op == op` кладут обе ветки. Разницы нет ни в
  одном достижимом состоянии.
- **Что с этим делать:** проверку снять, а довод оставить одной строкой со
  ссылкой на `Kept.put` — сейчас четыре строки комментария объясняют защиту,
  которой в этом месте нет. Докстринг `test_a_late_answer...` в `test_kept.py`
  это уже говорит прямо: «Раньше это держал сам домен поиска».

#### 5. `set_running_or_notify_cancel()` после `cancel()` не делает ничего наблюдаемого

- **Где:** `bridge/thread.py:152–155` (`_end`) и `bridge/thread.py:176–177`
  (`_shutdown`), обе пары `answer.cancel(); answer.set_running_or_notify_cancel()`.
- **Мутация B15:** снят второй вызов в `_end`. Молчит на 1288 тестах.
- **Замерено, а не выведено:**

  ```
  f = concurrent.futures.Future(); f.cancel()
  → state CANCELLED, done() True, result() поднимает CancelledError
  ```

  `Future.cancel()` сам зовёт `notify_all()`, поэтому ждущий в `result()`
  просыпается и без второго вызова. Различает состояния только
  `concurrent.futures.wait()` / `as_completed`, которые считают «сделанным»
  лишь `CANCELLED_AND_NOTIFIED`.
- **Проект их не зовёт нигде** — проверено поиском по `bridge/`, `backend/`,
  `main.py`: из `Future` читаются только `result()` и `done()`.
- **Отличие от находки 4:** здесь снятие второй строки безопасно **сегодня**, но
  становится наблюдаемым в тот день, когда кто-нибудь позовёт
  `concurrent.futures.wait`. Правильнее не снимать, а записать в
  `docs/deferred.md`, раздел «Свойства без сторожа»: следствия у свойства нет, и
  тест на него читал бы объявление. Существенная половина — `answer.cancel()` —
  сторожится и в `_end` (B08), и в `_shutdown` (B18, B18b).

#### 6. Внутри одного пространства порядок жанров не сторожит ничто

- **Где:** `backend/service/genres.py:21–28`, `resolved_genres`.
- **Мутация S53:** вместо накопления меток по пространствам справочник
  спрашивается по одной метке за раз (`resolve(space, [ext_id])`). Молчит на
  1288 тестах.
- **Свойство без сторожа:** `GenresRepository.resolve` обещает в докстринге, что
  «порядок сохраняется… в том порядке, в каком лежат в справочнике», и это
  наблюдаемо — но только когда в одном пространстве **две и более** метки.
  Сегодня `test_genre_resolution.py` сторожит порядок **между** пространствами
  (`test_the_order_of_the_spaces_is_the_order_of_the_answer`), а внутри одного —
  никто; `test_genres.py` сверяет `resolve` через `sorted()`, то есть набор.
- **Второе следствие, тоже без сторожа:** ради чего пространства и собираются в
  словарь — один запрос на пространство вместо запроса на метку. У игры из Steam
  меток бывает под два десятка, и это разница между двумя запросами и двадцатью
  на каждую записываемую карточку.
- **Как наблюдать** (проба зелёная на чистом коде, красная под мутацией):

  ```python
  # 'B' лежит в справочнике раньше 'A', а на карточке стоит позже
  MAP = ("INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
         "('steam', 'B', 2), ('steam', 'A', 1)")

  found = await resolved_genres(genres, (
      (GenreSource.STEAM, "B"), (GenreSource.STEAM, "A"),
  ))
  assert found == [1, 2]
  ```

  Место — `tests/backend/test_genre_resolution.py`. Замечание на будущее:
  чистый код здесь отвечает `[1, 2]`, а не «в порядке строк `genre_map`», —
  порядок задаёт план запроса, и **проверять надо то, что он выдаёт, а не то,
  что обещает докстринг**. Первая версия пробы упала именно на этом: я поверил
  комментарию раньше замера.

#### 7. Оговорка о методе: одна мутация оказалась негодной и была переделана

`B18` в первом заходе снял две строки внутри `for`, оставив пустое тело, —
`IndentationError`, то есть проверялся синтаксис, а не свойство. Переделано двумя
годными мутациями (`B18`, `B18b`), обе пойманы
`test_closing_cancels_instead_of_waiting_them_out`. Записано, потому что
«поймана» на сломанном синтаксисе — это ложный зелёный у самого измерения.

## Полный список мутаций

Обозначения: A — сборка `backend/app.py`, B — `bridge/`, S — `backend/service/`.
В последней колонке — первый упавший тест.

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| A01 | `card_parts`: люди и студии поменяны местами | поймана | `test_offline.py::test_the_cast_of_a_hand_made_card_is_kept` |
| A02 | `Backend.people`/`companies` поменяны местами | поймана | `test_offline.py::test_the_cast_of_a_hand_made_card_is_kept` |
| A03 | `PeopleSearch`: люди и студии поменяны местами | поймана | `test_offline.py::test_the_assembly_wires_the_click_on_a_name` |
| A04 | `loader=None` | поймана | `test_offline.py::test_the_assembly_wires_the_three_services_nobody_asked_about` |
| A05 | `series=None` | поймана | `test_offline.py::test_the_assembly_wires_the_three_services_nobody_asked_about` |
| A06 | `finder=None` | поймана | `test_offline.py::test_the_assembly_wires_the_click_on_a_name` |
| A07 | транспорт не доехал до каталожных клиентов | поймана | `test_offline.py::test_the_external_search_reports_the_reason` |
| A08 | три постерных клиента названы одинаково | поймана | `test_offline.py::test_every_poster_source_got_its_own_named_client` |
| A09 | транспорт не доехал до постерных клиентов | поймана | `test_offline.py::test_every_poster_source_got_its_own_named_client` |
| A10 | одному источнику постерного клиента не досталось | поймана | `test_offline.py::test_every_poster_source_got_its_own_named_client` |
| A11 | хранилище постеров не открыто | поймана | `test_offline.py::test_a_card_is_deleted_with_everything_of_mine` |
| A12 | соединения источников не закрываются | поймана | `test_offline.py::test_everything_closes_and_lets_go` |
| A13 | хранилище постеров не закрывается | поймана | `test_offline.py::test_everything_closes_and_lets_go` |
| A14 | движок базы не закрывается | поймана | `test_offline.py::test_everything_closes_and_lets_go` |
| A15 | ручная карточка не ложится в список дел | поймана | `test_offline.py::test_a_hand_made_card_lands_in_the_wishlist` |
| A16 | `delete_card` не трогает второй файл базы | поймана | `test_offline.py::test_a_card_is_deleted_with_everything_of_mine` |
| A17 | `feed=None` | поймана | `test_offline.py::test_the_feed_works` |
| A18 | обогащению подан репозиторий своих оценок | поймана | `test_offline.py::test_the_enrichment_asks_nobody_without_the_network` |
| A19 | `linker=None` | поймана | `test_offline.py::test_a_hand_made_card_gets_linked_to_a_source` |
| A20 | `Backend.ratings` — репозиторий чужих оценок | поймана | `test_offline.py::test_a_score_is_given_and_kept` |
| A21 | в части карточки подан репозиторий своих оценок | поймана | `test_card_writer.py`, откат карточки |
| A22 | поиску достался реестр без внедрённого транспорта | поймана | `test_offline.py::test_the_external_search_reports_the_reason` |
| **A23** | **загрузчику досталась служба обложек без клиентов** | **молча** | — |
| A24 | `Backend.wishlist` — репозиторий разделов | поймана | `test_offline.py::test_the_wishlist_works` |
| B01 | устаревший второй шаг назван отменой | поймана | `test_bridge_search.py::test_a_stale_number_gets_nothing` |
| B02 | род отказа без дефиса | поймана | `test_answer.py::test_a_denial_becomes_a_kind_of_failure` |
| B03 | чужой `TimeoutError` выдан за наш срок | поймана | `test_answer.py::test_a_timeout_raised_by_the_operation_is_not_ours` |
| B04 | просроченная работа не гасится | поймана | `test_answer.py::test_a_hung_call_is_cut_off` |
| B05 | срок назван поломкой | поймана | `test_answer.py::test_a_hung_call_is_cut_off` |
| B06 | перевода в JSON нет | поймана | `test_answer.py::test_the_answer_is_translated_on_the_way_out` |
| B07 | закрытый поток назван поломкой | поймана | `test_answer.py::test_a_closed_thread_answers_instead_of_raising` |
| B08 | отмена названа закрытием | поймана | `test_answer.py::test_a_cancelled_operation_answers_quietly` |
| B09 | номер операции не доезжает до потока | поймана | девять тестов через `Watched.ops` |
| B10 | опоздавший затирает ячейку | поймана | `test_kept.py::test_a_late_answer_does_not_take_the_cell_from_a_newer_one` |
| B11 | свой же второй шаг в ячейку не пишет | поймана | `test_bridge_search.py::test_a_candidate_from_the_outer_half_can_be_added_too` |
| B12 | чужой номер получает чужую выдачу | поймана | `test_bridge_search.py`, три теста |
| B13 | снимается чужая запись номера | поймана | `test_thread.py::test_the_number_taken_twice_stays_cancellable` |
| B14 | номер не запоминается — отмена никого не находит | поймана | `test_thread.py`, шесть тестов |
| **B15** | **`set_running_or_notify_cancel` снят в `_end`** | **молча** | — |
| B16 | заявка, разминувшаяся с закрытием, вешает просителя | поймана | `test_thread.py::test_a_request_that_raced_closing_is_refused` |
| B17 | развалившаяся заявка оставляет фьючерс неразрешённым | поймана | `test_thread.py`, восемь тестов |
| B18 | при закрытии ответы отменённых задач теряются | поймана | `test_thread.py::test_closing_cancels_instead_of_waiting_them_out` |
| B18b | при закрытии ответы помечаются, но не отменяются | поймана | `test_thread.py::test_closing_cancels_instead_of_waiting_them_out` |
| B19 | `cancel` ничего не гасит | поймана | `test_thread.py`, шесть тестов |
| B20 | `run` на закрытом потоке не отказывает | поймана | `test_thread.py`, четыре теста |
| B21 | порядок ветвей: перечисление уходит объектом | поймана | `test_wire.py::test_an_enum_travels_as_a_plain_string` |
| B22 | `NaN` уезжает на страницу | поймана | `test_wire.py::test_not_a_number_becomes_nothing` |
| B23 | байты молча становятся пустотой | поймана | `test_wire.py::test_bytes_are_refused` |
| B24 | «такого нет» выдано за находку | поймана | `test_bridge_search.py::test_a_source_that_lost_the_card_says_so` |
| B25 | отказ выдан за «такого нет» | поймана | `test_wire.py::test_a_refusal_carries_its_reason` |
| B26 | внешний шаг без запомненного запроса падает `TypeError` | поймана | `test_bridge_search.py::test_a_second_step_after_a_click_gets_nothing` |
| **B27** | **снят страж ячейки в `Search._outer`** | **молча** | — |
| B28 | кандидат ищется без учёта источника | поймана | `test_bridge_search.py::test_a_candidate_is_added_by_its_pair` |
| B29 | чужое встало впереди своего | поймана | `test_bridge_search.py::test_external_is_merged_with_what_was_shown` |
| B30 | исключённые оценки выпали из контракта | поймана | `test_bridge_feed.py::test_all_six_kinds_of_filter_reach_the_backend` |
| B31 | сторона сортировки не доезжает | поймана | `test_bridge_feed.py::test_the_side_of_the_order_survives_the_way` |
| B32 | смещение и размер порции поменяны местами | поймана | `test_bridge_feed.py::test_paging_carries_the_offset_and_the_size` |
| B33 | незаполненное поле стирает известное | поймана | `test_bridge_library.py::test_an_empty_field_does_not_reach_the_backend` |
| B34 | правка теряет название | поймана | `test_bridge_library.py::test_editing_names_the_card_and_keeps_the_fields` |
| B35 | правка удалённой карточки отвечает успехом | поймана | `test_bridge_library.py::test_editing_a_card_that_is_gone_is_a_failure` |
| B36 | роль студии разбирается как роль человека | поймана | `test_bridge_refs.py::test_a_role_the_shelf_does_not_keep_is_a_failure` |
| B37 | домен не выбирает справочник — всегда люди | поймана | `test_bridge_refs.py::test_the_domain_chooses_the_repository` |
| B38 | негодная картинка молча становится пустотой | поймана | `test_bridge_covers.py::test_broken_base64_does_not_reach_the_backend` |
| B39 | открывается любая `http`-схема | поймана | `test_bridge_world.py::test_a_foreign_scheme_is_refused` |
| B40 | ненайденное помнится и уезжает в привязку | поймана | `test_bridge_world.py::test_a_card_that_was_not_found_is_not_kept_for_linking` |
| B41 | непохожее на адрес уходит в бэкенд пустотой | поймана | `test_bridge_world.py::test_an_unparsable_link_never_reaches_the_network` |
| B42 | нечисловой номер карточки поднимает `ValueError` | поймана | `test_serve.py::test_a_number_that_is_not_a_number_is_a_bad_request` |
| B43 | выход за корень отдаётся | поймана | `test_serve.py::test_a_way_out_of_the_root_is_refused` |
| B44 | пустые байты отдаются кодом 200 | поймана | `test_serve.py::test_an_empty_picture_is_not_a_picture_either` |
| B45 | тип файла всегда `octet-stream` | поймана | `test_serve.py::test_the_root_gives_the_page` |
| B46 | кеш обложек снят | поймана | `test_serve.py::test_a_cover_of_a_library_card_is_taken_by_its_number` |
| B47 | отмена с корня ничего не гасит | поймана | `test_bridge_surface.py::test_cancelling_reaches_the_thread` |
| S01 | работы найденных людей выпали из выдачи строки | поймана | `test_search.py::test_a_name_in_the_query_brings_the_works_of_that_person` |
| S02 | выдачи склеены подряд, а не вперемешку | поймана | `test_search.py::test_titles_and_people_come_woven` |
| S03 | отказ половины «по людям» теряется | поймана | `test_search.py::test_a_refusal_of_the_name_search_travels_as_a_refusal` |
| S04 | две причины от одного источника схлопнуты в одну | поймана | `test_people_search.py::test_two_reasons_from_one_source_stay_two` |
| S05 | `Missing` разбирается как находка | поймана | `test_search.py::test_a_missing_answer_is_not_a_refusal_either` |
| S06 | бесплатная оценка источника не проводится | поймана | `test_search.py::test_the_free_rating_reaches_the_candidate` |
| S07 | жанры кандидата выдачи потеряны | поймана | `test_search.py::test_genres_are_unfolded_from_the_reference` |
| S08 | спрашиваются и непросроченные источники | поймана | `test_enrich.py::test_a_client_with_nothing_stale_is_not_asked` |
| S09 | побеждает спрошенный последним, а не первым | поймана | `test_enrich.py::test_the_first_value_wins_when_two_sources_know_the_same_rating` |
| S10 | необъявленная оценка уезжает в базу | поймана | `test_enrich.py::test_a_rating_nobody_promised_is_not_written` |
| S11 | отказ записан как «у источника нет» | поймана | `test_enrich.py`, четыре теста |
| S12 | отказавший не попадает в список отказавших | поймана | `test_enrich.py`, четыре теста |
| S13 | непросроченное спрашивается заново | поймана | `test_enrich.py::test_nothing_stale_costs_nothing_extra` |
| **S14** | **за `imdb_id` берётся первый попавшийся идентификатор** | **молча** | — |
| S15 | уже лежащая карточка заводится заново | поймана | `test_loading.py::test_a_card_already_in_the_base_is_not_asked_for_again` |
| S16 | карточка пишется без обложки | поймана | `test_loading.py`, откат карточки |
| S17 | своя карточка проходит круг загрузки заново | поймана | `test_loading.py::test_a_view_that_knows_its_identifier_costs_nothing` |
| S18 | слаг разрешается не у того магазина | поймана | `test_link_loading.py::test_a_gog_slug_becomes_a_number_before_the_card` |
| S19 | отмена не откатывает карточку | поймана | `test_card_writer.py::test_cancelling_the_write_takes_the_card_with_it` |
| S20 | откат не трогает хранилище обложек | поймана | `test_card_writer.py::test_the_rollback_takes_the_poster_with_it` |
| S21 | писатель не добывает обложку сам | поймана | `test_loading.py::test_a_cover_absent_from_the_search_but_present_in_the_detail` |
| S22 | писатель складывает людей в студии | поймана | `test_loading.py::test_the_detail_round_brings_what_the_search_lacked` |
| S23 | пустая строка считается заполненной | поймана | `test_linking.py::test_every_field_a_source_may_fill_is_filled` |
| S24 | перезапись стирает своё пустой строкой источника | поймана | `test_linking.py::test_overwrite_keeps_what_the_source_never_sent` |
| S25 | привязка перетирает свои жанры | поймана | `test_linking.py::test_a_chosen_genre_is_not_topped_up` |
| S26 | перезапись состава не снимает прежний | поймана | `test_linking.py::test_overwrite_takes_everything_the_source_gave` |
| S27 | занятость чужих идентификаторов не проверяется | поймана | `test_linking.py::test_an_identifier_taken_by_another_card_stops_everything` |
| S28 | залитая руками обложка перетирается чужой | поймана | `test_linking.py::test_an_own_poster_is_not_replaced` |
| S29 | привязка складывает людей в студии | поймана | `test_offline.py::test_a_hand_made_card_gets_linked_to_a_source` |
| S30 | пустой состав источника стирает свой | поймана | `test_linking.py::test_overwrite_does_not_wipe_what_the_source_never_had` |
| S31 | не приехавшее число стирает известное | поймана | `test_series_refresh.py::test_a_half_empty_answer_does_not_erase_what_was_known` |
| S32 | перезапрос идёт и у ручной карточки | поймана | `test_series_refresh.py::test_a_manual_card_is_never_re_asked` |
| S33 | срок годности не проверяется | поймана | `test_series_refresh.py::test_a_fresh_series_is_not_asked_about` |
| S34 | перезапрос идёт и у фильма | поймана | `test_series_refresh.py::test_a_film_is_never_re_asked` |
| S35 | порядок двух файлов базы обратный | поймана | `test_delete.py::test_a_broken_deletion_leaves_the_card_not_the_poster` |
| S36 | HTML-заглушка ложится в хранилище как обложка | поймана | `test_poster_service.py::test_an_empty_body_is_a_refusal` |
| S37 | лежащая обложка качается заново | поймана | `test_cover_reads.py::test_a_stored_cover_comes_back_without_the_network` |
| S38 | скачанная обложка не сохраняется | поймана | `test_cover_reads.py::test_a_missing_cover_is_downloaded_and_kept` |
| S39 | 404 от CDN проходит за обложку | поймана | `test_poster_service.py::test_a_failed_download_is_a_refusal` |
| S40 | у кандидата обложка идёт в хранилище под `None` | поймана | `test_cover_reads.py::test_a_candidate_gets_its_cover_but_nothing_is_stored` |
| S41 | залитая картинка не обрезается | поймана | `test_poster_service.py::test_an_upload_is_cropped` |
| S42 | название студии уходит в поиск по людям | поймана | `test_offline.py::test_the_assembly_wires_the_click_on_a_name` |
| S43 | внешняя идентичность не используется | поймана | `test_people_search.py::test_an_identified_person_is_asked_by_identifier` |
| S44 | клик по несуществующему номеру идёт дальше | поймана | `test_people_search.py::test_an_unknown_entity_has_nothing_to_show` |
| S45 | чужое встало впереди своего | поймана | `test_people_search.py::test_own_card_wins_over_the_same_one_from_outside` |
| S46 | вкладка перестала быть первичным фильтром | поймана | `test_offline.py::test_the_assembly_wires_the_click_on_a_name` |
| S47 | пустое имя уходит в источник | поймана | `test_people_search.py::test_an_empty_name_is_not_asked_outside` |
| S48 | фильмография спрашивается у отсутствующего клиента | поймана | `test_people_search.py::test_an_identified_person_in_the_game_tab_never_goes_outside` |
| S49 | позиция состава всегда ноль | поймана | `test_card_writer.py::test_people_are_attached_with_their_roles` |
| S50 | оценки агрегаторов с карточки не пишутся | поймана | `test_card_writer.py::test_external_identifiers_and_ratings_are_written` |
| S51 | смещение и размер порции поменяны местами | поймана | `test_offline.py::test_the_feed_works` |
| S52 | дубли жанров не снимаются | поймана | `test_genre_resolution.py::test_one_genre_from_two_spaces_is_returned_once` |
| **S53** | **пространства спрашиваются по одной метке за раз** | **молча** | — |
| S54 | обрезка не по центру, а от левого края | поймана | `test_images.py::test_the_sides_are_trimmed_equally` |
| S55 | стороны обрезки перепутаны | поймана | `test_images.py::test_a_small_picture_is_still_cropped_to_shape` |
| S56 | отмена превращается в отказ | поймана | `test_asking.py`, два теста |
| S57 | запросы идут мимо защиты от исключений | поймана | `test_search.py::test_a_broken_client_becomes_a_refusal_with_its_name` |
| S58 | карточка и обложка поменяны местами | поймана | `test_loading.py::test_a_candidate_becomes_a_card` |

## Вердикт

**Готово к продолжению работы?** С правками

**Обоснование:** ошибок поведения в боевом коде не нашла ни одна из 130 мутаций,
и сборка — прежде самое дырявое место проекта — держится 23 мутациями из 24. Но
две дыры закрывать надо: боевой `Loader` не наблюдается ничем, и подмена его
службы обложек оставляет **все 1288 тестов зелёными при мёртвом главном
сценарии** — та же поломка, что `loader=None` и сломанный целиком GOG; а проверка
типов границы сегодня зелена только потому, что `tests/backend` собирается раньше
`tests/bridge` по алфавиту.

---

**Состояние дерева после ревью:** `git status` чист, временная проба удалена,
все 130 мутаций откачены. Прогон на чистом дереве — 1288 тестов зелёные.
