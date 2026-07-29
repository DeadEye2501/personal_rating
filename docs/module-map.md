# Карта модулей

Собирается из кода, а не ведётся руками.
Править руками нельзя — правки затрёт следующая сборка.
Число в скобках — сколько строк занимает объявление.

## backend — 45 модулей

### `backend/config.py` — 49 строк

Настройки приложения, прочитанные из окружения.

Зависит от: —

- `class Config` (20)
  - `def library_db(self) -> Path` (2)
  - `def posters_db(self) -> Path` (2)
  - `def log_file(self) -> Path` (2)
- `def value(env: Mapping[str, str], name: str) -> str` (4)
- `def load_config(env: Mapping[str, str], base_dir: Path) -> Config` (11)

### `backend/model/__init__.py` — 45 строк

Поверхность модели: отсюда типы границы слоёв импортирует клиент.

Зависит от: `backend.model.card`, `backend.model.credit`, `backend.model.external`, `backend.model.genre`, `backend.model.item`, `backend.model.kinds`, `backend.model.rating`, `backend.model.ratings`, `backend.model.search`, `backend.model.suggestion`

Отдаёт наружу: `CompanyRole`, `Credit`, `ExternalId`, `ExternalRating`, `Genre`, `GenreKind`, `GenreSource`, `IdSource`, `Item`, `Kind`, `PersonRole`, `Rating`, `RatingSource`, `Ratings`, `SearchHit`, `Source`, `SourceCard`, `Suggestion`, `average_score`, `new_manual_item`, `new_source_id`


### `backend/model/card.py` — 25 строк

Всё, что источник отдал о карточке, в наших типах.

Зависит от: `backend.model.credit`, `backend.model.external`, `backend.model.item`, `backend.model.kinds`

- `class SourceCard` (14)

### `backend/model/credit.py` — 18 строк

Человек или студия в роли на карточке.

Зависит от: `backend.model.kinds`

- `class Credit` (10)

### `backend/model/external.py` — 19 строк

Что знают о карточке чужие источники.

Зависит от: `backend.model.kinds`

- `class ExternalId` (3)
- `class ExternalRating` (4)

### `backend/model/genre.py` — 12 строк

Жанр на границе слоёв.

Зависит от: `backend.model.kinds`

- `class Genre` (4)

### `backend/model/item.py` — 48 строк

Карточка любого типа содержимого на границе слоёв.

Зависит от: `backend.model.kinds`

- `class Item` (16)
- `def new_source_id() -> str` (5)
- `def new_manual_item(kind: Kind, title: str, **fields) -> Item` (13)

### `backend/model/kinds.py` — 70 строк

Закрытые наборы значений, которыми описывается карточка.

Зависит от: —

- `class Kind(StrEnum)` (4)
- `class Source(StrEnum)` (7)
- `class GenreSource(StrEnum)` (10)
- `class IdSource(StrEnum)` (7)
- `class RatingSource(StrEnum)` (11)
- `class PersonRole(StrEnum)` (4)
- `class CompanyRole(StrEnum)` (3)
- `class GenreKind(StrEnum)` (5)

### `backend/model/rating.py` — 23 строк

Своя оценка карточки.

Зависит от: —

- `def average_score(*aspects: int | None) -> float | None` (7)
- `class Rating` (8)

### `backend/model/ratings.py` — 16 строк

Ответ оценочного источника на границе слоёв.

Зависит от: `backend.model.external`

- `class Ratings` (8)

### `backend/model/search.py` — 27 строк

Кандидат в выдаче поиска — то, чем карточка ещё не стала.

Зависит от: `backend.model.kinds`

- `class SearchHit` (19)

### `backend/model/suggestion.py` — 15 строк

Строка подсказки при вводе имени человека или студии.

Зависит от: —

- `class Suggestion` (9)

### `backend/sources/convert.py` — 52 строк

Куски чужого ответа, которые все источники переводят одинаково.

Зависит от: `backend.model`

- `def genres(space: GenreSource, rows: list[dict], key: str='id') -> tuple[tuple[GenreSource, str], ...]` (7)
- `def year(value: str | None) -> int | None` (5)
- `def companies(payload: dict) -> tuple[Credit, ...]` (11)
- `def rating(source: RatingSource, value: float | int | None, now: datetime) -> tuple[ExternalRating, ...]` (10)

### `backend/sources/errors.py` — 58 строк

Чем может кончиться запрос к источнику: находкой, честным «нет» или отказом.

Зависит от: —

