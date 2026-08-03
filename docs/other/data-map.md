# Карта данных

Собирается из кода, а не ведётся руками.
Править руками нельзя — правки затрёт следующая сборка.
У набора называется размер, а не содержимое.

## .

### `main.py`

- `logger` = `logging.getLogger(__name__)`
- `BASE_DIR` = `Path(__file__).resolve().parent`
- `LOG_BYTES` = `5 * 1024 * 1024`
- `LOG_FILES` = `3`

## backend

### `backend/app.py`

- `class Backend`
  - `library: LibraryRepository`
  - `ratings: RatingsRepository`
  - `tags: TagsRepository`
  - `wishlist: WishlistRepository`
  - `genres: GenresRepository`
  - `people: CreditRepository`
  - `companies: CreditRepository`
  - `search: SearchService`
  - `finder: PeopleSearch`
  - `feed: LibraryService`
  - `loader: Loader`
  - `series: SeriesRefresh`
  - `enricher: Enricher`
  - `linker: Linker`
  - `posters: PosterService`
  - `_removed: RemovedRepository`
  - `_sources: Sources`
  - `_engine: AsyncEngine`

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

### `backend/language.py`

- `RUSSIAN_LETTERS` = `frozenset('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')`
- `LATIN_LETTERS` = `frozenset('abcdefghijklmnopqrstuvwxyz')`

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
  - `entity_id: int | None` = `None`
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
- `class GenreRule`
  - `genre: Genre`
  - `required: frozenset[str]`
  - `forbidden: frozenset[str]` = `frozenset()`
  - `alone: bool` = `False`

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
- `class SeriesCounts`
  - `seasons: int | None`
  - `episodes: int | None`

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
  - `OLD_GAMES` = `'old_games'`
- `class GenreSource(StrEnum)`
  - `TMDB` = `'tmdb'`
  - `STEAM` = `'steam'`
  - `GOG` = `'gog'`
  - `OLD_GAMES` = `'old_games'`
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

### `backend/model/link.py`

- `class ExternalLink`
  - `source: Source`
  - `source_id: str`
  - `kind: Kind`
- `_TMDB` = `re.compile('themoviedb\\.org/(movie|tv)/(\\d+)',…`
- `_STEAM` = `re.compile('store\\.steampowered\\.com/(?:ageche…`
- `_GOG` = `re.compile('gog\\.com/(?:[a-z-]+/)?game/([a-z0-9…`
- `_BARE` = `re.compile('^\\d+$')`
- `_TMDB_KINDS` = `словарь из 2`
- `_FILMS` = `набор из 2`

### `backend/model/outcome.py`

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

### `backend/model/query.py`

- `class Section(StrEnum)`
  - `RATED` = `'rated'`
  - `WISHLIST` = `'wishlist'`
- `class Sort(StrEnum)`
  - `SCORE` = `'score'`
  - `RATED_AT` = `'rated_at'`
  - `YEAR` = `'year'`
  - `TITLE` = `'title'`
  - `ADDED_AT` = `'added_at'`
- `class Order`
  - `key: Sort`
  - `descending: bool` = `True`
- `class Filters`
  - `tag_ids: tuple[int, ...]` = `набор из 0`
  - `genre_ids: tuple[int, ...]` = `набор из 0`
  - `scores: tuple[int, ...]` = `набор из 0`
  - `excluded_tag_ids: tuple[int, ...]` = `набор из 0`
  - `excluded_genre_ids: tuple[int, ...]` = `набор из 0`
  - `excluded_scores: tuple[int, ...]` = `набор из 0`
- `class Feed`
  - `section: Section`
  - `kind: Kind`
  - `filters: Filters`
  - `order: Order`
- `class Bucket`
  - `score: int`
  - `count: int`
- `class Histogram`
  - `buckets: tuple[Bucket, ...]`
  - `total: int`
  - `average: float | None`

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

### `backend/model/results.py`

- `class ExternalSearch`
  - `views: tuple[CardView, ...]`
  - `refusals: tuple[Refusal, ...]`
  - `removed: bool` = `False`

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
  - `aliases: tuple[str, ...]` = `field(default_factory=tuple)`
