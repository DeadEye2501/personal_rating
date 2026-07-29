# Ревью повторов — план 3, задача 7

Дата 30.07.2026. Измерение: повторы во всём проекте (не только в новом
слайсе). Разобрано по `docs/module-map.md`, `docs/data-map.md`,
`docs/not-duplicates.md`; кандидаты подтверждены чтением обоих мест в коде.

## Находки

### Серьёзная (1)

**`backend/service/cards.py:CardWriter._refuse` повторяет
`backend/sources/errors.py:broken`.**

```python
# backend/service/cards.py
def _refuse(self, card: SourceCard, error: Exception) -> Refusal:
    return Refusal(source=str(card.item.source), reason=Reason.BROKEN,
                   detail=str(error))
```

```python
# backend/sources/errors.py
def broken(source: str, error: Exception) -> Refusal:
    return Refusal(source=source, reason=Reason.BROKEN, detail=str(error))
```

Тело идентично — `Refusal` с `reason=Reason.BROKEN` и `detail=str(error)` из
пойманного исключения; разница только в том, что `_refuse` сам достаёт строку
источника из `card.item.source`. `broken` — уже общий помощник, которым
пользуются клиенты источников (`backend/sources/gog/client.py:51`,
`backend/sources/steam/client.py:58,90`) ровно для этого же случая: «разбор
или запись упали — заверни в отказ». `CardWriter` его не импортировал и
завёл свою копию.

**Что оставить:** `broken` из `backend/sources/errors.py`. Правка в
`cards.py`:

```python
def _refuse(self, card: SourceCard, error: Exception) -> Refusal:
    return broken(str(card.item.source), error)
```

и заменить импорт `Reason, Refusal` на `Refusal, broken` (`Reason` в файле
после этого больше не используется).

### Незначительные (2)

**Идиома дедупликации с сохранением порядка повторена дважды новым кодом.**

- `backend/service/genres.py:27-28` (`resolved_genres`):
  ```python
  if genre_id not in found:
      found.append(genre_id)
  ```
- `backend/storage/repository/genres.py:38-39`
  (`GenresRepository.resolve`):
  ```python
  if row.genre_id not in resolved:
      resolved.append(row.genre_id)
  ```

Оба тела короче пяти инструкций, машинная проверка дублей их не увидит.
Это не повтор ответственности (см. «разобрано» ниже — уровни разные), но
сам приём «набрать список без повторов, сохранив порядок» списан дважды в
пределах одного слайса. Кандидат на común вынос (`dedup_preserving_order`
или подобный), но это два раза по две строки — решение на усмотрение
исполнителя, не блокирует коммит.

**Заведение справочника жанров сырым SQL повторено трижды.**

- `tests/backend/test_genres.py:21-36` (`reference(engine)`, уже был в базе
  до слайса);
- `tests/backend/test_card_writer.py:78-89` (`reference(engine)`, новый);
- `tests/backend/test_genre_resolution.py:28-33` (фикстура `genres`,
  новая) — те же два `INSERT INTO genre` / `INSERT INTO genre_map` через
  `connection.execute(text(...))`.

Значения в каждом свои и являются предметом конкретного теста — то же
основание, по которому в `not-duplicates.md` уже разведены
`migrations/versions/0002_genres.py:FILM` и
`tests/backend/test_genre_reference.py:FILM_GENRES`: одинаковые списки
здесь не ошибка, а необходимость. Но сама процедура — два `text()`-запроса
внутри `engine.begin()` — теперь повторена три раза тремя разными файлами.
Небольшой помощник вида
`insert_genre_map(engine, genre_rows: str, map_rows: str)` в
`tests/conftest.py` убрал бы обвязку, оставив в каждом файле только
значения. Не блокирует коммит: часть значений здесь и был до слайса, слайс
только добавил третье повторение того же приёма.

## Разобрано и признано разным

- `backend/service/genres.py:resolved_genres` ≠
  `backend/storage/repository/genres.py:GenresRepository.resolve` — разные
  уровни: `resolve` — SQL-запрос по одному пространству меток (жанры или
  теги отдельно), `resolved_genres` — оркестрация поверх него: группирует
  метки карточки по пространствам, зовёт `resolve` на каждое отдельно (у
  Steam номер `9` — это разные вещи в жанрах и в тегах) и снимает повторы
  уже между результатами разных пространств, чего сам `resolve` сделать не
  может. Слияние потребовало бы, чтобы репозиторий знал про группировку по
  пространствам, которая ему не нужна нигде больше.
- `backend/service/cards.py:CardWriter._attach` ≠
  `backend/storage/repository/credits.py:CreditRepository.ensure`/`attach`
  — `_attach` их не дублирует, а зовёт по очереди на каждый `Credit` карточки
  (`ensure`, потом `attach`). Это цикл-оркестратор поверх уже существующих
  методов репозитория, а не второй способ найти-или-завести и привязать.
- `backend/service/cards.py:CardWriter._refuse` ≠
  `backend/service/posters.py:PosterService._refuse` — разные сигнатуры и
  предметы: `PosterService._refuse(source, detail)` принимает уже готовую
  строку причины и добавляет префикс `poster:` к источнику — он не привязан
  к пойманному исключению и не может быть выражен через `broken`, который
  берёт `Exception` и сам вызывает `str()`. Дубль — только у `CardWriter`
  с `broken`, см. находку выше.
- `backend/service/cards.py:CardWriter.save` ≠ то, как клиенты источников
  (`refuse_undocumented`, `broken`, ручные `Refusal` в `TmdbClient`/
  `GogClient`) классифицируют отказ по сети — `save` не решает, какой
  `Reason` у отказа; она либо получает уже готовый `Refusal` от
  `PosterService.fetch`, либо строит свой через `_refuse`/`broken` после
  падения записи в базу. Классификация сетевых причин (`quota`, `rate`,
  `key`, `network`) в `cards.py` не воспроизводится вовсе.
- `tests/backend/test_card_writer.py:source_card`/`game_card`/
  `another_movie` ≠ `tests/conftest.py:card` и
  `tests/backend/test_library.py:make_item` — разные типы и разное
  назначение. `card` — фикстура, которая пишет строку через
  `LibraryRepository.create` и отдаёт готовый `id`; `make_item` — голый
  `Item` для тестов `LibraryRepository`, где предмет проверки — поля самой
  карточки. `source_card` строит целый `SourceCard` — `Item` плюс люди,
  студии, внешние идентификаторы и оценки, — потому что `CardWriter` пишет
  всё это разом в несколько репозиториев; без этих полей тесты `CardWriter`
  ничего не проверили бы. `game_card` и `another_movie` уже переиспользуют
  `source_card` через `overrides`, второго дубля внутри файла нет.
- `tests/backend/sources/conftest.py:unreachable` ≠ `responding` — разные
  виды отказа сети: `responding` строит форму ответа (код, тело), которую
  клиент разбирает как ответ; `unreachable` вообще не отвечает и роняет
  `httpx.ConnectError` до разбора — то, что наверху классифицируется как
  `Reason.NETWORK`, а не `Reason.BROKEN`.

## Вердикт

Коммитить как есть не стоит: `CardWriter._refuse` — прямой повтор уже
существующего общего помощника `broken`, который этот же модуль мог бы
просто позвать. Правка на одну строку и снятие неиспользуемого импорта
`Reason`. Остальные две находки незначительны и не блокируют — решение по
ним на усмотрение исполнителя.
