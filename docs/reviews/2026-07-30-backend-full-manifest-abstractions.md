# Ревью бэкенда целиком: правила 7, 10 и 11

Диапазон: `4fd1235..43a7922` (весь бэкенд). Судится код на `HEAD`.
Измерение: три правила манифеста, которых не проверяет машина, —
**7 (абстракция со второй реализацией)**, **10 (логика не в интерфейсе, здесь —
на границе слоёв)**, **11 (комментарий объясняет неочевидное)**.

Прочитано целиком: `docs/module-map.md`, `backend/app.py`, `backend/config.py`,
`backend/model/__init__.py`, `model/view.py`, `model/rating.py`,
`model/results.py`, `backend/sources/registry.py`, `sources/http.py`,
`sources/errors.py`, `sources/undocumented.py`,
`sources/ratings/kinopoisk/mirror.py`, `backend/service/asking.py`,
`service/card_parts.py`, `service/cards.py`, `service/loading.py`,
`service/posters.py`, `service/search.py`, `service/library.py`,
`service/enrich.py` (публичная часть), `backend/storage/repository/base.py`,
`repository/library.py`, `repository/credits.py` (голова и хвост),
`backend/storage/posters.py`, `tests/backend/test_layers.py`,
`tests/backend/test_offline.py`, обе клиентские плана в местах, где они зовут
бэкенд. Комментарии и однострочные докстринги `backend/` просмотрены сплошь —
все 128 строк комментариев и все 30 однострочных докстрингов.

Мутаций не гонял, тестов не запускал, рабочее дерево не трогал.

## Strengths

- **Правило 7 держится по-настоящему, а не на словах.** Во всём своём коде —
  `backend`, `client`, `tests`, `scripts`, `migrations` — нет ни одного
  `Protocol`, `ABC`, `abstractmethod` или `NotImplementedError` (проверено
  грепом по всем пяти пакетам, ноль совпадений). Раздел «Абстракции с одной
  реализацией» в карте модулей содержит три строки, и все три — тестовые
  двойники либо требование чужой библиотеки. Разбор — в отдельном разделе ниже.
- **Каждый вынесенный кусок сам называет, на какой реализации он появился.**
  `Repository` — «заведено на третьей реализации, а не в ожидании первой»
  (`backend/storage/repository/base.py:13`); `CardParts` — «наследников двое,
  `CardWriter` и `Linker`» (`backend/service/card_parts.py:18`);
  `refuse_undocumented` — «отдельным модулем, а не методом `SourceHttp`:
  транспорт ответы не классифицирует» (`backend/sources/undocumented.py:15`);
  `to_credit` объясняет, почему лежит не в `rows.py`
  (`backend/storage/repository/credits.py:60`). Следующему проходу не придётся
  разбирать это заново — довод уже записан рядом с кодом.
- **Комментарии — образцовые по правилу 11.** Ноль `TODO`/`FIXME`/`XXX`, ноль
  закомментированного кода (искал регуляркой по началам инструкций), ноль
  декоративных рамок, ноль `# noqa` и `# type: ignore`, ноль ссылок на чужие
  проекты и пути. Почти каждый комментарий — либо замеренный факт («у Steam 220
  запросов подряд прошли без троттлинга», `sources/undocumented.py:8`;
  «выключенный Wi-Fi отвечает ошибкой сразу», `sources/http.py:19`), либо
  объяснение того, чего в коде не видно («`NULL NOT IN (3)` в SQL — это NULL, а
  не истина», `repository/sections.py:73`; «`id` SQLite выдаёт повторно, `item`
  без `AUTOINCREMENT`», `repository/library.py:130`). Проверку «удали —
  потеряется ли смысл» не проходит ровно одна пара строк, и та не комментарий, а
  докстринг (см. Minor 1).
- **Правило 10 в главном соблюдено: ни `Row`, ни сессии, ни ORM-объекта наружу
  нет.** Все репозитории отдают типы `backend/model/`, и это не соглашение, а
  устройство: `Repository._mapped`/`_maybe` принимают преобразователь, а
  преобразователи собраны в `storage/rows.py`. Сырой `httpx.Response` дальше
  клиента источника не уходит: `PosterService._picture` превращает его в
  `bytes` (`service/posters.py:56`).
- **Находка предыдущего ревью закрыта, и закрыта по правилу 7.**
  `ViewsRepository` с поверхности `Backend` снят, а `LibraryService.views_of`
  — сквозной метод, а не новый класс, и причина записана прямо в докстринге:
  «отдельный класс на один проброс был бы абстракцией без второй реализации»
  (`service/library.py:20`).