- `class PersonHit`
  - `source_id: str`

### `backend/model/suggestion.py`

- `class Suggestion`
  - `entity_id: int`
  - `name: str`
  - `hint: str`
  - `hint_item_id: int | None`

### `backend/model/tag.py`

- `class Tag`
  - `id: int`
  - `name: str`

### `backend/model/view.py`

- `class CardView`
  - `kind: Kind`
  - `source: Source`
  - `source_id: str`
  - `title: str`
  - `item_id: int | None` = `None`
  - `original_title: str` = `''`
  - `year: int | None` = `None`
  - `synopsis: str` = `''`
  - `poster_url: str` = `''`
  - `runtime: int | None` = `None`
  - `seasons_count: int | None` = `None`
  - `episodes_count: int | None` = `None`
  - `synced_at: datetime | None` = `None`
  - `genres: tuple[Genre, ...]` = `набор из 0`
  - `tags: tuple[Tag, ...]` = `набор из 0`
  - `people: tuple[Credit, ...]` = `набор из 0`
  - `companies: tuple[Credit, ...]` = `набор из 0`
  - `external: tuple[ExternalRating, ...]` = `набор из 0`
  - `external_ids: tuple[ExternalId, ...]` = `набор из 0`
  - `rating: Rating | None` = `None`
  - `in_wishlist: bool` = `False`

### `backend/service/asking.py`

- `logger` = `logging.getLogger(__name__)`

### `backend/service/cards.py`

- `logger` = `logging.getLogger(__name__)`

### `backend/service/creation.py`

- `logger` = `logging.getLogger(__name__)`

### `backend/service/enrich.py`

- `logger` = `logging.getLogger(__name__)`
- `class _Harvest`
  - `values: dict[RatingSource, float]` = `field(default_factory=dict)`
  - `refused: set[RatingSource]` = `field(default_factory=set)`

### `backend/service/genres.py`

- `Book` = `dict[GenreSource, tuple[GenreRule, ...]]`
- `Marked` = `Iterable[tuple[GenreSource, str]]`

### `backend/service/images.py`

- `TARGET_RATIO` = `2 / 3`
- `TARGET_SIZE` = `набор из 2`
- `_QUALITY` = `88`

### `backend/service/library.py`

- `PAGE_SIZE` = `50`

### `backend/service/linking.py`

- `logger` = `logging.getLogger(__name__)`
- `_FILLABLE` = `набор из 9`
- `_EMPTY` = `набор из 2`

### `backend/service/loading.py`

- `logger` = `logging.getLogger(__name__)`

### `backend/service/merging.py`

- `SETS` = `набор из 7`
- `PRIORITY` = `набор из 3`
- `YEAR_GAP` = `3`

### `backend/service/posters.py`

- `logger` = `logging.getLogger(__name__)`
- `_SIGNATURES` = `набор из 3`
- `_ABSENT` = `404`
- `POSTER_SOURCES` = `набор из 4`

### `backend/service/search.py`

- `SEARCH_SIZE` = `20`
- `COMMANDS` = `frozenset({'удалено', 'удаленное', 'удаленный', …`
- `class SearchParts`
  - `genres: GenresRepository`
  - `removed: RemovedRepository`

### `backend/service/series.py`

- `logger` = `logging.getLogger(__name__)`
- `REFRESH_TTL` = `timedelta(days=30)`

### `backend/service/titles.py`

- `ROMAN` = `словарь из 20`
- `EDITION_WORDS` = `frozenset({'edition', 'editions', 'ed', 'goty', …`
- `SYMBOLS` = `str.maketrans({'™': ' ', '®': ' ', '©': ' ', '℠'…`
- `ARTICLES` = `frozenset({'the', 'a', 'an'})`

### `backend/sources/convert.py`

- `FREE_IN_SEARCH` = `словарь из 2`

### `backend/sources/errors.py`

- `BROKEN_BY_PARSING` = `набор из 5`

### `backend/sources/gog/client.py`

- `logger` = `logging.getLogger(__name__)`
- `CATALOG` = `'https://catalog.gog.com/v1/catalog'`
- `PRODUCT` = `'https://api.gog.com/products/{source_id}'`
- `PRODUCT_TYPES` = `'in:game,pack'`

