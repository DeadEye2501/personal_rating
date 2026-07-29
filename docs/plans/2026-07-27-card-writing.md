# План 3. Карточка в базе

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** то, что приехало из источника, полностью ложится в базу. `SourceCard`
из плана 2 превращается в строки плана 1 — карточку, жанры, людей, студии,
внешние идентификаторы, оценки агрегаторов и обложку. Плюс ручная привязка:
разбор ссылки и правило «внешнее заполняет только пустое».

**Архитектура:** два новых репозитория в `backend/storage/repository/` и пять
модулей в `backend/service/`, по одной ответственности на каждый: чистая обрезка
картинки отдельно от сети, чистый разбор ссылки отдельно от привязки. Люди и
студии сделаны одной реализацией — для приложения эти сущности почти
неразличимы.

**Стек:** то же, что в планах 1 и 2, плюс **Pillow** — обрезка обложки живёт в
бэкенде, чтобы не тащить работу с картинкой в главный поток.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от планов 1 и 2.** Готовы схема, репозитории карточки, оценок,
  тегов, закладок и жанров; хранилище постеров; шесть клиентов источников,
  отдающих `Found`/`Missing`/`Refusal` и типы `SourceCard`, `Ratings`,
  `SearchHit`.
- **`backend` не импортирует `client`.** Тест из плана 1 это стережёт.
- **В сеть тесты не ходят.** Сеть подменяется `httpx.MockTransport`.
- **База в тестах — временный файл**, свой на каждый прогон. Файлов два:
  основной и хранилище постеров.
- **Исключений из сервисов наружу не летит.** `CardWriter.save` и
  `PosterService.fetch` возвращают `Refusal`. Единственное исключение —
  `Linker.link`, и оно объявлено: занятая идентичность там поднимает
  `ItemExists`, потому что это ответ на прямое действие человека, а не сбой.
- **Молча не глотаем ничего.** Пойманное исключение ведёт либо к отказу в
  результате, либо к записи в лог — минимум одно из двух.
- **Три состояния `external_rating`:** строки нет — не спрашивали; строка с
  пустым значением — спрашивали, у источника нет; строка со значением — есть
  оценка. Отказ не пишется никогда.
- **Частичной карточки из внешнего источника в базе не бывает.** Строка
  появляется только когда приехало всё, а если запись всё-таки сорвалась —
  убираем за собой.
- **Байтовые литералы только ASCII.** `b"текст"` с кириллицей — это
  `SyntaxError` на сборе, который валит весь прогон.
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ Pipfile, Pipfile.lock         + Pillow
├─ backend/
│  ├─ model/
│  │  ├─ suggestion.py           Suggestion — строка подсказки при вводе имени
│  │  └─ link.py                 ExternalLink — разобранная ссылка
│  ├─ storage/repository/
│  │  ├─ credits.py              люди и студии одной реализацией
│  │  └─ external.py             external_id и external_rating
│  └─ service/
│     ├─ __init__.py
│     ├─ images.py               чистая обрезка байтов, без сети и базы
│     ├─ posters.py              скачать и сохранить обложку
│     ├─ links.py                чистый разбор ссылки, без сети и базы
│     ├─ cards.py                сборка SourceCard в базу
│     └─ linking.py              привязка ручной карточки к внешней
└─ tests/backend/
   ├─ test_credits.py            test_suggestions.py
   ├─ test_external_ids.py       test_external_ratings.py
   ├─ test_images.py             test_poster_service.py
   ├─ test_card_writer.py
   ├─ test_links.py              test_linking.py
```

`docs/specs/2026-07-27-code-structure.md:28` перечисляет в `service/` только
`search, library, rate, enrich`. Список там иллюстративный; `images`, `posters`,
`links`, `cards` и `linking` его дополняют, `search` и `library` появятся в
плане 4.

---

### Задача 1: Репозиторий людей и студий

Одна реализация на две сущности. Это не преждевременное обобщение: обе
реализации существуют с первого дня, а расходятся они только в двух местах — у
`person_credit` есть `position` (порядок в титрах, нужный для «топ-5 актёров»),
и набор ролей у каждой свой.

**Идентичность бывает трёх видов.** У человека из TMDB она внешняя. У
заведённого руками — `manual` со своим `uuid4`, как и у ручной карточки. У
студии из Steam или GOG её нет вовсе: названия приходят голыми строками, класть
туда нечего.

**Отсюда правило сопоставления:** приехавшего ищем по идентичности источника, и
только у тех, у кого её нет вовсе, склеиваем по имени. Без этого два разных
актёра-тёзки из TMDB стали бы одной строкой молча — человек в импорте не
участвует и заметить подмену не может.

**Файлы:**
- Создать: `backend/storage/repository/credits.py`
- Создать: `tests/backend/test_credits.py`

**Интерфейсы:**
- Потребляет: таблицы `person`, `person_credit`, `company`, `company_credit`;
  `Credit`, `Source` из `backend.model`; `fold` из `backend.storage.session`.
- Отдаёт: `CreditRepository(sessions, entity, credit, position_column, roles)` с
  методами
  `create(name, source=None, source_id=None) -> int`,
  `create_manual(name) -> int` — `source = manual`, идентификатор `uuid4`,
  `find_by_source(source, source_id) -> int | None`,
  `find_by_name(name) -> list[int]` — все тёзки, для подсказки,
  `find_anonymous_by_name(name) -> int | None` — тёзка без идентичности,
  `ensure(credit) -> int`,
  `attach(item_id, entity_id, role, position=None) -> None`,
  `detach_all(item_id) -> None`,
  `credits_of(item_id) -> list[Credit]`;
  фабрики `people(sessions)` и `companies(sessions)`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_credits.py`:

```python
from datetime import datetime

from backend.model import CompanyRole, Credit, Item, Kind, PersonRole, Source
from backend.storage.repository.credits import companies, people
from backend.storage.repository.library import LibraryRepository

WHEN = datetime(2026, 7, 27, 12, 0)


class NoPosters:
    """Удаление карточки просит хранилище убрать обложку. Здесь проверяется
    не оно, а то, что человек переживает удаление карточки."""

    async def delete(self, item_id: int) -> None:
        return None


async def make_card(sessions, source_id: str = "1") -> int:
    return await LibraryRepository(sessions).create(
        Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id=source_id,
             title=f"карточка {source_id}", synced_at=WHEN)
    )


async def test_a_studio_may_have_no_identity_at_all(sessions):
    """Steam и GOG отдают названия студий голыми строками."""
    studio = await companies(sessions).create("CD Projekt RED")
    assert studio > 0


async def test_a_manual_person_gets_its_own_identity(sessions):
    """Как и ручная карточка: source = manual, идентификатор свой."""
    repository = people(sessions)
    first = await repository.create_manual("Василий Пупкин")
    second = await repository.create_manual("Василий Пупкин")

    assert first != second
    found = await repository.credits_of(await make_card(sessions))
    assert found == []   # ни к чему не привязаны


async def test_find_by_source_finds_only_the_identified_one(sessions):
    repository = people(sessions)
    await repository.create("Кристофер Нолан")
    identified = await repository.create("Кристофер Нолан", Source.TMDB, "525")

    assert await repository.find_by_source(Source.TMDB, "525") == identified
    assert await repository.find_by_source(Source.TMDB, "999") is None


async def test_find_by_name_returns_every_namesake(sessions):
    """Совпадение имени само по себе ничего не решает: тёзки существуют,
    и выбирает между ними человек."""
    repository = people(sessions)
    first = await repository.create_manual("Василий Пупкин")
    second = await repository.create("Василий Пупкин", Source.TMDB, "7")

    assert sorted(await repository.find_by_name("василий пупкин")) == sorted(
        [first, second]
    )


async def test_find_anonymous_skips_those_who_have_an_identity(sessions):
    """По имени склеиваем только тех, у кого идентичности нет вовсе."""
    repository = people(sessions)
    await repository.create("Мосфильм", Source.TMDB, "12")
    bare = await repository.create("Мосфильм")

    assert await repository.find_anonymous_by_name("мосфильм") == bare


async def test_find_by_name_ignores_case_in_russian(sessions):
    repository = people(sessions)
    found = await repository.create("Андрей Тарковский")
    assert await repository.find_by_name("АНДРЕЙ ТАРКОВСКИЙ") == [found]


async def test_ensure_reuses_the_same_identity(sessions):
    """Один и тот же человек на двух карточках — одна строка, иначе
    «показать всё с этим человеком» разваливается."""
    repository = people(sessions)
    first = await repository.ensure(
        Credit("Кристофер Нолан", PersonRole.DIRECTOR,
               source=Source.TMDB, source_id="525")
    )
    second = await repository.ensure(
        Credit("Кристофер Нолан", PersonRole.ACTOR,
               source=Source.TMDB, source_id="525")
    )
    assert first == second


async def test_ensure_keeps_two_namesakes_from_the_source_apart(sessions):
    """Ровно то, ради чего Credit несёт идентичность: без неё два разных
    актёра с одним именем слились бы молча."""
    repository = people(sessions)
    first = await repository.ensure(
        Credit("Василий Пупкин", PersonRole.ACTOR,
               source=Source.TMDB, source_id="1")
    )
    second = await repository.ensure(
        Credit("Василий Пупкин", PersonRole.ACTOR,
               source=Source.TMDB, source_id="2")
    )
    assert first != second


async def test_ensure_falls_back_to_the_name_without_identity(sessions):
    repository = companies(sessions)
    first = await repository.ensure(Credit("CD Projekt RED", CompanyRole.DEVELOPER))
    second = await repository.ensure(Credit("CD Projekt RED", CompanyRole.PUBLISHER))
    assert first == second


async def test_ensure_does_not_hijack_a_manual_namesake(sessions):
    """Заведённый руками Нолан и приехавший из TMDB — разные строки:
    идентичности у них разные, и присвоить чужую мы не вправе."""
    repository = people(sessions)
    mine = await repository.create_manual("Кристофер Нолан")
    imported = await repository.ensure(
        Credit("Кристофер Нолан", PersonRole.DIRECTOR,
               source=Source.TMDB, source_id="525")
    )
    assert mine != imported


async def test_a_nameless_credit_does_not_stick_to_an_identified_namesake(sessions):
    """Обратный порядок: сначала приехал из источника, потом пришла голая
    строка с тем же именем. Прилипать к чужой идентичности нельзя."""
    repository = companies(sessions)
    identified = await repository.create("Мосфильм", Source.TMDB, "12")
    bare = await repository.ensure(Credit("Мосфильм", CompanyRole.PUBLISHER))
    assert bare != identified


async def test_attach_keeps_the_order_from_the_credits(sessions):
    item_id = await make_card(sessions)
    repository = people(sessions)

    first = await repository.create("Мэттью Макконахи")
    second = await repository.create("Энн Хэтэуэй")
    await repository.attach(item_id, first, PersonRole.ACTOR, position=0)
    await repository.attach(item_id, second, PersonRole.ACTOR, position=1)

    names = [c.name for c in await repository.credits_of(item_id)]
    assert names == ["Мэттью Макконахи", "Энн Хэтэуэй"]


async def test_one_person_can_hold_two_roles_on_one_card(sessions):
    """Роль входит в первичный ключ именно поэтому."""
    item_id = await make_card(sessions)
    repository = people(sessions)
    person_id = await repository.create("Клинт Иствуд")

    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)
    await repository.attach(item_id, person_id, PersonRole.ACTOR, position=0)

    roles = {c.role for c in await repository.credits_of(item_id)}
    assert roles == {PersonRole.DIRECTOR, PersonRole.ACTOR}


async def test_attaching_the_same_role_twice_is_quiet(sessions):
    item_id = await make_card(sessions)
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан")

    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)
    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)

    assert len(await repository.credits_of(item_id)) == 1


async def test_credits_carry_the_identity_back(sessions):
    item_id = await make_card(sessions)
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан", Source.TMDB, "525")
    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)

    found = (await repository.credits_of(item_id))[0]
    assert (found.source, found.source_id) == (Source.TMDB, "525")
    # Именно перечисление, а не строка: `==` у StrEnum истинно и для сырого
    # 'director', поэтому проверяем тип.
    assert isinstance(found.role, PersonRole)


async def test_credits_of_survives_rows_without_identity(sessions):
    item_id = await make_card(sessions)
    repository = companies(sessions)
    studio = await repository.create("CD Projekt RED")
    await repository.attach(item_id, studio, CompanyRole.DEVELOPER)

    found = (await repository.credits_of(item_id))[0]
    assert found.source is None and found.source_id is None


async def test_detach_all_clears_the_card_but_keeps_the_people(sessions):
    item_id = await make_card(sessions)
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан")
    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)

    await repository.detach_all(item_id)

    assert await repository.credits_of(item_id) == []
    assert await repository.find_by_name("Кристофер Нолан") == [person_id]


async def test_companies_work_the_same_way(sessions):
    """Для приложения эти две сущности почти неразличимы."""
    item_id = await make_card(sessions)
    repository = companies(sessions)

    studio = await repository.create("CD Projekt RED")
    await repository.attach(item_id, studio, CompanyRole.DEVELOPER)

    found = await repository.credits_of(item_id)
    assert [(c.name, c.role) for c in found] == [
        ("CD Projekt RED", CompanyRole.DEVELOPER)
    ]


async def test_companies_have_no_position(sessions):
    """У company_credit колонки position нет — просить её нечем."""
    item_id = await make_card(sessions)
    repository = companies(sessions)
    studio = await repository.create("Мосфильм")

    await repository.attach(item_id, studio, CompanyRole.PUBLISHER, position=3)

    assert (await repository.credits_of(item_id))[0].position is None


async def test_people_and_companies_do_not_share_a_table(sessions):
    item_id = await make_card(sessions)
    person_id = await people(sessions).create("Мосфильм")
    await people(sessions).attach(item_id, person_id, PersonRole.DIRECTOR)

    assert await companies(sessions).credits_of(item_id) == []
    assert await companies(sessions).find_by_name("Мосфильм") == []


async def test_deleting_the_card_takes_the_credits_but_not_the_person(sessions):
    item_id = await make_card(sessions)
    repository = people(sessions)
    person_id = await repository.create("Кристофер Нолан")
    await repository.attach(item_id, person_id, PersonRole.DIRECTOR)

    await LibraryRepository(sessions).delete(item_id, posters=NoPosters())

    assert await repository.find_by_name("Кристофер Нолан") == [person_id]
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_credits.py -v`
Ожидается: FAIL — `No module named 'backend.storage.repository.credits'`.

