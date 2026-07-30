# Ревью повторов — план 4, задача 9 (перезапрос сериала по сроку)

Измерение: повторы во всём проекте, не в диффе. Дифф не читался.

## Рассмотренные кандидаты

1. `TmdbClient.series_counts` против `TmdbClient.card` и `.search`
   (`backend/sources/tmdb/client.py`) — три метода одной формы
2. `REFRESH_TTL` (`backend/service/loading.py`) против `VALUE_TTL`/`EMPTY_TTL`
   (`backend/storage/repository/external.py`) — 30 дней в двух местах
3. `Loader.refresh` против `Loader.ensure` (`backend/service/loading.py`)
4. `SeriesCounts` (`backend/model/item.py`) против `Item` (там же) и против
   `Ratings` (`backend/model/ratings.py`) / `Suggestion`
   (`backend/model/suggestion.py`)
5. `parse_series_counts` против `parse_series` (`backend/sources/tmdb/parse.py`)
6. `FakeTmdb` (`tests/backend/test_series_refresh.py`) против `FakeCatalog` в
   `tests/backend/test_loading.py` и в `tests/backend/test_search.py`
7. `series` (`tests/backend/test_series_refresh.py`) против `an_item` и
   `rated` (`tests/conftest.py`)

Итого рассмотрено: **7**. Подтверждённых повторов, требующих действия: **3**
(пп. 5, 6, 7).

## Разбор по каждому

### 1. `series_counts` / `card` / `search` — не повтор, идиома всего слоя источников

Прочитаны все три метода целиком (`backend/sources/tmdb/client.py:89-138`).
Общая форма действительно есть: запрос → «не ответ — верни как есть» →
`self._verdict(response)` → `try: return Found(parse(...)) except
BROKEN_BY_PARSING as error: logger.warning(...); return broken("tmdb",
error)`. `_verdict` уже забрал себе разбор отказа и взвод предохранителя —
ровно то общее, что стоило вынести.

То, что осталось, — не повтор задачи 9, а установленная идиома всего пакета
`backend/sources`: тот же блок `try / except BROKEN_BY_PARSING as error:
logger.warning(...); return broken(source, error)` найден ещё в восьми
местах шести файлов — `gog/client.py:53-57`, `steam/client.py:60-64,
93-96, 129-132`, `ratings/omdb/client.py:75-79`,
`ratings/kinopoisk/poiskkino.py:86-90`,
`ratings/kinopoisk/unofficial.py:54-58`, `ratings/mdblist/client.py:52-56`.
Различается в каждом источник ошибки, разбираемая функция и текст сообщения
в лог — то есть именно то, ради чего блок нельзя механически объединить.
Это тот же довод, что уже записан в `docs/not-duplicates.md` для пары
`SteamClient.card` ≠ `GogClient._catalog`: идиома повторяется осознанно,
короче она не станет, а вынести её можно было бы только вместе с самим
контрактом `Outcome`. Задача 9 не добавила нового повтора — только третий
экземпляр уже существовавшего внутри `TmdbClient`. Не повтор к действию.

### 2. `REFRESH_TTL` / `VALUE_TTL` — не повтор, разные основания при одном числе

Прочитаны `backend/service/loading.py:18-20` и
`backend/storage/repository/external.py:14-17`. Оба — `timedelta(days=30)`,
но governing разные данные: `REFRESH_TTL` мерит `Item.synced_at` (когда
перезапросить число сезонов и серий у видимой карточки), `VALUE_TTL` —
`ExternalRating.fetched_at` (когда протухла оценка агрегатора). Таблицы,
репозитории и вызывающий код не пересекаются.

Комментарий у `REFRESH_TTL` — «Срок тот же, что у оценок со значением» — это
не случайное совпадение (как у пары `RATE_BACKOFF` в `mirror.py` и
`tmdb/client.py`, уже разобранной в `docs/not-duplicates.md`), а осознанный
выбор числа по аналогии. Но политика при этом остаётся независимой:
`test_series_refresh.py` цепляется к значению самой константы
(`assert REFRESH_TTL == timedelta(days=30)`), а не к `VALUE_TTL`, и это
верно — смена срока годности оценок не должна молча менять частоту
перезапроса сериалов, и наоборот. Общей константой они не заменяются:
слитые, они дали бы ложную связь между двумя независимыми решениями.
Комментарий уже объясняет выбор числа — этого достаточно. Не повтор.

### 3. `Loader.refresh` / `Loader.ensure` — не повтор, разные пути записи

