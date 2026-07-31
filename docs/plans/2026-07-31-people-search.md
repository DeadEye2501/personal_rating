# План 11. Поиск по человеку и компании

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** щелчок по имени в карточке показывает всё, что с этим человеком
связано — свои карточки и работы, о которых вы не знали. У игр то же самое с
разработчиком и издателем, но только по своей библиотеке.

**Порядок:** после плана 7. Бэкендовая половина ни от чего не зависит, но
последняя задача проводит клик в ленте, а лента появляется там. Делается до
плана 10.

**Архитектура.** Решение пользователя от 31.07.2026, дословно.

**Строка поиска — широкий общий поиск:** по людям, по названию и по
оригинальному названию.

**Клик по человеку — два случая:**

1. **Есть внешний идентификатор.** Все карточки с ним и только с ним, во
   внутренней базе и во внешней. Внутри — по внутреннему идентификатору,
   однозначно; снаружи — по внешнему.
2. **Внешнего идентификатора нет.** Ответ складывается из двух: внутри по
   внутреннему идентификатору всё, что с этим человеком связано; снаружи — все
   карточки, где есть человек с таким именем, то есть этот и все тёзки.

| Кто | Внутренняя половина | Внешняя половина |
|---|---|---|
| человек с идентичностью TMDB | `people.items_of` | фильмография по внешнему идентификатору |
| человек, заведённый руками | `people.items_of` | `/search/person` по имени, потом фильмографии всех найденных |
| компания у игр | `companies.items_of` | **нет:** ни Steam, ни GOG не умеют |

**Внутренняя половина всегда по внутреннему идентификатору** — он есть у всех, по
нему и кликают. Ветвится только внешняя.

**Магазины не трогаются вовсе, и это замерено, а не предположено.** Steam по
разработчику находит, но отдаёт разметку витрины; GOG молча игнорирует параметр
и возвращает весь каталог — 12 511 строк вместо игр студии. Разметку не
разбираем: правило пользователя — нет валидной ручки, значит только своя база.

**Бэкенд был закрыт 31.07.2026, и этот план открывает его заново.** После него —
своё ревью, тем же порядком, что и закрывающее: измерениями, отдельными
агентами.

**Стек:** тот же. Ни одной новой зависимости.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от планов 1–5 и 7.** Готовы схема, репозитории, шесть клиентов, мост
  и лента с карточкой.
- **В сеть тесты не ходят.** Ответы источников записаны в `tests/fixtures/`;
  сеть подменяется `httpx.MockTransport`.
- **Исключений из клиента источника наружу не летит.** Отказ — один из трёх
  исходов: `Found`, `Missing`, `Refusal`.
- **Отрицательный факт пишется только по разобранному телу.** Правило проекта,
  и оно уже нарушалось дважды — у GOG и у MDBList.
- **Разметку не разбираем ни при каких условиях.**
- **Байтовые литералы только ASCII.**
- **Дописывая метод в чужой файл, сверяйся с файлом.** Имена полей, констант и
  псевдонимов таблиц берутся оттуда, а не из головы.
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ backend/
│  ├─ model/credit.py             + entity_id
│  ├─ model/search.py             + PersonHit
│  ├─ sources/tmdb/
│  │  ├─ client.py                + credits_of, find_people
│  │  └─ parse.py                 + parse_credits, parse_people
│  ├─ storage/
│  │  ├─ rows.py                  to_credit заполняет entity_id
│  │  └─ repository/
│  │     ├─ library.py            search расширяется на состав
│  │     └─ credits.py            + find_identity, + колонка id
│  ├─ service/people.py           поиск по человеку: два пути
│  └─ app.py                      + finder в сборке
├─ bridge/search.py               + by_person
├─ client/
│  ├─ components/Facts.svelte     имя становится кнопкой поиска
│  └─ app/SearchScreen.svelte     принимает поиск по человеку
└─ tests/
   ├─ backend/test_credit_search.py    поиск по составу
   ├─ backend/sources/test_tmdb_people.py
   ├─ backend/test_people_search.py    сервис: два пути
   ├─ bridge/test_bridge_search.py     + by_person
   └─ fixtures/tmdb/                   три новых ответа