- [ ] **Шаг 3: Реализовать**

Создать `backend/storage/repository/credits.py`:

```python
from collections.abc import Callable
from uuid import uuid4

from sqlalchemy import Column, Table, delete, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.model import Credit, CompanyRole, PersonRole, Source
from backend.storage.session import fold
from backend.storage.tables import company, company_credit, person, person_credit


class CreditRepository:
    """Одна реализация на людей и студии: для приложения они почти
    неразличимы. Расходятся только в порядке в титрах — у студий его нет."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        entity: Table,
        credit: Table,
        position_column: Column | None,
        roles: Callable[[str], PersonRole | CompanyRole],
    ) -> None:
        self._sessions = sessions
        self._entity = entity
        self._credit = credit
        self._position = position_column
        # Чем переводить строку из базы обратно в роль. У людей и студий
        # наборы ролей разные, а репозиторий один.
        self._roles = roles

    async def create(self, name: str, source: Source | None = None,
                     source_id: str | None = None) -> int:
        async with self._sessions() as session:
            result = await session.execute(
                self._entity.insert()
                .values(name=name,
                        source=str(source) if source is not None else None,
                        source_id=source_id)
                .returning(self._entity.c.id)
            )
            await session.commit()
            return result.scalar_one()

    async def create_manual(self, name: str) -> int:
        """Заведённый руками получает свою идентичность — как и ручная
        карточка. Иначе он попал бы в корзину «идентичности нет вовсе»,
        которая отведена студиям из магазинов."""
        return await self.create(name, Source.MANUAL, str(uuid4()))

    async def find_by_source(self, source: Source, source_id: str) -> int | None:
        async with self._sessions() as session:
            result = await session.execute(
                select(self._entity.c.id).where(
                    self._entity.c.source == str(source),
                    self._entity.c.source_id == source_id,
                )
            )
            return result.scalar_one_or_none()

    async def find_by_name(self, name: str) -> list[int]:
        """Все тёзки. Выбирает между ними человек, а не мы."""
        async with self._sessions() as session:
            result = await session.execute(
                select(self._entity.c.id)
                .where(func.py_lower(self._entity.c.name) == fold(name.strip()))
                .order_by(self._entity.c.id)
            )
            return list(result.scalars().all())

    async def find_anonymous_by_name(self, name: str) -> int | None:
        """Тёзка без идентичности. Прилипать к чужой нельзя ни в какую
        сторону: ни приехавшему к ручному, ни голой строке к приехавшему."""
        async with self._sessions() as session:
            result = await session.execute(
                select(self._entity.c.id)
                .where(func.py_lower(self._entity.c.name) == fold(name.strip()),
                       self._entity.c.source_id.is_(None))
                .order_by(self._entity.c.id)
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def ensure(self, credit: Credit) -> int:
        """Найти существующего или завести нового."""
        if credit.source is not None and credit.source_id is not None:
            found = await self.find_by_source(credit.source, credit.source_id)
            if found is not None:
                return found
            return await self.create(credit.name, credit.source, credit.source_id)

        found = await self.find_anonymous_by_name(credit.name)
        return found if found is not None else await self.create(credit.name)

    async def attach(self, item_id: int, entity_id: int, role: str,
                     position: int | None = None) -> None:
        values = {
            "item_id": item_id,
            f"{self._entity.name}_id": entity_id,
            "role": str(role),
        }
        if self._position is not None:
            values["position"] = position

        async with self._sessions() as session:
            await session.execute(
                insert(self._credit).values(**values).on_conflict_do_nothing()
            )
            await session.commit()

    async def detach_all(self, item_id: int) -> None:
        async with self._sessions() as session:
            await session.execute(
                delete(self._credit).where(self._credit.c.item_id == item_id)
            )
            await session.commit()

    async def credits_of(self, item_id: int) -> list[Credit]:
        link = self._credit.c[f"{self._entity.name}_id"]
        order = self._position if self._position is not None else self._entity.c.name

        columns = [self._entity.c.name, self._entity.c.source,
                   self._entity.c.source_id, self._credit.c.role]
        if self._position is not None:
            columns.append(self._position)

        async with self._sessions() as session:
            result = await session.execute(
                select(*columns)
                .join_from(self._credit, self._entity, link == self._entity.c.id)
                .where(self._credit.c.item_id == item_id)
                .order_by(order)
            )
            rows = result.all()

        return [
            Credit(
                # Роль возвращается перечислением, а не сырой строкой из базы.
                # `Credit.role` объявлен как `PersonRole | CompanyRole`, и
                # строка проходит только сравнение через `==`: `is` и
                # `isinstance` на ней ложны. План 4 читает то же поле через
                # `role is PersonRole.ACTOR` — два пути чтения не должны
                # возвращать разные типы.
                name=row.name,
                role=self._roles(row.role),
                position=getattr(row, "position", None),
                source=Source(row.source) if row.source else None,
                source_id=row.source_id,
            )
            for row in rows
        ]


def people(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository:
    return CreditRepository(sessions, person, person_credit,
                            person_credit.c.position, PersonRole)


def companies(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository:
    return CreditRepository(sessions, company, company_credit, None, CompanyRole)
```

Роль из базы возвращается **перечислением**, а не строкой. `StrEnum` делает
равным только `==`; `is` и `isinstance` на сырой строке ложны, а через границу
слоёв по манифесту ходят свои типы. План 4 читает то же поле как
`role is PersonRole.ACTOR` — если бы репозитории отдавали разное, это разошлось
бы молча.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_credits.py -v`
Ожидается: PASS, двадцать один тест.

- [ ] **Шаг 5: Коммит**

```bash
git add backend/storage/repository/credits.py tests/backend/test_credits.py
git commit -m "feat: репозиторий людей и студий одной реализацией"
```

---

### Задача 2: Подсказка при вводе имени

То, ради чего затевалась `docs/specs/2026-07-27-people.md`. В строке подсказки после
маркера `•` стоит название фильма, по которому этого человека узнают, — иначе
двух Василиев Пупкиных не различить.

**Какой это фильм — по порядку:**

1. самый высоко оценённый **тобой**; оценки агрегаторов не участвуют;
2. если оценённых нет — самое свежее из отложенного;
3. если нет и этого — любая связанная карточка, какую отдаст база.

Третья ступень не для красоты: человек, снявшийся только в неоценённых и
неотложенных карточках, — обычное дело.

**Подсказка несёт и идентификатор карточки**, а не только название: при
наведении показывается ещё и обложка, а хранилище постеров ключуется по
`item_id`. По названию его не запросить — тёзки названий существуют.

**Решения этого плана, которых в спеке нет:** сопоставление идёт по началу
имени, а не по вхождению; список ограничен десятью строками; при равных оценках
берётся любой, какой отдаст база.

**Файлы:**
- Создать: `backend/model/suggestion.py`; изменить `backend/model/__init__.py`
- Изменить: `backend/storage/repository/credits.py`
- Создать: `tests/backend/test_suggestions.py`

**Интерфейсы:**
- Потребляет: `CreditRepository` из задачи 1; таблицы `item`, `rating`,
  `wishlist`.
- Отдаёт: `Suggestion(entity_id, name, hint, hint_item_id)` в `backend.model`;
  `CreditRepository.suggest(name: str, limit: int = 10) -> list[Suggestion]`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_suggestions.py`:

```python
from datetime import datetime, timedelta

from sqlalchemy import insert as core_insert

from backend.model import Item, Kind, PersonRole, Source
from backend.storage.repository.credits import companies, people
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.ratings import RatingsRepository
from backend.storage.repository.wishlist import WishlistRepository
from backend.storage.tables import external_rating

WHEN = datetime(2026, 7, 27, 12, 0)


async def card(sessions, title: str, source_id: str) -> int:
    return await LibraryRepository(sessions).create(
        Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id=source_id,
             title=title, synced_at=WHEN)
    )


async def person_with(sessions, name: str, item_ids: list[int]) -> int:
    repository = people(sessions)
    person_id = await repository.create_manual(name)
    for item_id in item_ids:
        await repository.attach(item_id, person_id, PersonRole.DIRECTOR)
    return person_id


async def test_hint_is_the_highest_rated_film(sessions):
    good = await card(sessions, "Интерстеллар", "1")
    meh = await card(sessions, "Довод", "2")
    await person_with(sessions, "Кристофер Нолан", [good, meh])

    ratings = RatingsRepository(sessions)
    await ratings.set_score(good, 9.0, now=WHEN)
    await ratings.set_score(meh, 6.0, now=WHEN)

    found = await people(sessions).suggest("Кристофер")
    assert [(s.name, s.hint) for s in found] == [
        ("Кристофер Нолан", "Интерстеллар")
    ]


async def test_the_hint_carries_the_card_identifier(sessions):
    """При наведении показывается ещё и обложка, а хранилище постеров
    ключуется по item_id: по названию его не запросить."""
    only = await card(sessions, "Интерстеллар", "1")
    await person_with(sessions, "Кристофер Нолан", [only])

    found = await people(sessions).suggest("Кристофер")
    assert found[0].hint_item_id == only


async def test_aggregator_scores_do_not_count(sessions):
    """Узнают человека по тому, что он значит для тебя, а не для IMDb."""
    mine = await card(sessions, "Наш выпускной", "1")
    theirs = await card(sessions, "Дюнкерк", "2")
    await person_with(sessions, "Василий Пупкин", [mine, theirs])
    await RatingsRepository(sessions).set_score(mine, 7.0, now=WHEN)

    async with sessions() as session:
        await session.execute(
            core_insert(external_rating).values(
                item_id=theirs, source="imdb", value=9.5, fetched_at=WHEN
            )
        )
        await session.commit()

    found = await people(sessions).suggest("Василий")
    assert found[0].hint == "Наш выпускной"


async def test_without_ratings_the_hint_is_the_freshest_wish(sessions):
    older = await card(sessions, "Старое желание", "1")
    newer = await card(sessions, "Свежее желание", "2")
    await person_with(sessions, "Андрей Тарковский", [older, newer])

    wishes = WishlistRepository(sessions)
    await wishes.add(older, now=WHEN)
    await wishes.add(newer, now=WHEN + timedelta(days=1))

    found = await people(sessions).suggest("Андрей")
    assert found[0].hint == "Свежее желание"


async def test_a_rated_film_beats_a_wished_one(sessions):
    rated = await card(sessions, "Оценённый", "1")
    wished = await card(sessions, "Отложенный", "2")
    await person_with(sessions, "Кто-то", [rated, wished])

    await RatingsRepository(sessions).set_score(rated, 4.0, now=WHEN)
    await WishlistRepository(sessions).add(wished, now=WHEN)

    found = await people(sessions).suggest("Кто")
    assert found[0].hint == "Оценённый"


async def test_neither_rated_nor_wished_still_gets_a_hint(sessions):
    """Искал «Одиссею», нашлось три фильма, оценил один — остальные два
    остались. Актёр из них обязан быть узнаваем."""
    only = await card(sessions, "Ничем не отмеченный", "1")
    await person_with(sessions, "Никто", [only])

    found = await people(sessions).suggest("Никто")
    assert found[0].hint == "Ничем не отмеченный"


async def test_a_person_without_any_card_has_an_empty_hint(sessions):
    await people(sessions).create_manual("Только что заведённый")
    found = await people(sessions).suggest("Только")
    assert found[0].hint == ""
    assert found[0].hint_item_id is None


async def test_namesakes_are_told_apart_by_their_hints(sessions):
    """Ровно тот случай, ради которого всё это делается."""
    famous = await card(sessions, "Интерстеллар", "1")
    mine = await card(sessions, "Наш выпускной", "2")
    await person_with(sessions, "Василий Пупкин", [famous])
    await person_with(sessions, "Василий Пупкин", [mine])

    await RatingsRepository(sessions).set_score(famous, 9.0, now=WHEN)
    await RatingsRepository(sessions).set_score(mine, 5.0, now=WHEN)

    hints = {s.hint for s in await people(sessions).suggest("Василий")}
    assert hints == {"Интерстеллар", "Наш выпускной"}


async def test_suggest_matches_the_beginning_of_the_name(sessions):
    await people(sessions).create_manual("Кристофер Нолан")
    await people(sessions).create_manual("Дени Вильнёв")

    assert len(await people(sessions).suggest("крис")) == 1
    assert len(await people(sessions).suggest("")) == 2


async def test_like_wildcards_typed_by_a_human_are_literal(sessions):
    """Подчёркивание и процент — обычные символы имени, а не подстановки."""
    await people(sessions).create_manual("И_ван")
    await people(sessions).create_manual("Иван")

    assert [s.name for s in await people(sessions).suggest("И_")] == ["И_ван"]
    assert await people(sessions).suggest("%") == []


async def test_suggest_respects_the_limit(sessions):
    for index in range(5):
        await people(sessions).create_manual(f"Человек {index}")

    assert len(await people(sessions).suggest("Человек", limit=3)) == 3


async def test_studios_are_suggested_the_same_way(sessions):
    """Для приложения эти две сущности почти неразличимы."""
    game = await card(sessions, "Ведьмак", "1")
    studio = await companies(sessions).create("CD Projekt RED")
    await companies(sessions).attach(game, studio, "developer")
    await RatingsRepository(sessions).set_score(game, 10.0, now=WHEN)

    found = await companies(sessions).suggest("CD")
    assert [(s.name, s.hint) for s in found] == [("CD Projekt RED", "Ведьмак")]
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_suggestions.py -v`
Ожидается: FAIL — `AttributeError: 'CreditRepository' object has no attribute
'suggest'`.

