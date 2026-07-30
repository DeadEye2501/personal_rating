# Ревью: повторы по картам после чистки бэкенда

**Измерение:** повторы логики во всём проекте сразу — одно дело под двумя
именами, две реализации одного алгоритма, два перечисления с одними значениями,
две таблицы одного смысла.

**Судится код на `569ace6`** (рабочее дерево чистое). Дифф не читался.
`python scripts/module_map.py --check` зелёный, то есть ни один вердикт в
`docs/not-duplicates.md` не протух и разбирать записанное заново не пришлось.

Прочитано целиком: `docs/module-map.md`, `docs/data-map.md`,
`docs/not-duplicates.md`, `docs/deferred.md`. Кандидаты собирались по картам,
затем каждый подтверждался чтением обоих мест. Дополнительно — прогон
`scripts/project_ast.py:declarations` с группировкой по отпечаткам: он показывает
дословно совпадающие тела, включая вложенные и короче пяти инструкций, которых
хук не сравнивает.

---

## Strengths

**Все одиннадцать выносов имеют по два и больше потребителей сегодня.**
Ни один не нарушает правило 7. Проверено вызовами, а не объявлениями — таблица
ниже.

**`parsed()` — самый нужный из них и самый честный.** Одиннадцать вызовов в семи
модулях (`gog` ×3, `tmdb` ×3, `poiskkino`, `unofficial`, `mdblist`, `omdb`,
`steam`). Довод про `logger` параметром **подтверждён кодом, а не только
докстрингом**: `poiskkino.py:77` и `unofficial.py:54` передают одно и то же
`source=SOURCE` («kinopoisk») с двумя разными модульными логгерами. Два измерения
не совпадают, и ни одно не выводится из другого — ни «взять логгер по source», ни
«взять source из логгера». Параметров четыре, то есть ровно предел правила 5, и
лишнего среди них нет.

**Ни один вынос не склеил разные правила.** Проверено по каждому: `is_json`
отвечает только на «разобралось ли тело» и вывод оставляет вызывающему —
`poiskkino._absent` делает из «не JSON» отказ, `mdblist._denied` — чужой периметр,
и это два разных вывода из одной проверки. `_by_source` в докстринге сам
перечисляет, почему остальные четыре `_*`-метода `ViewsRepository` под него не
подошли. `Entity` держит только то, чем человек отличается от студии в схеме.

**Обёртка `mirror.refuse_code` — не лишний слой.** Она подставляет `SOURCE` и
стоит в одном ряду с `refuse_quota`, `refuse_rate`, `refuse_key`; снять её значило
бы размазать `SOURCE` по двум модулям зеркал, ради экономии трёх строк.

**Общее в тестах вынесено там, где различие осталось на месте вызова.** Три
фикстуры сервиса обложек (`test_delete.py:service`,
`test_poster_service.py:service`, `test_cover_reads.py:covers`) зовут один
`builders.poster_service`, а различаются транспортом — `None`, отвечающий
постером, запоминающий запросы. Это ровно то, что должно было остаться разным.

**`tests/conftest.py` после разделения остался единственным адресом импорта** — и
это записано в его докстринге. Задвоений после переезда не нашлось: `fakes.py` и
`builders.py` ничего друг у друга не повторяют, а `conftest` только
переэкспортирует. Проверено чтением всех трёх файлов целиком.

**`docs/not-duplicates.md` ведётся по существу, а не отпечатками.** Шесть
вердиктов (строки 29, 34, 51, 66, 71, 124) после этих коммитов переписаны:
довод пересмотрен и в нём названо, что общего кода у пары стало меньше. Это
дороже, чем продлить отпечаток, и это правильно.

---

## Issues

### Critical (Must Fix)

Нет.

### Important (Should Fix)

#### 1. OMDB собирает `Refusal` по коду руками — ровно то выражение, ради которого заведён `refuse_code`

- `backend/sources/errors.py:22-26` — `refuse_code(source, status)` →
  `Refusal(source=source, reason=Reason.BROKEN, detail=f"HTTP {status}")`
- `backend/sources/ratings/omdb/client.py:68-72` —
  `Refusal(source="omdb", reason=Reason.BROKEN, detail=f"HTTP {response.status_code}")`