### `backend/sources/gog/parse.py`

- `SPELLING` = `словарь из 5`

### `backend/sources/http.py`

- `logger` = `logging.getLogger(__name__)`
- `USER_AGENT` = `'PersonalRating/0.1 (dead.eye.2501@gmail.com)'`
- `DEFAULT_TIMEOUT` = `20.0`
- `NETWORK_BACKOFF` = `timedelta(seconds=15)`
- `AT_ONCE` = `словарь из 1`
- `POSTER_SUFFIX` = `'-poster'`

### `backend/sources/oldgames/client.py`

- `logger` = `logging.getLogger(__name__)`
- `BASE` = `'https://www.old-games.ru'`
- `CATALOG` = `f'{BASE}/catalog/'`
- `CARD` = `BASE + '/game/{source_id}.html'`
- `BUSY` = `503`
- `ATTEMPTS` = `3`

### `backend/sources/oldgames/parse.py`

- `GAME_HREF` = `re.compile('^/game/(\\d+)\\.html$')`
- `NOCOVER` = `'nocover-rus.gif'`
- `GAME_SCOPE` = `'[itemtype*="SoftwareApplication"]'`
- `BY` = `'Автор обзора:'`
- `ALT_NAMES` = `'span.game_alt_names'`
- `UNKNOWN` = `'-'`

### `backend/sources/ratings/kinopoisk/client.py`

- `logger` = `logging.getLogger(__name__)`
- `class KinopoiskClient`
  - `PROVIDES: ClassVar[tuple[RatingSource, ...]]` = `набор из 1`

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
- `class MdbListClient`
  - `PROVIDES: ClassVar[tuple[RatingSource, ...]]` = `набор из 4`

### `backend/sources/ratings/mdblist/parse.py`

- `OWNERS` = `словарь из 4`

### `backend/sources/ratings/omdb/client.py`

- `logger` = `logging.getLogger(__name__)`
- `BASE` = `'https://www.omdbapi.com/'`
- `class OmdbClient`
  - `PROVIDES: ClassVar[tuple[RatingSource, ...]]` = `набор из 3`

### `backend/sources/ratings/omdb/parse.py`

- `OWNERS` = `словарь из 3`

### `backend/sources/registry.py`

- `class Sources`
  - `tmdb: TmdbClient`
  - `steam: SteamClient`
  - `gog: GogClient`
  - `old_games: OldGamesClient`
  - `mdblist: MdbListClient`
  - `omdb: OmdbClient`
  - `kinopoisk: KinopoiskClient`
  - `connections: tuple[SourceHttp, ...]`

### `backend/sources/steam/client.py`

- `logger` = `logging.getLogger(__name__)`
- `SEARCH` = `'https://steamcommunity.com/actions/SearchApps'`
- `DETAILS` = `'https://store.steampowered.com/api/appdetails'`
- `ITEMS` = `'https://api.steampowered.com/IStoreBrowseServic…`
- `ITEMS_CONTEXT` = `словарь из 3`
- `SIFT_WANTED` = `словарь из 2`
- `CARD_WANTED` = `SIFT_WANTED | {'include_tag_count': 20}`

### `backend/sources/steam/parse.py`

- `ASSETS` = `'https://shared.akamai.steamstatic.com/store_ite…`
- `TYPE_GAME` = `0`
- `ANSWERED` = `1`
- `GENRE_TWIN` = `словарь из 8`

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
- `_KEYS` = `словарь из 2`

### `backend/sources/undocumented.py`

- `UNDOCUMENTED_BACKOFF` = `timedelta(minutes=5)`

### `backend/storage/entity.py`

- `class Entity`
  - `table: Table`
  - `credit: Table`
  - `roles: Callable[[str], PersonRole | CompanyRole]`
  - `position: Column | None` = `None`
- `PEOPLE` = `Entity(person, person_credit, PersonRole, person…`
- `COMPANIES` = `Entity(company, company_credit, CompanyRole)`

### `backend/storage/posters.py`

- `metadata` = `MetaData()`
- `poster` = `Table('poster', metadata, Column('item_id', Inte…`