```

---

### Задача 1: Поиск по составу в своей базе

Сейчас `LibraryRepository.search` ищет по двум названиям подстрокой. Строка
поиска обязана быть шире: **по людям, по названию и по оригинальному названию**.

**Это про строку поиска, а не про клик.** Клик по человеку ищет внутри по
внутреннему идентификатору и в эту функцию не заходит вовсе.

**Ищем одним запросом.** Отдельного метода не заводим: это тот же поиск, просто
он смотрит ещё в две таблицы. Заведи мы второй — страница выбирала бы между ними,
то есть знала бы про схему.

**`distinct` обязателен.** Один человек бывает на карточке и режиссёром, и
актёром — это две строки связи и одна карточка. Та же ловушка уже описана в
`items_of`, и там она закрыта.

**Файлы:**
- Изменить: `backend/storage/repository/library.py:93-111`
- Создать: `tests/backend/test_credit_search.py`

**Интерфейсы:**
- Потребляет: `person_credit`, `company_credit`, `person`, `company` из
  `backend.storage.tables`.
- Отдаёт: `search(kind, query, limit)` — та же сигнатура, шире охват.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_credit_search.py`:

```python
"""Поиск по своей библиотеке смотрит и в состав, а не только в названия."""

from backend.model import Credit, Kind, PersonRole, CompanyRole
from backend.storage.repository.credits import companies, people
from backend.storage.repository.library import LibraryRepository
from tests.builders import an_item


async def test_finds_by_the_name_of_a_person(sessions, migrated):
    """Клик по заведённому руками человеку иначе не нашёл бы ни одной его
    работы: до этого поиск смотрел только в два названия."""
    library = LibraryRepository(sessions)
    crew = people(sessions)
    item_id = await library.create(an_item(title="Начало"))
    entity_id = await crew.create_manual("Кристофер Нолан")
    await crew.attach(item_id, entity_id, PersonRole.DIRECTOR)

    assert await library.search(Kind.MOVIE, "нолан", limit=20) == [item_id]


async def test_finds_by_the_name_of_a_company(sessions, migrated):
    """У игр вместо людей студии, и путь у них тот же."""
    library = LibraryRepository(sessions)
    studios = companies(sessions)
    item_id = await library.create(an_item(kind=Kind.GAME, title="Ведьмак 3"))
    entity_id = await studios.create_manual("CD PROJEKT RED")
    await studios.attach(item_id, entity_id, CompanyRole.DEVELOPER)

    assert await library.search(Kind.GAME, "projekt", limit=20) == [item_id]


async def test_still_finds_by_title(sessions, migrated):
    """Прежнее поведение не потеряно: поиск по названию остаётся."""
    library = LibraryRepository(sessions)
    item_id = await library.create(an_item(title="Интерстеллар"))

    assert await library.search(Kind.MOVIE, "интерстел", limit=20) == [item_id]


async def test_a_card_is_returned_once_even_with_two_roles(sessions, migrated):
    """Один человек бывает и режиссёром, и актёром — это две строки связи и одна
    карточка. Без `distinct` она приехала бы дважды и заняла бы два места в
    выдаче."""
    library = LibraryRepository(sessions)
    crew = people(sessions)
    item_id = await library.create(an_item(title="Ирландец"))
    entity_id = await crew.create_manual("Мартин Скорсезе")
    await crew.attach(item_id, entity_id, PersonRole.DIRECTOR)
    await crew.attach(item_id, entity_id, PersonRole.ACTOR, position=3)

    assert await library.search(Kind.MOVIE, "скорсезе", limit=20) == [item_id]


async def test_the_kind_still_narrows(sessions, migrated):
    """Фильм «Ведьмак» и игра «Ведьмак» — разные вещи, и поиск по составу это
    правило не отменяет."""
    library = LibraryRepository(sessions)
    studios = companies(sessions)
    game = await library.create(an_item(kind=Kind.GAME, title="Ведьмак 3"))
    entity_id = await studios.create_manual("CD PROJEKT RED")
    await studios.attach(game, entity_id, CompanyRole.DEVELOPER)

    assert await library.search(Kind.MOVIE, "projekt", limit=20) == []


async def test_a_person_of_another_card_does_not_bring_this_one(sessions, migrated):
    """Проверяется привязка, а не наличие строки в таблице: без условия по
    `item_id` в подзапросе нашлась бы любая карточка, пока в базе есть хоть один
    человек с таким именем."""
    library = LibraryRepository(sessions)
    crew = people(sessions)
    theirs = await library.create(an_item(title="Начало"))
    mine = await library.create(an_item(title="Одиссея"))
    entity_id = await crew.create_manual("Кристофер Нолан")
    await crew.attach(theirs, entity_id, PersonRole.DIRECTOR)

    assert await library.search(Kind.MOVIE, "нолан", limit=20) == [theirs]
    assert mine not in await library.search(Kind.MOVIE, "нолан", limit=20)


async def test_the_register_does_not_count(sessions, migrated):
    """Встроенный в SQLite `lower()` кириллицу не понимает — обе стороны идут
    через ту же `fold`, что и названия."""
    library = LibraryRepository(sessions)
    crew = people(sessions)
    item_id = await library.create(an_item(title="Начало"))
    entity_id = await crew.create_manual("Кристофер Нолан")
    await crew.attach(item_id, entity_id, PersonRole.DIRECTOR)

    assert await library.search(Kind.MOVIE, "НОЛАН", limit=20) == [item_id]
```