**Какое дело делается дважды.** Перевод неописанного кода ответа в отказ. Не
«похоже» — совпадает всё: `reason`, формат `detail`, смысл. Вызов
`refuse_code("omdb", response.status_code)` даёт побайтно тот же объект.

**Почему важно.** Докстринг `refuse_code` называет эту ситуацию своим
основанием: «была функцией у зеркал Кинопоиска и держала их `SOURCE` внутри,
поэтому остальные трое ею воспользоваться не могли и писали то же выражение по
месту». Трое — это магазины (через `undocumented.refuse_undocumented`), MDBList
(`client.py:77`) и зеркала (`mirror.py:42`). Все трое получили вынос, OMDB — нет,
то есть вынос сделан, а один из четырёх поводов остался как был. Формат `detail`
теперь живёт в двух местах: смена «HTTP 500» на что-либо другое поправит пять
источников и молча оставит шестой.

**Что остаётся:** `backend/sources/errors.py:refuse_code`. В OMDB — вызов.
Тесты это переживут: `tests/backend/sources/test_omdb.py` сверяет `source` и
`reason` (строки 147, 197, 282, 293), `detail` не проверяет нигде, а он и не
меняется.

#### 2. OMDB разбирает тело своим `try/except` — двенадцатая копия того, что уехало в `parsed`

- `backend/sources/errors.py:42-59` — `parsed(log, source, note, produce)`:
  `try: produce() except BROKEN_BY_PARSING as error: log.warning(...); return broken(...)`
- `backend/sources/ratings/omdb/client.py:52-55` —
  `try: payload = response.json() except ValueError as error: return broken("omdb", error)`

**Какое дело делается дважды.** «Разбор чужого тела сорвался — отказать по
`broken`». Ровно то, ради чего заведён `parsed`.

**Почему важно, и это не косметика.** Копия расходится с образцом по двум
наблюдаемым пунктам:

1. **Записи в лог нет.** Пять остальных клиентов на неразобранном теле пишут
   `warning`; OMDB молчит. Причину сбоя у одного источника из шести искать будет
   нечем — а именно это `parsed` и заводился беречь.
2. **Перечень исключений уже, чем `BROKEN_BY_PARSING`.** Здесь только
   `ValueError`; `TypeError`, `KeyError` и `AttributeError` пролетят наружу через
   границу потоков. Комментария, который объяснял бы сужение, нет — то есть это
   не решение, а недоделка. Второй `try/except` в этом же файле отсутствует
   вовсе: `_answer` уже зовёт `parsed`, и почему у соседней строки другой
   контракт, из кода не следует.

Ровно тот сорт расхождения, который докстринг `parsed` называет своим
основанием: «седьмой источник, написанный по образцу, легко получил бы
`except Exception` вместо перечня… и заметить это было бы негде».

**Что остаётся:** `errors.parsed`. В OMDB:
`payload = parsed(logger, "omdb", "тело не разобралось", response.json)` и
`if isinstance(payload, Refusal): return payload`. Проверка
`isinstance(payload, dict)` (строки 59-62) при этом нужна по-прежнему — она даёт
внятное «тело не объект» вместо `AttributeError`, — и её оставить как есть.

### Minor (Nice to Have)

#### 3. Steam ловит разбор своим `except` — тринадцатая копия обработчика `parsed`

- `backend/sources/errors.py:57-59` —
  `except BROKEN_BY_PARSING as error: log.warning("%s: %s — %s", ...); return broken(source, error)`
- `backend/sources/steam/client.py:83-85` —
  `except BROKEN_BY_PARSING as error: logger.warning("steam: карточка %s не разобралась — %s", ...); return broken("steam", error)`

Обработчик совпадает по существу целиком: перечень тот же, запись та же,
возврат тот же. Не совпадает только тело `try` — в нём три досрочных выхода
(`Refusal` про чужой appid, `Missing` про `success: false`, сама сборка карточки),
и как лямбда оно не записывается.

**Почему всё же стоит починить.** `parsed` пропускает наружу любое `T`, включая
`Missing` и `Refusal`, — значит вложенная функция на три ветки заходит без
натяжки:

```python
def read() -> Outcome | SourceCard: ...   # то же тело, что сейчас в try
card = parsed(logger, "steam", f"карточка {source_id} не разобралась", read)
```

Довод против: вложенная функция на девять строк читается хуже нынешнего
`try/except`. Решение здесь исполнителя; но записать надо либо правку, либо
вердикт в `docs/not-duplicates.md` — сейчас пара не записана нигде, и следующий
проход найдёт её заново.

Второй `try/except` этого же файла (`_tags`, строки 119-121) — **не** копия:
он возвращает `()`, а не отказ, и это его содержание («отказ здесь карточку не
роняет»). Его разбирать не надо.

#### 4. Группировка строк по колонке написана дважды

- `backend/storage/repository/genres.py:55-58` (`GenresRepository.index`)
- `backend/storage/repository/views.py:181-184` (`ViewsRepository._by_card`)

```python
found = defaultdict(list)
for row in rows:
    found[<колонка>].append(make(row))
```

Одно и то же дело: разложить строки выборки по значению одной колонки. Отпечатки
инициализации совпадают дословно (`1747d801` у обоих), различаются колонка
(`ext_id` против `item_id`) и то, что делают с результатом: `index` переводит в
`dict` с кортежами, `_by_card` отдаёт `defaultdict` со списками.

**Почему важно.** Оба класса — наследники `Repository`, то есть дом для общего
уже есть, и его отсутствие означает, что третий такой же запрос напишут в
третий раз. Это тот самый случай «два файла, которых слайс не касался, молчат
друг о друге».

**Что остаётся, если выносить:** `Repository._grouped(rows, key, make)` с `key`
как `Callable[[Row], object]`; `_by_card` тогда исчезает, `index` оставляет себе
перевод в кортежи. Оговорка честная: выигрыш — три строки, а на месте вызова
появляется лямбда `lambda row: row.ext_id`. Если исполнитель решит не выносить,
это надо записать вердиктом, а не оставить молча.

#### 5. Пролог `TmdbClient` написан трижды

`backend/sources/tmdb/client.py` — `search` (82-89), `card` (95-103),
`series_counts` (112-118). Во всех трёх одно и то же, дословно:

```python
if not isinstance(response, httpx.Response):
    return response
verdict = self._verdict(response)
if verdict is not None:
    return verdict
```

Правило 3 считает со второго появления, здесь их три. Записанный в
`not-duplicates.md:34` вердикт закрывает только первые две строки и только
между клиентами (`SteamClient.card` ≠ `GogClient._payload`); четырёхстрочный
пролог внутри одного класса не закрыт ничем.

**Что остаётся, если выносить:** метод `TmdbClient._asked(path, **params)`,
возвращающий `httpx.Response | Missing | Refusal`. Каждый из трёх методов
сокращается до вызова, guard-а и `parsed`. Выигрыш — четыре строки из
двенадцати; не обязательный, но и не выдуманный.

#### 6. `tests/backend/test_loading.py:candidate` собирает руками то, что собирают два общих помощника

- `tests/backend/test_loading.py:35-37` —
  `CardView(kind=Kind.MOVIE, source=Source.TMDB, source_id=..., title="Интерстеллар", poster_url=...)`
- `backend/model/view.py:58-76` (`view_from_hit`) + `tests/builders.py:100-107`
  (`hit`) — та же композиция, и именно так она записана в
  `tests/backend/test_search.py:43` и `tests/backend/test_view_types.py:28`

`view_from_hit(hit(source_id, poster_url=poster))` даёт объект, совпадающий с
`candidate(...)` поле в поле: `view_from_hit` переносит `kind`, `source`,
`source_id`, `title`, `original_title`, `year`, `synopsis`, `poster_url` и
оставляет `item_id` пустым.

**Почему важно.** Дело не только в двух строках. `Loader.ensure` в работе
получает **только** результат `view_from_hit` — других кандидатов не бывает, —
а тринадцать проверок в этом файле кормят его самодельным объектом. Появится у
`CardView` поле, которое `view_from_hit` переносит, и тесты загрузки продолжат
идти на карточке, которой в приложении не бывает. Ровно та же связка, которую
`test_search.py` уже собирает правильно.