### `backend/storage/repository/base.py`

- `_NO_TARGET` = `'SQLITE_CONSTRAINT_FOREIGNKEY'`

### `backend/storage/repository/external.py`

- `VALUE_TTL` = `timedelta(days=30)`
- `EMPTY_TTL` = `timedelta(days=7)`

### `backend/storage/repository/library.py`

- `_FIELDS` = `набор из 13`

### `backend/storage/repository/sections.py`

- `_COLUMN` = `cast(rating.c.score, Integer)`
- `_KEYS` = `словарь из 5`

### `backend/storage/tables/base.py`

- `metadata` = `MetaData(naming_convention={'pk': 'pk_%(table_na…`

### `backend/storage/tables/catalog.py`

- `item` = `Table('item', metadata, Column('id', Integer, pr…`
- `genre` = `Table('genre', metadata, Column('id', Integer, p…`
- `genre_rule` = `Table('genre_rule', metadata, Column('id', Integ…`
- `genre_rule_mark` = `Table('genre_rule_mark', metadata, Column('rule_…`
- `item_genre` = `Table('item_genre', metadata, item_fk(nullable=F…`
- `person` = `Table('person', metadata, Column('id', Integer, …`
- `person_credit` = `Table('person_credit', metadata, item_fk(nullabl…`
- `company` = `Table('company', metadata, Column('id', Integer,…`
- `company_credit` = `Table('company_credit', metadata, item_fk(nullab…`
- `external_id` = `Table('external_id', metadata, item_fk(nullable=…`
- `external_rating` = `Table('external_rating', metadata, item_fk(nulla…`

### `backend/storage/tables/mine.py`

- `removed` = `Table('removed', metadata, Column('kind', Text, …`
- `rating` = `Table('rating', metadata, item_fk(primary_key=Tr…`
- `tag` = `Table('tag', metadata, Column('id', Integer, pri…`
- `item_tag` = `Table('item_tag', metadata, item_fk(nullable=Fal…`
- `wishlist` = `Table('wishlist', metadata, item_fk(primary_key=…`

## bridge

### `bridge/answer.py`

- `logger` = `logging.getLogger(__name__)`
- `_EDGE` = `re.compile('(?<!^)(?=[A-Z])')`

### `bridge/feed.py`

- `FILTER_FIELDS` = `набор из 6`

### `bridge/refs.py`

- `DOMAINS` = `набор из 2`
- `ROLES` = `словарь из 2`

### `bridge/serve.py`

- `logger` = `logging.getLogger(__name__)`
- `WEB_ROOT` = `Path(__file__).resolve().parent.parent / 'client…`
- `TYPES` = `словарь из 8`
- `MAGIC` = `набор из 3`

### `bridge/thread.py`

- `logger` = `logging.getLogger(__name__)`
- `BUILD_TIMEOUT` = `30.0`
- `DEADLINE` = `60.0`

### `bridge/window.py`

- `logger` = `logging.getLogger(__name__)`
- `TITLE` = `'Personal Rating'`
- `RENDERER` = `'edgechromium'`
- `MIN_WIDTH` = `1200`
- `MIN_HEIGHT` = `600`
- `WIDTH` = `1280`
- `HEIGHT` = `820`
- `BACKGROUND` = `'#0a0a0a'`

## migrations

### `migrations/env.py`

- `config` = `context.config`
- `target_metadata` = `metadata`

### `migrations/reference/gog.py`

- `GOG` = `набор из 101`

### `migrations/reference/names.py`

- `FILM` = `набор из 25`
- `GAME` = `набор из 19`

### `migrations/reference/old_games.py`

- `OLD_GAMES` = `набор из 13`

### `migrations/reference/rule.py`

- `class Rule(NamedTuple)`
  - `genre: str`
  - `marks: str`
  - `without: str` = `''`
  - `alone: bool` = `False`

### `migrations/reference/steam.py`

- `STEAM` = `набор из 219`

### `migrations/reference/tmdb.py`

- `TMDB` = `набор из 30`

### `migrations/versions/0001_schema.py`

- `revision: str` = `'0001'`
- `down_revision: str | None` = `None`