- [ ] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/backend/test_credit_search.py -v`
Ожидание: FAIL — четыре теста про состав падают, два про название проходят.

- [ ] **Шаг 3: Расширить поиск**

В `backend/storage/repository/library.py` заменить условие в `search`:

```python
    async def search(self, kind: Kind, query: str, limit: int) -> list[int]:
        """Поиск по своей библиотеке: вхождение в любое из двух названий или в
        имя связанного человека либо студии.

        В отличие от `find_by_title`, который сравнивает названия целиком ради
        предупреждения о совпадении, здесь нужна подстрока. `autoescape` гасит
        `%` и `_` в самом запросе: иначе «%» вывалил бы всю библиотеку.

        `distinct` обязателен: один человек бывает на карточке и режиссёром, и
        актёром — это две строки связи и одна карточка."""
        needle = fold(query.strip())
        if not needle:
            return []

        rows = await self._rows(
            select(item_table.c.id)
            .where(
                item_table.c.kind == kind,
                folded(item_table.c.title).contains(needle, autoescape=True)
                | folded(item_table.c.original_title).contains(
                    needle, autoescape=True
                )
                | _named(person, person_credit, needle)
                | _named(company, company_credit, needle),
            )
            .distinct()
            .limit(limit)
        )
        return [row.id for row in rows]
```

и рядом с модулем — общее для двух половин состава:

```python
def _named(table, credit, needle):
    """Связан ли с карточкой кто-то с таким именем. Вынесено, потому что людей и
    студий две штуки, а запрос у них один и тот же с точностью до таблицы."""
    return exists(
        select(credit.c.item_id)
        .join_from(credit, table, credit.c[f"{table.name}_id"] == table.c.id)
        .where(credit.c.item_id == item_table.c.id,
               folded(table.c.name).contains(needle, autoescape=True))
    )
```

Имя колонки связи собирается по имени таблицы — так же, как в
`storage/entity.py`, где это уже сделано и объяснено.

- [ ] **Шаг 4: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/backend/ -v`
Ожидание: PASS. Прежние тесты поиска обязаны остаться зелёными: охват
расширился, поведение по названиям не изменилось.

- [ ] **Шаг 5: Коммит**

```bash
git add backend/storage/repository/library.py tests/backend/test_credit_search.py
git commit -m "feat: поиск по своей библиотеке смотрит и в состав"
```

---

### Задача 2: Фильмография у TMDB

Один запрос отдаёт всё, что человек сделал. Замерено: у Кристофера Нолана 78
строк съёмочной группы и 33 актёрских, у Киллиана Мёрфи — 70 актёрских.

**Строка фильмографии по составу полей совпадает с выдачей поиска** — замерено.
`id`, `title`, `original_title`, `release_date`, `poster_path`, `overview`,
`genre_ids`, `vote_average`: ровно то, из чего собирается `SearchHit`, и
отдельного запроса за жанрами не нужно.

**Разбирать надо оба списка.** У режиссёра работы лежат в `crew`, у актёра — в
`cast`; у Нолана есть и то и другое.

**Порций у фильмографии нет.** TMDB отдаёт её целиком, и резать нечего: 78 строк
у самого плодовитого — это меньше, чем две страницы обычной выдачи.

**Файлы:**
- Изменить: `backend/sources/tmdb/client.py`, `backend/sources/tmdb/parse.py`
- Создать: `tests/backend/sources/test_tmdb_people.py`
- Создать: `tests/fixtures/tmdb/person_credits_movie.json`,
  `person_credits_tv.json`

**Интерфейсы:**
- Потребляет: `parse_search`-подобный разбор, `SearchHit`.
- Отдаёт: `TmdbClient.credits_of(person_id, kind) -> Outcome`,
  `parse_credits(payload, kind) -> list[SearchHit]`.

- [ ] **Шаг 1: Записать ответы источника**

Живьём, тем же инструментом, которым записаны остальные фикстуры:

```bash
pipenv run python scripts/record_fixtures.py
```

Дописать в него три ручки: `/person/525/movie_credits`,
`/person/525/tv_credits`, `/search/person?query=Christopher Nolan`. Файл
инструмента одноразовый и в чистовик не едет — он уже есть и уже так
используется.

**Записывать надо настоящий ответ, а не урезанный руками.** Фикстура, из которой
выкинули «лишние» поля, перестаёт ловить то, ради чего заведена: у GOG именно на
подогнанной под ожидание фикстуре клиент вёл себя правильно, а живьём был сломан
целиком.