- `class Reason(StrEnum)` (6)
- `class Found` (2)
- `class Missing` (3)
- `class Refusal` (8)
- `Outcome: TypeAlias = Found | Missing | Refusal`
- `def broken(source: str, error: Exception) -> Refusal` (4)
- `def is_answer(outcome: Outcome) -> bool` (5)

### `backend/sources/gog/client.py` — 79 строк

Разговор с GOG по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.gog.parse`, `backend.sources.http`, `backend.sources.undocumented`

- `class GogClient` (55)
  - `async def _catalog(self, query: str) -> list | Refusal` (13)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (5)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (18)
  - `async def aclose(self) -> None` (2)

### `backend/sources/gog/parse.py` — 64 строк

Перевод ответов GOG в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `def _marks(row: dict) -> tuple[tuple[GenreSource, str], ...]` (8)
- `def parse_catalog(payload: dict) -> list[SourceCard]` (24)
- `def to_hit(card: SourceCard) -> SearchHit` (12)

### `backend/sources/http.py` — 90 строк

Общая дверь в сеть для всех источников.

Зависит от: `backend.sources.errors`

- `class Breaker` (28)
  - `def is_open(self) -> bool` (7)
  - `def trip(self, delay: timedelta, reason: Reason=Reason.QUOTA) -> None` (7)
  - `def reason(self) -> Reason` (2)
- `class SourceHttp` (41)
  - `async def get(self, url: str, params: Mapping[str, object] | None=None, headers: Mapping[str, str] | None=None) -> httpx.Response | Refusal` (15)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/kinopoisk/client.py` — 35 строк

Кинопоиск снаружи: одно имя над двумя зеркалами.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`

- `class KinopoiskClient` (23)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (11)
  - `async def aclose(self) -> None` (3)

### `backend/sources/ratings/kinopoisk/mirror.py` — 50 строк

Общее у двух зеркал Кинопоиска.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`

- `def refuse_quota(http: SourceHttp) -> Refusal` (3)
- `def refuse_rate(http: SourceHttp) -> Refusal` (5)
- `def refuse_key() -> Refusal` (3)
- `def refuse_code(status: int) -> Refusal` (2)
- `def answered(answer: Ratings) -> Outcome` (7)

### `backend/sources/ratings/kinopoisk/parse.py` — 47 строк

Перевод ответов обоих зеркал Кинопоиска в наши типы.

Зависит от: `backend.model`

- `def _rating(value, now: datetime) -> tuple[ExternalRating, ...]` (8)
- `def _ident(value) -> tuple[ExternalId, ...]` (4)
- `def parse_poiskkino(payload: dict) -> Ratings` (11)
- `def parse_unofficial(payload: dict) -> Ratings` (11)

### `backend/sources/ratings/kinopoisk/poiskkino.py` — 93 строк

Основное зеркало Кинопоиска.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.parse`

- `class PoiskkinoClient` (60)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (9)
  - `def _verdict(self, response: httpx.Response) -> Outcome` (16)
  - `def _absent(self, response: httpx.Response) -> Outcome` (14)
  - `def _answer(self, response: httpx.Response) -> Outcome` (6)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/kinopoisk/unofficial.py` — 61 строк

Запасное зеркало Кинопоиска.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.parse`

- `class UnofficialClient` (35)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (9)
  - `def _verdict(self, response: httpx.Response) -> Outcome` (17)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/mdblist/client.py` — 94 строк

Разговор с MDBList по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.mdblist.parse`

- `def _retry_after(response: httpx.Response) -> timedelta | None` (3)
- `class MdbListClient` (60)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (8)
  - `def _verdict(self, response: httpx.Response) -> Outcome` (26)
  - `def _denied(self, response: httpx.Response) -> Refusal` (16)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/mdblist/parse.py` — 35 строк

Перевод ответов MDBList в наши типы.

Зависит от: `backend.model`

- `def parse_ratings(payload: dict) -> Ratings` (18)

### `backend/sources/ratings/omdb/client.py` — 100 строк

Разговор с OMDB по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.omdb.parse`

- `def until_midnight(now: datetime) -> timedelta` (7)
- `class OmdbClient` (66)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (28)
  - `def _answer(self, payload: dict) -> Outcome` (11)
  - `def _denied(self, payload: dict) -> Refusal` (17)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/omdb/parse.py` — 46 строк

Перевод ответов OMDB в наши типы.

Зависит от: `backend.model`

- `def _number(raw: str | None) -> float | None` (10)
- `def parse_ratings(payload: dict) -> Ratings` (21)

### `backend/sources/registry.py` — 85 строк

Кто отвечает за какой тип содержимого.