### `migrations/versions/0002_genres.py`

- `revision: str` = `'0002'`
- `down_revision: str | None` = `'0001'`
- `BOOKS` = `набор из 4`

## scripts

### `scripts/collect_game_genres.py`

- `HEADERS` = `словарь из 1`
- `STEAM_MENU` = `'https://store.steampowered.com/api/getgenrelist…`
- `STEAM_APP` = `'https://store.steampowered.com/api/appdetails'`
- `GOG_CATALOG` = `'https://catalog.gog.com/v1/catalog'`
- `EXAMPLES_PER_GENRE` = `2`

### `scripts/record_fixtures.py`

- `ROOT` = `Path(__file__).resolve().parents[1]`
- `OUT` = `ROOT / 'tests' / 'fixtures'`
- `HEADERS` = `словарь из 1`
- `KEEP_HEADERS` = `набор из 5`
- `INTERSTELLAR_TMDB` = `157336`
- `ANDOR_TMDB` = `83867`
- `INTERSTELLAR_IMDB` = `'tt0816692'`
- `WITCHER_APPID` = `292030`
- `REDKIT_APPID` = `2684660`
- `ARCANUM_APPID` = `500810`
- `PLAYTEST_APPID` = `4926960`
- `NOLAN_TMDB` = `525`
- `MURPHY_TMDB` = `2037`

## tests

### `tests/alembic_runner.py`

- `ROOT` = `Path(__file__).resolve().parents[1]`

### `tests/backend/sources/test_gog.py`

- `WANTED` = `'1456460669'`

### `tests/backend/sources/test_gog_slug.py`

- `SLUG` = `'arcanum_of_steamworks_and_magick_obscura'`

### `tests/backend/sources/test_rating_provides.py`

- `FULL_ANSWERS` = `набор из 3`

### `tests/backend/sources/test_registry.py`

- `SILENT` = `responding(json={})`
- `CATALOG_OWNERS` = `набор из 4`

### `tests/backend/sources/test_steam_items.py`

- `FOUND` = `набор из 4`

### `tests/backend/test_config.py`

- `KEYS` = `словарь из 5`

### `tests/backend/test_cover_reads.py`

- `STORED` = `bytes.fromhex('ffd8ffe000104a46') + b'0' * 64`

### `tests/backend/test_delete.py`

- `ALONE` = `набор из 3`

### `tests/backend/test_denied.py`

- `SIX` = `набор из 6`

### `tests/backend/test_external_ratings.py`

- `WANTED` = `набор из 3`

### `tests/backend/test_genre_reference.py`

- `MIGRATION` = `'migrations.versions.0002_genres'`
- `REFERENCE` = `Path(__file__).resolve().parents[1] / 'fixtures/…`
- `FILM_GENRES` = `набор из 25`
- `GAME_GENRES` = `набор из 19`
- `COMPOSITE` = `словарь из 3`
- `RULES` = `363`
- `MARKS` = `385`

### `tests/backend/test_genre_resolution.py`

- `REFERENCE` = `"INSERT INTO genre (id, name, kind) VALUES (1, '…`
- `RULES` = `"INSERT INTO genre_rule (id, source, genre_id, a…`
- `MARKS` = `"INSERT INTO genre_rule_mark (rule_id, ext_id, f…`

### `tests/backend/test_genre_rules.py`

- `FALLOUT` = `набор из 3`
- `STARDEW` = `набор из 10`
- `STEAM_GENRES` = `словарь из 8`
- `FROZEN_SPELLING` = `словарь из 5`

### `tests/backend/test_images.py`

- `DEGENERATE` = `набор из 3`

### `tests/backend/test_language.py`

- `RUSSIAN` = `набор из 5`
- `NOT_RUSSIAN` = `набор из 6`
- `LATIN` = `набор из 4`
- `NOT_LATIN` = `набор из 6`

### `tests/backend/test_layers.py`

- `ROOT` = `Path(__file__).resolve().parents[2]`
- `BANNED_IN_BACKEND` = `набор из 4`
- `BANNED_IN_BRIDGE` = `набор из 6`
- `ALLOWED_FROM_BACKEND` = `набор из 2`

