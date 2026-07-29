# Ревью: повторы по картам (план 3, задачи 3–4)

Измерение — повторы во всём проекте по `docs/module-map.md`, `docs/data-map.md`
и `docs/not-duplicates.md`. Дифф не читался. Пары из `not-duplicates.md`
пропущены. Каждый кандидат ниже подтверждён чтением обоих мест в коде.

## Подтверждённые повторы

### 1. Вставка с обновлением по конфликту — четвёртая копия одного тела

Места:

- `backend/storage/repository/external.py:34` — `ExternalIdsRepository.put`
- `backend/storage/repository/external.py:68` — `ExternalRatingsRepository.record`
- `backend/storage/repository/ratings.py:27` — `RatingsRepository._write`
- `backend/storage/posters.py:64` — `PosterStore.put`

Тело у всех одно: собрать `statement = insert(<таблица>).values(...)`, затем
`statement.on_conflict_do_update(index_elements=[<ключевые колонки>], set_={<не
ключевые> из statement.excluded})` и отдать полученное исполнителю. У трёх из
четырёх правило совпадает дословно — «обновить из `excluded` всё, чего нет в
ключе»:

| место | ключ | обновляется из `excluded` |
|---|---|---|
| `ExternalIdsRepository.put` | `item_id`, `source` | `value` |
| `ExternalRatingsRepository.record` | `item_id`, `source` | `value`, `fetched_at` |
| `PosterStore.put` | `item_id` | `data`, `fetched_at` |

Четвёртое, `RatingsRepository._write`, из того же семейства с одной оговоркой:
`created_at` в `set_` намеренно не попадает, а `updated_at` берётся литералом
`now`, а не из `excluded` (значение то же — оно и вставлялось).

Это не «общее слово в имени» и не «один глагол над разными предметами»: тела
совпадают структурно, а расходятся только таблицей и списком колонок. Машинная
проверка дублей его не видит — сравнивается записываемый файл, а тела всё же
отличаются именами колонок. По правилу 3 выносить следовало уже на втором
появлении; сейчас в одном новом файле лежат сразу два.

Существующий вердикт `CreditRepository.attach ≠ TagsRepository.assign` сюда не
переносится: там общего было одно выражение `on_conflict_do_nothing()`, здесь —
две связанные инструкции с построением `set_` по `excluded`.

**Что должно остаться.** Общее — только построение оператора, не его
исполнение: `put` обязан идти через `_written` со своим `ExternalIdTaken`,
`record` — через `_run`. Значит, статический построитель рядом с уже
существующим `Repository._clearing` в `backend/storage/repository/base.py`:

```python
@staticmethod
def _upsert(table: Table, values: dict, keys: Sequence[str]) -> Insert:
    statement = insert(table).values(**values)
    return statement.on_conflict_do_update(
        index_elements=[table.c[name] for name in keys],
        set_={name: statement.excluded[name]
              for name in values if name not in keys},
    )
```

Минимум по правилу 3 — перевести на него `ExternalIdsRepository.put` и
`ExternalRatingsRepository.record`. `PosterStore` живёт на другом транспорте и
`Repository` не наследует (см. вердикты про `_read ≠ _row`), но построитель
оператора транспорта не касается — если он окажется доступен посторам, туда же
уедет и их `put`. `RatingsRepository._write` под общее правило не подходит
из-за `created_at` и остаётся как есть; параметра «а это не трогать» ради
одного вызывающего заводить нельзя (правило 8).

### 2. Тестовая картинка объявлена дважды

- `tests/backend/test_posters.py:9` — `PICTURE = b"\x89PNG\r\n\x1a\n" + b"0" * 512`
- `tests/backend/test_delete.py:10` — `PICTURE = b"\x89PNG\r\n\x1a\n" + b"0" * 128`

Одно и то же значение с точностью до длины набивки, и разница ничего не
проверяет: в `test_delete.py` `PICTURE` используется ровно один раз, в
`furnished`, где от неё нужны любые байты. `tests/conftest.py` заведён как раз
под «общее для тестов: фикстуры и минимальные строки», и `MOMENT` из него оба
модуля уже берут.

**Что должно остаться.** Одна константа в `tests/conftest.py`; `test_delete.py`
импортирует её оттуда, как импортирует `MOMENT as WHEN`. Длина остаётся та, что
нужна `test_posters.py` (512): там она участвует в проверке сохранности
содержимого.

## Разобрано и повтором не является

Кандидаты, поднятые картой и снятые чтением обоих мест. Годятся строками в
`docs/not-duplicates.md`.