Зависит от: `backend.config`, `backend.model`, `backend.sources.gog.client`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`, `backend.sources.steam.client`, `backend.sources.tmdb.client`

- `class Sources` (35)
  - `def catalog_for(self, kind: Kind) -> list` (6)
  - `def rating_sources(self, kind: Kind) -> list` (6)
  - `def breakers(self) -> list[Breaker]` (2)
  - `async def aclose(self) -> None` (3)
- `def build_sources(config: Config, transport: httpx.AsyncBaseTransport | None=None) -> Sources` (28)
  - `def http(name: str) -> SourceHttp` (7)

### `backend/sources/steam/client.py` — 129 строк

Разговор со Steam по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.steam.parse`, `backend.sources.undocumented`

- `class SteamClient` (93)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (15)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (39)
  - `async def _tags(self, source_id: str) -> tuple[tuple[GenreSource, str], ...]` (27)
  - `async def aclose(self) -> None` (2)

### `backend/sources/steam/parse.py` — 87 строк

Перевод ответов Steam в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `def poster_url(appid: str) -> str` (4)
- `def parse_search(payload: list[dict]) -> list[SearchHit]` (11)
- `def _year(value: str | None) -> int | None` (7)
- `def _metascore(data: dict, now: datetime) -> tuple[ExternalRating, ...]` (5)
- `def parse_card(data: dict) -> SourceCard` (21)
- `def parse_tags(payload: dict) -> tuple[tuple[GenreSource, str], ...]` (7)

### `backend/sources/tmdb/client.py` — 118 строк

Разговор с TMDB по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.tmdb.parse`

- `def classify(response: httpx.Response) -> Missing | Refusal | None` (20)
- `class TmdbClient` (59)
  - `def _params(self, **extra: object) -> dict` (2)
  - `def _verdict(self, response: httpx.Response) -> Missing | Refusal | None` (7)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (15)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (18)
  - `async def aclose(self) -> None` (2)

### `backend/sources/tmdb/parse.py` — 178 строк

Перевод ответов TMDB в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `class Incomplete(Exception)` (5)
- `def _released(value: str | None) -> date | None` (7)
- `def _poster(payload: dict) -> str` (3)
- `def _genres(payload: dict) -> tuple[tuple[GenreSource, str], ...]` (2)
- `def _own_rating(payload: dict, now: datetime) -> tuple[ExternalRating, ...]` (2)
- `def _imdb(value: str | None) -> tuple[ExternalId, ...]` (4)
- `def _person(row: dict, role: PersonRole, position: int | None=None) -> Credit` (10)
- `def _cast(rows: list[dict]) -> list[Credit]` (5)
- `def _required(payload: dict, block: str) -> dict` (9)
- `def parse_search(payload: dict, kind: Kind) -> list[SearchHit]` (27)
- `def parse_movie(payload: dict) -> SourceCard` (30)
- `def parse_series(payload: dict) -> SourceCard` (29)

### `backend/sources/undocumented.py` — 22 строк

Отказ источника, который своих лимитов не объявляет.

Зависит от: `backend.sources.errors`, `backend.sources.http`

- `def refuse_undocumented(http: SourceHttp, status: int) -> Refusal` (9)

### `backend/storage/posters.py` — 89 строк

Второй файл базы: картинка по карточке.

Зависит от: `backend.storage.session`

- `class PosterStore` (56)
  - `async def open(self) -> None` (7)
  - `async def close(self) -> None` (4)
  - `async def _read(self, statement: Executable)` (3)
  - `async def _write(self, statement: Executable) -> None` (3)
  - `async def put(self, item_id: int, data: bytes, now: datetime) -> None` (11)
  - `async def get(self, item_id: int) -> bytes | None` (5)
  - `async def has(self, item_id: int) -> bool` (5)
  - `async def delete(self, item_id: int) -> None` (2)

### `backend/storage/repository/base.py` — 86 строк

Общее у репозиториев: сессия и способы с ней обойтись.

Зависит от: —

- `class Repository` (77)
  - `async def _row(self, statement: Executable) -> Row | None` (3)
  - `async def _rows(self, statement: Executable) -> list[Row]` (3)
  - `async def _mapped(self, statement: Executable, make: Callable[[Row], object])` (3)
  - `async def _maybe(self, statement: Executable, make: Callable[[Row], object])` (6)
  - `async def _has_item(self, table: Table, item_id: int) -> bool` (8)
  - `def _clearing(table: Table, item_id: int) -> Delete` (7)
  - `async def _created(self, statement: Executable, taken: Exception) -> int` (15)
  - `async def _written(self, statement: Executable, taken: Exception) -> None` (7)
  - `async def _run(self, *statements: Executable) -> None` (7)

### `backend/storage/repository/credits.py` — 236 строк

Всё, что приложение делает в базе с человеком или студией как с

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.session`, `backend.storage.tables`

