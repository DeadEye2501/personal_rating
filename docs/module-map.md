# Карта модулей

Собирается из кода: `pipenv run python scripts/module_map.py`.
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
  - `async def put(self, item_id: int, data: bytes, now: datetime) -> None` (11)
  - `async def get(self, item_id: int) -> bytes | None` (5)
  - `async def has(self, item_id: int) -> bool` (5)
  - `async def delete(self, item_id: int) -> None` (2)

### `backend/storage/repository/base.py` — 66 строк

Общее у репозиториев: сессия и три способа с ней обойтись.

Зависит от: —

- `class Repository` (57)

### `backend/storage/repository/genres.py` — 114 строк

Жанры карточки и разрешение чужих идентификаторов в свои.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.tables`

- `def _is_news(source: GenreSource, ext_id: str) -> bool` (5)
- `def _to_genre(row) -> Genre` (2)
- `class GenresRepository(Repository)` (67)
  - `async def resolve(self, source: GenreSource, ext_ids: list[str]) -> list[int]` (29)
  - `async def set_for_item(self, item_id: int, genre_ids: list[int]) -> None` (16)
  - `async def genres_of(self, item_id: int) -> list[Genre]` (8)
  - `async def list_for_kind(self, kind: GenreKind) -> list[Genre]` (10)

### `backend/storage/repository/library.py` — 184 строк

Карточки библиотеки.

Зависит от: `backend.model`, `backend.storage.posters`, `backend.storage.repository.base`, `backend.storage.session`, `backend.storage.tables`

- `class ItemExists(Exception)` (2)
- `def _values(item: Item) -> dict` (6)
- `def _to_item(row: Row) -> Item` (22)
- `class LibraryRepository(Repository)` (125)
  - `async def create(self, item: Item) -> int` (5)
  - `async def get(self, item_id: int) -> Item | None` (2)
  - `async def find_by_source(self, source: Source, source_id: str) -> Item | None` (7)
  - `async def list_by_kind(self, kind: Kind, limit: int, offset: int) -> list[Item]` (12)
  - `async def find_by_title(self, kind: Kind, title: str) -> list[Item]` (16)
  - `async def deletion_summary(self, item_id: int) -> dict[str, int | bool]` (18)
  - `async def delete(self, item_id: int, posters: PosterStore) -> None` (5)
  - `async def refresh_series_counts(self, item_id: int, seasons_count: int | None, episodes_count: int | None, now: datetime) -> None` (14)
  - `async def replace_fields(self, item_id: int, item: Item) -> None` (8)
  - `async def link(self, item_id: int, source: Source, source_id: str, now: datetime) -> None` (15)
  - `async def unlink(self, item_id: int) -> None` (8)

### `backend/storage/repository/ratings.py` — 69 строк

Моя оценка карточки.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.tables`

- `class RatingsRepository(Repository)` (57)
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

### `backend/storage/repository/wishlist.py` — 41 строк

Список запланированного.

Зависит от: `backend.storage.repository.base`, `backend.storage.tables`

- `class WishlistRepository(Repository)` (30)
  - `async def add(self, item_id: int, now: datetime) -> None` (7)
  - `async def remove(self, item_id: int) -> None` (4)
  - `async def contains(self, item_id: int) -> bool` (5)
  - `async def list_ids(self, limit: int, offset: int) -> list[int]` (10)

### `backend/storage/session.py` — 44 строк

Доступ к основной базе.

Зависит от: —

- `def fold(value: str | None) -> str | None` (5)
- `def prepare_connection(dbapi_connection) -> None` (9)
- `def create_engine(path: Path) -> AsyncEngine` (9)
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

## Абстракции с одной реализацией

Нет.
