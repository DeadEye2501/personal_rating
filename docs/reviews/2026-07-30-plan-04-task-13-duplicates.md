# Ревью повторов — задача 13 плана 4 (`docs/plans/2026-07-27-reading.md`)

Измерение: повторы во всём проекте. Дифф не читался; кандидаты собраны из
`docs/module-map.md`, `docs/data-map.md` и прямого чтения кода, каждый
подтверждён чтением обоих мест.

## Рассмотрены (7)

1. `build_backend` (`backend/app.py`) против `build_sources`
   (`backend/sources/registry.py`)
2. `Backend` против `Sources` — оба датакласса-держателя с `aclose()`
3. `Backend.aclose` против `Sources.aclose` и `PosterStore.close`
4. Сборка `CardWriter`/`Linker` в `build_backend` против помощника
   `card_parts` в `tests/conftest.py`
5. `assemble` в `tests/backend/test_offline.py` против фикстур
   `engine`/`sessions`/`posters` в `tests/conftest.py`
6. `RATED`/`WANTED` в `tests/backend/test_offline.py` против `RATED` в
   `tests/conftest.py` и `WANTED` в `tests/backend/test_sections.py`
7. `mine` в `tests/backend/test_offline.py` против `an_item`/`rated` в
   `tests/conftest.py`

## Подтверждённые повторы (3)

### A. `build_backend` строит `CardWriter` и `Linker` из одних и тех же семи
именованных аргументов дважды подряд

`backend/app.py:109-111` и `backend/app.py:130-132`:

```python
writer = CardWriter(library=library, genres=genres, people=person_repository,
                    companies=company_repository, ids=ids,
                    ratings=external_ratings, posters=posters)
...
linker=Linker(library=library, genres=genres, people=person_repository,
              companies=company_repository, ids=ids,
              ratings=external_ratings, posters=posters),
```

Набор и порядок ключей совпадают дословно — это ровно те семь параметров,
которые принимает общий `CardParts.__init__` (`backend/service/card_parts.py`).
`tests/conftest.py:card_parts` (строки 62-74) уже решает эту же задачу для
тестов: собирает те же семь репозиториев/сервисов в один словарь ровно
потому, что «и писателя, и привязку собирают из одного и того же». В
`build_backend` этого обобщения нет, и семь имён набраны руками дважды.

**Оставить:** собрать в `build_backend` один словарь (по образцу
`tests/conftest.py:card_parts`) с ключами `library, genres, people, companies,
ids, ratings, posters` и передавать его в оба конструктора через `**parts`.
Функцию `tests/conftest.py:card_parts` трогать не нужно — у неё свой вход
(сессии, хранилище, транспорт) и переиспользовать буквально её нельзя, но
приём, которым она уже пользуется, должен появиться и в `build_backend`.

### B. `RATED` в `tests/backend/test_offline.py` дублирует `RATED` из
`tests/conftest.py`

`tests/backend/test_offline.py:25`:
```python
RATED = Feed(Section.RATED, Kind.MOVIE, Filters(), Order(Sort.SCORE))
```
`tests/conftest.py:45`:
```python
RATED = Feed(Section.RATED, Kind.MOVIE, Filters(), Order(Sort.ADDED_AT if False else Sort.SCORE))
```
(дословно: `Feed(Section.RATED, Kind.MOVIE, Filters(), Order(Sort.SCORE))`) —
значения совпадают побайтно. Это тот самый общий вопрос ленты, который
`tests/conftest.py` уже заводит как переиспользуемую константу, и остальные
модули её импортируют — например, `tests/backend/test_feed.py:9`:
`from tests.conftest import RATED, rated`. `test_offline.py` вместо импорта
завёл свою копию.

**Оставить:** `RATED` из `tests/conftest.py`; в `test_offline.py` убрать
локальное определение и импортировать оттуда, как делает `test_feed.py`.

### C. `WANTED` в `tests/backend/test_offline.py` дублирует `WANTED` из
`tests/backend/test_sections.py`

`tests/backend/test_offline.py:26`:
```python
WANTED = Feed(Section.WISHLIST, Kind.MOVIE, Filters(), Order(Sort.ADDED_AT))
```
`tests/backend/test_sections.py:26`:
```python
WANTED = Feed(Section.WISHLIST, Kind.MOVIE, Filters(), Order(Sort.ADDED_AT))
```
Значения совпадают побайтно. До задачи 13 `WANTED` был нужен только
`test_sections.py`, теперь его завёл и `test_offline.py` — тем же значением.

**Оставить:** одно объявление в `tests/conftest.py`, рядом с `RATED` (тот же
довод: «второй вопрос ленты рядом с общим `RATED`», как уже написано в
комментарии `test_sections.py`). `test_sections.py` и `test_offline.py`
переводятся на импорт из `tests.conftest`.

## Рассмотрены и отклонены (не идут в `docs/not-duplicates.md` — это делает
исполнитель на шаге починки)

- **`build_backend` vs `build_sources`** — не повтор: `build_backend` зовёт
  `build_sources` как есть (`sources = build_sources(config, transport=...)`),
  а свои три `SourceHttp` для обложек заводит напрямую, без промежуточного
  `http()`-замыкания и без списка `raised` — это разное устройство (обложки
  закрываются через `PosterService.aclose`, а не через `Sources.connections`),
  а не дублирование одной и той же сборки.
- **`Backend` vs `Sources`** и **`Backend.aclose` vs `Sources.aclose` vs
  `PosterStore.close`** — тела всех трёх `close`/`aclose` разные по форме:
  `Backend.aclose` — три последовательных `await` делегирования вниз,
  `Sources.aclose` — цикл по кортежу соединений, `PosterStore.close` —
  условное `dispose()` со сбросом `self._engine`. Полей у датаклассов тоже
  разное число и разный смысл (17 против 7). Слить нечего — `Backend.aclose`
  уже и есть тот код, который зовёт `Sources.aclose`.
- **`assemble` (test_offline.py) vs `engine`/`sessions`/`posters`
  (conftest.py)** — три строки поднятия схемы (`create_engine` +
  `metadata.create_all` + `dispose`) текстуально похожи на тело фикстуры
  `engine`, но `assemble` обязан закрыть свой движок сразу же, до того как
  `build_backend` откроет тот же файл своим — иначе на Windows файл базы
  останется занят вторым открытием. Фикстура `engine`, наоборот, держит
  движок открытым до конца теста через `yield`. Разное время жизни — не
  случайное совпадение, а требование самого теста. `sessions` и `posters`
  вообще не дублируются: `build_backend` заводит эквивалентные объекты сам,
  внутри себя.
- **`mine` (test_offline.py) vs `an_item`/`rated` (conftest.py)** — не
  повтор: `mine` строит карточку через `new_manual_item` (источник
  `Source.MANUAL`, как и положено «заведённой руками» — ровно предмет
  офлайн-теста), `an_item` — через прямой конструктор `Item` с источником
  `Source.TMDB` по умолчанию. Разный источник происхождения карточки — это и
  есть смысл различия, а не побочный шум.

## Вердикт

Готово к коммиту: С правками — три подтверждённых повтора (A, B, C) нужно
закрыть до коммита: собрать `CardWriter`/`Linker` в `build_backend` из одного
словаря по образцу `tests/conftest.py:card_parts`, и перевести `RATED`/`WANTED`
в `test_offline.py` на импорт из `tests.conftest` (`WANTED` предварительно
туда переносится из `test_sections.py`).