- `class IdentityTaken(Exception)` (2)
- `class Entity` (8)
- `class CreditRepository(Repository)` (178)
  - `def _link(self) -> Column` (2)
  - `def _folded_name(self) -> ColumnElement[str]` (2)
  - `def _same_name(self, name: str) -> ColumnElement[bool]` (2)
  - `def _name_starts_with(self, name: str) -> ColumnElement[bool]` (4)
  - `async def _found_id(self, statement: Select) -> int | None` (2)
  - `async def create(self, name: str, source: Source | None=None, source_id: str | None=None) -> int` (9)
  - `async def create_manual(self, name: str) -> int` (5)
  - `async def find_by_source(self, source: Source, source_id: str) -> int | None` (7)
  - `async def find_by_name(self, name: str) -> list[int]` (8)
  - `async def find_anonymous_by_name(self, name: str) -> int | None` (12)
  - `async def ensure(self, credit: Credit) -> int` (10)
  - `async def attach(self, item_id: int, entity_id: int, role: PersonRole | CompanyRole, position: int | None=None) -> None` (13)
  - `async def detach_all(self, item_id: int) -> None` (2)
  - `async def credits_of(self, item_id: int) -> list[Credit]` (14)
  - `async def suggest(self, name: str, limit: int=10) -> list[Suggestion]` (15)
  - `def _linked(self, entity_id: int) -> Select` (10)
  - `async def _hint(self, entity_id: int) -> tuple[str, int | None]` (21)
  - `def _to_credit(self, row: Row) -> Credit` (11)
- `def people(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository` (2)
- `def companies(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository` (2)

### `backend/storage/repository/genres.py` — 74 строк

Жанры карточки и разрешение чужих идентификаторов в свои.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.tables`

- `def _to_genre(row) -> Genre` (2)
- `class GenresRepository(Repository)` (58)
  - `async def resolve(self, source: GenreSource, ext_ids: list[str]) -> list[int]` (22)
  - `async def set_for_item(self, item_id: int, genre_ids: list[int]) -> None` (14)
  - `async def genres_of(self, item_id: int) -> list[Genre]` (8)
  - `async def list_for_kind(self, kind: GenreKind) -> list[Genre]` (10)

### `backend/storage/repository/library.py` — 177 строк

Карточки библиотеки.

Зависит от: `backend.model`, `backend.storage.posters`, `backend.storage.repository.base`, `backend.storage.session`, `backend.storage.tables`

- `class ItemExists(Exception)` (2)
- `def _values(item: Item) -> dict` (6)
- `def _to_item(row: Row) -> Item` (22)
- `class LibraryRepository(Repository)` (118)
  - `async def _one(self, statement: Select) -> Item | None` (2)
  - `async def create(self, item: Item) -> int` (5)
  - `async def get(self, item_id: int) -> Item | None` (2)
  - `async def find_by_source(self, source: Source, source_id: str) -> Item | None` (7)
  - `async def list_by_kind(self, kind: Kind, limit: int, offset: int) -> list[Item]` (12)
  - `async def find_by_title(self, kind: Kind, title: str) -> list[Item]` (16)
  - `async def deletion_summary(self, item_id: int) -> dict[str, int | bool]` (12)
  - `async def delete(self, item_id: int, posters: PosterStore) -> None` (5)
  - `async def refresh_series_counts(self, item_id: int, seasons_count: int | None, episodes_count: int | None, now: datetime) -> None` (14)
  - `async def replace_fields(self, item_id: int, item: Item) -> None` (8)
  - `async def link(self, item_id: int, source: Source, source_id: str, now: datetime) -> None` (15)
  - `async def unlink(self, item_id: int) -> None` (8)

### `backend/storage/repository/ratings.py` — 71 строк

Моя оценка карточки.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.tables`

- `def _to_rating(row) -> Rating` (11)
- `class RatingsRepository(Repository)` (46)
  - `async def _write(self, item_id: int, values: dict, now: datetime) -> None` (11)
  - `async def set_score(self, item_id: int, score: float | None, now: datetime) -> None` (3)
  - `async def set_aspects(self, item_id: int, visual: int | None, narrative: int | None, gameplay: int | None, now: datetime) -> float | None` (16)
  - `async def set_review(self, item_id: int, review: str, now: datetime) -> None` (2)
  - `async def get(self, item_id: int) -> Rating | None` (5)
  - `async def clear(self, item_id: int) -> None` (3)