- **Отказ — данные, а не второй канал.** `answered()` (`service/asking.py:10`) —
  единственная точка перехвата, и она сознательно не ловит `CancelledError`, с
  объяснением почему. Через границу потоков исключений не летит.

## Issues

### Critical (Must Fix)

Не найдено. Ни одной абстракции в ожидании второй реализации; ни одного
ORM-объекта, `Row`, `httpx.Response` или открытой сессии в сигнатуре публичного
метода.

### Important (Should Fix)

#### 1. Через границу требуется передать живое хранилище: `LibraryRepository.delete`

`backend/storage/repository/library.py:125` — **правило 10**.

```python
async def delete(self, item_id: int, posters: PosterStore) -> None:
```

Что утекает: `PosterStore` держит `AsyncEngine` (`backend/storage/posters.py:40`),
то есть открытый движок второй базы. Публичный метод требует, чтобы вызывающий
раздобыл его и передал. Вызывающий — клиент: план 6 уже пишет вызов целиком,
`backend.library.delete(item_id, backend.posters.store)`
(`docs/plans/2026-07-27-client-modals.md:3157` и `:3276`), и так же устроен
`tests/backend/test_offline.py:130`.

Утекает не только объект, но и знание: «удалить карточку» — это две базы в
строго определённом порядке, и порядок этот критичен (о нём есть отдельный
комментарий на `library.py:128`). Сейчас правильность порядка держится на том,
что клиент подставит нужный аргумент.

Чем заменить: одна операция на стороне бэкенда, принимающая `int` и ничего не
возвращающая, — метод `Backend` либо метод сервиса, который и так держит оба
хранилища (`PosterService` уже держит `store`, `CardWriter` уже зовёт эту пару в
`service/cards.py:44` и `:55`). Публичная подпись должна стать
`delete(item_id: int)`.

Почему важно: это единственное место, где через границу слоёв едет не данные, а
объект с открытым соединением к базе. Правило «через границу ходят только
простые данные» (`docs/specs/2026-07-27-async-and-qt.md:50`) нарушено буквально,
а не по духу.

#### 2. Типы, которые клиент обязан понимать, лежат вне `backend/model/`

**Правило 10.** Публичные методы возвращают `Refusal`, `Missing` и
`ExternalSearch`:

- `backend/service/posters.py:81` → `bytes | None | Refusal`;
- `backend/service/loading.py:58` → `int | Missing | Refusal`;
- `backend/service/loading.py:88` → `SourceCard | Missing | Refusal`;
- `backend/service/search.py:72` → `ExternalSearch` (объявлен там же, `:31`,
  и несёт `tuple[Refusal, ...]`).

`Refusal`, `Missing` и `Reason` живут в `backend/sources/errors.py`,
`ExternalSearch` — в `backend/service/search.py`. Спека прямо говорит: через
границу ходят «типы из `backend/model/`, байты, числа и строки»
(`docs/specs/2026-07-27-async-and-qt.md:50`), а `tests/backend/test_layers.py:18`
это проверяет машиной: клиенту открыты только `backend.model` и
`backend.config`.

Следствие уже написано в плане 5: `from backend.sources.errors import Reason,
Refusal` (`docs/plans/2026-07-27-client-shell.md:5627`). Этот импорт уронит
`test_client_takes_only_the_boundary_types_from_the_backend` на первом же
клиентском слайсе. Обойтись без него нельзя: клиент обязан отличать отказ от
результата и различать причины — плашка снизу говорит разное при обрыве сети и
при исчерпанной квоте, и `tests/backend/test_offline.py:84` этого требует.

Чем заменить: перенести `Reason`, `Found`, `Missing`, `Refusal` в
`backend/model/` — они уже `frozen=True, slots=True` и ни от чего своего не
зависят, `errors.py` не импортирует ни одного нашего модуля; `ExternalSearch` —
туда же, рядом с `CardView`. Альтернатива — сознательно расширить
`ALLOWED_FROM_BACKEND`, но тогда правило «типы границы лежат в `backend/model/`»
из `docs/specs/2026-07-27-code-structure.md:49` правится вместе с ним.

Почему важно: предыдущее ревью похвалило обе половины по отдельности — и «типы
границы простые», и «граница проверяется машиной», — не заметив, что одно
противоречит другому. Расхождение не видно ни одной мутацией и всплывёт только
при первом клиентском коде.

