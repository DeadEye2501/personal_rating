# Ревью повторов — план 4, задача 10 (обогащение оценками)

Измерение: повторы во всём проекте, не в диффе. Карты (`docs/module-map.md`,
`docs/data-map.md`) прочитаны целиком, `docs/not-duplicates.md` — тоже; пары,
уже разобранные там, заново не поднимались.

## Рассмотренные кандидаты — 11

1. `_union` (`backend/service/enrich.py`) ↔ `GenresRepository.resolve`
   (`backend/storage/repository/genres.py`)
2. `_union` ↔ `resolved_genres` (`backend/service/genres.py`)
3. `_union` ↔ `_genres_of` (`backend/service/search.py`)
4. `_union` ↔ `merge_results` (`backend/model/results.py`)
5. `Enricher.enrich` ↔ `Loader.ensure` / `Loader.refresh` (`backend/service/loading.py`)
6. `Enricher._write` ↔ `CardParts._write_external` (`backend/service/card_parts.py`)
7. `Enricher._imdb_id` ↔ `ExternalIdsRepository.ids_of` / `.find_item` (`backend/storage/repository/external.py`)
8. `Enricher._keep` ↔ занятый идентификатор в `CardWriter` (`backend/service/cards.py`) и `Linker` (`backend/service/linking.py`)
9. `PROVIDES` у трёх клиентов ↔ `OWNERS` в `omdb/parse.py` и `mdblist/parse.py`
10. `FakeRatings` (`tests/backend/test_enrich.py`) ↔ `FakeClient` / `FakeCatalog` / `FakeTmdb`
11. `stored_ratings` (`tests/backend/test_enrich.py`) ↔ похожие помощники в других тестовых модулях (напр. `columns` в `test_histogram.py`)

## Подтверждённый повтор — 1 (кластер из четырёх объявлений)

### Снятие повторов с сохранением порядка — четыре реализации одного алгоритма

Прочитаны все четыре тела:

- `backend/service/enrich.py:_union` (9 строк) — ручной цикл: `seen: list`,
  вложенный `for group in groups: for source in group: if source not in seen:
  seen.append(source)`.
- `backend/storage/repository/genres.py:GenresRepository.resolve` (строка 37)
  — `list(dict.fromkeys(row.genre_id for row in rows))`.
- `backend/service/genres.py:resolved_genres` (строка 28) — `list(dict.fromkeys(found))`
  после того как `found` собран из нескольких пространств циклом `extend`.
- `backend/service/search.py:_genres_of` (строки 109–113) — тот же ручной
  приём, что у `_union`, дословно: `found: list`, `for space, ext_id in ...:
  for genre in index[space].get(ext_id, ()): if genre not in found:
  found.append(genre)`.

Все четыре решают одну задачу — «собрать значения из нескольких групп,
оставить первое вхождение, сохранить порядок» — над разными, но одинаково
хэшируемыми типами (`RatingSource`, `int`, `Genre` — `Genre` заморожен и
хэшируется дефолтно). В отличие от пар вроде `to_genre`/`to_item` из
`not-duplicates.md`, где предмет (колонки таблицы) заставляет держать сборщики
разными, здесь предмет ни на что не влияет: алгоритм полностью общий над
`Hashable`. Пары `resolve`/`resolved_genres` уже используют один и тот же
приём (`dict.fromkeys`), а `_union`/`_genres_of` — другой (ручной `if x not in
seen: seen.append(x)`), при этом делают буквально одно и то же с точностью до
имени переменной. Это ровно тот повтор короче пяти инструкций и внутри тела
функции, который автоматика по манифесту не ловит, а ручной проход — должен.

`_union` из этого слайса — самая общая по форме (`Iterable[Iterable[T]]`,
накрывает и одну группу, и много), и её тело короче как одна строка через
`dict.fromkeys`, а не ручной цикл. Проверено также против `merge_results`
(`backend/model/results.py`) — там другой алгоритм: `seen` копит не сами
значения, а ключ для двух разных списков с приоритетом одного над другим и
подменой значения (`mine.get(key, view)`), а не просто фильтрация одного
потока. Это не повтор, довод как у `refuse_undocumented` ≠ `classify` — общий
глагол «отбросить виденное», разное дело.

