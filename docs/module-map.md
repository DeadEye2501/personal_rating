# Карта модулей

Собирается из кода, а не ведётся руками.
Править руками нельзя — правки затрёт следующая сборка.
Число в скобках — сколько строк занимает объявление.

## backend — 73 модулей

### `backend/app.py` — 149 строк

Бэкенд, собранный целиком.

Зависит от: `backend.config`, `backend.service.cards`, `backend.service.enrich`, `backend.service.library`, `backend.service.linking`, `backend.service.loading`, `backend.service.posters`, `backend.service.removal`, `backend.service.search`, `backend.service.series`, `backend.sources.build`, `backend.sources.http`, `backend.sources.registry`, `backend.storage.posters`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.sections`, `backend.storage.repository.tags`, `backend.storage.repository.views`, `backend.storage.repository.wishlist`, `backend.storage.session`

- `class Backend` (39)
  - `async def delete_card(self, item_id: int) -> None` (7)
  - `async def aclose(self) -> None` (8)
- `def card_parts(sessions, posters: PosterService) -> dict` (13)
- `async def build_backend(config: Config, transport: httpx.AsyncBaseTransport | None=None) -> Backend` (56)

### `backend/config.py` — 49 строк

Настройки приложения, прочитанные из окружения.

Зависит от: —

- `class Config` (20)
  - `def library_db(self) -> Path` (2)
  - `def posters_db(self) -> Path` (2)
  - `def log_file(self) -> Path` (2)
- `def value(env: Mapping[str, str], name: str) -> str` (4)
- `def load_config(env: Mapping[str, str], base_dir: Path) -> Config` (11)

### `backend/model/__init__.py` — 94 строк

Поверхность модели: отсюда типы границы слоёв импортирует клиент.

Зависит от: `backend.model.card`, `backend.model.credit`, `backend.model.external`, `backend.model.genre`, `backend.model.item`, `backend.model.kinds`, `backend.model.link`, `backend.model.outcome`, `backend.model.query`, `backend.model.rating`, `backend.model.ratings`, `backend.model.results`, `backend.model.search`, `backend.model.suggestion`, `backend.model.tag`, `backend.model.view`

Отдаёт наружу: `Bucket`, `CardView`, `CompanyRole`, `Credit`, `ExternalId`, `ExternalLink`, `ExternalRating`, `ExternalSearch`, `Feed`, `Filters`, `Found`, `Genre`, `GenreKind`, `GenreSource`, `Histogram`, `IdSource`, `Item`, `Kind`, `Missing`, `Order`, `Outcome`, `PersonRole`, `Rating`, `RatingSource`, `Ratings`, `Reason`, `Refusal`, `SearchHit`, `Section`, `SeriesCounts`, `Sort`, `Source`, `SourceCard`, `Suggestion`, `Tag`, `average_score`, `is_answer`, `merge_results`, `new_manual_item`, `new_source_id`, `parse_link`, `view_from_hit`, `view_from_item`


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

### `backend/model/item.py` — 56 строк

Карточка любого типа содержимого на границе слоёв.

Зависит от: `backend.model.kinds`

- `class Item` (16)
- `class SeriesCounts` (5)
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

### `backend/model/link.py` — 66 строк

Разобранная ссылка на страницу во внешней базе.

Зависит от: `backend.model.kinds`

- `class ExternalLink` (4)
- `def parse_link(raw: str, kind: Kind | None=None) -> ExternalLink | None` (34)

### `backend/model/outcome.py` — 52 строк

Чем может кончиться запрос к источнику: находкой, честным «нет» или отказом.

Зависит от: —

- `class Reason(StrEnum)` (6)
- `class Found` (2)
- `class Missing` (3)
- `class Refusal` (8)
- `Outcome: TypeAlias = Found | Missing | Refusal`
- `def is_answer(outcome: Outcome) -> bool` (5)

### `backend/model/query.py` — 88 строк

Язык, которым лента разговаривает с базой о разделах.

Зависит от: `backend.model.kinds`

- `class Section(StrEnum)` (6)
- `class Sort(StrEnum)` (10)
- `class Order` (6)
- `class Filters` (15)
- `class Feed` (11)
- `class Bucket` (5)
- `class Histogram` (10)

### `backend/model/rating.py` — 23 строк

Своя оценка карточки.

Зависит от: —

- `def average_score(*aspects: int | None) -> float | None` (7)
- `class Rating` (8)

### `backend/model/ratings.py` — 16 строк

Ответ оценочного источника на границе слоёв.

Зависит от: `backend.model.external`

- `class Ratings` (8)

### `backend/model/results.py` — 45 строк

Что ответила чужая база и как её выдача складывается со своей.

Зависит от: `backend.model.kinds`, `backend.model.outcome`, `backend.model.view`

- `class ExternalSearch` (6)
- `def merge_results(local: list[CardView], external: list[CardView]) -> list[CardView]` (23)

### `backend/model/search.py` — 27 строк

Кандидат в выдаче поиска — то, чем карточка ещё не стала.

Зависит от: `backend.model.kinds`

- `class SearchHit` (19)

### `backend/model/suggestion.py` — 15 строк

Строка подсказки при вводе имени человека или студии.

Зависит от: —

- `class Suggestion` (9)

### `backend/model/tag.py` — 11 строк

Свой тег на границе слоёв.

Зависит от: —

- `class Tag` (5)

### `backend/model/view.py` — 89 строк

Карточка в том виде, в каком её показывает лента.

Зависит от: `backend.model.credit`, `backend.model.external`, `backend.model.genre`, `backend.model.item`, `backend.model.kinds`, `backend.model.rating`, `backend.model.search`, `backend.model.tag`

- `class CardView` (32)
- `def view_from_hit(hit: SearchHit, genres: tuple[Genre, ...]=(), external: tuple[ExternalRating, ...]=()) -> CardView` (19)
- `def view_from_item(item: Item) -> CardView` (18)

### `backend/service/asking.py` — 23 строк

Запрос к источнику, из которого не вылетает исключение.

Зависит от: `backend.sources.errors`

- `async def answered(awaitable, source: str)` (14)

### `backend/service/card_parts.py` — 52 строк

Общая основа записи карточки в базу.

Зависит от: `backend.model`, `backend.service.posters`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`

- `class CardParts` (39)
  - `async def _attach_credits(self, repository: CreditRepository, item_id: int, credits: tuple[Credit, ...]) -> None` (6)
  - `async def _write_external(self, item_id: int, card: SourceCard) -> None` (6)

### `backend/service/cards.py` — 73 строк

Карточка источника строками базы.

Зависит от: `backend.model`, `backend.service.card_parts`, `backend.service.genres`, `backend.service.removal`, `backend.sources.errors`, `backend.storage.repository.library`

- `class CardWriter(CardParts)` (58)
  - `async def save(self, card: SourceCard, poster: bytes | None=None) -> int | Refusal` (39)
  - `async def _write_the_rest(self, item_id: int, card: SourceCard, poster: bytes | None) -> None` (13)

### `backend/service/enrich.py` — 156 строк

Чужие оценки у карточки.