### `backend/storage/repository/tags.py` — 109 строк

Мои теги: наборы по типам содержимого и их развеска по карточкам.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.tables`

- `class WrongTagKind(Exception)` (2)
- `class TagExists(Exception)` (2)
- `def _named(row) -> tuple[int, str]` (2)
- `class TagsRepository(Repository)` (85)
  - `async def create(self, kind: Kind, name: str) -> int` (17)
  - `async def list_for_kind(self, kind: Kind) -> list[tuple[int, str]]` (7)
  - `async def reorder(self, kind: Kind, tag_ids: list[int]) -> None` (10)
  - `async def rename(self, tag_id: int, name: str) -> None` (6)
  - `async def delete(self, tag_id: int) -> None` (2)
  - `async def assign(self, item_id: int, tag_id: int) -> None` (20)
  - `async def unassign(self, item_id: int, tag_id: int) -> None` (7)
  - `async def tags_of(self, item_id: int) -> list[tuple[int, str]]` (8)

### `backend/storage/repository/wishlist.py` — 36 строк

Список запланированного.

Зависит от: `backend.storage.repository.base`, `backend.storage.tables`

- `class WishlistRepository(Repository)` (25)
  - `async def add(self, item_id: int, now: datetime) -> None` (7)
  - `async def remove(self, item_id: int) -> None` (2)
  - `async def contains(self, item_id: int) -> bool` (2)
  - `async def list_ids(self, limit: int, offset: int) -> list[int]` (10)

### `backend/storage/session.py` — 50 строк

Доступ к основной базе.

Зависит от: —

- `def fold(value: str | None) -> str | None` (5)
- `def folded(column: ColumnElement) -> ColumnElement[str]` (4)
- `def prepare_connection(dbapi_connection) -> None` (9)
- `def create_engine(path: Path) -> AsyncEngine` (9)
  - `def prepare(dbapi_connection, _record)` (2)
- `def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]` (2)

### `backend/storage/tables/__init__.py` — 34 строк

Поверхность схемы: отсюда таблицы берут репозитории.

Зависит от: `backend.storage.tables.base`, `backend.storage.tables.catalog`, `backend.storage.tables.mine`

Отдаёт наружу: `company`, `company_credit`, `external_id`, `external_rating`, `genre`, `genre_map`, `item`, `item_genre`, `item_tag`, `metadata`, `person`, `person_credit`, `rating`, `tag`, `wishlist`


### `backend/storage/tables/base.py` — 32 строк

Общее для всех объявлений схемы.

Зависит от: —

- `def item_fk(**kwargs: Any) -> Column` (6)
- `def genre_fk(**kwargs: Any) -> Column` (5)

### `backend/storage/tables/catalog.py` — 127 строк

Таблицы каталога: то, что наполняется из источников.

Зависит от: `backend.storage.tables.base`


### `backend/storage/tables/mine.py` — 56 строк

Таблицы моих данных: то, что не зависит от источника.

Зависит от: `backend.storage.tables.base`


## client — 0 модулей

## migrations — 3 модулей

### `migrations/env.py` — 56 строк

Точка входа Alembic: адрес базы и соединение под миграции.

Зависит от: `backend.config`, `backend.storage.session`, `backend.storage.tables`

- `def database_path() -> Path` (7)
- `def database_url() -> str` (7)
- `def migrate() -> None` (15)
  - `def prepare(dbapi_connection, _record)` (2)

### `migrations/versions/0001_schema.py` — 176 строк

Схема целиком: четырнадцать таблиц каталога и моих данных.

Зависит от: —

- `def upgrade() -> None` (131)
- `def downgrade() -> None` (24)

### `migrations/versions/0002_genres.py` — 403 строк ⚠ подошёл к 300

Справочник жанров и соответствия к нему.

Зависит от: —

- `def upgrade() -> None` (29)
- `def downgrade() -> None` (5)

## scripts — 6 модулей

### `scripts/collect_game_genres.py` — 80 строк

Разовый сбор игровых жанров: справочника в документации нет ни у Steam, ни у

Зависит от: `backend.sources.http`

- `def example_appids(menu: list[dict]) -> list[int]` (8)
- `async def app_genres(client: httpx.AsyncClient, appid: int) -> list[dict]` (11)
- `async def steam_genres(client: httpx.AsyncClient) -> dict[str, str]` (11)
- `async def gog_genres(client: httpx.AsyncClient) -> dict[str, str]` (7)
- `async def main() -> None` (7)

### `scripts/genre_map.py` — 83 строк

Сверка соответствий жанров: спека против миграции.

Зависит от: —

- `def from_spec() -> dict[str, dict[str, list[str]]]` (18)
- `def from_migration() -> dict[str, dict[str, list[str]]]` (9)
- `def differences(spec: dict, code: dict) -> list[str]` (8)
- `def main() -> int` (9)

### `scripts/module_map.py` — 298 строк

Две карты проекта, собираемые из кода.

Зависит от: `not_duplicates`, `project_ast`

- `def alias(node: ast.AST) -> str | None` (17)
- `def declared(body: list, depth: int=0) -> tuple[list[str], int]` (30)
- `def module_block(path: str, tree: ast.Module, lines_total: int) -> str` (24)
- `def _counted(kind: str, amount: int, spread: bool) -> str` (4)
- `def brief(value: ast.AST | None) -> str` (17)
- `def assigned(node: ast.AST) -> list[tuple[str, str]]` (11)
- `def _data_nodes(body: list) -> list[ast.AST]` (11)
- `def _class_lines(node: ast.ClassDef) -> list[str]` (11)
- `def contents(tree: ast.Module) -> list[str]` (20)
- `def data_block(path: str, tree: ast.Module) -> list[str]` (4)
- `def lonely_block(found: list[tuple]) -> str` (9)
- `def within(found: list[tuple], root: str) -> list[tuple]` (4)
- `def heading(title: str, note: str) -> list[str]` (5)
- `def render(found: list[tuple]) -> str` (9)
- `def render_data(found: list[tuple]) -> str` (11)
- `def main() -> int` (23)

### `scripts/not_duplicates.py` — 103 строк

Вердикты «это не повтор того» и их срок годности.

Зависит от: `project_ast`

- `def verdict_lines() -> list[str]` (5)
- `def is_verdict(line: str) -> bool` (4)
- `def places(line: str) -> list[tuple[str, str]]` (10)
- `def stamped(token: str) -> bool` (2)
- `def sealed(line: str, index: dict[str, str]) -> str` (11)
- `def seal(index: dict[str, str]) -> None` (5)
- `def malformed(line: str) -> str` (16)
- `def expired(lines: list[str], index: dict[str, str]) -> list[str]` (18)

### `scripts/project_ast.py` — 196 строк

Свой код проекта как дерево разбора.

Зависит от: —

- `def project_root() -> Path` (7)
- `def roots() -> list[str]` (10)
- `def modules() -> list[tuple[str, ast.Module, int]]` (26)
- `def signature(node: ast.AST) -> str` (7)
- `def size(node: ast.AST) -> int` (2)
- `def _siblings(path: str) -> set[str]` (9)
- `def depends_on(tree: ast.Module, path: str='') -> list[str]` (13)
- `def exported(tree: ast.Module) -> list[str]` (9)
- `def implementations(found: list[tuple]) -> dict[str, list[str]]` (17)
- `def bound_names(node: ast.AST) -> list[str]` (14)
- `def _stamp(node: ast.AST) -> str` (2)
- `def declarations(found: list[tuple]) -> dict[str, str]` (28)
  - `def walk(body: list, path: str, prefix: str) -> None` (13)

### `scripts/record_fixtures.py` — 198 строк

Разовая запись живых ответов источников в tests/fixtures/.

Зависит от: `backend.config`, `backend.sources.http`

- `def save(source: str, case: str, response: httpx.Response) -> None` (23)
- `async def record_tmdb(client: httpx.AsyncClient, key: str) -> None` (24)
- `async def record_steam(client: httpx.AsyncClient) -> None` (35)
  - `def ask(ids: list[dict]) -> str` (7)
- `async def record_gog(client: httpx.AsyncClient) -> None` (9)
- `async def record_mdblist(client: httpx.AsyncClient, key: str) -> None` (11)
- `async def record_omdb(client: httpx.AsyncClient, key: str) -> None` (13)
- `async def record_kinopoisk_unofficial(client: httpx.AsyncClient, key: str) -> None` (13)
- `async def main() -> None` (20)

## tests — 35 модулей

### `tests/alembic_runner.py` — 21 строк

Запуск миграций из теста.

Зависит от: —

- `def alembic(db_path: Path, *command: str) -> None` (10)

### `tests/backend/sources/conftest.py` — 95 строк

Записанные ответы источников: живьём тесты не ходят никуда.

Зависит от: —

- `class FakeClock` (12)
  - `def __call__(self) -> datetime` (2)
  - `def advance(self, delta: timedelta) -> None` (2)
- `def _load(relative: str)` (4)
- `def _meta(relative: str) -> dict` (3)
- `def responding(status: int=200, *, json=None, text=None, headers=None)` (11)
- `def fixture()` (3)
- `def meta()` (2)
- `def replay()` (33)
  - `def build(*relatives: str) -> httpx.MockTransport` (21)
    - `def handler(request: httpx.Request) -> httpx.Response` (7)

### `tests/backend/sources/test_convert.py` — 91 строк

Общее у разборов: перевод чужих кусков ответа в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`, `tests.conftest`

