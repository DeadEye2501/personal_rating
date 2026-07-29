# Карта данных

Собирается из кода, а не ведётся руками.
Править руками нельзя — правки затрёт следующая сборка.
У набора называется размер, а не содержимое.

## backend

### `backend/config.py`

- `DEFAULT_DATA_DIR` = `'data'`
- `class Config`
  - `data_dir: Path`
  - `tmdb_key: str`
  - `mdblist_key: str`
  - `omdb_key: str`
  - `poiskkino_key: str`
  - `kinopoisk_unofficial_key: str`
  - `log_level: str`

### `backend/model/card.py`

- `class SourceCard`
  - `item: Item`
  - `genre_ext_ids: tuple[tuple[GenreSource, str], ...]` = `field(default_factory=tuple)`
  - `people: tuple[Credit, ...]` = `field(default_factory=tuple)`
  - `companies: tuple[Credit, ...]` = `field(default_factory=tuple)`
  - `external_ids: tuple[ExternalId, ...]` = `field(default_factory=tuple)`
  - `ratings: tuple[ExternalRating, ...]` = `field(default_factory=tuple)`

### `backend/model/credit.py`

- `class Credit`
  - `name: str`
  - `role: PersonRole | CompanyRole`
  - `position: int | None` = `None`
  - `source: Source | None` = `None`
  - `source_id: str | None` = `None`

### `backend/model/external.py`

- `class ExternalId`
  - `source: IdSource`
  - `value: str`
- `class ExternalRating`
  - `source: RatingSource`
  - `value: float | None`
  - `fetched_at: datetime`

### `backend/model/genre.py`

- `class Genre`
  - `id: int`
  - `name: str`
  - `kind: GenreKind`

### `backend/model/item.py`

- `class Item`
  - `id: int`
  - `kind: Kind`
  - `source: Source`
  - `source_id: str`
  - `title: str`
  - `synced_at: datetime`
  - `original_title: str` = `''`
  - `year: int | None` = `None`
  - `released_at: date | None` = `None`
  - `synopsis: str` = `''`
  - `poster_url: str` = `''`
  - `runtime: int | None` = `None`
  - `seasons_count: int | None` = `None`
  - `episodes_count: int | None` = `None`

### `backend/model/kinds.py`

- `class Kind(StrEnum)`
  - `MOVIE` = `'movie'`
  - `SERIES` = `'series'`
  - `GAME` = `'game'`
- `class Source(StrEnum)`
  - `MANUAL` = `'manual'`
  - `TMDB` = `'tmdb'`
  - `STEAM` = `'steam'`
  - `GOG` = `'gog'`
- `class GenreSource(StrEnum)`
  - `TMDB` = `'tmdb'`
  - `STEAM` = `'steam'`
  - `STEAM_TAG` = `'steam_tag'`
  - `GOG` = `'gog'`
  - `GOG_TAG` = `'gog_tag'`
- `class IdSource(StrEnum)`
  - `IMDB` = `'imdb'`
  - `KINOPOISK` = `'kinopoisk'`
  - `STEAM` = `'steam'`
  - `GOG` = `'gog'`
- `class RatingSource(StrEnum)`
  - `IMDB` = `'imdb'`
  - `KINOPOISK` = `'kinopoisk'`
  - `TMDB` = `'tmdb'`
  - `ROTTEN` = `'rotten'`
  - `METACRITIC` = `'metacritic'`
  - `STEAM` = `'steam'`
  - `GOG` = `'gog'`
- `class PersonRole(StrEnum)`
  - `DIRECTOR` = `'director'`
  - `ACTOR` = `'actor'`
  - `SHOWRUNNER` = `'showrunner'`
- `class CompanyRole(StrEnum)`
  - `DEVELOPER` = `'developer'`
  - `PUBLISHER` = `'publisher'`
- `class GenreKind(StrEnum)`
  - `FILM` = `'film'`
  - `GAME` = `'game'`