Зависит от: `backend.model`, `backend.service.asking`, `backend.sources.registry`, `backend.storage.repository.external`, `backend.unique`

- `class _Harvest` (10)
- `class Enricher` (114)
  - `async def enrich(self, item_id: int, kind: Kind) -> list[ExternalRating]` (28)
  - `def expected(self, kind: Kind) -> list[RatingSource]` (9)
  - `async def _imdb_id(self, item_id: int) -> str | None` (5)
  - `async def _harvested(self, item_id: int, asked: list, outcomes: list) -> _Harvest` (16)
  - `def _take(harvest: _Harvest, values: tuple[ExternalRating, ...], provides: tuple[RatingSource, ...]) -> None` (16)
  - `async def _record(self, item_id: int, harvest: _Harvest, stale: list[RatingSource], now: datetime) -> None` (13)
  - `async def _keep(self, item_id: int, external: ExternalId) -> None` (5)

### `backend/service/genres.py` — 28 строк

Чужие метки жанров в наши идентификаторы.

Зависит от: `backend.model`, `backend.storage.repository.genres`, `backend.unique`

- `async def resolved_genres(genres: GenresRepository, marked: tuple[tuple[GenreSource, str], ...]) -> list[int]` (21)

### `backend/service/images.py` — 51 строк

Приведение залитой с диска картинки к виду обложки.

Зависит от: —

- `class BadImage(Exception)` (2)
- `def _centred_box(width: int, height: int) -> tuple[int, int, int, int]` (11)
- `def crop_to_cover(data: bytes) -> bytes` (20)

### `backend/service/library.py` — 41 строк

Что показывает раздел.

Зависит от: `backend.model`, `backend.storage.repository.sections`, `backend.storage.repository.views`

- `class LibraryService` (30)
  - `async def page(self, feed: Feed, offset: int=0, limit: int=PAGE_SIZE) -> list[CardView]` (4)
  - `async def views_of(self, item_ids: list[int]) -> list[CardView]` (8)
  - `async def histogram(self, kind: Kind, filters: Filters) -> Histogram` (2)

### `backend/service/linking.py` — 126 строк

Привязка карточки к внешнему источнику: внешнее заполняет только пустое.

Зависит от: `backend.model`, `backend.service.card_parts`, `backend.service.genres`, `backend.storage.repository.credits`, `backend.storage.repository.library`

- `def merge_fields(existing: Item, incoming: Item) -> Item` (7)
- `def overwrite_fields(existing: Item, incoming: Item) -> Item` (14)
- `class Linker(CardParts)` (76)
  - `async def link(self, item_id: int, card: SourceCard, now: datetime, overwrite: bool=False) -> None` (24)
  - `async def _check_identifiers(self, item_id: int, card: SourceCard) -> None` (11)
  - `async def _fill_genres(self, item_id: int, card: SourceCard, overwrite: bool) -> None` (11)
  - `async def _fill(self, repository: CreditRepository, item_id: int, credits: tuple[Credit, ...], overwrite: bool) -> None` (12)
  - `async def _fill_poster(self, item_id: int, item: Item, overwrite: bool) -> None` (11)

### `backend/service/loading.py` — 106 строк

Кандидат превращается в карточку.

Зависит от: `backend.model`, `backend.service.asking`, `backend.service.cards`, `backend.service.posters`, `backend.sources.registry`, `backend.storage.repository.library`

- `class Loader` (80)
  - `def _catalog(self, source: Source, action: str)` (12)
  - `async def ensure(self, view: CardView) -> int | Missing | Refusal` (29)
  - `async def card_for_link(self, link: ExternalLink) -> SourceCard | Missing | Refusal` (20)

### `backend/service/posters.py` — 136 строк

Путь обложки от источника до хранилища.

Зависит от: `backend.model`, `backend.service.asking`, `backend.service.images`, `backend.sources.errors`, `backend.sources.http`, `backend.storage.posters`

- `class PosterService` (109)
  - `async def fetch(self, source: Source, url: str) -> bytes | None | Refusal` (7)
  - `async def _fetched(self, source: Source, url: str) -> bytes | None | Refusal` (16)
  - `def _picture(self, source: Source, url: str, response: httpx.Response) -> bytes | Refusal` (18)
  - `def _name(source: Source) -> str` (4)
  - `def _refuse(self, source: Source, detail: str) -> Refusal` (6)
  - `async def poster_for(self, item_id: int | None, source: Source, url: str, now: datetime) -> bytes | None | Refusal` (19)
  - `async def save(self, item_id: int, data: bytes, now: datetime) -> None` (2)
  - `async def delete(self, item_id: int) -> None` (4)
  - `async def has(self, item_id: int) -> bool` (4)
  - `async def store_upload(self, item_id: int, data: bytes, now: datetime) -> None` (5)
  - `async def aclose(self) -> None` (4)

### `backend/service/removal.py` — 23 строк

Удаление карточки из обоих файлов базы.

Зависит от: `backend.service.posters`, `backend.storage.repository.library`

- `async def remove_card(library: LibraryRepository, posters: PosterService, item_id: int) -> None` (17)

### `backend/service/search.py` — 119 строк

Что найдётся по запросу.

Зависит от: `backend.model`, `backend.service.asking`, `backend.sources.convert`, `backend.sources.registry`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.views`, `backend.unique`

- `def _weave(answers: list[list[SearchHit]]) -> list[SearchHit]` (16)
- `class SearchService` (55)
  - `async def local(self, kind: Kind, query: str) -> list[CardView]` (3)
  - `async def external(self, kind: Kind, query: str) -> ExternalSearch` (20)
  - `async def _to_views(self, hits: list[SearchHit]) -> list[CardView]` (14)
- `def _genres_of(hit: SearchHit, index: dict[GenreSource, dict[str, tuple[Genre, ...]]]) -> tuple[Genre, ...]` (11)

### `backend/service/series.py` — 62 строк

Перезапрос сериала по сроку годности.

Зависит от: `backend.model`, `backend.service.asking`, `backend.sources.registry`, `backend.storage.repository.library`

- `def _kept(fresh: int | None, stored: int | None) -> int | None` (4)
- `class SeriesRefresh` (38)
  - `async def refresh(self, item_id: int) -> None` (28)

### `backend/sources/build.py` — 45 строк

Шесть клиентов источников, поднятых из настроек.

Зависит от: `backend.config`, `backend.sources.gog.client`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`, `backend.sources.registry`, `backend.sources.steam.client`, `backend.sources.tmdb.client`

- `def build_sources(config: Config, transport: httpx.AsyncBaseTransport | None=None) -> Sources` (28)
  - `def http(name: str) -> SourceHttp` (7)

### `backend/sources/convert.py` — 85 строк

Куски чужого ответа, которые все источники переводят одинаково.

Зависит от: `backend.model`

- `def identifier(source: IdSource, value) -> tuple[ExternalId, ...]` (12)
- `def genres(space: GenreSource, rows: list[dict], key: str='id') -> tuple[tuple[GenreSource, str], ...]` (7)
- `def year(value: str | None) -> int | None` (5)
- `def companies(payload: dict) -> tuple[Credit, ...]` (11)
- `def from_search(source: Source, value: float | None, now: datetime) -> tuple[ExternalRating, ...]` (5)
- `def rating(source: RatingSource, value: float | int | None, now: datetime) -> tuple[ExternalRating, ...]` (10)