**Что оставить.** Один общий чистый хелпер вида
`def unique(items: Iterable[T]) -> list[T]: return list(dict.fromkeys(items))`,
доступный и слою `storage`, и слою `service` — по прецеденту `merge_results`,
которая лежит в `backend/model/results.py` именно потому, что нужна больше
чем одному слою. `_union` в `enrich.py` переписывается через него
(`unique(source for group in groups for source in group)`), `resolved_genres`
и `GenresRepository.resolve` зовут его вместо своего `dict.fromkeys`, а
`_genres_of` — вместо ручного цикла (после того как внутренний генератор
сведён к плоскому). Отдельная функция `_union` с текущим ручным телом не
остаётся ни в каком виде: она дублирует то, что уже есть в двух местах, и хуже
— другим приёмом.

## Проверено и не подтверждено

- **`Enricher.enrich` ↔ `Loader.ensure`/`Loader.refresh`.** Общая форма —
  «спросить источник, записать» — намеренно повторяется у всех кругов
  загрузки (спека это описывает как три круга), но исполняемого кода общего
  нет: разные критерии раннего выхода, разная конкурентность, разные цели
  записи. Как `SteamClient.card` ↔ `GogClient._catalog` в
  `not-duplicates.md` — общий глагол, разное дело.
- **`Enricher._write` ↔ `CardParts._write_external`.** `_write_external`
  пишет уже готовый `SourceCard` без ветвлений и без перехвата занятости;
  `_write` разбирает список сетевых исходов, ведёт `values`/`answers`/`refused`
  и решает, когда писать пустое значение вместо найденного. Общих строк нет.
- **`Enricher._imdb_id` ↔ `ExternalIdsRepository.ids_of`/`find_item`.**
  `_imdb_id` не повторяет код репозитория — он зовёт `ids_of` и фильтрует
  результат в Python. Это вопрос расположения (стоило бы это быть отдельным
  запросом в репозитории), а не повтора кода: аналогичного точечного запроса
  «значение по item_id и источнику» в репозитории пока нет ни для одной
  сущности, второй реализации у него нет — по правилу манифеста абстракция
  раньше второго случая не выносится.
- **`Enricher._keep` ↔ занятый идентификатор в `CardWriter`/`Linker`.** Три
  разные политики: `CardWriter` не ловит `ExternalIdTaken` точечно — она
  вылетает и откатывает всю карточку через общий `except Exception`;
  `Linker._check_identifiers` проверяет занятость **до** любой записи и
  поднимает `ItemExists`; `_keep` ловит `ExternalIdTaken` только вокруг
  одного `put` и продолжает, залогировав. Совпадает только имя исключения,
  которое каждый перехватывает на своём уровне.
- **`PROVIDES` у клиентов ↔ `OWNERS` в разборах OMDB и MDBList.** `PROVIDES`
  — объявление возможностей для реестра и `Enricher` (`ClassVar[tuple]`),
  `OWNERS` — карта чужих строковых ключей в `RatingSource` внутри разбора,
  наружу не выходит. У Кинопоиска `OWNERS` нет вовсе — `PROVIDES` там одна
  запись без всякой карты. Множества значений `OWNERS` у OMDB и MDBList
  совпадают с их `PROVIDES` по содержанию, но это не повтор кода, а факт,
  который и охраняет `test_every_rating_client_declares_exactly_what_it_brings` —
  ровно на случай, если они разойдутся. Тот же довод, что у пары `OWNERS`
  ≠ `OWNERS` в `not-duplicates.md`: ключи и предмет разные.
- **`FakeRatings` ↔ `FakeClient`/`FakeCatalog`/`FakeTmdb`.** Это и есть
  предусмотренное расширение общего `FakeClient`: `FakeCatalog` добавляет
  `card`/`search`, `FakeTmdb` — `series_counts`, `FakeRatings` — `PROVIDES` и
  `ratings`. Наследование, а не повтор.
- **`stored_ratings` ↔ похожие тестовые помощники.** Читает одну конкретную
  таблицу через `ExternalRatingsRepository`; у аналогов вроде `columns` в
  `test_histogram.py` — другой репозиторий и другая форма результата. Разный
  предмет, как у пар `_of`/`_of` в `not-duplicates.md`.

## Вердикт

Готово к коммиту: **С правками** — единственная правка: убрать ручной повтор
снятия дублей (`_union`, `_genres_of`) и общий `dict.fromkeys(...)` (`resolve`,
`resolved_genres`), свести к одной функции, как описано выше.