Тестов: 11


### `tests/backend/sources/test_errors.py` — 93 строк



Зависит от: `backend.sources.errors`

Тестов: 12


### `tests/backend/sources/test_gog.py` — 269 строк

GOG: поиск не умеет отвечать «не найдено», и отрицательный факт отсюда не

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.gog.client`, `backend.sources.gog.parse`, `backend.sources.http`, `tests.backend.sources.conftest`

Тестов: 21

- `def answering(body) -> SourceHttp` (3)

### `tests/backend/sources/test_http.py` — 331 строк ⚠ подошёл к 300



Зависит от: `backend.sources.errors`, `backend.sources.http`, `backend.sources.undocumented`, `tests.backend.sources.conftest`

Тестов: 21

- `def capture() -> tuple[httpx.MockTransport, list[httpx.Request]]` (9)
  - `def handler(request: httpx.Request) -> httpx.Response` (3)

### `tests/backend/sources/test_kinopoisk.py` — 415 строк ⚠ подошёл к 300

Кинопоиск: два зеркала под одним именем, и телу здесь верить нельзя.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`, `tests.backend.sources.conftest`

Тестов: 28

- `def primary(transport) -> PoiskkinoClient` (2)
- `def fallback(transport) -> UnofficialClient` (2)

### `tests/backend/sources/test_mdblist.py` — 235 строк