### `tests/backend/test_linking.py`

- `FULL` = `an_item('83867', 'Andor', kind=Kind.SERIES, orig…`

### `tests/backend/test_links.py`

- `ADDRESSES` = `набор из 6`
- `SHOUTED` = `набор из 5`
- `NONSENSE` = `набор из 9`

### `tests/backend/test_loading.py`

- `SEARCH_COVER` = `'https://example.com/p.jpg'`
- `DETAIL_COVER` = `'https://example.com/d.jpg'`
- `class Rig`
  - `load: Loader`
  - `client: FakeCatalog`
  - `posters: PosterService`
  - `requests: list`

### `tests/backend/test_merging_sets.py`

- `FROZEN_SETS` = `набор из 7`

### `tests/backend/test_migrations.py`

- `STAMP` = `'alembic_version'`

### `tests/backend/test_model.py`

- `SCHEMA` = `набор из 8`

### `tests/backend/test_posters.py`

- `OTHER` = `'другая обложка'.encode()`

### `tests/backend/test_removed.py`

- `FALLOUT` = `набор из 3`

### `tests/backend/test_restore.py`

- `WORDS` = `набор из 6`

### `tests/backend/test_series_refresh.py`

- `LONG_AGO` = `MOMENT - timedelta(days=40)`

### `tests/backend/test_session.py`

- `class Note(Base)`
  - `__tablename__` = `'note'`
  - `id: Mapped[int]` = `mapped_column(primary_key=True)`
  - `title: Mapped[str]`

### `tests/backend/test_tables.py`

- `TYPES` = `набор из 9`
- `REQUIRED` = `набор из 12`
- `UNIQUE` = `набор из 4`
- `COMPOSITE` = `набор из 8`
- `PARENTS` = `набор из 5`

### `tests/backend/test_titles.py`

- `SAME` = `набор из 14`
- `EDITIONS` = `набор из 3`
- `FROZEN_EDITIONS` = `набор из 49`

### `tests/backend/test_view_types.py`

- `DRAMA` = `Genre(id=1, name='Драма', kind=GenreKind.FILM)`

### `tests/bridge/test_bridge_covers.py`

- `PNG` = `base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()`

### `tests/bridge/test_bridge_feed.py`

- `WISHED` = `словарь из 4`

### `tests/bridge/test_bridge_surface.py`

- `ROOT` = `Path(__file__).resolve().parents[2]`
- `SOURCES` = `sorted((ROOT / 'bridge').glob('*.py'))`
- `DOMAINS` = `набор из 7`
- `CHOOSER` = `'_of'`

### `tests/bridge/test_page_contract.py`

- `WEB` = `Path(__file__).resolve().parents[2] / 'client'`
- `SKIPPED` = `набор из 2`
- `CHOSEN` = `re.compile('export function chosen\\(filters\\) …`
- `CALLED` = `re.compile("'(\\w+)\\.(\\w+)'")`

### `tests/bridge/test_serve.py`

- `PNG` = `b'\x89PNG\r\n\x1a\nthe rest'`
- `JPEG` = `b'\xff\xd8\xff\xe0the rest'`
- `CANDIDATE` = `'source=tmdb&url=https%3A%2F%2Fimage%2F1.jpg'`

### `tests/builders.py`

- `FIXTURES` = `Path(__file__).resolve().parent / 'fixtures'`
- `MOMENT` = `datetime(2026, 7, 29, 12, 0)`
- `LATER` = `datetime(2026, 7, 30, 12, 0)`
- `PICTURE` = `b'\x89PNG\r\n\x1a\n' + b'0' * 512`
- `POSTER` = `picture(600, 900, fmt='JPEG')`
- `STORES` = `набор из 3`

### `tests/conftest.py`

- `ACTION` = `набор из 3`
- `ADVENTURE` = `набор из 3`
- `DRAMA` = `набор из 3`
- `RATED` = `Feed(Section.RATED, Kind.MOVIE, Filters(), Order…`
- `WANTED` = `Feed(Section.WISHLIST, Kind.MOVIE, Filters(), Or…`
- `TABLES` = `набор из 16`
- `MINIMAL` = `словарь из 5`