- [ ] **Шаг 2: Написать падающий тест**

Создать `tests/backend/sources/test_tmdb_people.py`:

```python
"""Фильмография человека: один запрос, два списка."""

from backend.model import Found, Kind
from tests.fakes import counting, responding


async def test_a_director_is_found_in_the_crew(tmdb_client):
    """У режиссёра работы лежат в `crew`, и разбор обязан их видеть."""
    outcome = await tmdb_client.credits_of("525", Kind.MOVIE)

    assert isinstance(outcome, Found)
    titles = [hit.title for hit in outcome.value]
    assert "Начало" in titles


async def test_an_actor_is_found_in_the_cast(tmdb_client):
    """У актёра — в `cast`. Разбирать один список значило бы потерять половину
    людей: у Мёрфи 70 актёрских работ и 9 в съёмочной группе."""
    outcome = await tmdb_client.credits_of("2037", Kind.MOVIE)

    assert isinstance(outcome, Found)
    assert outcome.value


async def test_a_work_carries_everything_a_candidate_needs(tmdb_client):
    """Замерено: строка фильмографии по составу полей совпадает с выдачей
    поиска. Если это перестанет быть правдой, карточки поедут без жанров, и
    фильтр по жанру спрячет их целиком."""
    outcome = await tmdb_client.credits_of("525", Kind.MOVIE)
    hit = next(one for one in outcome.value if one.title == "Начало")

    assert hit.source_id
    assert hit.year
    assert hit.poster_url
    assert hit.genre_ext_ids
    assert hit.source_rating


async def test_the_same_work_is_not_returned_twice(tmdb_client):
    """Человек бывает на карточке и режиссёром, и продюсером — это две строки
    `crew` и одна работа."""
    outcome = await tmdb_client.credits_of("525", Kind.MOVIE)
    ids = [hit.source_id for hit in outcome.value]

    assert len(ids) == len(set(ids))


async def test_a_series_asks_the_other_door(tmdb_client_capturing):
    """У сериалов своя ручка и свои имена полей: `name` вместо `title`."""
    client, sent = tmdb_client_capturing
    await client.credits_of("525", Kind.SERIES)

    assert "/tv_credits" in str(sent[-1].url)


async def test_one_request_and_no_more(tmdb_client_counting):
    """Фильмография отдаётся целиком: порций у неё нет, и второй запрос значил
    бы, что мы их выдумали."""
    client, count = tmdb_client_counting
    await client.credits_of("525", Kind.MOVIE)

    assert count() == 1
```

Фикстуры клиента (`tmdb_client`, `tmdb_client_capturing`, `tmdb_client_counting`)
берутся по образцу соседних тестов TMDB — `tests/backend/sources/test_tmdb_*.py`;
там же лежит и приём с `responding`, `capture` и `counting`.

- [ ] **Шаг 3: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/backend/sources/test_tmdb_people.py -v`
Ожидание: FAIL, `AttributeError: 'TmdbClient' object has no attribute 'credits_of'`.

- [ ] **Шаг 4: Написать разбор**

В `backend/sources/tmdb/parse.py`, рядом с `parse_search` — общее у них
выносится сразу, потому что вторая реализация появляется в этот же момент:

```python
def parse_credits(payload: dict, kind: Kind) -> list[SearchHit]:
    """Фильмография человека. Разбираются оба списка: у режиссёра работы лежат в
    `crew`, у актёра — в `cast`, и у многих есть и то и другое.

    Одна и та же работа приезжает дважды, если человек на ней в двух ролях, —
    снимаем по идентификатору, порядок при этом сохраняется."""
    rows = [*payload.get("cast", []), *payload.get("crew", [])]
    return unique_hits(_hits(rows, kind))
```

где `_hits` — тело нынешнего `parse_search` без обёртки по `results`, а сам
`parse_search` становится однострочным:

```python
def parse_search(payload: dict, kind: Kind) -> list[SearchHit]:
    return _hits(payload.get("results", []), kind)
```

Снятие повторов идёт через `backend/unique.py` — он уже есть и делает ровно это,
с сохранением порядка.

- [ ] **Шаг 5: Написать ручку**

В `backend/sources/tmdb/client.py`, рядом с `search`:

```python
    async def credits_of(self, person_id: str, kind: Kind) -> Outcome:
        """Всё, что человек сделал, одним запросом. Порций нет: замерено, у
        самого плодовитого режиссёра 78 строк."""
        path = "tv_credits" if kind is Kind.SERIES else "movie_credits"
        answer = await self._asked(f"{BASE}/person/{person_id}/{path}")
        if not isinstance(answer, httpx.Response):
            return answer
        return parsed(logger, "tmdb", f"фильмография {person_id} не разобралась",
                      lambda: Found(parse_credits(answer.json(), kind)))