- `ExternalIdsRepository.find_item` ≠ `CreditRepository._found_id` — общего один
  вызов `_maybe` с однострочным преобразователем; `_found_id` — обёртка без
  запроса, читающая `row.id`, `find_item` строит отбор по паре (source, value) и
  читает `row.item_id`. Общее уже вынесено в `Repository._maybe`.
- `ExternalIdsRepository.find_item` ≠ `LibraryRepository.find_by_source` — форма
  отбора по двум колонкам общая, предметы разные: номер карточки против
  собранной `Item`. Та же семья, что уже разобранная пара
  `CreditRepository.find_by_source ≠ LibraryRepository.find_by_source`.
- `_to_external_id`, `_to_external_rating` ≠ `_to_genre`, `_to_item`,
  `_to_rating`, `_named` — по преобразователю строки на таблицу, каждый знает
  свои колонки; ровно тот случай, ради которого заведён `Repository._mapped`.
  Внутри `external.py` их два, потому что таблиц две.
- `ExternalIdTaken` ≠ `IdentityTaken`, `ItemExists`, `TagExists` — пустые
  наследники `Exception` с разными докстрингами; различение занятого ключа и
  есть их содержание, и слитые они его сотрут.
- `ExternalRatingsRepository.stale_sources` ≠ `Breaker.is_open`,
  `until_midnight`, `_retry_after` — общего только арифметика над `datetime`.
  `is_open` держит один срок в памяти и сбрасывает его, `until_midnight` считает
  остаток суток, `_retry_after` читает заголовок, `stale_sources` отбирает из
  списка источников те, чья строка в базе старше своего срока. Ни строки общего
  кода.
- `VALUE_TTL`, `EMPTY_TTL` ≠ `RATE_BACKOFF`, `QUOTA_BACKOFF`,
  `UNDOCUMENTED_BACKOFF` — совпадает тип `timedelta`, дело разное: первые — срок
  годности записанного в базу, вторые — пауза перед следующим запросом к
  источнику. Первые читает хранилище, вторые — предохранитель.
- `backend/sources/ratings/kinopoisk/mirror.py:RATE_BACKOFF` ≠
  `backend/sources/tmdb/client.py:RATE_BACKOFF` — совпали и имя, и значение
  (минута), но основания разные и записаны рядом с каждым: у TMDB это её
  объявленная политика, у зеркал Кинопоиска — пять запросов в секунду на
  запасном и вовсе неописанный частотный ответ у основного. Общая константа
  связала бы два независимых источника: правка политики TMDB молча меняла бы
  поведение Кинопоиска.
- `backend/sources/convert.py:year` ≠ `backend/sources/steam/parse.py:_year` —
  сигнатура одна, разбор разный: первый берёт первые четыре знака машинной даты
  (`2014-11-05`, `2023.08.03`), второй ищет год регулярным выражением в дате,
  написанной человеком на языке запроса («18 мая. 2015 г.»). Слитые, они вернули
  бы ту самую ошибку, ради которой `_year` и заведён.
- `omdb/parse.py:OWNERS` ≠ `mdblist/parse.py:OWNERS` — совпало имя, ключи из
  разных словарей: у OMDB это человеческие названия («Rotten Tomatoes»), у
  MDBList — слаги («tomatoes»). Общая таблица позволила бы разобрать чужую метку
  в разборе соседа.
- `omdb/parse.py:parse_ratings` ≠ `mdblist/parse.py:parse_ratings` — совпало имя
  (поверхность разбора у всех источников зовётся одинаково), тела разные: OMDB
  вытаскивает число из «8.6/10» и «72%» и отсеивает второй приезд IMDb, MDBList
  берёт готовое число и сохраняет `null` как пустое значение.
- Тесты `test_external_ids.py` ≠ `test_external_ratings.py` — парные по виду
  проверки (`..._do_not_leak_into_another`, `..._go_away_with_the_card`) сторожат
  разные таблицы и разные каскады; общее у них — фикстуры `sessions`, `card`,
  `posters`, которые уже лежат в `tests/conftest.py`. Своих помощников ни один из
  двух модулей не завёл, дублировать нечего.

## Вердикт

**Найдено два повтора: один существенный, один мелкий.** Существенный —
`on_conflict_do_update` четвёртой копией, из них две в новом файле; чинится
построителем оператора в `Repository`. Мелкий — константа `PICTURE` в двух
тестовых модулях; чинится переездом в `tests/conftest.py`.

Остальные одиннадцать кандидатов подтверждения не получили и годятся строками в
`docs/not-duplicates.md`.