**Что остаётся:** `view_from_hit` + `builders.hit`; тело `candidate` становится
одной строкой. `local_view` в `test_search.py:36-38` под это **не** подпадает:
ему нужен `item_id=7` при пустом `synced_at`, а `view_from_item(an_item(...))`
даёт `item_id=0` и заполненный `synced_at` — вердикт на эту пару ниже.

---

## Вынесенное общее: проверено

Потребители считаны вызовами в коде, не объявлениями.

| Вынос | Потребителей сегодня | Слито лишнее? | Вердикт |
|---|---|---|---|
| `sources/errors.py:parsed` | 11 вызовов в 7 модулях: gog ×3, tmdb ×3, poiskkino, unofficial, mdblist, omdb, steam | нет; `log` и `source` — два независимых измерения, подтверждено парой зеркал | **оправдан**; обошёл OMDB (Important 2) и Steam (Minor 3) |
| `sources/errors.py:refuse_code` | 3 прямых (mdblist, undocumented, mirror) + 2 через `mirror` | нет | **оправдан**; обошёл OMDB (Important 1) |
| `sources/errors.py:is_json` | 2 (`poiskkino._absent`, `mdblist._denied`) | нет — отвечает на вопрос, вывод оставляет вызывающему, и выводы у двоих разные | **оправдан** |
| `mirror.py:refuse_code` (обёртка над общей) | 2 (`poiskkino._verdict`, `unofficial._verdict`) | нет | **оправдан**; в одном ряду с `refuse_quota`/`rate`/`key`, снятие размазало бы `SOURCE` |
| `convert.py:identifier` | 4 вызова в 2 модулях (kinopoisk/parse ×2, tmdb/parse ×2) | нет — правило «отбрасываем по `is None` и `''`, а не по ложности» одно на обоих | **оправдан** |
| `kinopoisk/parse.py:_first_row` | 2 (`parse_poiskkino`, `parse_unofficial`) | нет — берёт только нулевую строку, пути к значениям внутри остались у каждого свои | **оправдан** |
| `views.py:_by_source` | 2 (`_external`, `_identifiers`) | нет — докстринг сам называет, почему остальные четыре не подошли | **оправдан** |
| `tmdb/parse.py:_item` | 2 (`parse_movie`, `parse_series`) | нет — различие уехало в `**extra` и в `_KEYS`, а не в флаг | **оправдан** |
| `tmdb/parse.py:_KEYS` | 2 (`_item`, `parse_search`) | нет | **оправдан**; имя совпало с `sections.py:_KEYS`, содержимое разное — вердикт ниже |
| `service/removal.py:remove_card` | 3 в бою (`Backend.delete_card`, `CardWriter.save` — ветка отмены и ветка ошибки) + 5 в тестах | нет | **оправдан**; порядок двух файлов базы иначе жил бы в трёх местах |
| `rows.py:to_tag` | 3 (`tags.list_for_kind`, `tags.tags_of`, `views._tags`) | нет | **оправдан** |
| `repository/entity.py:Entity` | 3 модуля (`credits`, `views`, `rows`) | нет — держит только различие человека и студии в схеме | **оправдан** |
| tests `fakes.py:FakeClient` | 4 модуля | нет | **оправдан** |
| tests `fakes.py:FakeCatalog` | 2 модуля (`test_loading`, `test_link_loading`) | нет | **оправдан** |
| tests `fakes.py:FakeSources` | 5 модулей | нет | **оправдан** |
| tests `builders.py:hit` | 2 модуля, 30+ вызовов | нет | **оправдан** |
| tests `builders.py:POSTER` | 3 модуля | нет — от `picture` отличается тем, что рисуется один раз на импорт | **оправдан** |
| tests `builders.py:an_item` | 12 модулей | нет — `id=0` жёстко, и единственное исключение (`test_linking.mine` с `id=1`) оставлено с записанным доводом | **оправдан** |
| tests `builders.py:card_parts` | 3 (`test_card_writer`, `test_linking`, `test_loading`) | нет | **оправдан** |
| tests `builders.py:poster_service` | 3 фикстуры с тремя разными транспортами | нет — различие осталось на месте вызова, а не уехало в параметр-флаг | **оправдан** |