```

- [ ] **Шаг 6: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/backend/sources/ -v`
Ожидание: PASS. Прежние тесты поиска обязаны остаться зелёными — `parse_search`
изменил форму, но не поведение.

- [ ] **Шаг 7: Коммит**

```bash
git add backend/sources/tmdb/ tests/backend/sources/test_tmdb_people.py \
        tests/fixtures/tmdb/ scripts/record_fixtures.py
git commit -m "feat: фильмография человека у TMDB"
```

---

### Задача 3: Поиск человека по имени

Для того, у кого идентичности нет. Ищем его **человеком, а не строкой**: у TMDB
есть `/search/person`, и он отдаёт всех тёзок.

**Обычный поиск по названию тут не годится и был бы хуже.** Он нашёл бы карточки
со словом «Нолан» в названии, а не его работы.

**Файлы:**
- Изменить: `backend/model/search.py`, `backend/sources/tmdb/client.py`,
  `backend/sources/tmdb/parse.py`
- Изменить: `tests/backend/sources/test_tmdb_people.py`
- Создать: `tests/fixtures/tmdb/search_person.json`

**Интерфейсы:**
- Отдаёт: `PersonHit(source_id, name)`; `TmdbClient.find_people(name) ->
  Outcome`; `parse_people(payload) -> list[PersonHit]`.

- [ ] **Шаг 1: Написать падающий тест**

Дописать в `tests/backend/sources/test_tmdb_people.py`:

```python
async def test_namesakes_all_come_back(tmdb_client):
    """Тёзки — это и есть ответ: у безымянной идентичности точнее не бывает, и
    решение проекта прямо принимает, что найдутся все."""
    outcome = await tmdb_client.find_people("Christopher Nolan")

    assert isinstance(outcome, Found)
    assert outcome.value[0].name
    assert outcome.value[0].source_id


async def test_nobody_found_is_not_a_refusal(tmdb_client_empty):
    """Пустая выдача — не событие: источник ответил, просто такого у него нет."""
    outcome = await tmdb_client_empty.find_people("нет такого человека")

    assert isinstance(outcome, Found)
    assert outcome.value == []
```

- [ ] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/backend/sources/test_tmdb_people.py -v`
Ожидание: FAIL, `AttributeError: … has no attribute 'find_people'`.

- [ ] **Шаг 3: Завести тип**

В `backend/model/search.py`:

```python
@dataclass(frozen=True, slots=True)
class PersonHit:
    """Человек, найденный у источника по имени. Своего типа он требует потому,
    что `SearchHit` — это карточка, а тут не карточка: ни года, ни постера, ни
    жанров, и показывать его человеку не будут вовсе."""

    source_id: str
    name: str
```

и в `backend/model/__init__.py` — имя в импорт и в `__all__`.

- [ ] **Шаг 4: Написать разбор и ручку**

В `parse.py`:

```python
def parse_people(payload: dict) -> list[PersonHit]:
    return [PersonHit(source_id=str(row["id"]), name=row.get("name") or "")
            for row in payload.get("results", [])]
```

В `client.py`:

```python
    async def find_people(self, name: str) -> Outcome:
        """Для того, у кого идентичности нет. Тёзки приезжают все — это и есть
        ответ, и решение проекта прямо принимает их появление в выдаче."""
        answer = await self._asked(f"{BASE}/search/person", query=name)
        if not isinstance(answer, httpx.Response):
            return answer
        return parsed(logger, "tmdb", "поиск человека не разобрался",
                      lambda: Found(parse_people(answer.json())))
```

- [ ] **Шаг 5: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/backend/ -v`
Ожидание: PASS.

- [ ] **Шаг 6: Коммит**

```bash
git add backend/model/ backend/sources/tmdb/ tests/
git commit -m "feat: поиск человека по имени у TMDB"
```

---

### Задача 4: Сервис поиска по человеку

Оркестровка: выбрать путь по наличию идентичности и сложить своё с чужим.

**Внутренняя половина одна на все случаи:** `items_of` по внутреннему
идентификатору. Он есть всегда — по нему и кликают.

**Ветвится только внешняя, и различает её одно поле.** У человека из TMDB
`source_id` заполнен — спрашиваем фильмографию по нему. У заведённого руками его
нет — спрашиваем `/search/person` по имени и берём фильмографии всех найденных:
этого и всех тёзок.

**У игровых компаний чужой половины нет вовсе.** Замерено: Steam отдаёт разметку,
GOG молча игнорирует фильтр. Правило пользователя — нет валидной ручки, значит
только своя база.

**Складывание — уже написанное `merge_results`.** Своё стоит на своём месте и
показывается именно оно: у него есть оценка, теги и закладка.