Прочитаны `backend/service/loading.py:36-94` целиком. Общее у них —
`self._sources.client_for(...)`, обёртка `answered(...)` и разбор `Outcome`
по типу, — но это общий язык всего сервисного слоя (`asking.answered`,
`Found`/`Missing`/`Refusal`), а не повтор друг друга. Дальше расходятся по
существу: `ensure` сперва проверяет `item_id` и `find_by_source`, спрашивает
клиента и обложку **разом** через `asyncio.gather` и передаёт результат
`CardWriter.save` — заводит строку с нуля. `refresh` проверяет тип
содержимого, источник и срок годности по `synced_at`, спрашивает только
дешёвый `series_counts` и правит **два поля существующей** строки через
`LibraryRepository.refresh_series_counts`. Это тот же довод, что уже
записан в `docs/not-duplicates.md` для пары `refresh_series_counts` ≠
`replace_fields`: два пути обновления заведены нарочно. Общего кода на
уровне тела нет ни строки. Не повтор.

### 4. `SeriesCounts` — не повтор ни с `Item`, ни с `Ratings`/`Suggestion`

`SeriesCounts` (`backend/model/item.py:29-34`) — два поля, `seasons` и
`episodes`. У `Item` (там же, `id=1-26`) есть одноимённые по смыслу
`seasons_count`/`episodes_count`, но это одно из четырнадцати полей строки
базы целиком, а `SeriesCounts` заведена как «единственное, что у карточки
перезапрашивается» — минимальная нагрузка между `TmdbClient.series_counts`
и `LibraryRepository.refresh_series_counts`, и в докстроке это сказано прямо.
Тот же довод, что уже записан в `docs/not-duplicates.md` для пары
`SearchHit` ≠ `Item`: общий тип потребовал бы необязательных
идентичности, `id`, `synced_at` и одиннадцати чужих полей в каждом месте,
где нужны только два числа. Не повтор.

`Ratings` (`backend/model/ratings.py`: `values`, `external_ids`) и
`Suggestion` (`backend/model/suggestion.py`: `entity_id`, `name`, `hint`,
`hint_item_id`) не делят с `SeriesCounts` ни одного поля по имени или
смыслу — сравнение отклонено сразу же при чтении, повтора нет.

### 5. `parse_series_counts` / `parse_series` — подтверждённый повтор

Прочитаны обе функции в `backend/sources/tmdb/parse.py:151-188`.
`parse_series` собирает `Item.seasons_count`/`episodes_count`:

```python
seasons_count=payload.get("number_of_seasons"),
episodes_count=payload.get("number_of_episodes"),
```

`parse_series_counts` — ровно то же самое чтение того же ключа, вторым
местом:

```python
return SeriesCounts(seasons=payload.get("number_of_seasons"),
                    episodes=payload.get("number_of_episodes"))
```

Две инструкции — ниже порога автоматической проверки (пять инструкций), и
поэтому хук на запись файла его не поймал; ровно тот случай, который
manifest-ревью обязано ловить руками. Функции возвращают разные типы
(`SourceCard` целиком против `SeriesCounts`) и это оправданно — `parse_series`
собирает карточку целиком, `parse_series_counts` заведена отдельно ради
дешёвого запроса без довеска. Но знание «оба числа лежат под этими двумя
ключами» продублировано, а не переиспользовано, хотя `parse_series_counts`
уже существует и делает ровно это.

**Что оставить:** `parse_series_counts` как источник знания о ключах;
`parse_series` должен звать её и брать поля из результата, а не читать
`payload.get(...)` заново:

```python
counts = parse_series_counts(payload)
...
seasons_count=counts.seasons,
episodes_count=counts.episodes,
```

### 6. `FakeTmdb` / `FakeCatalog` (×2) — подтверждённый повтор

Прочитаны все три конструктора: `tests/backend/test_series_refresh.py:14-24`,
`tests/backend/test_loading.py:25-35`, `tests/backend/test_search.py:20-33`.
`__init__` у всех трёх буквально совпадает — три инструкции, слово в слово:

```python
def __init__(self, outcome, name: str = "tmdb") -> None:
    self.outcome = outcome
    self.name = name
    self.asked = []
```

Различаются они только единственным методом-действием
(`card`/`search`/`series_counts`), который пишет в `self.asked` и отдаёт
`self.outcome`. У `FakeCatalog` из `test_search.py` в методе есть ещё ветка
`if isinstance(self.outcome, BaseException): raise self.outcome` — метода
это касается, не конструктора.