MDBList: квота, битый ключ и чужой периметр — три разные беды.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.mdblist.parse`, `tests.backend.sources.conftest`

Тестов: 20

- `async def ask(transport, kind=Kind.MOVIE)` (5)

### `tests/backend/sources/test_omdb.py` — 297 строк

OMDB: единственный источник, у которого отказ приходит под кодом 401, а

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.omdb.client`, `backend.sources.ratings.omdb.parse`, `tests.backend.sources.conftest`

Тестов: 28

- `async def ask(transport)` (5)

### `tests/backend/sources/test_registry.py` — 210 строк

Реестр держится на том, что контракт у всех клиентов один.

Зависит от: `backend.config`, `backend.model`, `backend.sources.errors`, `backend.sources.gog.client`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`, `backend.sources.registry`, `backend.sources.steam.client`, `backend.sources.tmdb.client`

Тестов: 11

- `def sources()` (4)
- `def keyed()` (12)

### `tests/backend/sources/test_steam.py` — 341 строк ⚠ подошёл к 300

Steam: отсутствие игры приходит под кодом 200, а теги — вторым запросом.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.steam.client`, `backend.sources.steam.parse`

Тестов: 26

- `def block_of(payload: dict) -> dict` (2)

### `tests/backend/sources/test_tmdb_card.py` — 292 строк

Второй круг загрузки: карточка, которую уже можно записать.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.tmdb.client`, `backend.sources.tmdb.parse`

Тестов: 25


### `tests/backend/sources/test_tmdb_failures.py` — 203 строк

Отказ TMDB отличается от «такого у меня нет» — и то, и другое от успеха.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.tmdb.client`, `tests.backend.sources.conftest`

Тестов: 15

- `async def ask(transport: httpx.MockTransport)` (5)

### `tests/backend/sources/test_tmdb_search.py` — 183 строк

Первый круг загрузки: кандидат выдачи — ещё не карточка.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.tmdb.client`, `backend.sources.tmdb.parse`

Тестов: 15


### `tests/backend/test_config.py` — 66 строк



Зависит от: `backend.config`

Тестов: 9


### `tests/backend/test_credits.py` — 287 строк

Люди и студии: одна реализация на две сущности, и различает их идентичность.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.library`

Тестов: 24


### `tests/backend/test_delete.py` — 117 строк



Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 8

- `async def furnished(sessions, posters, item_id: int, tag: str='пересмотреть') -> int` (9)

### `tests/backend/test_genre_reference.py` — 171 строк



Зависит от: `tests.alembic_runner`

Тестов: 12