### `backend/model/rating.py`

- `class Rating`
  - `item_id: int`
  - `score: float | None`
  - `visual: int | None` = `None`
  - `narrative: int | None` = `None`
  - `gameplay: int | None` = `None`
  - `review: str` = `''`

### `backend/model/ratings.py`

- `class Ratings`
  - `values: tuple[ExternalRating, ...]` = `field(default_factory=tuple)`
  - `external_ids: tuple[ExternalId, ...]` = `field(default_factory=tuple)`

### `backend/model/search.py`

- `class SearchHit`
  - `kind: Kind`
  - `source: Source`
  - `source_id: str`
  - `title: str`
  - `original_title: str` = `''`
  - `year: int | None` = `None`
  - `synopsis: str` = `''`
  - `poster_url: str` = `''`
  - `genre_ext_ids: tuple[tuple[GenreSource, str], ...]` = `field(default_factory=tuple)`
  - `source_rating: float | None` = `None`

### `backend/sources/errors.py`

- `class Reason(StrEnum)`
  - `QUOTA` = `'quota'`
  - `RATE` = `'rate'`
  - `KEY` = `'key'`
  - `NETWORK` = `'network'`
  - `BROKEN` = `'broken'`
- `class Found`
  - `value: T`
- `class Refusal`
  - `source: str`
  - `reason: Reason`
  - `retry_after: timedelta | None` = `None`
  - `detail: str` = `''`
- `Outcome: TypeAlias` = `Found | Missing | Refusal`
- `BROKEN_BY_PARSING` = `набор из 4`

### `backend/sources/gog/client.py`

- `logger` = `logging.getLogger(__name__)`
- `CATALOG` = `'https://catalog.gog.com/v1/catalog'`

### `backend/sources/http.py`

- `logger` = `logging.getLogger(__name__)`
- `USER_AGENT` = `'PersonalRating/0.1 (personal library app)'`
- `DEFAULT_TIMEOUT` = `20.0`
- `UNDOCUMENTED_BACKOFF` = `timedelta(minutes=5)`

### `backend/sources/ratings/kinopoisk/client.py`

- `logger` = `logging.getLogger(__name__)`

### `backend/sources/ratings/kinopoisk/mirror.py`

- `SOURCE` = `'kinopoisk'`
- `QUOTA_BACKOFF` = `timedelta(hours=6)`
- `RATE_BACKOFF` = `timedelta(minutes=1)`

### `backend/sources/ratings/kinopoisk/poiskkino.py`

- `logger` = `logging.getLogger(__name__)`
- `BASE` = `'https://api.poiskkino.dev/v1.4/movie'`
- `FIELDS` = `набор из 3`

### `backend/sources/ratings/kinopoisk/unofficial.py`

- `logger` = `logging.getLogger(__name__)`
- `BASE` = `'https://kinopoiskapiunofficial.tech/api/v2.2/fi…`

### `backend/sources/ratings/mdblist/client.py`

- `logger` = `logging.getLogger(__name__)`
- `BASE` = `'https://api.mdblist.com'`
- `QUOTA_FALLBACK` = `timedelta(hours=1)`

### `backend/sources/ratings/mdblist/parse.py`

- `OWNERS` = `словарь из 4`

### `backend/sources/ratings/omdb/client.py`

- `logger` = `logging.getLogger(__name__)`
- `BASE` = `'https://www.omdbapi.com/'`

### `backend/sources/ratings/omdb/parse.py`

- `OWNERS` = `словарь из 3`

### `backend/sources/registry.py`

- `class Sources`
  - `tmdb: TmdbClient`
  - `steam: SteamClient`
  - `gog: GogClient`
  - `mdblist: MdbListClient`
  - `omdb: OmdbClient`
  - `kinopoisk: KinopoiskClient`
  - `connections: tuple[SourceHttp, ...]`