### `backend/sources/errors.py` — 59 строк

Как источник сообщает, что ответ не разобрался.

Зависит от: `backend.model`

- `def broken(source: str, error: Exception) -> Refusal` (4)
- `def refuse_code(source: str, status: int) -> Refusal` (5)
- `def is_json(response: httpx.Response) -> bool` (11)
- `def parsed(log: Logger, source: str, note: str, produce: Callable[[], T]) -> T | Refusal` (18)

### `backend/sources/gog/client.py` — 149 строк

Разговор с GOG по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.gog.parse`, `backend.sources.http`, `backend.sources.undocumented`

- `class GogClient` (127)
  - `def name(self) -> str` (4)
  - `async def _payload(self, query: str) -> dict | Refusal` (12)
  - `async def _catalog(self, query: str) -> list | Refusal` (6)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (5)
  - `async def _title(self, source_id: str) -> str | Outcome` (19)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (21)
  - `async def resolve_slug(self, slug: str) -> Outcome` (32)
  - `async def aclose(self) -> None` (2)

### `backend/sources/gog/parse.py` — 74 строк

Перевод ответов GOG в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `def _marks(row: dict) -> tuple[tuple[GenreSource, str], ...]` (8)
- `def parse_catalog(payload: dict) -> list[SourceCard]` (24)
- `def to_hit(card: SourceCard) -> SearchHit` (12)
- `def find_slug(payload: dict, slug: str) -> str | None` (8)

### `backend/sources/http.py` — 97 строк

Общая дверь в сеть для всех источников.

Зависит от: `backend.model`

- `class Breaker` (28)
  - `def is_open(self) -> bool` (7)
  - `def trip(self, delay: timedelta, reason: Reason=Reason.QUOTA) -> None` (7)
  - `def reason(self) -> Reason` (2)
- `class SourceHttp` (43)
  - `async def get(self, url: str, params: Mapping[str, object] | None=None, headers: Mapping[str, str] | None=None) -> httpx.Response | Refusal` (17)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/kinopoisk/client.py` — 45 строк

Кинопоиск снаружи: одно имя над двумя зеркалами.

Зависит от: `backend.model`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`

- `class KinopoiskClient` (32)
  - `def name(self) -> str` (4)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (11)
  - `async def aclose(self) -> None` (3)

### `backend/sources/ratings/kinopoisk/mirror.py` — 51 строк

Общее у двух зеркал Кинопоиска.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`

- `def refuse_quota(http: SourceHttp) -> Refusal` (3)
- `def refuse_rate(http: SourceHttp) -> Refusal` (5)
- `def refuse_key() -> Refusal` (3)
- `def refuse_code(status: int) -> Refusal` (3)
- `def answered(answer: Ratings) -> Outcome` (7)

### `backend/sources/ratings/kinopoisk/parse.py` — 50 строк

Перевод ответов обоих зеркал Кинопоиска в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `def _rating(value, now: datetime) -> tuple[ExternalRating, ...]` (8)
- `def _first_row(payload: dict, key: str) -> dict | None` (8)
- `def parse_poiskkino(payload: dict) -> Ratings` (10)
- `def parse_unofficial(payload: dict) -> Ratings` (10)

### `backend/sources/ratings/kinopoisk/poiskkino.py` — 81 строк

Основное зеркало Кинопоиска.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.parse`

- `class PoiskkinoClient` (55)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (9)
  - `def _verdict(self, response: httpx.Response) -> Outcome` (16)
  - `def _absent(self, response: httpx.Response) -> Outcome` (12)
  - `def _answer(self, response: httpx.Response) -> Outcome` (3)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/kinopoisk/unofficial.py` — 58 строк

Запасное зеркало Кинопоиска.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.parse`

- `class UnofficialClient` (32)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (9)
  - `def _verdict(self, response: httpx.Response) -> Outcome` (14)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/mdblist/client.py` — 95 строк

Разговор с MDBList по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.mdblist.parse`

- `def _retry_after(response: httpx.Response) -> timedelta | None` (3)
- `class MdbListClient` (68)
  - `def name(self) -> str` (4)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (8)
  - `def _verdict(self, response: httpx.Response) -> Outcome` (21)
  - `def _denied(self, response: httpx.Response) -> Refusal` (14)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/mdblist/parse.py` — 35 строк

Перевод ответов MDBList в наши типы.

Зависит от: `backend.model`

- `def parse_ratings(payload: dict) -> Ratings` (18)

### `backend/sources/ratings/omdb/client.py` — 98 строк

Разговор с OMDB по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.omdb.parse`

- `def until_midnight(now: datetime) -> timedelta` (7)
- `class OmdbClient` (71)
  - `def name(self) -> str` (4)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (24)
  - `def _answer(self, payload: dict) -> Outcome` (8)
  - `def _denied(self, payload: dict) -> Refusal` (17)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/omdb/parse.py` — 46 строк

Перевод ответов OMDB в наши типы.

Зависит от: `backend.model`

- `def _number(raw: str | None) -> float | None` (10)
- `def parse_ratings(payload: dict) -> Ratings` (21)

### `backend/sources/registry.py` — 59 строк

Кто отвечает за какой тип содержимого.

Зависит от: `backend.model`, `backend.sources.gog.client`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`, `backend.sources.steam.client`, `backend.sources.tmdb.client`

- `class Sources` (41)
  - `def catalog_for(self, kind: Kind) -> list` (6)
  - `def client_for(self, source: Source)` (8)
  - `def rating_sources(self, kind: Kind) -> list` (6)
  - `async def aclose(self) -> None` (3)

### `backend/sources/steam/client.py` — 134 строк

Разговор со Steam по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.steam.parse`, `backend.sources.undocumented`

- `class SteamClient` (106)
  - `def name(self) -> str` (4)
  - `async def _asked(self, url: str, params: dict | None=None) -> httpx.Response | Refusal` (13)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (10)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (37)
  - `async def _tags(self, source_id: str) -> tuple[tuple[GenreSource, str], ...]` (27)
  - `async def aclose(self) -> None` (2)

### `backend/sources/steam/parse.py` — 85 строк

Перевод ответов Steam в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `def poster_url(appid: str) -> str` (4)
- `def parse_search(payload: list[dict]) -> list[SearchHit]` (11)
- `def _year(value: str | None) -> int | None` (7)
- `def _metascore(data: dict, now: datetime) -> tuple[ExternalRating, ...]` (5)
- `def parse_card(data: dict) -> SourceCard` (21)
- `def parse_tags(payload: dict) -> tuple[tuple[GenreSource, str], ...]` (5)

### `backend/sources/tmdb/client.py` — 122 строк