#### 3. `Backend.sources` отдаёт клиенту сами клиенты источников и их `httpx`

`backend/app.py:55`, `backend/sources/registry.py:21-34` — **правило 10**.

`Sources` — датакласс с полями `tmdb`, `steam`, `gog`, `mdblist`, `omdb`,
`kinopoisk` и `connections: tuple[SourceHttp, ...]`. Через `backend.sources.tmdb`
главный поток Qt может позвать `.search()` напрямую — уйти в сеть из потока с
циклом Qt, ровно то, от чего граница и заведена. Через
`backend.sources.connections` он добирается до `SourceHttp`, внутри которого
живой `httpx.AsyncClient` (`backend/sources/http.py:71`).

Потребителя у поля со стороны клиента нет: во всём плане 5 и плане 6 ни одной
ссылки на `backend.sources` как на поле (единственное совпадение по `sources.` —
импорт `backend.sources.errors`, находка 2). Поле нужно только `aclose()`
(`app.py:64`) и тесту закрытия (`test_offline.py:238`).

Чем заменить: переименовать в `_sources` — ровно как уже сделано с `_engine`.
Публичная поверхность от этого не теряет ничего.

Та же дыра, помельче, у обложек: `PosterService.clients` и `PosterService.store`
— публичные атрибуты (`backend/service/posters.py:28-29`), так что
`backend.posters` — второй маршрут и к `httpx`, и к базе постеров. `store` при
этом используется клиентом намеренно (находка 1); после её починки оба атрибута
надо закрыть подчёркиванием.

#### 4. Два репозитория на границе без единого потребителя

`backend/app.py:46-47` — **правило 10**, и заодно правило 8.

```python
ids: ExternalIdsRepository
external_ratings: ExternalRatingsRepository
```

Ни один из двух не зовётся ниоткуда: ни в плане 5, ни в плане 6, ни в
`tests/backend/test_offline.py` (проверено грепом по `ids.`, `external_ratings.`
и по строковым именам вызовов в фейковом рантайме планов). Внутри бэкенда оба
уже держат `Enricher` (`service/enrich.py:47-48`) и `CardParts`
(`service/card_parts.py:36-37`), которым их передают отдельно.

Чем заменить: убрать оба поля из `Backend`. Сборка не меняется — объекты
создаются в `build_backend` и уезжают в `Enricher` и в `parts`.

Почему важно: репозиторий на границе — не только лишнее поле, а приглашение.
Пока поле есть, первый же клиентский слайс, которому понадобится внешний
идентификатор, возьмёт его отсюда, а не попросит сервисный метод.

### Minor (Nice to Have)

#### 1. Два докстринга утверждают правило, которого код не держит

`backend/service/library.py:19` — «а через границу слоёв клиент репозитории не
видит вовсе»; `backend/service/library.py:37` — «репозитории клиенту не видны».
**Правило 11.**

Что теряется при удалении: **ничего верного.** `Backend` отдаёт девять
репозиториев (`app.py:39-47`), и клиентские планы их зовут —
`backend.ratings.set_score`, `backend.tags.assign`, `backend.wishlist.add`,
`backend.library.delete` (`docs/plans/2026-07-27-client-modals.md:3929-3935`),
`genres.list_for_kind`, `tags.tags_of`. Комментарий не объясняет решение, а
сообщает факт, и факт ложный.

Чем заменить: сузить до того, что правда, — «`ViewsRepository` наружу не
отдаётся: клиент читает список, а не словарь по номеру». Это и есть настоящий
довод, ради которого `views_of` заведён.

#### 2. `Backend._engine: object`

`backend/app.py:57`. Аннотация не говорит ничего, при этом `aclose` зовёт
`.dispose()` (`app.py:66`), а тест — `._engine.pool.checkedin()`
(`test_offline.py:228`). `app.py` — код бэкенда и вправе назвать `AsyncEngine`
своим именем; сейчас аннотация выключает любую проверку типов на самом опасном
поле сборки. Ни к 7, ни к 10, ни к 11 напрямую не относится — отмечаю как
замеченное по пути.

#### 3. Теги переезжают границу в двух видах