### `backend/sources/steam/client.py`

- `logger` = `logging.getLogger(__name__)`
- `SEARCH` = `'https://steamcommunity.com/actions/SearchApps'`
- `DETAILS` = `'https://store.steampowered.com/api/appdetails'`
- `TAGS` = `'https://api.steampowered.com/IStoreBrowseServic…`
- `TAGS_CONTEXT` = `словарь из 3`
- `TAGS_WANTED` = `словарь из 1`

### `backend/sources/steam/parse.py`

- `ASSETS` = `'https://shared.akamai.steamstatic.com/store_ite…`
- `YEAR` = `re.compile('(?:19|20)\\d{2}')`

### `backend/sources/tmdb/client.py`

- `logger` = `logging.getLogger(__name__)`
- `BASE` = `'https://api.themoviedb.org/3'`
- `LANGUAGE` = `'ru-RU'`
- `RATE_BACKOFF` = `timedelta(minutes=1)`
- `_ABSENT` = `набор из 2`
- `class TmdbClient`
  - `_APPEND` = `словарь из 2`

### `backend/sources/tmdb/parse.py`

- `POSTER_BASE` = `'https://image.tmdb.org/t/p/w500'`

### `backend/storage/posters.py`

- `metadata` = `MetaData()`
- `poster` = `Table('poster', metadata, Column('item_id', Inte…`

### `backend/storage/repository/library.py`

- `_FIELDS` = `набор из 13`

### `backend/storage/tables/base.py`

- `metadata` = `MetaData(naming_convention={'pk': 'pk_%(table_na…`

### `backend/storage/tables/catalog.py`

- `item` = `Table('item', metadata, Column('id', Integer, pr…`
- `genre` = `Table('genre', metadata, Column('id', Integer, p…`
- `genre_map` = `Table('genre_map', metadata, Column('source', Te…`
- `item_genre` = `Table('item_genre', metadata, item_fk(nullable=F…`
- `person` = `Table('person', metadata, Column('id', Integer, …`
- `person_credit` = `Table('person_credit', metadata, item_fk(nullabl…`
- `company` = `Table('company', metadata, Column('id', Integer,…`
- `company_credit` = `Table('company_credit', metadata, item_fk(nullab…`
- `external_id` = `Table('external_id', metadata, item_fk(nullable=…`
- `external_rating` = `Table('external_rating', metadata, item_fk(nulla…`

### `backend/storage/tables/mine.py`

- `rating` = `Table('rating', metadata, item_fk(primary_key=Tr…`
- `tag` = `Table('tag', metadata, Column('id', Integer, pri…`
- `item_tag` = `Table('item_tag', metadata, item_fk(nullable=Fal…`
- `wishlist` = `Table('wishlist', metadata, item_fk(primary_key=…`

## migrations

### `migrations/env.py`

- `config` = `context.config`
- `target_metadata` = `metadata`

### `migrations/versions/0001_schema.py`

- `revision: str` = `'0001'`
- `down_revision: str | None` = `None`

### `migrations/versions/0002_genres.py`

- `revision: str` = `'0002'`
- `down_revision: str | None` = `'0001'`
- `FILM` = `набор из 25`
- `TMDB` = `словарь из 27`
- `GAME` = `набор из 22`
- `STEAM` = `словарь из 8`
- `STEAM_TAG` = `словарь из 168`
- `GOG` = `словарь из 39`
- `GOG_TAG` = `словарь из 68`

## scripts

### `scripts/collect_game_genres.py`

- `HEADERS` = `словарь из 1`
- `STEAM_MENU` = `'https://store.steampowered.com/api/getgenrelist…`
- `STEAM_APP` = `'https://store.steampowered.com/api/appdetails'`
- `GOG_CATALOG` = `'https://catalog.gog.com/v1/catalog'`
- `EXAMPLES_PER_GENRE` = `2`

### `scripts/genre_map.py`