Разговор с TMDB по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.tmdb.parse`

- `def classify(response: httpx.Response) -> Missing | Refusal | None` (20)
- `class TmdbClient` (71)
  - `def name(self) -> str` (4)
  - `def _params(self, **extra: object) -> dict` (2)
  - `def _verdict(self, response: httpx.Response) -> Missing | Refusal | None` (7)
  - `async def _asked(self, url: str, **extra: object) -> httpx.Response | Missing | Refusal` (12)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (7)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (10)
  - `async def series_counts(self, source_id: str) -> Outcome` (8)
  - `async def aclose(self) -> None` (2)

### `backend/sources/tmdb/parse.py` — 190 строк

Перевод ответов TMDB в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `class Incomplete(ValueError)` (9)
- `def _released(value: str | None) -> date | None` (7)
- `def _poster(payload: dict) -> str` (3)
- `def _genres(payload: dict) -> tuple[tuple[GenreSource, str], ...]` (2)
- `def _own_rating(payload: dict, now: datetime) -> tuple[ExternalRating, ...]` (2)
- `def _person(row: dict, role: PersonRole, position: int | None=None) -> Credit` (10)
- `def _cast(rows: list[dict]) -> list[Credit]` (5)
- `def _required(payload: dict, block: str) -> dict` (9)
- `def _item(payload: dict, kind: Kind, now: datetime, **extra) -> Item` (20)
- `def parse_search(payload: dict, kind: Kind) -> list[SearchHit]` (23)
- `def parse_movie(payload: dict) -> SourceCard` (18)
- `def parse_series_counts(payload: dict) -> SeriesCounts` (7)
- `def parse_series(payload: dict) -> SourceCard` (19)

### `backend/sources/undocumented.py` — 23 строк

Отказ источника, который своих лимитов не объявляет.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`

- `def refuse_undocumented(http: SourceHttp, status: int) -> Refusal` (9)

### `backend/storage/entity.py` — 34 строк

Чем человек отличается от студии в схеме.

Зависит от: `backend.model`, `backend.storage.tables`

- `class Entity` (14)
  - `def link(self) -> Column` (4)

### `backend/storage/posters.py` — 98 строк

Второй файл базы: картинка по карточке.

Зависит от: `backend.storage.session`, `backend.storage.statements`

- `class NotOpened(Exception)` (5)
- `class PosterStore` (59)
  - `async def open(self) -> None` (7)
  - `async def close(self) -> None` (4)
  - `def _opened(self) -> AsyncEngine` (4)
  - `async def _read(self, statement: Executable)` (3)
  - `async def _write(self, statement: Executable) -> None` (3)
  - `async def put(self, item_id: int, data: bytes, now: datetime) -> None` (8)
  - `async def get(self, item_id: int) -> bytes | None` (5)
  - `async def has(self, item_id: int) -> bool` (5)
  - `async def delete(self, item_id: int) -> None` (2)

### `backend/storage/repository/base.py` — 77 строк

Общее у репозиториев: сессия и способы с ней обойтись.

Зависит от: —

- `class Repository` (68)
  - `async def _row(self, statement: Executable) -> Row | None` (3)
  - `async def _rows(self, statement: Executable) -> list[Row]` (3)
  - `async def _mapped(self, statement: Executable, make: Callable[[Row], object])` (3)
  - `async def _maybe(self, statement: Executable, make: Callable[[Row], object])` (6)
  - `async def _has_item(self, table: Table, item_id: int) -> bool` (8)
  - `async def _created(self, statement: Executable, taken: Exception) -> int` (15)
  - `async def _written(self, statement: Executable, taken: Exception) -> None` (7)
  - `async def _run(self, *statements: Executable) -> None` (7)

### `backend/storage/repository/credits.py` — 230 строк

Один репозиторий на людей и на студий — различает их только описатель.