**Ни одного «рано» и ни одного «слито лишнее».** Помощника с единственным
потребителем среди выносов нет. Лямбд «на каждом вызове там, где четыре явных
строки читались лучше» тоже нет: единственные лямбды — `produce` у `parsed`
(без неё разбор не отложить) и `lambda row: to_credit(row, entity)` в
`views._credits` (существовала до этих коммитов).

Раздел «Абстракции с одной реализацией» карты модулей чист от боевого кода: там
четыре записи, и все четыре — тестовые подставные (`Base`/`Note`,
`FakeCatalog`/`FakeCatalogWithSlug`, `FakeRatings`/`Breaking`,
`ViewsRepository`/`Forgetful`), то есть наследование ради подмены в тесте, а не
абстракция в ожидании второго.

---

## Разобрано и повтором не является

Пары проверены чтением обоих мест и отведены. Отсюда исполнитель дописывает
`docs/not-duplicates.md`.

- `backend/sources/ratings/omdb/client.py:OmdbClient.aclose` ≠ то же у GogClient,
  SteamClient, TmdbClient, MdbListClient, PoiskkinoClient, UnofficialClient —
  тело `await self._http.aclose()` совпадает дословно у всех семи (отпечаток
  `dd12822a`). Тот же довод, что записан для `name`: общий интерфейс клиента
  источника, общего предка у клиентов нет намеренно.
- `backend/sources/ratings/omdb/client.py:OmdbClient.__init__` ≠ то же у
  PoiskkinoClient, UnofficialClient, MdbListClient, TmdbClient — совпадает
  дословно (`66cb96a4`); `GogClient.__init__` ≠ `SteamClient.__init__` —
  совпадают между собой (`e3729e2f`), потому что ключа не требуют. Тот же довод
  про общий интерфейс: примесь ради двух присваиваний связала бы шесть
  независимых модулей.
- `backend/sources/ratings/mdblist/parse.py:parse_ratings` ≠
  `backend/sources/ratings/kinopoisk/parse.py:_rating` — оба сохраняют пустое
  вместо того, чтобы отбросить его, но по-разному и это разница по существу:
  MDBList пишет строку с `value=None` («у них этой оценки нет»), Кинопоиск на
  `None` не отдаёт строки вовсе, а ноль считает значением.
- `backend/model/view.py:view_from_hit` ≠ `backend/model/view.py:view_from_item` —
  два перевода в один тип из двух разных, и различие — сам шов `CardView`:
  первый оставляет `item_id` пустым и не знает про `runtime`, сезоны и
  `synced_at`, второй их переносит. Слитые, они потребовали бы объединения
  `SearchHit` и `Item`, а этот вердикт уже записан.
- `backend/sources/tmdb/parse.py:_KEYS` ≠
  `backend/storage/repository/sections.py:_KEYS` — совпало имя: первое ведёт от
  типа содержимого к именам полей в чужом теле, второе от ключа сортировки к
  колонке базы. Ни одно о другом не знает.
- `backend/sources/ratings/mdblist/client.py:MdbListClient._verdict` ≠
  `backend/sources/ratings/kinopoisk/poiskkino.py:PoiskkinoClient._verdict` —
  форма общая (`status = response.status_code`, цепочка `if`, общий `refuse_code`
  в хвосте), соответствие «код → действие» разное: у MDBList 202 означает
  «кеш строится», у зеркала 403 — квоту, а 404 требует разобранного тела. Тот же
  довод, что у записанной пары `poiskkino._verdict ≠ unofficial._verdict`.
- `backend/storage/repository/library.py:LibraryRepository.find_by_title` ≠
  `backend/storage/repository/library.py:LibraryRepository.search` — оба
  приводят строку `fold(…strip())` и отбирают по двум колонкам названий, но
  первое сравнивает целиком (предупреждение о совпадении), второе ищет подстроку
  с `autoescape` и отдаёт номера с порядком и порцией. Различие названо в
  докстринге `search`.
- `backend/storage/repository/credits.py:CreditRepository.credits_of` ≠
  `backend/storage/repository/views.py:ViewsRepository._credits` в части
  «необязательная колонка позиции и `order_by` с запасным ключом» — набор колонок
  и запасной ключ разные (`table.c.name` против `table.c.id`), а описатель
  `Entity` и сборка `Credit` у них уже общие. Пара самих методов записана.