**Файлы:**
- Создать: `backend/service/people.py`
- Изменить: `backend/model/credit.py` (+ `entity_id`),
  `backend/storage/rows.py`, `backend/storage/repository/credits.py`
  (+ `find_identity`, + колонка `id` в `credits_of`), `backend/app.py`
- Создать: `tests/backend/test_people_search.py`

**Интерфейсы:**
- Потребляет: `CreditRepository`, `LibraryRepository`, `ViewsRepository`,
  `Sources`, `GenresRepository`.
- Отдаёт: `PeopleSearch.by_entity(domain, entity_id, kind) -> ExternalSearch`;
  `CreditRepository.find_identity(entity_id) -> tuple[Source, str] | None`;
  `Credit.entity_id`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_people_search.py`:

```python
"""Поиск по человеку и компании: два пути, и различает их идентичность."""

from backend.model import CompanyRole, Found, Kind, PersonRole, SearchHit, Source
from backend.service.people import PeopleSearch


async def test_an_identified_person_is_asked_by_identifier(finder, asked):
    """У человека из TMDB идентификатор уже в базе: спрашивать его по имени
    значило бы притащить тёзок туда, где их не должно быть."""
    outcome = await finder.by_entity("people", NOLAN, Kind.MOVIE)

    assert ("credits_of", ("525", Kind.MOVIE)) in asked
    assert ("find_people", ("Кристофер Нолан",)) not in asked


async def test_a_manual_person_is_asked_outside_by_name(finder, asked):
    """Внешней идентичности у заведённого руками нет и присвоить ему чужую мы не
    вправе — снаружи остаётся имя."""
    outcome = await finder.by_entity("people", MANUAL, Kind.MOVIE)

    names = [name for name, _ in asked]
    assert "find_people" in names


async def test_namesakes_bring_all_their_work(finder, asked):
    """Тёзок находится несколько, и фильмография спрашивается у каждого: иначе
    «поиск по имени» отдавал бы работы одного случайного."""
    await finder.by_entity("people", MANUAL, Kind.MOVIE)

    asked_ids = [args[0] for name, args in asked if name == "credits_of"]
    assert len(asked_ids) > 1


async def test_a_game_company_never_goes_outside(finder, asked):
    """Замерено: Steam отдаёт разметку, GOG молча игнорирует фильтр и возвращает
    весь каталог. Валидной ручки нет — значит только своя база."""
    await finder.by_entity("companies", STUDIO, Kind.GAME)

    assert asked == []


async def test_the_inside_half_never_goes_by_name(finder, asked):
    """Внутри идентификатор есть всегда — по нему и кликают. Пойди эта половина
    по имени, клик по человеку вернул бы и карточку, которая просто так
    называется, и работы тёзки: то самое, чего клик как раз и не должен."""
    await finder.by_entity("people", MANUAL, Kind.MOVIE)

    assert ("library.search", ("Кристофер Нолан",)) not in asked
    assert ("people.items_of", MANUAL) in [(name, args[0]) for name, args in asked]


async def test_own_cards_come_even_when_the_source_refuses(finder, refusing):
    """Своя половина не зависит от сети: без неё жест перестал бы работать
    офлайн, а это по правильную сторону главной границы проекта."""
    outcome = await refusing.by_entity("people", NOLAN, Kind.MOVIE)

    assert outcome.views
    assert outcome.refusals


async def test_own_card_wins_over_the_same_one_from_outside(finder):
    """Дубли снимаются по паре «источник + идентификатор», и показывается своё:
    у него есть оценка, теги и закладка."""
    outcome = await finder.by_entity("people", NOLAN, Kind.MOVIE)

    same = [view for view in outcome.views if view.source_id == "27205"]
    assert len(same) == 1
    assert same[0].item_id is not None


async def test_the_card_carries_the_row_of_every_person(sessions, migrated):
    """Клик по имени зовёт `by_entity`, а звать его нечем без этого поля: имя
    тёзку не различает, а внешняя идентичность есть не у всех. Проверяется
    здесь, а не в задаче 5: там оно уже понадобится готовым."""
    from backend.storage.repository.credits import people

    crew = people(sessions)
    item_id = await library.create(an_item(title="Начало"))
    entity_id = await crew.create_manual("Кристофер Нолан")
    await crew.attach(item_id, entity_id, PersonRole.DIRECTOR)

    credit = (await crew.credits_of(item_id))[0]
    assert credit.entity_id == entity_id
```

Имена `NOLAN`, `MANUAL`, `STUDIO` и фикстуры `finder`, `refusing`, `asked`
заводятся в этом же файле по образцу `tests/backend/test_search.py`: подставные
источники — `FakeSources` с `FakeCatalog`, база — временный файл.

- [ ] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/backend/test_people_search.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'backend.service.people'`.