Зависит от: `backend.model`, `backend.storage.entity`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.session`, `backend.storage.statements`, `backend.storage.tables`

- `class IdentityTaken(Exception)` (2)
- `class CreditRepository(Repository)` (189)
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
  - `async def items_of(self, entity_id: int, limit: int, offset: int) -> list[int]` (20)
  - `async def suggest(self, name: str, limit: int=10) -> list[Suggestion]` (15)
  - `def _linked(self, entity_id: int) -> Select` (12)
  - `async def _hint(self, entity_id: int) -> tuple[str, int | None]` (21)
- `def people(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository` (2)
- `def companies(sessions: async_sessionmaker[AsyncSession]) -> CreditRepository` (2)

### `backend/storage/repository/external.py` — 95 строк

Чем карточка известна чужим источникам.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.statements`, `backend.storage.tables`

- `class ExternalIdTaken(Exception)` (2)
- `class ExternalIdsRepository(Repository)` (31)
  - `async def put(self, item_id: int, external: ExternalId) -> None` (13)
  - `async def ids_of(self, item_id: int) -> list[ExternalId]` (7)
  - `async def find_item(self, source: IdSource, value: str) -> int | None` (8)
- `class ExternalRatingsRepository(Repository)` (39)
  - `async def record(self, item_id: int, rating: ExternalRating) -> None` (13)
  - `async def ratings_of(self, item_id: int) -> list[ExternalRating]` (7)
  - `async def stale_sources(self, item_id: int, wanted: list[RatingSource], now: datetime) -> list[RatingSource]` (16)

### `backend/storage/repository/genres.py` — 89 строк

Жанры в базе: свои, и чужие метки, ведущие к ним.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.statements`, `backend.storage.tables`, `backend.unique`

- `class GenresRepository(Repository)` (74)
  - `async def resolve(self, source: GenreSource, ext_ids: list[str]) -> list[int]` (20)
  - `async def index(self, source: GenreSource) -> dict[str, tuple[Genre, ...]]` (17)
  - `async def set_for_item(self, item_id: int, genre_ids: list[int]) -> None` (14)
  - `async def genres_of(self, item_id: int) -> list[Genre]` (8)
  - `async def list_for_kind(self, kind: GenreKind) -> list[Genre]` (10)

### `backend/storage/repository/library.py` — 183 строк

Карточки библиотеки.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.session`, `backend.storage.tables`

- `class ItemExists(Exception)` (2)
- `def _values(item: Item) -> dict` (6)
- `class LibraryRepository(Repository)` (148)
  - `async def _one(self, statement: Select) -> Item | None` (2)
  - `async def create(self, item: Item) -> int` (5)
  - `async def get(self, item_id: int) -> Item | None` (2)
  - `async def find_by_source(self, source: Source, source_id: str) -> Item | None` (7)
  - `async def list_by_kind(self, kind: Kind, limit: int, offset: int) -> list[Item]` (18)
  - `async def find_by_title(self, kind: Kind, title: str) -> list[Item]` (16)
  - `async def search(self, kind: Kind, query: str, limit: int) -> list[int]` (23)
  - `async def deletion_summary(self, item_id: int) -> dict[str, int | bool]` (12)
  - `async def delete(self, item_id: int) -> None` (5)
  - `async def refresh_series_counts(self, item_id: int, seasons_count: int | None, episodes_count: int | None, now: datetime) -> None` (14)
  - `async def replace_fields(self, item_id: int, item: Item) -> None` (8)
  - `async def link(self, item_id: int, source: Source, source_id: str, now: datetime) -> None` (15)
  - `async def unlink(self, item_id: int) -> None` (8)

### `backend/storage/repository/ratings.py` — 60 строк

Моя оценка карточки.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.statements`, `backend.storage.tables`

- `class RatingsRepository(Repository)` (46)
  - `async def _write(self, item_id: int, values: dict, now: datetime) -> None` (11)
  - `async def set_score(self, item_id: int, score: float | None, now: datetime) -> None` (3)
  - `async def set_aspects(self, item_id: int, visual: int | None, narrative: int | None, gameplay: int | None, now: datetime) -> float | None` (16)
  - `async def set_review(self, item_id: int, review: str, now: datetime) -> None` (2)
  - `async def get(self, item_id: int) -> Rating | None` (5)
  - `async def clear(self, item_id: int) -> None` (3)

### `backend/storage/repository/sections.py` — 153 строк

Вопросы к отфильтрованному набору раздела.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.session`, `backend.storage.tables`

- `def _carrying(link: Table, key: Column, ids: tuple[int, ...]) -> Select` (4)
- `def _included(query: Select, filters: Filters) -> Select` (13)
- `def _excluded(query: Select, filters: Filters) -> Select` (23)
- `class SectionsRepository(Repository)` (72)
  - `async def ids(self, feed: Feed, limit: int, offset: int) -> list[int]` (12)
  - `async def histogram(self, kind: Kind, filters: Filters) -> Histogram` (34)
  - `def _narrow(self, query: Select, section: Section, kind: Kind, filters: Filters) -> Select` (16)

### `backend/storage/repository/tags.py` — 106 строк

Мои теги в базе.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.tables`

- `class WrongTagKind(Exception)` (2)
- `class TagExists(Exception)` (2)
- `class TagsRepository(Repository)` (85)
  - `async def create(self, kind: Kind, name: str) -> int` (17)
  - `async def list_for_kind(self, kind: Kind) -> list[Tag]` (7)
  - `async def reorder(self, kind: Kind, tag_ids: list[int]) -> None` (10)
  - `async def rename(self, tag_id: int, name: str) -> None` (6)
  - `async def delete(self, tag_id: int) -> None` (2)
  - `async def assign(self, item_id: int, tag_id: int) -> None` (20)
  - `async def unassign(self, item_id: int, tag_id: int) -> None` (7)
  - `async def tags_of(self, item_id: int) -> list[Tag]` (8)

### `backend/storage/repository/views.py` — 181 строк

Пачечное чтение карточек для показа.

Зависит от: `backend.model`, `backend.storage.entity`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.tables`

- `class ViewsRepository(Repository)` (148)
  - `async def views_for(self, item_ids: list[int]) -> dict[int, CardView]` (5)
  - `async def in_order(self, item_ids: list[int]) -> list[CardView]` (9)
  - `async def _fetch_all(self, session: AsyncSession, item_ids: list[int]) -> dict[int, CardView]` (35)
  - `async def _genres(self, session, item_ids)` (9)
  - `async def _tags(self, session, item_ids)` (9)
  - `async def _credits(self, session, item_ids, entity: Entity)` (20)
  - `async def _by_source(self, session, table, item_ids, make)` (19)
  - `async def _external(self, session, item_ids)` (3)
  - `async def _identifiers(self, session, item_ids)` (3)
  - `async def _ratings(self, session, item_ids)` (5)
  - `async def _wishlist(self, session, item_ids)` (6)
  - `async def _read(self, session, statement)` (4)
  - `def _by_card(rows, make)` (4)

### `backend/storage/repository/wishlist.py` — 37 строк

Список запланированного.

Зависит от: `backend.storage.repository.base`, `backend.storage.statements`, `backend.storage.tables`

- `class WishlistRepository(Repository)` (25)
  - `async def add(self, item_id: int, now: datetime) -> None` (7)
  - `async def remove(self, item_id: int) -> None` (2)
  - `async def contains(self, item_id: int) -> bool` (2)
  - `async def list_ids(self, limit: int, offset: int) -> list[int]` (10)

### `backend/storage/rows.py` — 116 строк

Строки базы в типы границы слоёв.

Зависит от: `backend.model`, `backend.storage.entity`

- `def to_item(row: Row) -> Item` (20)
- `def to_genre(row: Row) -> Genre` (2)
- `def to_external_id(row: Row) -> ExternalId` (2)
- `def to_external_rating(row: Row) -> ExternalRating` (4)
- `def to_rating(row: Row) -> Rating` (11)
- `def to_tag(row: Row) -> Tag` (7)
- `def grouped(rows, column: str, make: Callable[[Row], object]) -> defaultdict[object, list]` (12)
- `def to_credit(row: Row, entity: Entity) -> Credit` (15)

### `backend/storage/session.py` — 55 строк

Доступ к основной базе.

Зависит от: —

- `def fold(value: str | None) -> str | None` (5)
- `def folded(column: ColumnElement) -> ColumnElement[str]` (4)
- `def prepare_connection(dbapi_connection) -> None` (14)
- `def create_engine(path: Path) -> AsyncEngine` (9)
  - `def prepare(dbapi_connection, _record)` (2)
- `def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]` (2)

### `backend/storage/statements.py` — 28 строк

Операторы над таблицами, которые в проекте собираются одинаково.

Зависит от: —

- `def clearing(table: Table, item_id: int) -> Delete` (6)
- `def upserting(table: Table, values: dict, key: list[Column]) -> Insert` (14)

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


### `backend/unique.py` — 16 строк

Снятие повторов с сохранением порядка.

Зависит от: —

- `def unique(items: Iterable[T]) -> list[T]` (11)

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

### `migrations/versions/0002_genres.py` — 401 строк ⚠ подошёл к 300

Справочник жанров и соответствия к нему.

Зависит от: —

- `def upgrade() -> None` (29)
- `def downgrade() -> None` (5)

## scripts — 2 модулей

### `scripts/collect_game_genres.py` — 80 строк

Разовый сбор игровых жанров: справочника в документации нет ни у Steam, ни у

Зависит от: `backend.sources.http`

- `def example_appids(menu: list[dict]) -> list[int]` (8)
- `async def app_genres(client: httpx.AsyncClient, appid: int) -> list[dict]` (11)
- `async def steam_genres(client: httpx.AsyncClient) -> dict[str, str]` (11)
- `async def gog_genres(client: httpx.AsyncClient) -> dict[str, str]` (7)
- `async def main() -> None` (7)

### `scripts/record_fixtures.py` — 207 строк

Разовая запись живых ответов источников в tests/fixtures/.

Зависит от: `backend.config`, `backend.sources.http`

- `def save(source: str, case: str, response: httpx.Response) -> None` (23)
- `async def record_tmdb(client: httpx.AsyncClient, key: str) -> None` (24)
- `async def record_steam(client: httpx.AsyncClient) -> None` (35)
  - `def ask(ids: list[dict]) -> str` (7)
- `async def record_gog(client: httpx.AsyncClient) -> None` (18)
- `async def record_mdblist(client: httpx.AsyncClient, key: str) -> None` (11)
- `async def record_omdb(client: httpx.AsyncClient, key: str) -> None` (13)
- `async def record_kinopoisk_unofficial(client: httpx.AsyncClient, key: str) -> None` (13)
- `async def main() -> None` (20)

## tests — 60 модулей

### `tests/alembic_runner.py` — 21 строк

Запуск миграций из теста.

Зависит от: —

- `def alembic(db_path: Path, *command: str) -> None` (10)

### `tests/backend/sources/conftest.py` — 67 строк

Записанные ответы источников: живьём тесты не ходят никуда.

Зависит от: —

- `def _load(relative: str)` (4)
- `def _meta(relative: str) -> dict` (3)
- `def fixture()` (3)
- `def meta()` (2)
- `def replay()` (33)
  - `def build(*relatives: str) -> httpx.MockTransport` (21)
    - `def handler(request: httpx.Request) -> httpx.Response` (7)

### `tests/backend/sources/test_convert.py` — 124 строк

Общее у разборов: перевод чужих кусков ответа в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`, `tests.conftest`

Тестов: 14


### `tests/backend/sources/test_gog.py` — 369 строк ⚠ подошёл к 300

GOG: поиск не умеет отвечать «не найдено», и отрицательный факт отсюда не

Зависит от: `backend.model`, `backend.sources.gog.client`, `backend.sources.gog.parse`, `backend.sources.http`, `tests.conftest`

Тестов: 26

- `def answering(body) -> SourceHttp` (3)

### `tests/backend/sources/test_gog_slug.py` — 147 строк

Слаг из адреса GOG в номер каталога.

Зависит от: `backend.model`, `backend.sources.gog.client`, `backend.sources.gog.parse`, `backend.sources.http`

Тестов: 14

- `def client(handler) -> GogClient` (2)

### `tests/backend/sources/test_http.py` — 393 строк ⚠ подошёл к 300

Общая дверь в сеть: заголовок, таймауты и предохранитель.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.undocumented`, `tests.conftest`

Тестов: 24


### `tests/backend/sources/test_kinopoisk.py` — 453 строк ⚠ подошёл к 300

Кинопоиск: два зеркала под одним именем, и телу здесь верить нельзя.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`, `tests.conftest`

Тестов: 29

- `def primary(transport) -> PoiskkinoClient` (2)
- `def fallback(transport) -> UnofficialClient` (2)

### `tests/backend/sources/test_mdblist.py` — 237 строк

MDBList: квота, битый ключ и чужой периметр — три разные беды.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.mdblist.parse`, `tests.conftest`

Тестов: 20

- `async def ask(transport, kind=Kind.MOVIE)` (5)

### `tests/backend/sources/test_omdb.py` — 300 строк

OMDB: единственный источник, у которого отказ приходит под кодом 401, а

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.ratings.omdb.client`, `backend.sources.ratings.omdb.parse`, `tests.conftest`

Тестов: 28

- `async def ask(transport)` (5)

### `tests/backend/sources/test_rating_provides.py` — 71 строк

`PROVIDES` против того, что клиент действительно разбирает.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`

Тестов: 2

- `def mdblist(transport) -> MdbListClient` (2)
- `def omdb(transport) -> OmdbClient` (2)
- `def kinopoisk(transport) -> KinopoiskClient` (7)
- `async def brought_by(build, recorded, replay) -> tuple[set, set]` (6)

### `tests/backend/sources/test_registry.py` — 265 строк

Реестр держится на том, что контракт у всех клиентов один.

Зависит от: `backend.config`, `backend.model`, `backend.sources.build`, `backend.sources.gog.client`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`, `backend.sources.steam.client`, `backend.sources.tmdb.client`, `tests.conftest`

Тестов: 14

- `def sources()` (4)
- `def keyed()` (12)

### `tests/backend/sources/test_steam.py` — 356 строк ⚠ подошёл к 300

Steam: отсутствие игры приходит под кодом 200, а теги — вторым запросом.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.steam.client`, `backend.sources.steam.parse`

Тестов: 26

- `def block_of(payload: dict) -> dict` (2)

### `tests/backend/sources/test_tmdb_card.py` — 418 строк ⚠ подошёл к 300

Второй круг загрузки: карточка, которую уже можно записать.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.tmdb.client`, `backend.sources.tmdb.parse`

Тестов: 32


### `tests/backend/sources/test_tmdb_failures.py` — 202 строк

Отказ TMDB отличается от «такого у меня нет» — и то, и другое от успеха.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.tmdb.client`, `tests.conftest`

Тестов: 15

- `async def ask(transport: httpx.MockTransport)` (5)

### `tests/backend/sources/test_tmdb_search.py` — 182 строк

Первый круг загрузки: кандидат выдачи — ещё не карточка.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.tmdb.client`, `backend.sources.tmdb.parse`

Тестов: 15


### `tests/backend/test_asking.py` — 73 строк

Что `answered` делает с сорвавшимся запросом и что — с отменой.

Зависит от: `backend.model`, `backend.service.asking`, `tests.conftest`

Тестов: 6

- `async def broken_request()` (2)
- `async def cancelled_request()` (2)
- `async def good_request()` (2)

### `tests/backend/test_by_credit.py` — 146 строк

Всё с этим человеком и с этой студией.

Зависит от: `backend.model`, `backend.service.library`, `backend.storage.repository.credits`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 10


### `tests/backend/test_card_writer.py` — 399 строк ⚠ подошёл к 300

Запись карточки источника в базу целиком — или ничего.

Зависит от: `backend.model`, `backend.service.cards`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 22

- `def source_card(**overrides) -> SourceCard` (17)
- `def game_card(source_id: str='292030', **overrides) -> SourceCard` (10)
- `def another_movie(source_id: str, **overrides) -> SourceCard` (9)
- `async def build(sessions, engine, posters, transport=None) -> CardWriter` (9)
- `async def writer(sessions, engine, posters)` (4)

### `tests/backend/test_config.py` — 68 строк

Чтение настроек из окружения и путей к файлам данных.

Зависит от: `backend.config`

Тестов: 9


### `tests/backend/test_cover_reads.py` — 93 строк

Обложка видимой карточки: лежащая отдаётся, недостающая скачивается.

Зависит от: `backend.model`, `tests.conftest`

Тестов: 7

- `async def covers(posters)` (5)

### `tests/backend/test_credits.py` — 315 строк ⚠ подошёл к 300

Люди и студии: одна реализация на две сущности, и различает их идентичность.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.library`

Тестов: 25


### `tests/backend/test_delete.py` — 156 строк

Удаление карточки из двух файлов базы и что пропадает вместе с ней.

Зависит от: `backend.model`, `backend.service.posters`, `backend.service.removal`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 9

- `async def service(posters)` (8)
- `async def furnished(sessions, posters, item_id: int, tag: str='пересмотреть') -> int` (9)

### `tests/backend/test_enrich.py` — 447 строк ⚠ подошёл к 300

Третий круг: оценки агрегаторов и сроки их годности.

Зависит от: `backend.model`, `backend.service.enrich`, `backend.storage.repository.external`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 24

- `class FakeRatings(FakeClient)` (11)
  - `async def ratings(self, imdb_id: str, _kind: Kind)` (3)
- `class Breaking(FakeRatings)` (7)
  - `async def ratings(self, imdb_id: str, _kind: Kind)` (3)
- `async def item_id(sessions)` (8)
- `async def enrich(sessions)` (12)
  - `def build(*clients) -> Enricher` (7)
- `def found(*pairs) -> Found` (4)
- `async def stored_ratings(sessions, item_id) -> dict` (3)

### `tests/backend/test_external_ids.py` — 120 строк

Внешние идентификаторы: всё, что не основной источник карточки.

Зависит от: `backend.model`, `backend.storage.repository.external`, `backend.storage.repository.library`

Тестов: 8


### `tests/backend/test_external_ratings.py` — 210 строк

Оценки агрегаторов: три состояния и сроки годности.

Зависит от: `backend.model`, `backend.storage.repository.external`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 13


### `tests/backend/test_feed.py` — 132 строк

Страница раздела и перерисовка одной карточки.

Зависит от: `backend.model`, `backend.service.library`, `backend.storage.repository.tags`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 9

- `async def feed(sessions, sections)` (2)
- `class Forgetful(ViewsRepository)` (13)
  - `async def views_for(self, item_ids: list[int]) -> dict` (4)

### `tests/backend/test_genre_reference.py` — 241 строк

Справочник жанров из миграции против записанного эталона.

Зависит от: `tests.alembic_runner`

Тестов: 13

- `def named(connection, source: str, ext_id: str) -> set[str]` (10)
- `def counted(connection, where: str) -> int` (4)
- `def declared_in_migration() -> dict[str, dict[str, list[str]]]` (4)
- `def differences(reference: dict, declared: dict) -> list[str]` (8)

### `tests/backend/test_genre_resolution.py` — 78 строк

Разрешение чужих меток жанров: то, что видно в самом списке наших номеров.

Зависит от: `backend.model`, `backend.service.genres`, `backend.storage.repository.genres`, `tests.conftest`

Тестов: 5

- `async def genres(engine, sessions)` (3)

### `tests/backend/test_genres.py` — 159 строк

Перевод чужих меток в наши жанры и запись их карточке.

Зависит от: `backend.model`, `backend.storage.repository.genres`, `tests.conftest`

Тестов: 14


### `tests/backend/test_histogram.py` — 199 строк

Гистограмма своих оценок по отфильтрованному набору.

Зависит от: `backend.model`, `backend.storage.repository.genres`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 17

- `async def columns(sections, kind: Kind=Kind.MOVIE, **filters) -> dict[int, int]` (3)

### `tests/backend/test_images.py` — 135 строк

Обрезка залитой руками картинки до формы обложки.

Зависит от: `backend.service.images`, `tests.conftest`

Тестов: 15

- `def painted(size: tuple[int, int], band: tuple[int, int, int, int]) -> bytes` (7)
- `def size_of(data: bytes) -> tuple[int, int]` (2)
- `def red_box(data: bytes) -> tuple[int, int, int, int] | None` (6)

### `tests/backend/test_layers.py` — 105 строк

Граница слоёв: кто кого имеет право импортировать.

Зависит от: —

Тестов: 4

- `def imported_modules(path: Path)` (10)
- `def imported_roots(path: Path)` (4)
- `def python_files(package: str) -> list[Path]` (7)
- `def offenders(package: str, banned: set[str]) -> list[str]` (7)

### `tests/backend/test_library.py` — 360 строк ⚠ подошёл к 300

Репозиторий библиотеки: карточка, окна и поиск по названию.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 24

- `def make_item(**overrides) -> Item` (4)
- `async def in_both_stores(repository) -> tuple[int, int]` (15)

### `tests/backend/test_link_loading.py` — 148 строк

Вставленная ссылка в карточку источника, готовую для привязки.

Зависит от: `backend.model`, `backend.service.loading`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 7

- `def source_card(source: Source, source_id: str) -> SourceCard` (4)
- `class FakeCatalogWithSlug(FakeCatalog)` (12)
  - `async def resolve_slug(self, slug: str)` (3)
- `async def loader(sessions)` (6)
  - `def build(client) -> Loader` (3)

### `tests/backend/test_linking.py` — 411 строк ⚠ подошёл к 300

Привязка ручной карточки к внешней базе и правила слияния.

Зависит от: `backend.model`, `backend.service.linking`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 27

- `def incoming(**overrides) -> SourceCard` (12)
- `def mine(**fields) -> Item` (4)
- `async def linker(sessions, engine, posters)` (5)
- `async def manual_card(sessions, **fields) -> int` (5)

### `tests/backend/test_links.py` — 136 строк

Разбор вставленной ссылки на карточку источника.

Зависит от: `backend.model`, `backend.model.link`

Тестов: 14


### `tests/backend/test_loading.py` — 321 строк ⚠ подошёл к 300

Три круга загрузки: кандидат становится карточкой в базе.

Зависит от: `backend.model`, `backend.service.cards`, `backend.service.loading`, `backend.service.posters`, `backend.storage.repository.library`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 16

- `def candidate(source_id='157336', poster=SEARCH_COVER) -> CardView` (6)
- `def source_card(source_id='157336', poster=DETAIL_COVER) -> SourceCard` (7)
- `class Rig` (8)
- `async def loader(sessions, posters)` (19)
  - `def build(outcome, poster_status: int=200) -> Rig` (13)

### `tests/backend/test_manual_cards.py` — 213 строк

Ручная карточка: заведение, правка и отвязка от источника.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `tests.conftest`

Тестов: 14


### `tests/backend/test_migrations.py` — 126 строк

Схема из миграций против схемы из объявлений.

Зависит от: `backend.storage.tables`, `tests.alembic_runner`, `tests.conftest`

Тестов: 4

- `def declared(db_path: Path) -> None` (5)
- `def table_shape(inspector, name: str) -> dict` (29)
- `def shape(db_path: Path) -> dict` (12)
- `def stamped(db_path: Path) -> list[str]` (8)

### `tests/backend/test_model.py` — 114 строк

Типы границы слоёв: их поля, значения и неизменность.

Зависит от: `backend.model`, `tests.conftest`

Тестов: 9


### `tests/backend/test_offline.py` — 302 строк ⚠ подошёл к 300

Главное обещание приложения: без сети работает всё, кроме поиска чужого.

Зависит от: `backend.app`, `backend.config`, `backend.model`, `backend.storage.posters`, `backend.storage.repository.external`, `backend.storage.session`, `backend.storage.tables`, `tests.conftest`

Тестов: 18

- `def mine(title: str, **fields)` (4)
- `async def assemble(tmp_path)` (9)
- `async def offline(tmp_path)` (4)

### `tests/backend/test_outcome.py` — 57 строк

Три исхода запроса к источнику: что считается ответом, что обязательно, что

Зависит от: `backend.model`

Тестов: 6


### `tests/backend/test_poster_service.py` — 226 строк

Путь обложки от источника до хранилища.

Зависит от: `backend.model`, `backend.service.images`, `backend.service.posters`, `backend.sources.http`, `backend.storage.posters`, `tests.conftest`

Тестов: 17

- `async def service(posters)` (4)

### `tests/backend/test_posters.py` — 181 строк

Хранилище постеров вторым файлом базы.

Зависит от: `backend.storage.posters`, `backend.storage.session`, `tests.conftest`

Тестов: 15


### `tests/backend/test_ratings.py` — 188 строк

Своя оценка карточки и её пересчёт.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.tables`, `tests.conftest`

Тестов: 16


### `tests/backend/test_search.py` — 447 строк ⚠ подошёл к 300

Поиск по чужим базам: выдача, отказы и склейка со своей.

Зависит от: `backend.model`, `backend.service.search`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 31

- `class FakeSearch(FakeClient)` (9)
  - `async def search(self, query: str, kind: Kind)` (5)
- `def local_view(source_id='157336', title='Интерстеллар') -> CardView` (3)
- `async def service(sessions)` (8)
  - `def build(*clients) -> SearchService` (6)

### `tests/backend/test_search_local.py` — 153 строк

Поиск по своей базе — единственный, который работает без сети.

Зависит от: `backend.model`, `backend.service.search`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.tags`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 12

- `async def search(sessions)` (5)

### `tests/backend/test_sections.py` — 426 строк ⚠ подошёл к 300

Запросы разделов: фильтры, сортировки и порции.

Зависит от: `backend.model`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 23

- `async def library(sessions)` (2)

### `tests/backend/test_series_refresh.py` — 196 строк

Дешёвый перезапрос сериала: сезоны и серии по сроку.

Зависит от: `backend.model`, `backend.service.series`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 12

- `class FakeTmdb(FakeClient)` (6)
  - `async def series_counts(self, source_id: str)` (3)
- `def series(synced_at, seasons=1, episodes=12) -> Item` (3)
- `async def refresher(sessions)` (11)
  - `def build(outcome)` (5)

### `tests/backend/test_session.py` — 111 строк

Движок базы, сессии и настройки соединения.

Зависит от: `backend.storage.session`

Тестов: 8

- `async def bare_engine(tmp_path)` (4)
- `class Base(DeclarativeBase)` (2)
- `class Note(Base)` (5)

### `tests/backend/test_suggestions.py` — 204 строк

Подсказка при вводе имени: тёзок различают по узнаваемой карточке.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.ratings`, `backend.storage.repository.wishlist`, `backend.storage.tables`, `tests.conftest`

Тестов: 14

- `async def person_with(sessions, name: str, item_ids: list[int]) -> int` (6)

### `tests/backend/test_tables.py` — 205 строк

Объявленная схема: таблицы, индексы, ключи и ограничения.

Зависит от: `backend.storage.tables`, `tests.conftest`

Тестов: 10

- `async def counted(engine, table_name: str) -> int` (5)
- `async def put(engine, table_name: str, **values) -> None` (4)

### `tests/backend/test_tags.py` — 330 строк ⚠ подошёл к 300

Свои теги: заведение, привязка к карточке и порядок.

Зависит от: `backend.model`, `backend.storage.repository.tags`

Тестов: 26


### `tests/backend/test_view_types.py` — 110 строк

Карточка для показа: сборка из кандидата и из строки базы.

Зависит от: `backend.model`, `tests.conftest`

Тестов: 9


### `tests/backend/test_views.py` — 356 строк ⚠ подошёл к 300

Пачечное чтение страницы: девять запросов на любое число карточек.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.views`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 19

- `async def item_id(sessions)` (4)

### `tests/backend/test_wishlist.py` — 119 строк

Список запланированного: закладка, порядок и порции.

Зависит от: `backend.storage.repository.wishlist`, `backend.storage.tables`, `tests.conftest`

Тестов: 10


### `tests/builders.py` — 74 строк

Строители данных для тестов: карточки, кандидаты, картинки.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`

- `def an_item(source_id: str, title: str, **fields) -> Item` (15)
- `async def rated(sessions, source_id: str, score: float | None, **fields) -> int` (12)
- `def picture(width: int, height: int, fmt: str='PNG') -> bytes` (6)
- `def hit(source_id: str='157336', title: str='Интерстеллар', **fields) -> SearchHit` (8)

### `tests/conftest.py` — 239 строк

Фикстуры тестов и поверхность общего.

Зависит от: `backend.model`, `backend.storage.posters`, `backend.storage.repository.library`, `backend.storage.repository.sections`, `backend.storage.session`, `backend.storage.tables`, `tests.alembic_runner`, `tests.builders`, `tests.fakes`, `tests.wiring`

Отдаёт наружу: `LATER`, `MOMENT`, `PICTURE`, `POSTER`, `POSTER_SOURCES`, `FakeCatalog`, `FakeClient`, `FakeClock`, `FakeSources`, `an_item`, `capture`, `card_parts`, `hit`, `picture`, `poster_service`, `rated`, `responding`, `unreachable`

- `def ours(caplog) -> list[str]` (8)
- `async def film_genres(engine) -> None` (11)
- `async def seed(engine, *statements: str) -> None` (7)
- `def migrated(tmp_path)` (16)
- `async def engine(tmp_path)` (8)
- `async def sections(sessions)` (3)
- `async def reference(engine)` (20)
- `async def sessions(engine)` (4)
- `async def posters(tmp_path)` (6)
- `async def card(sessions)` (11)
  - `async def make(kind: Kind=Kind.MOVIE, source_id: str='1', title: str='карточка') -> int` (5)
- `async def stored(engine)` (12)
  - `async def put(name: str, **values) -> int` (7)

### `tests/fakes.py` — 117 строк

Подставные заменители внешнего мира: клиенты источников, транспорты, часы.

Зависит от: `backend.model`

- `class FakeClient` (12)
- `class FakeCatalog(FakeClient)` (7)
  - `async def card(self, source_id: str, kind: Kind)` (3)
- `class FakeSources` (23)
  - `def catalog_for(self, _kind: Kind) -> list` (4)
  - `def client_for(self, _source: Source)` (4)
  - `def rating_sources(self, kind: Kind) -> list` (5)
- `class FakeClock` (12)
  - `def __call__(self) -> datetime` (2)
  - `def advance(self, delta: timedelta) -> None` (2)
- `def responding(status: int=200, *, json=None, text=None, content=None, headers=None)` (14)
- `def unreachable() -> httpx.MockTransport` (7)
  - `def handler(request: httpx.Request) -> httpx.Response` (2)
- `def capture(*, content: bytes | None=None, status: int=200)` (16)
  - `def handler(request: httpx.Request) -> httpx.Response` (5)

### `tests/wiring.py` — 30 строк

Части карточки и сервис обложек, собранные для теста на подставном транспорте.

Зависит от: `backend.app`, `backend.service.posters`, `backend.sources.http`, `backend.storage.posters`

- `def poster_service(store: PosterStore, transport: httpx.MockTransport) -> PosterService` (7)
- `def card_parts(sessions, store: PosterStore, transport: httpx.MockTransport) -> dict` (8)

## Абстракции с одной реализацией

- `Base` — наследник один: `Note`
- `FakeCatalog` — наследник один: `FakeCatalogWithSlug`
- `FakeRatings` — наследник один: `Breaking`
- `ViewsRepository` — наследник один: `Forgetful`
