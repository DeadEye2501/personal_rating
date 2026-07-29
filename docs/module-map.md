# Карта модулей

Собирается из кода, а не ведётся руками.
Править руками нельзя — правки затрёт следующая сборка.
Число в скобках — сколько строк занимает объявление.

## backend — 20 модулей

### `backend/config.py` — 49 строк

Настройки приложения, прочитанные из окружения.

Зависит от: —

- `class Config` (20)
  - `def library_db(self) -> Path` (2)
  - `def posters_db(self) -> Path` (2)
  - `def log_file(self) -> Path` (2)
- `def value(env: Mapping[str, str], name: str) -> str` (4)
- `def load_config(env: Mapping[str, str], base_dir: Path) -> Config` (11)

### `backend/model/__init__.py` — 37 строк

Поверхность модели: отсюда типы границы слоёв импортирует клиент.

Зависит от: `backend.model.credit`, `backend.model.external`, `backend.model.genre`, `backend.model.item`, `backend.model.kinds`, `backend.model.rating`

Отдаёт наружу: `CompanyRole`, `Credit`, `ExternalId`, `ExternalRating`, `Genre`, `GenreKind`, `GenreSource`, `IdSource`, `Item`, `Kind`, `PersonRole`, `Rating`, `RatingSource`, `Source`, `average_score`, `new_manual_item`, `new_source_id`


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

### `backend/storage/repository/base.py` — 70 строк

Общее у репозиториев: сессия и способы с ней обойтись.

Зависит от: —

- `class Repository` (61)
  - `async def _row(self, statement: Executable) -> Row | None` (3)
  - `async def _rows(self, statement: Executable) -> list[Row]` (3)
  - `async def _mapped(self, statement: Executable, make: Callable[[Row], object])` (3)
  - `async def _has_item(self, table: Table, item_id: int) -> bool` (8)
  - `async def _created(self, statement: Executable, taken: Exception) -> int` (15)
  - `async def _written(self, statement: Executable, taken: Exception) -> None` (7)
  - `async def _run(self, *statements: Executable) -> None` (7)

### `backend/storage/repository/genres.py` — 76 строк

Жанры карточки и разрешение чужих идентификаторов в свои.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.tables`

- `def _to_genre(row) -> Genre` (2)
- `class GenresRepository(Repository)` (60)
  - `async def resolve(self, source: GenreSource, ext_ids: list[str]) -> list[int]` (22)
  - `async def set_for_item(self, item_id: int, genre_ids: list[int]) -> None` (16)
  - `async def genres_of(self, item_id: int) -> list[Genre]` (8)
  - `async def list_for_kind(self, kind: GenreKind) -> list[Genre]` (10)

### `backend/storage/repository/library.py` — 178 строк

Карточки библиотеки.

Зависит от: `backend.model`, `backend.storage.posters`, `backend.storage.repository.base`, `backend.storage.session`, `backend.storage.tables`

- `class ItemExists(Exception)` (2)
- `def _values(item: Item) -> dict` (6)
- `def _to_item(row: Row) -> Item` (22)
- `class LibraryRepository(Repository)` (119)
  - `async def _one(self, statement: Select) -> Item | None` (3)
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

### `backend/storage/repository/ratings.py` — 69 строк

Моя оценка карточки.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.tables`

- `class RatingsRepository(Repository)` (57)
  - `async def _write(self, item_id: int, values: dict, now: datetime) -> None` (11)
  - `async def set_score(self, item_id: int, score: float | None, now: datetime) -> None` (3)
  - `async def set_aspects(self, item_id: int, visual: int | None, narrative: int | None, gameplay: int | None, now: datetime) -> float | None` (16)
  - `async def set_review(self, item_id: int, review: str, now: datetime) -> None` (2)
  - `async def get(self, item_id: int) -> Rating | None` (14)
  - `async def clear(self, item_id: int) -> None` (5)

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

### `backend/storage/repository/wishlist.py` — 38 строк

Список запланированного.

Зависит от: `backend.storage.repository.base`, `backend.storage.tables`