- [ ] **Шаг 3: Достать идентичность**

В `backend/storage/repository/credits.py`:

```python
    async def find_identity(self, entity_id: int) -> tuple[Source, str] | None:
        """Чем этот человек или студия известны источнику. `None` — значит
        заведён руками либо приехал голой строкой из магазина."""
        row = await self._maybe(
            select(self._entity.table.c.source, self._entity.table.c.source_id)
            .where(self._entity.table.c.id == entity_id),
            lambda row: (row.source, row.source_id) if row.source_id else None,
        )
        return row
```

- [ ] **Шаг 4: Написать сервис**

Создать `backend/service/people.py`:

```python
"""Поиск по человеку и студии: своё плюс чужое, если чужое вообще спросить."""

import asyncio
import logging

from backend.model import (
    ExternalSearch,
    Found,
    Kind,
    Refusal,
    Source,
    merge_results,
    view_from_hit,
)
from backend.service.asking import answered

logger = logging.getLogger(__name__)

# Сколько своих карточек берём. Столько же, сколько страница ленты: жест этот —
# «покажи всё с ним», и обрезать его мельче незачем.
OWN_SIZE = 50


class PeopleSearch:
    """Отдельный сервис, а не метод `SearchService`: тот ищет по строке запроса
    и спрашивает каталожных клиентов вида, а этот ищет по человеку и знает про
    идентичность. Общего у них — только складывание, и оно уже вынесено в
    модель."""

    def __init__(self, library, views, people, companies, sources, genres):
        self._library = library
        self._views = views
        self._entities = {"people": people, "companies": companies}
        self._sources = sources
        self._genres = genres

    async def by_entity(self, domain: str, entity_id: int,
                        kind: Kind) -> ExternalSearch:
        repository = self._entities[domain]
        identity = await repository.find_identity(entity_id)

        own = await self._own(repository, entity_id, kind, identity)
        outside, refusals = await self._outside(entity_id, kind, identity,
                                                repository)
        return ExternalSearch(views=tuple(merge_results(own, outside)),
                              refusals=tuple(refusals))
```

и дальше две половины отдельными методами, каждый не длиннее сорока строк.

**Внутренняя одна на все случаи:** `items_of` по внутреннему идентификатору плюс
`views_of`. Расширенный задачей 1 `search` сюда не заходит — он для строки
поиска.

**Внешняя ветвится:** есть внешний идентификатор — `credits_of` по нему; нет —
`find_people` по имени, потом `credits_of` каждому найденному, разом через
`asyncio.gather`. У игровых компаний внешней половины нет вовсе.

**Отказ обязан быть значением, а не исключением**, и заворачивает его тот же
`answered`, что и в остальных сервисах.

- [ ] **Шаг 5: Собрать в приложении**

В `backend/app.py` добавить поле `finder: PeopleSearch` и собрать его теми же
частями, что и `SearchService`. Довод для `card_parts` не нужен: своих записей у
этого сервиса нет, он только читает.

- [ ] **Шаг 6: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/backend/ -v`
Ожидание: PASS.

- [ ] **Шаг 7: Коммит**

```bash
git add backend/service/people.py backend/storage/repository/credits.py \
        backend/app.py tests/backend/test_people_search.py
git commit -m "feat: сервис поиска по человеку и студии"
```

---

### Задача 5: Мост и клик в карточке

Последняя задача: жест доходит до человека.

**Клик по имени открывает поиск**, а не отдельный вид: та же лента, те же
карточки, своё и чужое вперемешку. Раздел при этом переключается на «Поиск» —
там эта выдача и живёт.

**Файлы:**
- Изменить: `bridge/search.py`, `client/components/Facts.svelte`,
  `client/app/SearchScreen.svelte`, `client/app/App.svelte`
- Изменить: `tests/bridge/test_bridge_search.py`

**Интерфейсы:**
- Отдаёт: `Search.by_person(op, domain, entity_id, kind)` на мосту;
  `onperson(domain, entity_id)` в ленте.

- [ ] **Шаг 1: Написать падающий тест**

Дописать в `tests/bridge/test_bridge_search.py`:

```python
def test_a_person_search_is_remembered_like_any_other(spy, asked):
    """Выдача по человеку — обычная выдача поиска, и добавить из неё карточку
    можно тем же жестом: значит и помнить её надо тем же способом."""
    answers, log = asked
    answers["finder.by_entity"] = ExternalSearch(views=(a_view("1"),), refusals=())
    answers["loader.ensure"] = 12

    search = Search(spy)
    answer = search.by_person(1, "people", 9, "movie")

    assert answer["ok"]["views"][0]["source_id"] == "1"
    assert search.ensure(1, "tmdb", "1") == {"ok": {"outcome": "found",
                                                    "value": 12}}