`CardView.tags: tuple[Tag, ...]` (`backend/model/view.py:46`) против
`TagsRepository.tags_of() -> list[tuple[int, str]]`
(`backend/storage/repository/tags.py:120`), который план 6 зовёт для модалки
тегов (`docs/plans/2026-07-27-client-modals.md:2132`). Оба — простые данные,
утечки нет. Но одно и то же клиент будет держать под двумя типами, и `Tag`,
заведённый как тип границы, в половине путей не используется. Правило 10 не
нарушено, порядок — да.

#### 4. Два однострочных докстринга проверены и оставлены

`backend/model/query.py:72` — `Bucket`: «Столбец гистограммы». Удалить нельзя:
поля `score` и `count` сами не говорят, что объект — столбец гистограммы, а имя
`Bucket` тем более. `backend/storage/repository/credits.py:151` — `ensure`:
«Найти существующего или завести нового». На грани пересказа имени, но само имя
`ensure` неоднозначно, и строка снимает вопрос. Оба оставить; записано, чтобы
следующий проход не разбирал их заново.

## Проблема в самом требовании

**Правило «через границу слоёв клиент репозитории не видит вовсе» проект не
держит и, судя по всему, никогда не собирался держать.**

Формулировка встречается ровно в трёх местах: прозой в плане 6
(`docs/plans/2026-07-27-client-modals.md:3936`) и дважды докстрингом в
`service/library.py`. Против неё стоит всё остальное: `Backend` спроектирован как
девять репозиториев плюс семь сервисов; план 6 в том же абзаце, где формулирует
правило, пишет `ratings.set_score(...)` и `wishlist.add(...)`; а
`tests/backend/test_offline.py` целиком построен на прямых вызовах репозиториев
через `Backend`.

То есть предыдущее ревью нашло настоящую вещь — `ViewsRepository` на поверхности,
— но обобщило её до правила, которого нет. Развилка:

- либо правило настоящее — и тогда над девятью репозиториями нужен сервисный
  слой, а обе клиентские планы переписываются;
- либо оно про один `ViewsRepository` — и тогда формулировку надо поправить во
  всех трёх местах.

Это решение пользователя, а не рецензента. Все четыре находки Important выше от
развилки не зависят: они верны при любом из двух ответов.

## Абстракции: проверено

Из карты модулей — раздел «Абстракции с одной реализацией», плюс всё, что карта
не видит: реестры, фабричные функции, описатели, точки внедрения.