- `ROOT` = `Path(__file__).resolve().parents[1]`
- `MIGRATION` = `ROOT / 'migrations/versions/0002_genres.py'`
- `SPECS` = `словарь из 5`

### `scripts/module_map.py`

- `MAP` = `ROOT / 'docs/module-map.md'`
- `DATA_MAP` = `ROOT / 'docs/data-map.md'`
- `SHORT_VALUE` = `48`

### `scripts/not_duplicates.py`

- `VERDICTS` = `ROOT / 'docs/not-duplicates.md'`

### `scripts/project_ast.py`

- `STAMP` = `8`
- `SKIP` = `набор из 12`
- `DEFINITIONS` = `набор из 3`
- `FUNCTIONS` = `набор из 2`
- `ROOT` = `project_root()`

### `scripts/record_fixtures.py`

- `ROOT` = `Path(__file__).resolve().parents[1]`
- `OUT` = `ROOT / 'tests' / 'fixtures'`
- `HEADERS` = `словарь из 1`
- `KEEP_HEADERS` = `набор из 5`
- `INTERSTELLAR_TMDB` = `157336`
- `ANDOR_TMDB` = `83867`
- `INTERSTELLAR_IMDB` = `'tt0816692'`
- `WITCHER_APPID` = `292030`

## tests

### `tests/alembic_runner.py`

- `ROOT` = `Path(__file__).resolve().parents[1]`

### `tests/backend/sources/conftest.py`

- `FIXTURES` = `Path(__file__).resolve().parents[2] / 'fixtures'`

### `tests/backend/sources/test_registry.py`

- `SILENT` = `httpx.MockTransport(lambda request: httpx.Respon…`

### `tests/backend/test_config.py`

- `KEYS` = `словарь из 5`

### `tests/backend/test_delete.py`

- `PICTURE` = `b'\x89PNG\r\n\x1a\n' + b'0' * 128`
- `ALONE` = `набор из 3`

### `tests/backend/test_genre_reference.py`

- `FILM_GENRES` = `набор из 25`
- `GAME_GENRES` = `набор из 22`
- `COMPOSITE` = `словарь из 3`

### `tests/backend/test_genres.py`

- `SILENT` = `набор из 4`

### `tests/backend/test_layers.py`

- `ROOT` = `Path(__file__).resolve().parents[2]`
- `BANNED_IN_CLIENT` = `набор из 5`
- `BANNED_IN_BACKEND` = `набор из 2`
- `ALLOWED_FROM_BACKEND` = `набор из 2`

### `tests/backend/test_migrations.py`

- `STAMP` = `'alembic_version'`

### `tests/backend/test_model.py`

- `FROZEN` = `набор из 6`
- `SCHEMA` = `набор из 8`

### `tests/backend/test_posters.py`

- `PICTURE` = `b'\x89PNG\r\n\x1a\n' + b'0' * 512`
- `OTHER` = `'другая обложка'.encode()`

### `tests/backend/test_session.py`

- `class Note(Base)`
  - `__tablename__` = `'note'`
  - `id: Mapped[int]` = `mapped_column(primary_key=True)`
  - `title: Mapped[str]`

### `tests/backend/test_tables.py`

- `TYPES` = `набор из 9`
- `REQUIRED` = `набор из 12`
- `UNIQUE` = `набор из 4`
- `COMPOSITE` = `набор из 7`
- `PARENTS` = `набор из 5`

### `tests/conftest.py`

- `MOMENT` = `datetime(2026, 7, 29, 12, 0)`
- `LATER` = `datetime(2026, 7, 30, 12, 0)`
- `TABLES` = `набор из 14`
- `MINIMAL` = `словарь из 5`

### `tests/scripts/test_not_duplicates.py`

- `LINE` = `'- `a.py:one` `11111111` ≠ `b.py:two` `22222222`…`
- `INDEX` = `словарь из 2`