- `def named(connection, source: str, ext_id: str) -> set[str]` (10)
- `def counted(connection, where: str) -> int` (4)

### `tests/backend/test_genres.py` — 184 строк



Зависит от: `backend.model`, `backend.storage.repository.genres`

Тестов: 14

- `def ours(caplog) -> list[str]` (8)
- `async def reference(engine)` (16)

### `tests/backend/test_layers.py` — 82 строк



Зависит от: —

Тестов: 3

- `def imported_modules(path: Path)` (10)
- `def imported_roots(path: Path)` (4)
- `def python_files(package: str) -> list[Path]` (7)
- `def offenders(package: str, banned: set[str]) -> list[str]` (7)

### `tests/backend/test_library.py` — 380 строк ⚠ подошёл к 300



Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 25

- `def make_item(**overrides) -> Item` (12)
- `async def in_both_stores(repository) -> tuple[int, int]` (15)

### `tests/backend/test_manual_cards.py` — 210 строк



Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `tests.conftest`

Тестов: 14


### `tests/backend/test_migrations.py` — 124 строк



Зависит от: `backend.storage.tables`, `tests.alembic_runner`, `tests.conftest`

Тестов: 4

- `def declared(db_path: Path) -> None` (5)
- `def table_shape(inspector, name: str) -> dict` (29)
- `def shape(db_path: Path) -> dict` (12)
- `def stamped(db_path: Path) -> list[str]` (8)

### `tests/backend/test_model.py` — 108 строк



Зависит от: `backend.model`, `tests.conftest`

Тестов: 9


### `tests/backend/test_posters.py` — 173 строк



Зависит от: `backend.storage.posters`, `backend.storage.session`, `tests.conftest`

Тестов: 16


### `tests/backend/test_ratings.py` — 186 строк



Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.tables`, `tests.conftest`

Тестов: 16


### `tests/backend/test_session.py` — 90 строк



Зависит от: `backend.storage.session`

Тестов: 7

- `async def bare_engine(tmp_path)` (4)
- `class Base(DeclarativeBase)` (2)
- `class Note(Base)` (5)

### `tests/backend/test_suggestions.py` — 204 строк

Подсказка при вводе имени: тёзок различают по узнаваемой карточке.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.ratings`, `backend.storage.repository.wishlist`, `backend.storage.tables`, `tests.conftest`

Тестов: 14

- `async def person_with(sessions, name: str, item_ids: list[int]) -> int` (6)

### `tests/backend/test_tables.py` — 196 строк



Зависит от: `backend.storage.tables`, `tests.conftest`

Тестов: 10

- `async def counted(engine, table_name: str) -> int` (5)
- `async def put(engine, table_name: str, **values) -> None` (4)

### `tests/backend/test_tags.py` — 327 строк ⚠ подошёл к 300



Зависит от: `backend.model`, `backend.storage.repository.tags`

Тестов: 26


### `tests/backend/test_wishlist.py` — 117 строк



Зависит от: `backend.storage.repository.wishlist`, `backend.storage.tables`, `tests.conftest`

Тестов: 10


### `tests/conftest.py` — 120 строк

Общее для тестов: временные база и хранилище, фикстуры и минимальные строки.

Зависит от: `backend.model`, `backend.storage.posters`, `backend.storage.repository.library`, `backend.storage.session`, `backend.storage.tables`, `tests.alembic_runner`

- `def migrated(tmp_path)` (16)
- `async def engine(tmp_path)` (8)
- `async def sessions(engine)` (4)
- `async def posters(tmp_path)` (6)
- `async def card(sessions)` (12)
  - `async def make(kind: Kind=Kind.MOVIE, source_id: str='1', title: str='карточка') -> int` (6)
- `async def stored(engine)` (12)
  - `async def put(name: str, **values) -> int` (7)

### `tests/scripts/test_module_map.py` — 82 строк

Карта данных проверяется тем, что она показывает по данному ей коду.

Зависит от: —

Тестов: 10

- `def shown(source: str) -> list[str]` (2)
- `def only(source: str) -> str` (4)

### `tests/scripts/test_not_duplicates.py` — 118 строк

Вердикт живёт, пока живо то, что он сравнивал.

Зависит от: —

Тестов: 12


### `tests/scripts/test_project_ast.py` — 57 строк

Разбор проекта проверяется тем, что он вычитывает из данного ему кода.

Зависит от: —

Тестов: 6

- `def indexed(source: str, path: str='a.py') -> dict[str, str]` (2)

## Абстракции с одной реализацией

- `Base` — наследник один: `Note`