- [ ] **Шаг 3: Тип строки подсказки**

Создать `backend/model/suggestion.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Suggestion:
    """Строка подсказки при вводе имени.

    `hint` — название карточки, по которой этого человека узнают, `hint_item_id`
    — она же для показа обложки. Пусты только у того, за кем в библиотеке пока
    ничего не числится."""

    entity_id: int
    name: str
    hint: str = ""
    hint_item_id: int | None = None
```

Добавить `Suggestion` в импорт и в `__all__` в `backend/model/__init__.py`.

- [ ] **Шаг 4: Реализовать**

Дописать в `CreditRepository`, а в шапку файла добавить
`from backend.model import Credit, Source, Suggestion` и
`from backend.storage.tables import item, rating, wishlist`:

```python
    async def suggest(self, name: str, limit: int = 10) -> list[Suggestion]:
        needle = fold(name.strip())
        link = self._credit.c[f"{self._entity.name}_id"]

        async with self._sessions() as session:
            # autoescape: подчёркивание и процент в имени — обычные символы,
            # а не подстановки LIKE.
            found = await session.execute(
                select(self._entity.c.id, self._entity.c.name)
                .where(func.py_lower(self._entity.c.name)
                       .startswith(needle, autoescape=True))
                .order_by(self._entity.c.name, self._entity.c.id)
                .limit(limit)
            )
            rows = found.all()

            suggestions = []
            for row in rows:
                title, item_id = await self._hint(session, link, row.id)
                suggestions.append(
                    Suggestion(entity_id=row.id, name=row.name, hint=title,
                               hint_item_id=item_id)
                )
            return suggestions

    async def _hint(self, session, link, entity_id: int) -> tuple[str, int | None]:
        """Чем этот человек известен в твоей библиотеке. Три ступени, и
        третья нужна потому, что связанная карточка может быть и не оценена,
        и не отложена."""
        columns = (item.c.title, item.c.id)
        mine = (
            select(*columns)
            .join_from(self._credit, item, self._credit.c.item_id == item.c.id)
            .join(rating, rating.c.item_id == item.c.id)
            .where(link == entity_id, rating.c.score.is_not(None))
            .order_by(rating.c.score.desc())
            .limit(1)
        )
        planned = (
            select(*columns)
            .join_from(self._credit, item, self._credit.c.item_id == item.c.id)
            .join(wishlist, wishlist.c.item_id == item.c.id)
            .where(link == entity_id)
            .order_by(wishlist.c.added_at.desc())
            .limit(1)
        )
        any_card = (
            select(*columns)
            .join_from(self._credit, item, self._credit.c.item_id == item.c.id)
            .where(link == entity_id)
            .limit(1)
        )

        for statement in (mine, planned, any_card):
            row = (await session.execute(statement)).first()
            if row is not None:
                return row.title, row.id
        return "", None
```

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_suggestions.py -v`
Ожидается: PASS, двенадцать тестов.

- [ ] **Шаг 6: Коммит**

```bash
git add backend/model/suggestion.py backend/model/__init__.py \
        backend/storage/repository/credits.py tests/backend/test_suggestions.py
git commit -m "feat: подсказка при вводе имени с узнаваемой карточкой"
```

---

### Задача 3: Репозиторий внешних идентификаторов

Всё, что не основной источник карточки: IMDb ID и идентификатор Кинопоиска у
кино, идентификатор второго магазина у игры. На них же собираются ссылки
«открыть на IMDb».

`UNIQUE (source, value)` даёт бесплатную проверку: один и тот же IMDb ID не
может принадлежать двум карточкам.

**Файлы:**
- Создать: `backend/storage/repository/external.py`
- Создать: `tests/backend/test_external_ids.py`

**Интерфейсы:**
- Потребляет: `ExternalId`, `IdSource` из `backend.model`; таблицу
  `external_id`.
- Отдаёт: исключение `IdentityTaken` и `ExternalIdsRepository(sessions)` с
  `put(item_id, external) -> None`, `ids_of(item_id) -> list[ExternalId]`,
  `find_item(source, value) -> int | None`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_external_ids.py`:

```python
from datetime import datetime

import pytest

from backend.model import ExternalId, IdSource, Item, Kind, Source
from backend.storage.repository.external import (
    ExternalIdsRepository,
    IdentityTaken,
)
from backend.storage.repository.library import LibraryRepository

WHEN = datetime(2026, 7, 27, 12, 0)


class NoPosters:
    async def delete(self, item_id: int) -> None:
        return None


async def make_card(sessions, source_id: str) -> int:
    return await LibraryRepository(sessions).create(
        Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id=source_id,
             title=f"карточка {source_id}", synced_at=WHEN)
    )


async def test_put_and_read_back(sessions):
    item_id = await make_card(sessions, "1")
    repository = ExternalIdsRepository(sessions)

    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.ids_of(item_id) == [
        ExternalId(IdSource.IMDB, "tt0816692")
    ]


async def test_a_card_may_hold_several_identifiers(sessions):
    item_id = await make_card(sessions, "1")
    repository = ExternalIdsRepository(sessions)

    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))
    await repository.put(item_id, ExternalId(IdSource.KINOPOISK, "258687"))

    assert {i.source for i in await repository.ids_of(item_id)} == {
        IdSource.IMDB, IdSource.KINOPOISK
    }


async def test_the_same_source_is_replaced_not_duplicated(sessions):
    item_id = await make_card(sessions, "1")
    repository = ExternalIdsRepository(sessions)

    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0000001"))
    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.ids_of(item_id) == [
        ExternalId(IdSource.IMDB, "tt0816692")
    ]


async def test_one_identifier_cannot_belong_to_two_cards(sessions):
    first = await make_card(sessions, "1")
    second = await make_card(sessions, "2")
    repository = ExternalIdsRepository(sessions)

    await repository.put(first, ExternalId(IdSource.IMDB, "tt0816692"))

    with pytest.raises(IdentityTaken):
        await repository.put(second, ExternalId(IdSource.IMDB, "tt0816692"))


async def test_find_item_by_identifier(sessions):
    item_id = await make_card(sessions, "1")
    repository = ExternalIdsRepository(sessions)
    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    assert await repository.find_item(IdSource.IMDB, "tt0816692") == item_id
    assert await repository.find_item(IdSource.IMDB, "tt0000000") is None


async def test_identifiers_go_away_with_the_card(sessions):
    item_id = await make_card(sessions, "1")
    repository = ExternalIdsRepository(sessions)
    await repository.put(item_id, ExternalId(IdSource.IMDB, "tt0816692"))

    await LibraryRepository(sessions).delete(item_id, posters=NoPosters())

    assert await repository.find_item(IdSource.IMDB, "tt0816692") is None
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_external_ids.py -v`
Ожидается: FAIL — `No module named 'backend.storage.repository.external'`.

- [ ] **Шаг 3: Реализовать**

Создать `backend/storage/repository/external.py`:

```python
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.model import ExternalId, IdSource
from backend.storage.tables import external_id as external_id_table


class IdentityTaken(Exception):
    """Такой внешний идентификатор уже принадлежит другой карточке."""


class ExternalIdsRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def put(self, item_id: int, external: ExternalId) -> None:
        statement = insert(external_id_table).values(
            item_id=item_id, source=str(external.source), value=external.value
        )
        statement = statement.on_conflict_do_update(
            index_elements=[external_id_table.c.item_id,
                            external_id_table.c.source],
            set_={"value": statement.excluded.value},
        )
        async with self._sessions() as session:
            try:
                await session.execute(statement)
                await session.commit()
            except IntegrityError as error:
                # Разрешение конфликта целит в первичный ключ, поэтому
                # UNIQUE (source, value) сюда доезжает нетронутым.
                await session.rollback()
                raise IdentityTaken(
                    f"{external.source}:{external.value} уже занят"
                ) from error

    async def ids_of(self, item_id: int) -> list[ExternalId]:
        async with self._sessions() as session:
            result = await session.execute(
                select(external_id_table.c.source, external_id_table.c.value)
                .where(external_id_table.c.item_id == item_id)
                .order_by(external_id_table.c.source)
            )
            return [
                ExternalId(source=IdSource(row.source), value=row.value)
                for row in result.all()
            ]

    async def find_item(self, source: IdSource, value: str) -> int | None:
        async with self._sessions() as session:
            result = await session.execute(
                select(external_id_table.c.item_id).where(
                    external_id_table.c.source == str(source),
                    external_id_table.c.value == value,
                )
            )
            return result.scalar_one_or_none()
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_external_ids.py -v`
Ожидается: PASS, шесть тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add backend/storage/repository/external.py tests/backend/test_external_ids.py
git commit -m "feat: репозиторий внешних идентификаторов"
```

---

### Задача 4: Оценки агрегаторов — три состояния и сроки

Самая содержательная таблица плана. Без правильного различения трёх состояний
фильм, которого MDBList не знает, перезапрашивался бы при каждом показе — так и
было у предшественника.

| Строки нет | Строка есть, `value` пуст | Строка есть со значением |
|---|---|---|
| не спрашивали | спрашивали, у источника нет | есть оценка |

**Срок годности считается от `fetched_at`, а не хранится полем** — политику
тогда можно менять, не трогая базу. Значение живёт месяц, отрицательный ответ —
неделю: у свежего релиза оценка ещё может появиться, но ходить за ней ежедневно
незачем.

**Отказ не пишется никогда.** Этот репозиторий отказов и не принимает: на входе
у него `ExternalRating`, а `Refusal` в него не превратить. Кто отсеивает —
сервис обогащения из плана 4.

**Файлы:**
- Изменить: `backend/storage/repository/external.py`
- Создать: `tests/backend/test_external_ratings.py`

**Интерфейсы:**
- Потребляет: `ExternalRating`, `RatingSource` из `backend.model`; таблицу
  `external_rating`.
- Отдаёт: константы `VALUE_TTL` (30 дней) и `EMPTY_TTL` (7 дней);
  `ExternalRatingsRepository(sessions)` с
  `record(item_id, rating) -> None`,
  `ratings_of(item_id) -> list[ExternalRating]`,
  `stale_sources(item_id, wanted, now) -> list[RatingSource]`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_external_ratings.py`:

```python
from datetime import datetime, timedelta

from backend.model import ExternalRating, Item, Kind, RatingSource, Source
from backend.storage.repository.external import (
    EMPTY_TTL,
    VALUE_TTL,
    ExternalRatingsRepository,
)
from backend.storage.repository.library import LibraryRepository

WHEN = datetime(2026, 7, 27, 12, 0)
WANTED = [RatingSource.IMDB, RatingSource.ROTTEN, RatingSource.KINOPOISK]


class NoPosters:
    async def delete(self, item_id: int) -> None:
        return None


async def make_card(sessions) -> int:
    return await LibraryRepository(sessions).create(
        Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="1",
             title="карточка", synced_at=WHEN)
    )


async def test_three_states_are_told_apart(sessions):
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)

    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, WHEN))
    await repository.record(item_id, ExternalRating(RatingSource.ROTTEN, None, WHEN))
    # Про Кинопоиск не спрашивали вовсе — строки нет.

    stored = {r.source: r.value for r in await repository.ratings_of(item_id)}
    assert stored == {RatingSource.IMDB: 8.6, RatingSource.ROTTEN: None}


async def test_an_empty_answer_is_not_a_missing_row(sessions):
    """Иначе фильм, которого MDBList не знает, перезапрашивался бы при
    каждом показе — так и было у предшественника."""
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.ROTTEN, None, WHEN))

    assert RatingSource.ROTTEN not in await repository.stale_sources(
        item_id, WANTED, now=WHEN
    )


async def test_a_source_never_asked_is_stale(sessions):
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)

    assert set(await repository.stale_sources(item_id, WANTED, now=WHEN)) == set(
        WANTED
    )


async def test_a_value_lives_a_month(sessions):
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, WHEN))

    fresh = await repository.stale_sources(
        item_id, WANTED, now=WHEN + VALUE_TTL - timedelta(days=1)
    )
    expired = await repository.stale_sources(
        item_id, WANTED, now=WHEN + VALUE_TTL + timedelta(days=1)
    )

    assert RatingSource.IMDB not in fresh
    assert RatingSource.IMDB in expired


async def test_exactly_at_the_deadline_is_still_fresh(sessions):
    """Сравнение строгое: ровно в срок ещё не протухло."""
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, WHEN))

    assert RatingSource.IMDB not in await repository.stale_sources(
        item_id, WANTED, now=WHEN + VALUE_TTL
    )


async def test_an_empty_answer_lives_a_week(sessions):
    """У свежего релиза оценка ещё может появиться — но ходить за ней
    ежедневно незачем."""
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.ROTTEN, None, WHEN))

    fresh = await repository.stale_sources(
        item_id, WANTED, now=WHEN + EMPTY_TTL - timedelta(days=1)
    )
    expired = await repository.stale_sources(
        item_id, WANTED, now=WHEN + EMPTY_TTL + timedelta(days=1)
    )

    assert RatingSource.ROTTEN not in fresh
    assert RatingSource.ROTTEN in expired


def test_the_empty_answer_expires_sooner_than_a_value():
    assert EMPTY_TTL < VALUE_TTL


async def test_recording_again_moves_the_deadline(sessions):
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, WHEN))

    later = WHEN + VALUE_TTL + timedelta(days=1)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.7, later))

    stored = {r.source: r.value for r in await repository.ratings_of(item_id)}
    assert stored[RatingSource.IMDB] == 8.7
    assert RatingSource.IMDB not in await repository.stale_sources(
        item_id, WANTED, now=later
    )


async def test_an_empty_answer_may_later_become_a_value(sessions):
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.ROTTEN, None, WHEN))

    later = WHEN + EMPTY_TTL + timedelta(days=1)
    await repository.record(item_id, ExternalRating(RatingSource.ROTTEN, 72.0, later))

    stored = {r.source: r.value for r in await repository.ratings_of(item_id)}
    assert stored[RatingSource.ROTTEN] == 72.0


async def test_only_the_wanted_sources_are_reported(sessions):
    """У кино и у игр наборы источников разные."""
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)

    stale = await repository.stale_sources(item_id, [RatingSource.STEAM], now=WHEN)
    assert stale == [RatingSource.STEAM]


async def test_ratings_go_away_with_the_card(sessions):
    item_id = await make_card(sessions)
    repository = ExternalRatingsRepository(sessions)
    await repository.record(item_id, ExternalRating(RatingSource.IMDB, 8.6, WHEN))

    await LibraryRepository(sessions).delete(item_id, posters=NoPosters())

    assert await repository.ratings_of(item_id) == []
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_external_ratings.py -v`
Ожидается: FAIL — `ImportError: cannot import name 'VALUE_TTL'`.

- [ ] **Шаг 3: Реализовать**

Дописать в `backend/storage/repository/external.py`, а в шапку добавить
`from datetime import datetime, timedelta`,
`from backend.model import ExternalId, ExternalRating, IdSource, RatingSource` и
`from backend.storage.tables import external_rating as external_rating_table`:

```python
# Срок годности считается от fetched_at, а не хранится полем: политику тогда
# можно менять, не трогая базу.
VALUE_TTL = timedelta(days=30)
EMPTY_TTL = timedelta(days=7)


class ExternalRatingsRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(self, item_id: int, rating: ExternalRating) -> None:
        """Пишем и находку, и честное «у источника нет». Отказ сюда не
        попадает вовсе: на входе ExternalRating, а Refusal в него не
        превратить."""
        statement = insert(external_rating_table).values(
            item_id=item_id,
            source=str(rating.source),
            value=rating.value,
            fetched_at=rating.fetched_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[external_rating_table.c.item_id,
                            external_rating_table.c.source],
            set_={"value": statement.excluded.value,
                  "fetched_at": statement.excluded.fetched_at},
        )
        async with self._sessions() as session:
            await session.execute(statement)
            await session.commit()

    async def ratings_of(self, item_id: int) -> list[ExternalRating]:
        async with self._sessions() as session:
            result = await session.execute(
                select(external_rating_table)
                .where(external_rating_table.c.item_id == item_id)
                .order_by(external_rating_table.c.source)
            )
            return [
                ExternalRating(source=RatingSource(row.source), value=row.value,
                               fetched_at=row.fetched_at)
                for row in result.all()
            ]

    async def stale_sources(self, item_id: int, wanted: list[RatingSource],
                            now: datetime) -> list[RatingSource]:
        """У кого спрашивать: у тех, кого не спрашивали вовсе, и у тех, чей
        ответ протух. Пустой ответ протухает быстрее значения."""
        known = {r.source: r for r in await self.ratings_of(item_id)}

        stale = []
        for source in wanted:
            stored = known.get(source)
            if stored is None:
                stale.append(source)
                continue
            ttl = VALUE_TTL if stored.value is not None else EMPTY_TTL
            if now - stored.fetched_at > ttl:
                stale.append(source)
        return stale
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_external_ratings.py -v`
Ожидается: PASS, одиннадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add backend/storage/repository/external.py \
        tests/backend/test_external_ratings.py
git commit -m "feat: оценки агрегаторов с тремя состояниями и сроками годности"
```

---

### Задача 5: Обрезка картинки

Чистая функция над байтами: ни сети, ни базы, ни знания о карточках. Живёт в
бэкенде через Pillow — чтобы работа с картинкой не уезжала в главный поток, где
от неё замирает окно.

**Обрезаем по центру до 2:3, без вопросов.** Рамку кадрирования с
перетаскиванием не делаем: это отдельный виджет, а выигрывает он в редком
случае, когда картинка сильно не той формы.

**Заодно ужимаем до 500×750.** Спека считает хранилище из ~80 КБ на постер —
тысяча карточек это 80 МБ. Фотография с телефона на 4000×6000 ломает эту
арифметику в десятки раз. **Это решение плана, в спеках его нет.**

**Применяется всё это только к залитым с диска картинкам.** Скачанный постер не
трогаем вовсе — он уже 2:3 у всех трёх источников, а перекодирование готового
JPEG теряет качество на ровном месте и обнуляет запас под высокую плотность
экрана, который спека держит сознательно.

**Файлы:**
- Изменить: `Pipfile`, `Pipfile.lock`
- Создать: `backend/service/__init__.py`, `backend/service/images.py`
- Создать: `tests/backend/test_images.py`

**Интерфейсы:**
- Отдаёт: `TARGET_RATIO` (2/3), `TARGET_SIZE` (500, 750), исключение `BadImage`,
  `crop_to_cover(data: bytes) -> bytes`.

- [ ] **Шаг 1: Поставить Pillow**

В `Pipfile` в раздел `[packages]` добавить `pillow = "*"` и выполнить:

```bash
pipenv install
```

- [ ] **Шаг 2: Написать падающий тест**

Создать `tests/backend/test_images.py`:

```python
import io

import pytest
from PIL import Image

from backend.service.images import TARGET_SIZE, BadImage, crop_to_cover


def picture(width: int, height: int, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (10, 20, 30)).save(buffer, format=fmt)
    return buffer.getvalue()


def size_of(data: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(data)).size


def test_a_wide_picture_is_cropped_on_the_sides():
    assert size_of(crop_to_cover(picture(2000, 1000))) == TARGET_SIZE


def test_a_tall_picture_is_cropped_top_and_bottom():
    assert size_of(crop_to_cover(picture(1000, 4000))) == TARGET_SIZE


def test_an_already_correct_ratio_is_only_resized():
    assert size_of(crop_to_cover(picture(600, 900))) == TARGET_SIZE


def test_a_small_picture_is_not_blown_up():
    """Растягивать маленькую картинку незачем: она станет только хуже."""
    assert size_of(crop_to_cover(picture(200, 300))) == (200, 300)