- `tests/backend/test_genre_resolution.py:REFERENCE`/`MAP` ≠
  `tests/conftest.py:reference` ≠ `tests/conftest.py:film_genres` — три набора
  справочника, и каждый подобран под свою проверку: у первого игровые жанры с
  одним и тем же `ext_id` в двух пространствах Steam (иначе не проверить, что
  пространства спрашиваются порознь), у второго сборный `10759` и по строке на
  каждое чужое пространство, у третьего ровно два киножанра. Вторая пара уже
  записана, добавляется первый член.
- `tests/backend/test_offline.py:assemble` ≠ `tests/conftest.py:engine` — обе
  поднимают базу из `metadata`, но `assemble` затем закрывает движок и отдаёт
  собранный `Backend`: тот открывает свой движок сам по пути из настроек, и
  фикстуру `engine` ему не передать.
- `tests/backend/test_cover_reads.py:STORED` ≠ `tests/backend/test_posters.py:OTHER`
  ≠ `tests/builders.py:PICTURE` — три блоба байтов, и роли разные: `PICTURE` —
  общая «картинка», у которой проверяется побайтовая сохранность; `OTHER` —
  вторая строка для проверки перезаписи в хранилище; `STORED` — вторая с
  подписью JPEG, чтобы «отдали лежащее» отличалось от «скачали заново».
- `tests/backend/test_search.py:local_view` ≠ `backend/model/view.py:view_from_item`
  — похоже по делу, но `local_view` нужен `item_id=7` при пустом `synced_at`, а
  `view_from_item(an_item(...))` даёт `item_id=0` и заполненный `synced_at`;
  проверяется в этих тестах подстановка своей карточки по паре
  «источник + идентификатор», и оба поля к ней отношения не имеют.
- `tests/backend/sources/test_gog.py:answering` ≠
  `tests/backend/sources/conftest.py:responding` — обёртка в одну строку вокруг
  общей заготовки, а не вторая реализация.
- `backend/sources/registry.py:Sources.aclose` ≠
  `backend/service/posters.py:PosterService.aclose` — оба закрывают то, чем
  владеют, но первый идёт по объявленному списку соединений, второй по словарю
  клиентов и вдобавок закрывает хранилище.

---

## Recommendations

1. **Починить Important 1 и 2 одной правкой в `omdb/client.py`.** Причина у них
   общая: два выноса `errors.py` прошли мимо этого файла. Правка мелкая —
   один вызов `refuse_code` и один `parsed`.
2. **Проверить Important 2 мутацией.** После правки: сузить `BROKEN_BY_PARSING`
   до `(ValueError,)` в `errors.py` и убедиться, что тест OMDB на неразобранное
   тело краснеет. Сейчас его нечем уронить со стороны общего перечня — OMDB им не
   пользуется.
3. **По Minor 3–5 решить и записать.** Каждая — либо правка, либо строка в
   `docs/not-duplicates.md`. Оставленные без записи, они вернутся следующим
   проходом: ни одна из трёх пар не закрыта ни отпечатком, ни `deferred.md`.
4. **Дописать в `docs/not-duplicates.md` четырнадцать отведённых пар** из
   раздела выше. Самая нужная из них — `aclose` и `__init__` у семи клиентов:
   отпечатки у них совпадают дословно, и без вердикта каждый следующий проход
   будет находить их первыми.
5. **По `deferred.md` возражений нет.** Записанное там не разбиралось заново;
   доводы про `merge_results`/`parse_link`, второй ключ сортировки и подсказку в
   репозитории людей читаются как решения, а не как отложенный долг.

---

## Assessment

**Ready to merge?** With fixes

**Reasoning:** Выносы сделаны правильно — все одиннадцать имеют по два и больше
потребителей, ни один не склеил разные правила, и переусердствования нет ни в
одном. Но два из них прошли мимо OMDB: он до сих пор собирает отказ по коду
руками и ловит разбор своим `except` без записи в лог и с более узким перечнем
исключений — то есть вынос состоялся, а один из четырёх поводов остался как был.
Это правится в одном файле; после этого — merge.