```

- [ ] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_search.py -v`
Ожидание: FAIL, `AttributeError: 'Search' object has no attribute 'by_person'`.

- [ ] **Шаг 3: Дописать домен моста**

В `bridge/search.py`:

```python
    def by_person(self, op: int, domain: str, entity_id: int,
                  kind: str) -> dict:
        """Выдача по человеку — обычная выдача поиска, и помнится она так же:
        из неё добавляют карточку тем же `ensure`."""
        return self._reply(
            lambda back: self._found(back, op, domain, entity_id, Kind(kind)),
            op=op)

    async def _found(self, back, op, domain, entity_id, kind):
        answer = await back.finder.by_entity(domain, entity_id, kind)
        self._kept.put(op, list(answer.views))
        return {"views": answer.views, "refusals": answer.refusals}
```

- [ ] **Шаг 4: Провести клик**

**Сначала — идентификатор строки в `Credit`.** Проверено по коду: сейчас он
несёт `name`, `role`, `position`, `source`, `source_id`, и **своего `entity_id`
у него нет** (`backend/model/credit.py`). Звать `by_entity` нечем: имя тёзку не
различает, а внешняя идентичность есть не у всех.

Поле добавляется первым, до правки разметки:

```python
@dataclass(frozen=True, slots=True)
class Credit:
    name: str
    role: PersonRole | CompanyRole
    position: int | None = None   # порядок в титрах, нужен для «топ-5 актёров»

    # Строка человека или студии в своей базе. Нужен клику по имени: тёзок
    # различает он, а не имя, и внешней идентичности у половины строк нет.
    # Пуст у того, что приехало из источника и в базу ещё не легло.
    entity_id: int | None = None

    source: Source | None = None
    source_id: str | None = None
```

и заполняется в `backend/storage/rows.py::to_credit` — колонку `table.c.id`
придётся добавить в `credits_of`, там сейчас выбираются только четыре. Тест на
это ставится в задаче 4: без него разметка получила бы `undefined` и клик
уходил бы в никуда молча.

**У приехавшего из источника `entity_id` пуст, и это правильно:** `Credit` из
`SourceCard` описывает человека, которого в базе может ещё не быть. Клик по нему
и не понадобится — состав показывается только у карточек, которые в базе есть.

После этого в `client/components/Facts.svelte` имя уже кнопка, и меняется только
то, что она отдаёт: не имя, а домен и `entity_id`.

В `client/app/App.svelte` клик переключает раздел на поиск и отдаёт запрос вниз:

```svelte
  function byPerson(domain, entity_id) {
    person = { domain, entity_id }
    session = withSection(session, 'search')
  }
```

а `SearchScreen` при непустом `person` спрашивает `search.by_person` вместо
`search.local`.

- [ ] **Шаг 5: Прогнать и посмотреть**

```bash
pipenv run pytest
cd client && npm run build
cd .. && pipenv run python main.py
```

- щелчок по режиссёру показывает его фильмы: свои и незнакомые;
- щелчок по актёру — то же самое;
- щелчок по разработчику игры — только свои карточки, без плашки: чужого тут не
  бывает по устройству источников, и сообщать не о чем;
- щелчок по человеку, заведённому руками, находит и работы его тёзки из TMDB;
- добавление из этой выдачи работает тем же нажатием, что и в обычном поиске.

- [ ] **Шаг 6: Коммит**

```bash
git add bridge/search.py client/ tests/bridge/test_bridge_search.py
git commit -m "feat: клик по имени в карточке ищет всё с этим человеком"
```

---

## Самопроверка плана

**Покрытие.** `people.md`, раздел «Клик по имени — это поиск» — задачи 1–5
целиком: по идентичности точно, по имени приблизительно, у игровых компаний
только своя база.

**Что этот план сознательно не делает.** Ни одной правки в Steam и GOG: замерено,
что валидной ручки поиска по разработчику у них нет, а разметку не разбираем.
Порций у фильмографии нет — TMDB отдаёт её целиком, и резать нечего.
Кинокомпании не участвуют: в карточке фильма студий не показывается.

**Одно место проверено по коду до написания плана, и проверка нашла дыру.**
`Credit` не несёт идентификатора своей строки — только имя, роль, позицию и
внешнюю идентичность. Звать `by_entity` было бы нечем, а имя тёзку не различает.
Поле добавляется задачей 5 первым шагом, вместе с колонкой в `credits_of` и
тестом на неё.

**Чем измеряется готовность.** Весь набор зелёный. Щелчок по режиссёру находит
его работы, о которых вы не знали; щелчок по разработчику игры работает без
сети.