def test_the_crop_is_centred():
    """Левая и правая полосы срезаются поровну: центр остаётся центром."""
    source = Image.new("RGB", (900, 300), (0, 0, 0))
    for x in range(400, 500):
        for y in range(300):
            source.putpixel((x, y), (255, 0, 0))
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")

    result = Image.open(io.BytesIO(crop_to_cover(buffer.getvalue())))
    middle = result.getpixel((result.width // 2, result.height // 2))
    assert middle[0] > 200, "красная полоса из центра исходника потерялась"


def test_jpeg_is_accepted_too():
    assert size_of(crop_to_cover(picture(1200, 1800, fmt="JPEG"))) == TARGET_SIZE


def test_transparency_does_not_break_the_conversion():
    buffer = io.BytesIO()
    Image.new("RGBA", (1200, 1800), (10, 20, 30, 128)).save(buffer, format="PNG")
    assert size_of(crop_to_cover(buffer.getvalue())) == TARGET_SIZE


def test_the_result_is_always_the_same_format():
    """Чтобы интерфейс не гадал, что ему приехало."""
    for fmt in ("PNG", "JPEG"):
        data = crop_to_cover(picture(1200, 1800, fmt=fmt))
        assert Image.open(io.BytesIO(data)).format == "JPEG"


def test_degenerate_shapes_do_not_crash():
    for width, height in ((1, 1), (3000, 10), (10, 3000)):
        assert crop_to_cover(picture(width, height))


def test_garbage_is_a_named_error_not_a_crash():
    with pytest.raises(BadImage):
        crop_to_cover("это не картинка".encode())


def test_empty_bytes_are_a_named_error():
    with pytest.raises(BadImage):
        crop_to_cover(b"")
```

- [ ] **Шаг 3: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_images.py -v`
Ожидается: FAIL — `No module named 'backend.service'`.

- [ ] **Шаг 4: Реализовать**

Создать `backend/service/__init__.py` пустым и `backend/service/images.py`:

```python
import io

from PIL import Image, UnidentifiedImageError

TARGET_RATIO = 2 / 3
# Размер взят из w500 у TMDB. Решение плана: спека называет только пропорцию,
# но считает хранилище из ~80 КБ на постер.
TARGET_SIZE = (500, 750)

_QUALITY = 88


class BadImage(Exception):
    """Байты не разбираются как картинка."""


def crop_to_cover(data: bytes) -> bytes:
    """Обрезка по центру до 2:3 и ужатие до TARGET_SIZE.

    Только для залитых с диска картинок: скачанные постеры уже 2:3, и
    перекодировать их незачем.

    Маленькую картинку не растягиваем: от этого она только хуже."""
    try:
        source = Image.open(io.BytesIO(data))
        source.load()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise BadImage(str(error)) from error

    width, height = source.size
    if width / height > TARGET_RATIO:
        # Слишком широкая — режем бока поровну.
        keep = max(1, round(height * TARGET_RATIO))
        left = (width - keep) // 2
        box = (left, 0, left + keep, height)
    else:
        # Слишком высокая — режем верх и низ поровну.
        keep = max(1, round(width / TARGET_RATIO))
        top = (height - keep) // 2
        box = (0, top, width, top + keep)

    cropped = source.convert("RGB").crop(box)
    if cropped.width > TARGET_SIZE[0]:
        cropped = cropped.resize(TARGET_SIZE, Image.LANCZOS)

    buffer = io.BytesIO()
    cropped.save(buffer, format="JPEG", quality=_QUALITY, optimize=True)
    return buffer.getvalue()
```

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_images.py -v`
Ожидается: PASS, одиннадцать тестов.

- [ ] **Шаг 6: Коммит**

```bash
git add Pipfile Pipfile.lock backend/service tests/backend/test_images.py
git commit -m "feat: обрезка залитой картинки под 2:3 через Pillow"
```

---

### Задача 6: Загрузка и хранение обложки

**Постер — данные основного источника, и карточка его ждёт.** Не скачался —
карточка не пишется вовсе, как при любом другом неполном ответе: повторим при
следующем показе. Если обложки нет в самом источнике — ждать нечего.

**Скачанное не обрезаем.** У TMDB это `w500` — 500×750, у Steam
`library_600x900_2x` — настоящие 600×900, у GOG `coverVertical`. Все три уже
2:3, а 600×900 спека держит сознательно, «с запасом под высокую плотность
экрана».

**Клиент на источник свой.** Предохранитель живёт в `SourceHttp` и выключает
клиента целиком; один клиент на три разных CDN означал бы, что молчание одного
выключает обложки всех трёх магазинов.

**Файлы:**
- Создать: `backend/service/posters.py`
- Создать: `tests/backend/test_poster_service.py`

**Имя файла именно такое.** В плане 1 уже есть `tests/backend/test_posters.py` —
шесть тестов `PosterStore`, хранилища. Назвать этот файл так же значило бы
затереть их, а падение шага 2 на импорте это скрыло бы: общий прогон остался бы
зелёным, просто тестов стало бы меньше. Здесь проверяется сервис, там —
хранилище, и по слою они и разведены.

**Интерфейсы:**
- Потребляет: `SourceHttp`, `Reason`, `Refusal` из `backend.sources`;
  `PosterStore` из `backend.storage.posters`; `crop_to_cover`, `BadImage` из
  `backend.service.images`; `Source` из `backend.model`.
- Отдаёт: `PosterService(clients: Mapping[Source, SourceHttp], store: PosterStore)`
  с публичными полями `store` и `clients` (второе читает тест на то, что у
  каждого источника свой предохранитель), методами
  `fetch(source: Source, url: str) -> bytes | None | Refusal`,
  `save(item_id, data, now) -> None`,
  `store_upload(item_id, data, now) -> None` — залитая с диска картинка,
  обрезается,
  `aclose() -> None`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_poster_service.py`:

```python
import io
from datetime import datetime

import httpx
import pytest
import pytest_asyncio
from PIL import Image

from backend.model import Source
from backend.service.images import TARGET_SIZE, BadImage
from backend.service.posters import PosterService
from backend.sources.errors import Refusal
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore

WHEN = datetime(2026, 7, 27, 12, 0)


def picture(width: int = 600, height: int = 900) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (10, 20, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def responding(status: int, content: bytes = b"") -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda request: httpx.Response(status, content=content)
    )


async def build(tmp_path, transport) -> PosterService:
    store = PosterStore(tmp_path / "posters.db")
    await store.open()
    clients = {source: SourceHttp(f"poster:{source}", transport=transport)
               for source in (Source.TMDB, Source.STEAM, Source.GOG)}
    return PosterService(clients, store)


@pytest_asyncio.fixture
async def service(tmp_path):
    built = await build(tmp_path, responding(200, picture()))
    yield built
    await built.aclose()


async def test_a_downloaded_poster_is_not_re_encoded(service):
    """Скачанный уже 2:3. Перекодировать его — потерять качество и запас
    под высокую плотность экрана, который спека держит сознательно."""
    original = picture()
    data = await service.fetch(Source.TMDB, "https://example.com/poster.jpg")
    assert data == original
    assert Image.open(io.BytesIO(data)).size == (600, 900)


async def test_no_url_means_nothing_to_wait_for(service):
    """Обложки нет в самом источнике — он отдал всё, что имел."""
    assert await service.fetch(Source.TMDB, "") is None


async def test_a_failed_download_is_a_refusal(tmp_path):
    service = await build(tmp_path, responding(404))
    result = await service.fetch(Source.TMDB, "https://example.com/missing.jpg")
    await service.aclose()

    assert isinstance(result, Refusal)


async def test_an_empty_body_is_a_refusal(tmp_path):
    service = await build(tmp_path, responding(200, b""))
    result = await service.fetch(Source.TMDB, "https://example.com/poster.jpg")
    await service.aclose()

    assert isinstance(result, Refusal)


async def test_a_page_instead_of_a_picture_is_a_refusal(tmp_path):
    """CDN отдал заглушку или капчу под кодом 200. Проверку кода и непустоты
    она проходит насквозь, и HTML лёг бы в хранилище как обложка — а карточка
    считалась бы при этом полной."""
    service = await build(tmp_path, responding(200, b"<html>404 not found</html>"))
    result = await service.fetch(Source.TMDB, "https://example.com/poster.jpg")
    await service.aclose()

    assert isinstance(result, Refusal)


async def test_each_source_has_its_own_client(service):
    """Молчание одного CDN не должно выключать обложки остальных."""
    breakers = {id(client.breaker) for client in service.clients.values()}
    assert len(breakers) == 3


async def test_an_unknown_source_is_a_refusal(service):
    result = await service.fetch(Source.MANUAL, "https://example.com/p.jpg")
    assert isinstance(result, Refusal)


async def test_saved_poster_comes_back_from_the_store(service):
    data = await service.fetch(Source.TMDB, "https://example.com/poster.jpg")
    await service.save(1, data, now=WHEN)

    assert await service.store.get(1) == data


async def test_an_upload_is_cropped(service):
    """Залитая с диска — единственное, что обрезается."""
    await service.store_upload(1, picture(4000, 1000), now=WHEN)

    stored = await service.store.get(1)
    assert Image.open(io.BytesIO(stored)).size == TARGET_SIZE


async def test_a_bad_upload_is_a_named_error(service):
    with pytest.raises(BadImage):
        await service.store_upload(1, "не картинка".encode(), now=WHEN)
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_poster_service.py -v`
Ожидается: FAIL — `No module named 'backend.service.posters'`.

- [ ] **Шаг 3: Реализовать**

Создать `backend/service/posters.py`:

```python
import logging
from collections.abc import Mapping
from datetime import datetime

import httpx

from backend.model import Source
from backend.service.images import crop_to_cover
from backend.sources.errors import Reason, Refusal
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore

logger = logging.getLogger(__name__)

# Подписи форматов, которые встречаются у постеров: JPEG, PNG, WebP.
_SIGNATURES = (b"\xff\xd8", b"\x89PNG\r\n\x1a\n", b"RIFF")


class PosterService:
    """Обложка едет от того же источника, что и карточка, и карточка её
    ждёт: не скачалась — не пишем ничего, повторим при следующем показе."""

    def __init__(self, clients: Mapping[Source, SourceHttp],
                 store: PosterStore) -> None:
        self.clients = dict(clients)
        self.store = store

    async def fetch(self, source: Source, url: str) -> bytes | None | Refusal:
        if not url:
            # Обложки нет в самом источнике — ждать нечего.
            return None

        client = self.clients.get(source)
        if client is None:
            logger.warning("постер: нет клиента для источника %s", source)
            return Refusal(source="poster", reason=Reason.BROKEN,
                           detail=f"нет клиента для {source}")

        response = await client.get(url)
        if not isinstance(response, httpx.Response):
            return response
        if response.status_code != 200 or not response.content:
            logger.warning("постер %s: HTTP %s, %s байт",
                           url, response.status_code, len(response.content))
            return Refusal(source="poster", reason=Reason.BROKEN,
                           detail=f"HTTP {response.status_code}")

        if not response.content.startswith(_SIGNATURES):
            # Проверяем подпись формата, а не разбираем картинку. CDN, отдающий
            # под кодом 200 страницу-заглушку или капчу, проходит проверку кода
            # и непустоты насквозь — и HTML лёг бы в хранилище как обложка, а
            # карточка при этом считалась бы полной.
            logger.warning("постер %s: тело не похоже на изображение", url)
            return Refusal(source="poster", reason=Reason.BROKEN,
                           detail="тело не изображение")

        # Скачанное не трогаем: у всех трёх источников оно уже 2:3. Не трогаем
        # — не значит не смотрим: подпись читается, но ничего не перекодирует.
        return response.content

    async def save(self, item_id: int, data: bytes, now: datetime) -> None:
        await self.store.put(item_id, data, now)

    async def store_upload(self, item_id: int, data: bytes,
                           now: datetime) -> None:
        """Единственное место, где картинка обрезается: у залитой с диска
        форма произвольная."""
        await self.store.put(item_id, crop_to_cover(data), now)

    async def aclose(self) -> None:
        for client in self.clients.values():
            await client.aclose()
        await self.store.close()
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_poster_service.py -v`
Ожидается: PASS, десять тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add backend/service/posters.py tests/backend/test_poster_service.py
git commit -m "feat: загрузка обложки со своим клиентом на источник"
```

---

### Задача 7: Сборка карточки в базу

Здесь `SourceCard` из плана 2 превращается в строки плана 1. Главное правило:
**частичной карточки из внешнего источника в базе не бывает.**

Отсюда две вещи. Первая: обложка добывается **до** первой записи — иначе при
неудаче в базе осталась бы карточка без неё, а `synced_at` врал бы, что на этот
момент она была полной. Вторая: если запись всё-таки сорвалась на середине —
занятый IMDb ID, занятая идентичность карточки, — **убираем за собой** и
возвращаем отказ.

Общей транзакции на два файла базы не бывает, поэтому уборка делается кодом.

**Обложку можно передать заранее скачанной.** Спека считает, что круги 2а и 2б
можно пустить параллельно; оркестратор из плана 4 передаст готовые байты.

**Файлы:**
- Создать: `backend/service/cards.py`
- Создать: `tests/backend/test_card_writer.py`

**Интерфейсы:**
- Потребляет: `LibraryRepository`, `ItemExists`, `GenresRepository`,
  `CreditRepository`, `ExternalIdsRepository`, `IdentityTaken`,
  `ExternalRatingsRepository`, `PosterService`; `SourceCard`, `Refusal`.
- Отдаёт: `CardWriter(library, genres, people, companies, ids, ratings, posters)`
  с публичным полем `posters` и методом
  `save(card: SourceCard, poster: bytes | None = None) -> int | Refusal`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_card_writer.py`:

```python
import io
import logging
from datetime import datetime

import httpx
import pytest_asyncio
from PIL import Image
from sqlalchemy import text

from backend.model import (
    CompanyRole,
    Credit,
    ExternalId,
    ExternalRating,
    GenreSource,
    IdSource,
    Item,
    Kind,
    PersonRole,
    RatingSource,
    Source,
    SourceCard,
)
from backend.service.cards import CardWriter
from backend.service.posters import PosterService
from backend.sources.errors import Refusal
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore
from backend.storage.repository.credits import companies, people
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository

WHEN = datetime(2026, 7, 27, 12, 0)


def picture() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (600, 900), (10, 20, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def source_card(**overrides) -> SourceCard:
    fields = dict(
        item=Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="157336",
                  title="Интерстеллар", synced_at=WHEN, year=2014,
                  poster_url="https://example.com/poster.jpg", runtime=169),
        genre_ext_ids=(
            (GenreSource.TMDB, "878"), (GenreSource.TMDB, "12"),
        ),
        people=(
            Credit("Кристофер Нолан", PersonRole.DIRECTOR,
                   source=Source.TMDB, source_id="525"),
            Credit("Мэттью Макконахи", PersonRole.ACTOR, position=0,
                   source=Source.TMDB, source_id="10297"),
        ),
        companies=(),
        external_ids=(ExternalId(IdSource.IMDB, "tt0816692"),),
        ratings=(ExternalRating(RatingSource.TMDB, 8.4, WHEN),),
    )
    fields.update(overrides)
    return SourceCard(**fields)


async def build(sessions, engine, tmp_path, status: int = 200) -> CardWriter:
    async with engine.begin() as connection:
        await connection.execute(text(
            "INSERT INTO genre (id, name, kind) VALUES "
            "(1, 'фантастика', 'film'), (2, 'приключения', 'film')"
        ))
        await connection.execute(text(
            "INSERT INTO genre_map (source, ext_id, genre_id) VALUES "
            "('tmdb', '878', 1), ('tmdb', '12', 2)"
        ))

    store = PosterStore(tmp_path / "posters.db")
    await store.open()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status, content=picture())
    )
    clients = {source: SourceHttp(f"poster:{source}", transport=transport)
               for source in (Source.TMDB, Source.STEAM, Source.GOG)}

    return CardWriter(
        library=LibraryRepository(sessions),
        genres=GenresRepository(sessions),
        people=people(sessions),
        companies=companies(sessions),
        ids=ExternalIdsRepository(sessions),
        ratings=ExternalRatingsRepository(sessions),
        posters=PosterService(clients, store),
    )


@pytest_asyncio.fixture
async def writer(sessions, engine, tmp_path):
    built = await build(sessions, engine, tmp_path)
    yield built
    await built.posters.aclose()


async def test_a_whole_card_lands_in_the_database(writer, sessions):
    item_id = await writer.save(source_card())
    assert isinstance(item_id, int)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.title == "Интерстеллар"
    assert stored.runtime == 169


async def test_genres_are_resolved_through_the_reference(writer, sessions):
    item_id = await writer.save(source_card())
    names = {g.name for g in await GenresRepository(sessions).genres_of(item_id)}
    assert names == {"фантастика", "приключения"}


async def test_people_are_created_and_attached(writer, sessions):
    item_id = await writer.save(source_card())
    found = await people(sessions).credits_of(item_id)
    assert {(c.name, c.role) for c in found} == {
        ("Кристофер Нолан", PersonRole.DIRECTOR),
        ("Мэттью Макконахи", PersonRole.ACTOR),
    }


async def test_the_same_person_on_two_cards_is_one_row(writer, sessions):
    """Склейка по идентификатору источника: иначе «показать всё с этим
    человеком» разваливается на пять Кристоферов Ноланов."""
    await writer.save(source_card())
    await writer.save(source_card(
        item=Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="374720",
                  title="Дюнкерк", synced_at=WHEN,
                  poster_url="https://example.com/p.jpg"),
        external_ids=(),
    ))

    assert len(await people(sessions).find_by_name("Кристофер Нолан")) == 1


async def test_two_namesakes_from_the_source_do_not_merge(writer, sessions):
    """Два разных актёра с одним именем не должны стать одной строкой —
    человек в импорте не участвует и заметить подмену не может."""
    await writer.save(source_card(people=(
        Credit("Василий Пупкин", PersonRole.ACTOR, position=0,
               source=Source.TMDB, source_id="1"),
        Credit("Василий Пупкин", PersonRole.ACTOR, position=1,
               source=Source.TMDB, source_id="2"),
    )))

    assert len(await people(sessions).find_by_name("Василий Пупкин")) == 2


async def test_studios_without_identity_are_merged_by_name(writer, sessions):
    """У Steam и GOG студии приходят голыми строками — склеивать их больше
    не по чему, и это законно."""
    for source_id in ("1", "2"):
        await writer.save(source_card(
            item=Item(id=0, kind=Kind.GAME, source=Source.STEAM,
                      source_id=source_id, title=f"игра {source_id}",
                      synced_at=WHEN, poster_url="https://example.com/p.jpg"),
            genre_ext_ids=(), people=(), external_ids=(), ratings=(),
            companies=(Credit("CD Projekt RED", CompanyRole.DEVELOPER),),
        ))

    assert len(await companies(sessions).find_by_name("CD Projekt RED")) == 1


async def test_external_identifiers_and_ratings_are_written(writer, sessions):
    item_id = await writer.save(source_card())

    ids = await ExternalIdsRepository(sessions).ids_of(item_id)
    ratings = await ExternalRatingsRepository(sessions).ratings_of(item_id)
    assert [i.value for i in ids] == ["tt0816692"]
    # Со значением и отметкой времени, а не только с источником: на них стоят
    # три состояния external_rating и сроки годности. Проверка одного лишь
    # источника пропустила бы запись нуля, None или чужого числа.
    assert [(r.source, r.value) for r in ratings] == [(RatingSource.TMDB, 8.4)]
    assert ratings[0].fetched_at == WHEN


async def test_the_poster_is_stored(writer):
    item_id = await writer.save(source_card())
    assert await writer.posters.store.has(item_id)


async def test_a_prefetched_poster_is_not_downloaded_again(writer):
    """Круги 2а и 2б можно пустить параллельно — оркестратор передаст байты."""
    ready = picture()
    item_id = await writer.save(source_card(), poster=ready)
    assert await writer.posters.store.get(item_id) == ready


async def test_nothing_is_written_when_the_poster_fails(sessions, engine, tmp_path):
    """Частичной карточки из внешнего источника в базе не бывает."""
    writer = await build(sessions, engine, tmp_path, status=500)
    result = await writer.save(source_card())
    await writer.posters.aclose()

    assert isinstance(result, Refusal)
    assert await LibraryRepository(sessions).find_by_source(
        Source.TMDB, "157336"
    ) is None


async def test_a_taken_identifier_leaves_nothing_behind(writer, sessions):
    """Занятый IMDb ID срывает запись на середине — убираем за собой."""
    await writer.save(source_card())

    result = await writer.save(source_card(
        item=Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="999",
                  title="дубль", synced_at=WHEN,
                  poster_url="https://example.com/p.jpg"),
    ))

    assert isinstance(result, Refusal)
    assert await LibraryRepository(sessions).find_by_source(
        Source.TMDB, "999"
    ) is None


async def test_a_taken_card_identity_is_a_refusal_not_an_exception(writer):
    """Контракт save — int или Refusal, исключений наружу не летит."""
    await writer.save(source_card())
    result = await writer.save(source_card(external_ids=()))
    assert isinstance(result, Refusal)


async def test_a_card_without_a_poster_url_is_still_written(writer, sessions):
    """Обложки нет в самом источнике — ждать нечего."""
    item_id = await writer.save(source_card(
        item=Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="1",
                  title="Без обложки", synced_at=WHEN),
        external_ids=(),
    ))
    assert isinstance(item_id, int)
    assert not await writer.posters.store.has(item_id)


async def test_an_unknown_genre_does_not_stop_the_card(writer, sessions):
    """Источник добавил жанр, которого в миграции нет: карточка показывается
    без него, и всё — незнакомое молча отбрасывается."""
    item_id = await writer.save(source_card(genre_ext_ids=(
        (GenreSource.TMDB, "878"), (GenreSource.TMDB, "99999"),
    )))

    names = {g.name for g in await GenresRepository(sessions).genres_of(item_id)}
    assert names == {"фантастика"}


async def test_companies_are_written_for_a_game(writer, sessions):
    item_id = await writer.save(source_card(
        item=Item(id=0, kind=Kind.GAME, source=Source.STEAM, source_id="292030",
                  title="The Witcher 3", synced_at=WHEN,
                  poster_url="https://example.com/p.jpg"),
        genre_ext_ids=(), people=(), external_ids=(), ratings=(),
        companies=(Credit("CD Projekt RED", CompanyRole.DEVELOPER),),
    ))

    found = await companies(sessions).credits_of(item_id)
    assert [c.name for c in found] == ["CD Projekt RED"]
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_card_writer.py -v`
Ожидается: FAIL — `No module named 'backend.service.cards'`.

- [ ] **Шаг 3: Реализовать**

Создать `backend/service/cards.py`:

```python
import logging

from backend.model import Credit, GenreSource, SourceCard
from backend.service.posters import PosterService
from backend.sources.errors import Reason, Refusal
from backend.storage.repository.credits import CreditRepository
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import ItemExists, LibraryRepository

logger = logging.getLogger(__name__)


class CardWriter:
    """Собирает SourceCard в строки базы.

    Порядок задан правилом «частичной карточки не бывает»: сначала добываем
    обложку, и только потом пишем. Если запись сорвалась на середине —
    убираем за собой: общей транзакции на два файла базы не бывает."""

    def __init__(
        self,
        library: LibraryRepository,
        genres: GenresRepository,
        people: CreditRepository,
        companies: CreditRepository,
        ids: ExternalIdsRepository,
        ratings: ExternalRatingsRepository,
        posters: PosterService,
    ) -> None:
        self._library = library
        self._genres = genres
        self._people = people
        self._companies = companies
        self._ids = ids
        self._ratings = ratings
        self.posters = posters

    async def save(self, card: SourceCard,
                   poster: bytes | None = None) -> int | Refusal:
        if poster is None:
            poster = await self.posters.fetch(card.item.source,
                                              card.item.poster_url)
            if isinstance(poster, Refusal):
                # Не скачалась — не пишем ничего, повторим при следующем показе.
                return poster

        try:
            item_id = await self._library.create(card.item)
        except ItemExists as error:
            logger.warning("карточка уже в библиотеке: %s", error)
            return Refusal(source=str(card.item.source), reason=Reason.BROKEN,
                           detail=str(error))

        try:
            await self._write_the_rest(item_id, card, poster)
        except Exception as error:
            # Ловим всё, а не один `IdentityTaken`. Последний шаг записи —
            # постер, а он ложится **во второй файл базы**, со своей дисковой
            # ошибкой и своей блокировкой. Оставить там строку карточки значит
            # получить ту самую частичную карточку, которой «не бывает»:
            # обложки нет, состава может не быть, а `synced_at` утверждает, что
            # на этот момент карточка была полной, — и перезапроса не будет,
            # потому что она свежая.
            logger.warning("откатываю карточку %s: %s", item_id, error)
            await self._library.delete(item_id, self.posters.store)
            return Refusal(source=str(card.item.source), reason=Reason.BROKEN,
                           detail=str(error))

        return item_id

    async def _resolved(self, card: SourceCard) -> list[int]:
        """Жанры карточки по нашему справочнику.

        Идентификаторы приезжают из разных пространств: жанры магазина и его
        теги нумеруются порознь, и `9` у Steam — это жанр «Гонки» и тег
        «Стратегия». Справочник спрашивается по каждому пространству отдельно,
        а дубли снимаются: два разных тега нередко ведут в один наш жанр."""
        spaces: dict[GenreSource, list[str]] = {}
        for space, ext_id in card.genre_ext_ids:
            spaces.setdefault(space, []).append(ext_id)

        found: list[int] = []
        for space, ext_ids in spaces.items():
            for genre_id in await self._genres.resolve(space, ext_ids):
                if genre_id not in found:
                    found.append(genre_id)
        return found

    async def _write_the_rest(self, item_id: int, card: SourceCard,
                              poster: bytes | None) -> None:
        await self._genres.set_for_item(item_id, await self._resolved(card))

        await self._attach(self._people, item_id, card.people)
        await self._attach(self._companies, item_id, card.companies)

        for external in card.external_ids:
            await self._ids.put(item_id, external)
        for rating in card.ratings:
            await self._ratings.record(item_id, rating)

        if poster is not None:
            await self.posters.save(item_id, poster, card.item.synced_at)

    async def _attach(self, repository: CreditRepository, item_id: int,
                      credits: tuple[Credit, ...]) -> None:
        for credit in credits:
            entity_id = await repository.ensure(credit)
            await repository.attach(item_id, entity_id, credit.role,
                                    credit.position)
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_card_writer.py -v`
Ожидается: PASS, пятнадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add backend/service/cards.py tests/backend/test_card_writer.py
git commit -m "feat: сборка карточки источника в базу с уборкой за собой"
```

---

### Задача 8: Разбор ссылки на внешнюю базу

Привязка делается **вставкой ссылки**, а не поиском: если поиск находит вещь,
ручная карточка не появляется вовсе — её заводят как раз тогда, когда поиск
промахнулся, а страница найдена в браузере.

Чистая функция: строка и тип содержимого на входе, разобранная ссылка на выходе.
Ни сети, ни базы.

**Голый идентификатор принимается только у кино и сериалов.** Там источник один
и двусмысленности нет. У игр голое число ничего не значит: Steam и GOG
нумеруются независимо, и по числу их не различить — нужна ссылка.

**Файлы:**
- Создать: `backend/model/link.py`; изменить `backend/model/__init__.py`
- Создать: `tests/backend/test_links.py`

**Интерфейсы:**
- Отдаёт: `ExternalLink(source, source_id, kind)` и
  `parse_link(raw: str, kind: Kind | None = None) -> ExternalLink | None` —
  оба в `backend.model.link` и оба реэкспортируются из `backend.model`.

**Почему в модели, а не в сервисе.** `parse_link` — чистый разбор строки: у
него два импорта, `re` и сам `ExternalLink`. Живёт он рядом с типом, который
производит, и по ту же сторону границы: ссылку в окне карточки разбирает
клиент, а импортировать ради этого модуль сервиса ему нельзя — вместе с ним
приедут репозитории, сессия и поход к базе мимо рантайма.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_links.py`:

```python
import pytest

from backend.model import Kind, Source
from backend.model.link import ExternalLink, parse_link


@pytest.mark.parametrize(
    "raw, source, source_id, kind",
    [
        ("https://www.themoviedb.org/movie/157336",
         Source.TMDB, "157336", Kind.MOVIE),
        ("themoviedb.org/tv/83867", Source.TMDB, "83867", Kind.SERIES),
        ("https://store.steampowered.com/app/292030/",
         Source.STEAM, "292030", Kind.GAME),
        ("https://www.gog.com/game/arcanum_of_steamworks_and_magick_obscura",
         Source.GOG, "arcanum_of_steamworks_and_magick_obscura", Kind.GAME),
    ],
)
def test_addresses_are_understood(raw, source, source_id, kind):
    link = parse_link(raw)
    assert (link.source, link.source_id, link.kind) == (source, source_id, kind)


def test_the_type_comes_from_the_path():
    """movie или tv в адресе — единственное, что отличает фильм от сериала."""
    assert parse_link("themoviedb.org/movie/1").kind is Kind.MOVIE
    assert parse_link("themoviedb.org/tv/1").kind is Kind.SERIES


def test_an_address_wins_over_the_toggle():
    """Стоишь на «Играх», вставил ссылку на фильм — верим ссылке."""
    link = parse_link("themoviedb.org/movie/157336", kind=Kind.GAME)
    assert (link.source, link.kind) == (Source.TMDB, Kind.MOVIE)


def test_a_tail_after_the_identifier_is_dropped():
    link = parse_link("https://www.themoviedb.org/movie/157336-interstellar")
    assert link.source_id == "157336"


def test_query_parameters_are_dropped():
    link = parse_link("https://store.steampowered.com/app/292030/?snr=1_7_7_")
    assert link.source_id == "292030"


@pytest.mark.parametrize("kind", [Kind.MOVIE, Kind.SERIES])
def test_a_bare_identifier_is_accepted_for_films(kind):
    """У кино источник один, двусмысленности нет."""
    link = parse_link("157336", kind=kind)
    assert (link.source, link.source_id, link.kind) == (Source.TMDB, "157336", kind)


def test_a_bare_identifier_is_refused_for_games():
    """Steam и GOG нумеруются независимо: по числу их не различить."""
    assert parse_link("292030", kind=Kind.GAME) is None


def test_a_bare_identifier_without_a_type_is_refused():
    """Тип берётся из тумблера, и он всегда известен. Без него не гадаем."""
    assert parse_link("157336") is None


def test_whitespace_is_trimmed():
    assert parse_link("  themoviedb.org/movie/157336  ").source_id == "157336"


def test_the_age_gate_address_of_steam_is_understood():
    """У игр с возрастным шлюзом в строке браузера стоит именно этот адрес."""
    link = parse_link("https://store.steampowered.com/agecheck/app/292030/")
    assert (link.source, link.source_id) == (Source.STEAM, "292030")


def test_the_case_of_the_address_does_not_matter():
    """Человек вставляет то, что скопировал: «GOG.com» из письма — обычное
    дело."""
    link = parse_link("https://www.GOG.com/game/arcanum")
    assert (link.source, link.source_id) == (Source.GOG, "arcanum")


@pytest.mark.parametrize("raw", ["", "   ", "не ссылка", "https://example.com/",
                                 "themoviedb.org/person/525"])
def test_nonsense_is_refused(raw):
    assert parse_link(raw, kind=Kind.MOVIE) is None
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_links.py -v`
Ожидается: FAIL — `cannot import name 'parse_link' from 'backend.model.link'`.

- [ ] **Шаг 3: Тип разобранной ссылки и её разбор**

Создать `backend/model/link.py` — тип и разбор в одном файле, разносить их не
за чем:

```python
import re
from dataclasses import dataclass

from backend.model.kinds import Kind, Source


@dataclass(frozen=True, slots=True)
class ExternalLink:
    """Разобранная ссылка на страницу во внешней базе."""

    source: Source
    source_id: str
    kind: Kind

# Хвосты вроде -interstellar и параметры после ? отбрасываются: идентификатор
# кончается там, где кончаются цифры.
# Регистр не важен: человек вставляет то, что скопировал, а адресная строка и
# почтовые клиенты любят поднимать первую букву — «GOG.com» ломало бы разбор.
_TMDB = re.compile(r"themoviedb\.org/(movie|tv)/(\d+)", re.I)
# `agecheck/` — возрастной шлюз: у игр с ним именно этот адрес стоит в строке
# браузера, и без него разбор промахивается по половине ретро.
_STEAM = re.compile(r"store\.steampowered\.com/(?:agecheck/)?app/(\d+)", re.I)
# У GOG в адресе не идентификатор, а слаг: числовой придётся искать в каталоге.
_GOG = re.compile(r"gog\.com/(?:[a-z-]+/)?game/([a-z0-9_]+)", re.I)
_BARE = re.compile(r"^\d+$")

_TMDB_KINDS = {"movie": Kind.MOVIE, "tv": Kind.SERIES}
_FILMS = (Kind.MOVIE, Kind.SERIES)


def parse_link(raw: str, kind: Kind | None = None) -> ExternalLink | None:
    """`kind` — то, что выбрано тумблером. Ссылка его перебивает: она знает
    точнее."""
    text = raw.strip()
    if not text:
        return None

    found = _TMDB.search(text)
    if found:
        return ExternalLink(source=Source.TMDB, source_id=found.group(2),
                            kind=_TMDB_KINDS[found.group(1)])

    found = _STEAM.search(text)
    if found:
        return ExternalLink(source=Source.STEAM, source_id=found.group(1),
                            kind=Kind.GAME)

    found = _GOG.search(text)
    if found:
        return ExternalLink(source=Source.GOG, source_id=found.group(1),
                            kind=Kind.GAME)

    # Голое число значит что-то только у кино: там источник один. У игр Steam
    # и GOG нумеруются независимо, и по числу их не различить.
    if _BARE.match(text) and kind in _FILMS:
        return ExternalLink(source=Source.TMDB, source_id=text, kind=kind)

    return None
```

Добавить `ExternalLink` и `parse_link` в импорт и в `__all__` в
`backend/model/__init__.py`.

**У GOG в `source_id` лежит слаг, а не числовой идентификатор.** Превращение
слага в число — сетевой шаг, и он **живьём не проверен**; см. открытые вопросы.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_links.py -v`
Ожидается: PASS, двадцать тестов — девять обычных и три параметризации на
четыре, два и пять случаев.

- [ ] **Шаг 5: Коммит**

```bash
git add backend/model/link.py backend/model/__init__.py \
        tests/backend/test_links.py
git commit -m "feat: разбор ссылки на страницу во внешней базе"
```

---

### Задача 9: Привязка — внешнее заполняет только пустое

**Что ты написал — остаётся твоим, приезжает только то, чего не было.**

**Непустое значит занятое, в том числе у полей, которых много.** Вписал одного
разработчика — состав считается заполненным целиком и не дополняется.

**Галочка «перезаписать данные» заменяет только приехавшее.** Если источник
состава не отдал — свой остаётся: у игр `person_credit` заполняется только
руками, и восстановить стёртое будет неоткуда.

**Если ссылка ведёт на карточку, которая уже есть в библиотеке**, привязка не
выполняется: идентичность занята, поднимается `ItemExists`. Это ответ на прямое
действие человека, а не сбой источника, поэтому здесь исключение, а не `Refusal`.

**`synced_at` ставится заново** — иначе карточка, заведённая полгода назад, в
момент привязки сразу окажется просроченной.

**Файлы:**
- Создать: `backend/service/linking.py`
- Создать: `tests/backend/test_linking.py`

**Интерфейсы:**
- Потребляет: то же, что `CardWriter`, плюс `ItemExists`; `Item`, `SourceCard`.
- Отдаёт: `merge_fields(existing, incoming) -> Item` и
  `overwrite_fields(existing, incoming) -> Item` — две чистые функции слияния,
  «своё поверх приехавшего» и «приехавшее поверх своего»; обе трогают только
  непустое;
  `Linker(library, genres, people, companies, ids, ratings, posters)` с
  публичным полем `posters` и методом
  `link(item_id: int, card: SourceCard, overwrite: bool = False) -> None`.
  Поднимает `ItemExists`, если занята идентичность карточки **или** любой из
  её внешних идентификаторов.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_linking.py`:

```python
import io
from datetime import datetime

import httpx
import pytest
import pytest_asyncio
from PIL import Image
from sqlalchemy import text

from backend.model import (
    CompanyRole,
    Credit,
    GenreSource,
    Item,
    Kind,
    PersonRole,
    Source,
    SourceCard,
    new_manual_item,
)
from backend.service.linking import Linker, merge_fields
from backend.service.posters import PosterService
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore
from backend.storage.repository.credits import companies, people
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import ItemExists, LibraryRepository

WHEN = datetime(2026, 7, 27, 12, 0)


def picture() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (600, 900), (10, 20, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def incoming(**overrides) -> SourceCard:
    fields = dict(
        item=Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="157336",
                  title="Interstellar", synced_at=WHEN, year=2014,
                  synopsis="официальный синопсис", runtime=169,
                  poster_url="https://example.com/poster.jpg"),
        genre_ext_ids=((GenreSource.TMDB, "878"),),
        people=(Credit("Кристофер Нолан", PersonRole.DIRECTOR,
                       source=Source.TMDB, source_id="525"),),
        companies=(), external_ids=(), ratings=(),
    )
    fields.update(overrides)
    return SourceCard(**fields)


def test_merge_keeps_what_the_human_typed():
    mine = Item(id=1, kind=Kind.MOVIE, source=Source.MANUAL, source_id="u",
                title="Интерстеллар", synced_at=WHEN, synopsis="мой текст")
    merged = merge_fields(mine, incoming().item)

    assert merged.title == "Интерстеллар"
    assert merged.synopsis == "мой текст"


def test_merge_fills_only_the_empty():
    mine = Item(id=1, kind=Kind.MOVIE, source=Source.MANUAL, source_id="u",
                title="Интерстеллар", synced_at=WHEN)
    merged = merge_fields(mine, incoming().item)

    assert merged.year == 2014
    assert merged.runtime == 169


def test_merge_never_moves_identity_or_the_sync_mark():
    mine = Item(id=1, kind=Kind.MOVIE, source=Source.MANUAL, source_id="u",
                title="Интерстеллар", synced_at=WHEN)
    merged = merge_fields(mine, incoming().item)

    assert merged.id == 1
    assert merged.source is Source.MANUAL
    assert merged.source_id == "u"
    assert merged.synced_at == WHEN


async def make_linker(sessions, engine, tmp_path) -> Linker:
    async with engine.begin() as connection:
        await connection.execute(text(
            # Жанра два, и это важно: с одним нельзя проверить, что привязка
            # не затирает выбранное человеком — дополнять было бы нечем.
            "INSERT INTO genre (id, name, kind) VALUES "
            "(1, 'фантастика', 'film'), (2, 'приключения', 'film')"
        ))
        await connection.execute(text(
            "INSERT INTO genre_map (source, ext_id, genre_id) "
            "VALUES ('tmdb', '878', 1), ('tmdb', '12', 2)"
        ))

    store = PosterStore(tmp_path / "posters.db")
    await store.open()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=picture())
    )
    clients = {source: SourceHttp(f"poster:{source}", transport=transport)
               for source in (Source.TMDB, Source.STEAM, Source.GOG)}

    return Linker(
        library=LibraryRepository(sessions),
        genres=GenresRepository(sessions),
        people=people(sessions),
        companies=companies(sessions),
        ids=ExternalIdsRepository(sessions),
        ratings=ExternalRatingsRepository(sessions),
        posters=PosterService(clients, store),
    )


@pytest_asyncio.fixture
async def linker(sessions, engine, tmp_path):
    built = await make_linker(sessions, engine, tmp_path)
    yield built
    await built.posters.aclose()


async def manual_card(sessions, **fields) -> int:
    return await LibraryRepository(sessions).create(
        new_manual_item(Kind.MOVIE, fields.pop("title", "Интерстеллар"),
                        synced_at=WHEN, **fields)
    )


async def test_linking_moves_the_card_to_the_source(linker, sessions):
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming())

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.source is Source.TMDB
    assert stored.source_id == "157336"
    assert stored.title == "Интерстеллар", "своё название затёрли"


async def test_linking_fills_the_gaps(linker, sessions):
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming())

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.year == 2014
    assert stored.synopsis == "официальный синопсис"


async def test_linking_refreshes_the_sync_mark(linker, sessions):
    """Иначе карточка, заведённая полгода назад, сразу окажется просроченной."""
    item_id = await manual_card(sessions)
    before = (await LibraryRepository(sessions).get(item_id)).synced_at

    await linker.link(item_id, incoming())

    assert (await LibraryRepository(sessions).get(item_id)).synced_at > before


async def test_overwrite_also_refreshes_the_sync_mark(linker, sessions):
    """Отметка парсера не должна затирать момент привязки."""
    item_id = await manual_card(sessions)
    before = (await LibraryRepository(sessions).get(item_id)).synced_at

    await linker.link(item_id, incoming(), overwrite=True)

    assert (await LibraryRepository(sessions).get(item_id)).synced_at > before


async def test_a_filled_cast_is_not_topped_up(linker, sessions):
    """Вписал одного разработчика — состав считается заполненным целиком."""
    item_id = await manual_card(sessions)
    mine = await people(sessions).create_manual("Мой режиссёр")
    await people(sessions).attach(item_id, mine, PersonRole.DIRECTOR)

    await linker.link(item_id, incoming())

    names = [c.name for c in await people(sessions).credits_of(item_id)]
    assert names == ["Мой режиссёр"]


async def test_an_empty_cast_is_filled(linker, sessions):
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming())

    names = [c.name for c in await people(sessions).credits_of(item_id)]
    assert names == ["Кристофер Нолан"]


async def test_a_chosen_genre_is_not_topped_up(linker, sessions):
    """Источник даёт **свой** жанр, отличный от выбранного руками. С пустым
    `genre_ext_ids` дополнять было бы нечем по построению, и тест не упал бы
    даже при реализации, которая молча затирает выбранное человеком."""
    item_id = await manual_card(sessions)
    await GenresRepository(sessions).set_for_item(item_id, [1])

    await linker.link(item_id, incoming(genre_ext_ids=((GenreSource.TMDB, "12"),)))

    names = [g.name for g in await GenresRepository(sessions).genres_of(item_id)]
    assert names == ["фантастика"]


async def test_overwrite_takes_everything_the_source_gave(linker, sessions):
    """На случай, когда карточка заводилась на скорую руку."""
    item_id = await manual_card(sessions, synopsis="набросок")
    mine = await people(sessions).create_manual("Мой режиссёр")
    await people(sessions).attach(item_id, mine, PersonRole.DIRECTOR)

    await linker.link(item_id, incoming(), overwrite=True)

    stored = await LibraryRepository(sessions).get(item_id)
    assert stored.title == "Interstellar"
    assert stored.synopsis == "официальный синопсис"
    names = [c.name for c in await people(sessions).credits_of(item_id)]
    assert names == ["Кристофер Нолан"]


async def test_overwrite_does_not_wipe_what_the_source_never_had(linker, sessions):
    """У игр состав заполняется только руками: ни Steam, ни GOG людей не
    отдают. Стереть его перезаписью — значит потерять безвозвратно."""
    item_id = await manual_card(sessions)
    mine = await people(sessions).create_manual("Мой режиссёр")
    await people(sessions).attach(item_id, mine, PersonRole.DIRECTOR)
    studio = await companies(sessions).create("Моя студия")
    await companies(sessions).attach(item_id, studio, CompanyRole.DEVELOPER)

    await linker.link(item_id, incoming(people=(), companies=()), overwrite=True)

    assert [c.name for c in await people(sessions).credits_of(item_id)] == [
        "Мой режиссёр"
    ]
    assert [c.name for c in await companies(sessions).credits_of(item_id)] == [
        "Моя студия"
    ]


async def test_overwrite_does_not_wipe_genres_the_source_never_had(linker, sessions):
    item_id = await manual_card(sessions)
    await GenresRepository(sessions).set_for_item(item_id, [1])

    await linker.link(item_id, incoming(genre_ext_ids=()), overwrite=True)

    names = [g.name for g in await GenresRepository(sessions).genres_of(item_id)]
    assert names == ["фантастика"]


async def test_overwrite_does_replace_the_genres_the_source_gave(linker, sessions):
    """Обратная сторона предыдущего: с галочкой приехавшее побеждает. Без этого
    теста пара выше проходит и у реализации, которая жанры не трогает вовсе."""
    item_id = await manual_card(sessions)
    await GenresRepository(sessions).set_for_item(item_id, [1])

    await linker.link(
        item_id, incoming(genre_ext_ids=((GenreSource.TMDB, "12"),)), overwrite=True
    )

    names = [g.name for g in await GenresRepository(sessions).genres_of(item_id)]
    assert names == ["приключения"]


async def test_linking_to_an_occupied_identity_is_refused(linker, sessions):
    library = LibraryRepository(sessions)
    await library.create(
        Item(id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="157336",
             title="уже есть", synced_at=WHEN)
    )
    mine = await manual_card(sessions, title="мой дубль")

    with pytest.raises(ItemExists):
        await linker.link(mine, incoming())

    assert (await library.get(mine)).source is Source.MANUAL


async def test_a_manual_card_gets_its_poster_on_linking(linker, sessions):
    item_id = await manual_card(sessions)

    await linker.link(item_id, incoming())

    assert await linker.posters.store.has(item_id)


async def test_an_own_poster_is_not_replaced(linker, sessions):
    """Обложка — такое же поле: непустое значит занятое."""
    item_id = await manual_card(sessions)
    await linker.posters.store_upload(item_id, picture(), now=WHEN)
    mine = await linker.posters.store.get(item_id)

    await linker.link(item_id, incoming())

    assert await linker.posters.store.get(item_id) == mine
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/backend/test_linking.py -v`
Ожидается: FAIL — `No module named 'backend.service.linking'`.

- [ ] **Шаг 3: Реализовать**

Создать `backend/service/linking.py`:

```python
import logging
from dataclasses import replace

from backend.model import Credit, Item, SourceCard
from backend.service.posters import PosterService
from backend.sources.errors import Refusal
from backend.storage.repository.credits import CreditRepository
from backend.storage.repository.external import (
    ExternalIdsRepository,
    ExternalRatingsRepository,
)
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import ItemExists, LibraryRepository

logger = logging.getLogger(__name__)

# Поля, которые может долить источник. Идентичность, id и synced_at сюда не
# входят: их ставит сама привязка.
_FILLABLE = (
    "title", "original_title", "year", "released_at", "synopsis", "poster_url",
    "runtime", "seasons_count", "episodes_count",
)


def merge_fields(existing: Item, incoming: Item) -> Item:
    """Внешнее заполняет только пустое. Что человек написал — остаётся его."""
    filled = {}
    for name in _FILLABLE:
        if getattr(existing, name) in (None, ""):
            filled[name] = getattr(incoming, name)
    return replace(existing, **filled)


def overwrite_fields(existing: Item, incoming: Item) -> Item:
    """Галочка «перезаписать данные» — приехавшее поверх своего, но **только
    приехавшее**. Поле, которого источник не отдал, остаётся как было.

    Подменять карточку объектом источника целиком нельзя: разборщики кладут в
    непришедшие поля пустую строку, а не оставляют их незаполненными. У TMDB с
    `language=ru-RU` пустой `overview` — обычное дело, и написанный руками
    синопсис исчез бы безвозвратно. Для жанров и состава это правило уже
    соблюдается ниже; здесь оно то же."""
    filled = {}
    for name in _FILLABLE:
        value = getattr(incoming, name)
        if value not in (None, ""):
            filled[name] = value
    return replace(existing, **filled)


class Linker:
    def __init__(
        self,
        library: LibraryRepository,
        genres: GenresRepository,
        people: CreditRepository,
        companies: CreditRepository,
        ids: ExternalIdsRepository,
        ratings: ExternalRatingsRepository,
        posters: PosterService,
    ) -> None:
        self._library = library
        self._genres = genres
        self._people = people
        self._companies = companies
        self._ids = ids
        self._ratings = ratings
        self.posters = posters

    async def link(self, item_id: int, card: SourceCard,
                   overwrite: bool = False) -> None:
        """Поднимает ItemExists, если идентичность занята: это ответ на
        прямое действие человека, а не сбой источника."""
        # Занятость проверяем целиком и до первой записи. Идентичность самой
        # карточки ловит `library.link`, а вот занятый чужой карточкой imdb_id
        # всплыл бы только на `ids.put` — то есть после того, как source_id уже
        # переставлен и поля уже слиты. Карточка осталась бы привязанной
        # наполовину, без отката и с необъявленным типом исключения наружу.
        for external in card.external_ids:
            owner = await self._ids.find_item(external.source, external.value)
            if owner is not None and owner != item_id:
                raise ItemExists(
                    f"{external.source}:{external.value} уже за карточкой {owner}"
                )

        # Упрёмся здесь и ничего не тронем. Здесь же ставится свежий synced_at.
        await self._library.link(item_id, card.item.source, card.item.source_id)

        existing = await self._library.get(item_id)
        merge = overwrite_fields if overwrite else merge_fields
        merged = merge(existing, card.item)
        await self._library.replace_fields(item_id, merged)

        await self._fill_genres(item_id, card, overwrite)
        await self._fill(self._people, item_id, card.people, overwrite)
        await self._fill(self._companies, item_id, card.companies, overwrite)

        for external in card.external_ids:
            await self._ids.put(item_id, external)
        for rating in card.ratings:
            await self._ratings.record(item_id, rating)

        await self._fill_poster(item_id, merged, overwrite)

    async def _fill_genres(self, item_id: int, card: SourceCard,
                           overwrite: bool) -> None:
        if not card.genre_ext_ids:
            # Источник жанров не отдал — стирать свои нечего и незачем.
            return
        if not overwrite and await self._genres.genres_of(item_id):
            # Выбрал один жанр — набор считается заполненным целиком.
            return
        resolved = await self._genres.resolve(card.item.source,
                                              list(card.genre_ext_ids))
        if resolved:
            await self._genres.set_for_item(item_id, resolved)

    async def _fill(self, repository: CreditRepository, item_id: int,
                    credits: tuple[Credit, ...], overwrite: bool) -> None:
        if not credits:
            # У игр состав заполняется только руками — ни Steam, ни GOG людей
            # не отдают. Стереть его перезаписью значит потерять навсегда.
            return
        if not overwrite and await repository.credits_of(item_id):
            # Вписал одного — состав заполнен целиком и не дополняется.
            return
        if overwrite:
            await repository.detach_all(item_id)
        for credit in credits:
            entity_id = await repository.ensure(credit)
            await repository.attach(item_id, entity_id, credit.role,
                                    credit.position)

    async def _fill_poster(self, item_id: int, item: Item,
                           overwrite: bool) -> None:
        if not overwrite and await self.posters.store.has(item_id):
            return
        poster = await self.posters.fetch(item.source, item.poster_url)
        if isinstance(poster, bytes):
            await self.posters.save(item_id, poster, item.synced_at)
        elif isinstance(poster, Refusal):
            # Карточку не откатываем: строка уже есть, данные уже свои.
            logger.warning("обложка при привязке %s не приехала: %s",
                           item_id, poster.detail)
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_linking.py -v`
Ожидается: PASS, семнадцать тестов.

- [ ] **Шаг 5: Прогнать всё целиком**

Запустить: `pipenv run pytest -v`
Ожидается: PASS, весь набор планов 1, 2 и 3.

- [ ] **Шаг 6: Коммит**

```bash
git add backend/service/linking.py tests/backend/test_linking.py
git commit -m "feat: привязка карточки с правилом «внешнее заполняет только пустое»"
```

---

## Что этот план сознательно не делает

| Что | Куда |
|---|---|
| **Проверка полноты ответа основного источника** | план 2: заслон стоит выше по течению — разбор поднимает `Incomplete`, если в ответе TMDB нет блока состава, и `SourceCard` с потерянным составом просто не рождается. `CardWriter` получает уже проверенное и своей проверки не делает |
| Поиск: своё сразу, внешнее доливкой, снятие дублей | план 4 |
| Три круга загрузки и их порядок; параллельные 2а и 2б | план 4: `save` уже принимает готовые байты обложки |
| **Превращение `Missing` в строку с пустым значением** | план 4: второе из трёх состояний `external_rating` производит сервис обогащения. Репозиторий его уже принимает и хранит, а кто решает, что ответ источника — это «у него нет», решается там |
| Фоновая догрузка оценок только для видимых | план 4: `stale_sources` отвечает на вопрос «у кого спрашивать» |
| Перезапрос по сроку `synced_at` | план 4: `refresh_series_counts` из плана 1 готов |
| Запросы разделов, фильтры, сортировки, гистограмма | план 4 |
| Слаг GOG → числовой идентификатор | план 4: это сетевой шаг, и живьём он не проверен |
| Связать заведённого руками человека с внешним | не делаем: см. `docs/specs/2026-07-27-people.md` |
| Слияние двух людей в одного | не делаем: там же |

## Числа и правила, взятые не из спек

Решения этого плана. Ни одно ниоткуда не следует, менять свободно:

| Что | Значение | Почему так |
|---|---|---|
| `TARGET_SIZE` у залитой картинки | 500×750 | из `w500` у TMDB; спека называет только пропорцию, но считает хранилище из ~80 КБ на постер |
| `_QUALITY` при сохранении | 88 | ничем не обосновано |
| Сопоставление в подсказке | по началу имени | вхождение дало бы «Нолан» на запрос «олан» |
| Длина списка подсказки | 10 | ничем не обосновано |
| Разрешение ничьей в подсказке | любой, какой отдаст база | второй ключ сортировки не заводим |
| Источник у голого идентификатора | TMDB, и только у кино | у игр по числу магазин не определить |

## Открытые вопросы

**Слаг GOG живьём не проверен.** `parse_link` кладёт в `source_id` слаг, а
каталогу нужен числовой идентификатор. Как одно превращается в другое — шаг,
помеченный в спеке как непроверенный, и он уехал в план 4 вместе с остальной
сетью.

**Привязка карточки одного типа к ссылке другого.** Тумблер стоит на «Фильмах»,
вставлена ссылка на сериал: `parse_link` вернёт `Kind.SERIES`, и что делать
дальше — менять тип карточки, отказывать или спрашивать — не записано ни в
спеке, ни здесь. Сейчас `Linker` тип не трогает вовсе: `merge_fields` его не
меняет, а при перезаписи он приезжает из `card.item`.