- `class WishlistRepository(Repository)` (27)
  - `async def add(self, item_id: int, now: datetime) -> None` (7)
  - `async def remove(self, item_id: int) -> None` (4)
  - `async def contains(self, item_id: int) -> bool` (2)
  - `async def list_ids(self, limit: int, offset: int) -> list[int]` (10)

### `backend/storage/session.py` — 44 строк

Доступ к основной базе.

Зависит от: —

- `def fold(value: str | None) -> str | None` (5)
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

## scripts — 3 модулей

### `scripts/collect_game_genres.py` — 78 строк

Разовый сбор игровых жанров: справочника в документации нет ни у Steam, ни у

Зависит от: —

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

### `scripts/module_map.py` — 243 строк

Карта модулей: кто за что отвечает, что объявляет и от кого зависит.

Зависит от: —

- `def project_root() -> Path` (11)
- `def roots() -> list[str]` (10)
- `def modules() -> list[tuple[str, ast.Module, int]]` (22)
- `def signature(node: ast.AST) -> str` (7)
- `def size(node: ast.AST) -> int` (2)
- `def depends_on(tree: ast.Module) -> list[str]` (12)
- `def declared(body: list, depth: int=0) -> tuple[list[str], int]` (26)
- `def exported(tree: ast.Module) -> list[str]` (9)
- `def module_block(path: str, tree: ast.Module, lines_total: int) -> str` (24)
- `def implementations(found: list[tuple]) -> dict[str, list[str]]` (17)
- `def lonely_block(found: list[tuple]) -> str` (9)
- `def render() -> str` (16)
- `def main() -> int` (12)

## tests — 17 модулей

### `tests/alembic_runner.py` — 21 строк

Запуск миграций из теста.

Зависит от: —

- `def alembic(db_path: Path, *command: str) -> None` (10)

### `tests/backend/test_config.py` — 66 строк



Зависит от: `backend.config`

Тестов: 9


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

### `tests/backend/test_library.py` — 382 строк ⚠ подошёл к 300



Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`

Тестов: 25

- `def make_item(**overrides) -> Item` (12)
- `async def in_both_stores(repository) -> tuple[int, int]` (15)

### `tests/backend/test_manual_cards.py` — 212 строк



Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`

Тестов: 14


### `tests/backend/test_migrations.py` — 124 строк



Зависит от: `backend.storage.tables`, `tests.alembic_runner`, `tests.conftest`

Тестов: 4

- `def declared(db_path: Path) -> None` (5)
- `def table_shape(inspector, name: str) -> dict` (29)
- `def shape(db_path: Path) -> dict` (12)
- `def stamped(db_path: Path) -> list[str]` (8)

### `tests/backend/test_model.py` — 110 строк



Зависит от: `backend.model`

Тестов: 9


### `tests/backend/test_posters.py` — 173 строк



Зависит от: `backend.storage.posters`, `backend.storage.session`, `tests.conftest`

Тестов: 16


### `tests/backend/test_ratings.py` — 190 строк



Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.tables`

Тестов: 16


### `tests/backend/test_session.py` — 90 строк



Зависит от: `backend.storage.session`

Тестов: 7

- `async def bare_engine(tmp_path)` (4)
- `class Base(DeclarativeBase)` (2)
- `class Note(Base)` (5)

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


### `tests/conftest.py` — 114 строк

Общее для тестов: временные база и хранилище, фикстуры и минимальные строки.

Зависит от: `backend.model`, `backend.storage.posters`, `backend.storage.repository.library`, `backend.storage.session`, `backend.storage.tables`, `tests.alembic_runner`

- `def migrated(tmp_path)` (16)
- `async def engine(tmp_path)` (8)
- `async def sessions(engine)` (4)
- `async def posters(tmp_path)` (6)
- `async def card(sessions)` (11)
  - `async def make(kind: Kind=Kind.MOVIE, source_id: str='1') -> int` (5)
- `async def stored(engine)` (12)
  - `async def put(name: str, **values) -> int` (7)

## Абстракции с одной реализацией

- `Base` — наследник один: `Note`