Ревью задачи 8 (`docs/reviews/2026-07-30-plan-04-task-08-duplicates.md`,
п. 4) уже сравнивало пару `FakeCatalog`/`FakeCatalog` и признало её не
повтором — но на основании, которое сейчас не подтверждается чтением: там
сказано, что `FakeCatalog` в `test_loading.py` не несёт атрибута `name`.
В прочитанном сейчас файле атрибут есть (`self.name = name`, со значением
по умолчанию `"tmdb"`) и используется — `Loader.ensure` зовёт
`client.name` при обёртке `answered(...)`. Вердикт задачи 8 к текущему
состоянию файла не относится; тот пробел не записан и в
`docs/not-duplicates.md`, так что переоценка не требует снятия чужого
вердикта. С третьим экземпляром (`FakeTmdb`) утроенный дословный
конструктор — это уже не совпадение по имени, а тройной повтор одной и той
же бухгалтерии подставного клиента: «запомни исход, запомни имя, веди
список запросов».

**Что оставить:** одну общую заготовку — например, класс с этим
конструктором в `tests/conftest.py`, рядом с `FakeSources`, у которой
`FakeTmdb`, `FakeCatalog` (`test_loading.py`) и `FakeCatalog`
(`test_search.py`) станут тремя тонкими наследниками с одним отличающимся
методом. Метод `test_search.py` с веткой `raise` остаётся в своём
наследнике как есть.

### 7. `series` против `an_item` — подтверждённый повтор

Прочитаны `tests/backend/test_series_refresh.py:27-30` и
`tests/conftest.py:77-91`.

```python
def series(synced_at, seasons=1, episodes=12) -> Item:
    return Item(id=0, kind=Kind.SERIES, source=Source.TMDB, source_id="83867",
                title="Andor", synced_at=synced_at, seasons_count=seasons,
                episodes_count=episodes)
```

`an_item` уже делает ровно это — со свободными полями и умолчаниями,
подставляемыми `dict.pop`:

```python
def an_item(source_id: str, title: str, **fields) -> Item:
    return Item(
        id=0,
        kind=fields.pop("kind", Kind.MOVIE),
        source=fields.pop("source", Source.TMDB),
        source_id=source_id,
        title=title,
        synced_at=fields.pop("synced_at", MOMENT),
        **fields,
    )
```

Вызов `an_item("83867", "Andor", kind=Kind.SERIES, synced_at=synced_at,
seasons_count=seasons, episodes_count=episodes)` строит тот же `Item`, что
и `series(...)`. В отличие от разобранной в `docs/not-duplicates.md` пары
`make_item` ≠ `card` (там одна сторона пишет в базу и отдаёт номер, другая
нет), здесь обе стороны делают одно и то же — отдают незаписанный `Item` —
и `series` не несёт собственного знания сверх того, что уже есть в
`an_item`; она просто задаёт другие умолчания (`Kind.SERIES` вместо
`Kind.MOVIE`, фиксированные `source_id`/`title`) и вручную повторяет
устройство `Item`.

**Что оставить:** `an_item` в `tests/conftest.py` как единственное место,
знающее умолчания `Item`. `series(synced_at, seasons=1, episodes=12)` в
`test_series_refresh.py` можно оставить как локальную обёртку ради
краткости вызовов в этом файле, но её тело должно звать `an_item(...)`, а
не пересобирать `Item` заново.

## Вердикт

Из семи кандидатов подтверждены три: `parse_series_counts`/`parse_series`
дублируют чтение двух полей ответа, три подставных клиента источника несут
дословно одинаковый конструктор, и тестовый `series()` пересобирает то, что
уже умеет `an_item`. Остальные четыре при чтении обоих мест разошлись по
существу — либо это установленная идиома всего пакета источников, либо
разные основания при одном числе, либо разные пути записи, либо тип с
явно узкой ролью против типа-строки базы.

- где / где / что оставить:
  `backend/sources/tmdb/parse.py:parse_series` /
  `backend/sources/tmdb/parse.py:parse_series_counts` — `parse_series`
  переиспользует `parse_series_counts` вместо повторного чтения
  `number_of_seasons`/`number_of_episodes`.
- где / где / что оставить:
  `tests/backend/test_series_refresh.py:FakeTmdb` /
  `tests/backend/test_loading.py:FakeCatalog` /
  `tests/backend/test_search.py:FakeCatalog` — общий конструктор уезжает в
  одну заготовку в `tests/conftest.py`, три класса остаются её тонкими
  наследниками с одним отличающимся методом.
- где / где / что оставить:
  `tests/backend/test_series_refresh.py:series` /
  `tests/conftest.py:an_item` — `an_item` остаётся источником умолчаний
  `Item`; `series` либо зовёт её внутри, либо не заводится вовсе.

**Готово к коммиту: С правками**