| Кандидат | Где | Вторая реализация | Вердикт |
|---|---|---|---|
| `Base` → `Note` | `tests/backend/test_session.py:86` | нет | Одна, но оправдана: `DeclarativeBase` — требование SQLAlchemy, без наследника таблицу не объявить. Живёт в одном тесте, в `backend/` не выходит. |
| `FakeRatings` → `Breaking` | `tests/backend/test_enrich.py:27,40` | нет | Одна, но оправдана: тестовый двойник, отличается ровно тем, ради чего заведён, — падает не тем, что клиенты ловят. Сам `FakeRatings` — наследник `FakeClient`, у которого пять наследников. |
| `ViewsRepository` → `Forgetful` | `tests/backend/test_feed.py:68` | — | Не абстракция: `ViewsRepository` боевой, `Forgetful` — подмена поведения на один сценарий (карточка исчезла между двумя запросами). |
| `Repository` | `backend/storage/repository/base.py:10` | `LibraryRepository`, `RatingsRepository`, `TagsRepository`, `WishlistRepository`, `GenresRepository`, `CreditRepository`, `ExternalIdsRepository`, `ExternalRatingsRepository`, `SectionsRepository`, `ViewsRepository` — десять | Оправдана; докстринг сам сообщает, что заведена на третьей. |
| `CardParts` | `backend/service/card_parts.py:14` | `CardWriter`, `Linker` — две | Оправдана. |
| `Sources` (реестр) | `backend/sources/registry.py:21` | шесть клиентов: `TmdbClient`, `SteamClient`, `GogClient`, `MdbListClient`, `OmdbClient`, `KinopoiskClient` | Оправдана; спека структуры кода отдельно оговаривает, что общее заведено «не в ожидании второй реализации, а потому что источников уже шесть». |
| `Entity` (описатель) | `backend/storage/repository/credits.py:38` | `PEOPLE`, `COMPANIES` — два экземпляра | Оправдана. |
| `people()` / `companies()` | `backend/storage/repository/credits.py:266,270` | обе используются в `app.py:100-101` | Не фабрика, а два именованных конструктора. Оправданы. |
| `mirror.py` (общее у зеркал) | `backend/sources/ratings/kinopoisk/mirror.py` | `PoiskkinoClient`, `UnofficialClient` — две | Оправдана. |
| `KinopoiskClient` (обёртка) | `backend/sources/ratings/kinopoisk/client.py:19` | два зеркала под ней | Оправдана: наружу источник один, запасной путь внутри. |
| `refuse_undocumented` | `backend/sources/undocumented.py:14` | `SteamClient`, `GogClient` — две | Оправдана, довод записан в докстринге. |
| `convert.py` | `backend/sources/convert.py` | три и больше источников | Оправдана; вынесено на третьем. |
| `statements.py` (`clearing`, `upserting`) | `backend/storage/statements.py` | четыре и больше мест | Оправдана; вынесено на четвёртой копии. |
| `answered()` | `backend/service/asking.py:10` | зовут `search`, `loading`, `enrich`, `posters` | Оправдана. |
| `resolved_genres()` | `backend/service/genres.py` | `CardWriter`, `Linker` — две | Оправдана. |
| `item_fk` / `genre_fk` | `backend/storage/tables/base.py` | много таблиц в `catalog.py` и `mine.py` | Оправданы. |
| `rows.py` (`to_item` и прочие) | `backend/storage/rows.py` | по несколько репозиториев на каждую | Оправданы. |
| `Outcome: TypeAlias` | `backend/sources/errors.py:39` | — | Не абстракция: объединение трёх конкретных типов, а не точка расширения. |
| `SourceHttp`, `Breaker` | `backend/sources/http.py:55,25` | — | Не абстракции: по одному конкретному классу, наследников нет, интерфейса над ними нет. Экземпляров у `SourceHttp` девять. |
| `clock: Callable[[], datetime]` | `http.py:63`, `loading.py:38`, `enrich.py:45` | боевая одна (`datetime.now`) + подставные часы в тестах | Оправдана: внедряемая зависимость, которую `CLAUDE.md` требует прямо; проверить срок отката иначе нечем. |
| `transport: httpx.AsyncBaseTransport \| None` | `app.py:70`, `registry.py:68`, `http.py:62` | боевая одна + `httpx.MockTransport` в тестах | Оправдана: параметр чужой библиотеки, довод записан в докстринге `build_backend`. |

Своих `ABC`, `Protocol`, `abstractmethod` и `NotImplementedError` в проекте нет
ни одного — ни в `backend`, ни в `client`, ни в `tests`, ни в `scripts`, ни в
`migrations`.

## Recommendations

1. **Сначала — развилка про репозитории на границе** (раздел «Проблема в самом
   требовании»). От ответа зависит, чинить ли находку 4 удалением двух полей или
   заводить сервисный слой над всеми девятью.
2. **Находку 2 чинить до первого клиентского слайса**, а не после: сейчас это
   перенос четырёх датаклассов из `sources/errors.py` в `backend/model/`, потом —
   правка уже написанного клиента.
3. **Находки 1, 3 и 4 маленькие и независимые**: подпись `delete`,
   переименование `sources` → `_sources` вместе с закрытием
   `PosterService.clients` и `.store`, удаление двух полей `Backend`. Все три —
   одним слайсом.
4. **Раздел «Абстракции с одной реализацией» в карте видит только
   наследование.** Реестры, фабричные функции и точки внедрения он не
   показывает, и следующий рецензент по правилу 7 снова будет искать их руками.
   Таблица выше закрывает этот проход; если держать её как список разобранного —
   по образцу `docs/not-duplicates.md`, — следующий проход обойдётся сверкой
   отпечатков.
5. **Комментарии трогать не надо ничего, кроме двух докстрингов в
   `service/library.py`.** Правило 11 в этом коде выполняется лучше, чем в
   большинстве проектов: сплошной проход дал одну находку на 128 строк
   комментариев.

## Assessment

**Ready to merge?** With fixes.

**Reasoning:** Правило 7 чисто — ни одной абстракции в ожидании второй
реализации, и каждая существующая называет свою вторую поимённо; правило 11
чисто, кроме двух докстрингов, повторяющих несуществующее правило. Правило 10
даёт четыре находки уровня Important: через границу требуется передать живой
`PosterStore`, типы отказов лежат вне разрешённого клиенту `backend/model/`,
`Backend.sources` открывает главному потоку сетевые клиенты, и два репозитория
висят на поверхности без потребителя — ни одна не ломает нынешние 924 теста, все
четыре выстрелят на первом клиентском слайсе.
