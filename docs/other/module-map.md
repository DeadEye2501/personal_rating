# Карта модулей

Собирается из кода, а не ведётся руками.
Править руками нельзя — правки затрёт следующая сборка.
Число в скобках — сколько строк занимает объявление.

## . — 1 модулей

### `main.py` — 93 строк

Собирает зависимости, настраивает лог и поднимает окно.

Зависит от: `backend.app`, `backend.config`, `backend.startup`, `bridge.thread`, `bridge.window`

- `def setup_logging(config) -> None` (12)
- `def main() -> None` (45)

## backend — 88 модулей

### `backend/app.py` — 201 строк

Бэкенд, собранный целиком.

Зависит от: `backend.config`, `backend.model`, `backend.service.cards`, `backend.service.creation`, `backend.service.enrich`, `backend.service.library`, `backend.service.linking`, `backend.service.loading`, `backend.service.people`, `backend.service.posters`, `backend.service.removal`, `backend.service.search`, `backend.service.series`, `backend.sources.build`, `backend.sources.http`, `backend.sources.registry`, `backend.storage.posters`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.removed`, `backend.storage.repository.sections`, `backend.storage.repository.tags`, `backend.storage.repository.views`, `backend.storage.repository.wishlist`, `backend.storage.rescale`, `backend.storage.session`

- `class Backend` (76)
  - `async def create_manual_card(self, item: Item, now: datetime) -> int` (16)
  - `async def delete_card(self, item_id: int) -> None` (9)
  - `async def restore_removed(self, kind: Kind, source: Source, source_id: str) -> None` (9)
  - `async def aclose(self) -> None` (8)
- `def card_parts(sessions, posters: PosterService) -> dict` (13)
- `async def build_backend(config: Config, transport: httpx.AsyncBaseTransport | None=None) -> Backend` (65)

### `backend/config.py` — 59 строк

Настройки приложения, прочитанные из окружения.

Зависит от: —

- `class Config` (21)
  - `def library_db(self) -> Path` (2)
  - `def posters_db(self) -> Path` (2)
  - `def log_file(self) -> Path` (2)
- `def value(env: Mapping[str, str], name: str) -> str` (4)
- `def load_config(env: Mapping[str, str], base_dir: Path) -> Config` (15)

### `backend/language.py` — 72 строк

На каком языке написано название.

Зависит от: —

Отдаёт наружу: `by_language`, `in_latin`, `in_russian`

- `def in_russian(name: str) -> bool` (6)
- `def in_latin(name: str) -> bool` (17)
- `def by_language(names: list[str]) -> tuple[str, str]` (20)

### `backend/model/__init__.py` — 110 строк

Поверхность модели: отсюда типы границы слоёв импортирует клиент.

Зависит от: `backend.model.card`, `backend.model.credit`, `backend.model.denied`, `backend.model.external`, `backend.model.genre`, `backend.model.item`, `backend.model.kinds`, `backend.model.link`, `backend.model.outcome`, `backend.model.query`, `backend.model.rating`, `backend.model.ratings`, `backend.model.results`, `backend.model.search`, `backend.model.suggestion`, `backend.model.tag`, `backend.model.view`

Отдаёт наружу: `BadImage`, `Bucket`, `CardView`, `CompanyRole`, `Credit`, `Denied`, `Dangling`, `ExternalId`, `ExternalLink`, `ExternalRating`, `ExternalSearch`, `Feed`, `Filters`, `Found`, `Genre`, `GenreKind`, `GenreRule`, `GenreSource`, `Histogram`, `IdSource`, `IdentityTaken`, `Item`, `ItemExists`, `Kind`, `Missing`, `Order`, `Outcome`, `PersonHit`, `PersonRole`, `Rating`, `RatingSource`, `Ratings`, `Reason`, `Refusal`, `SearchHit`, `Section`, `SeriesCounts`, `Sort`, `Source`, `SourceCard`, `Suggestion`, `Tag`, `TagExists`, `WrongTagKind`, `average_score`, `merge_results`, `new_manual_item`, `new_source_id`, `parse_link`, `view_from_hit`, `view_from_item`


### `backend/model/card.py` — 25 строк

Всё, что источник отдал о карточке, в наших типах.

Зависит от: `backend.model.credit`, `backend.model.external`, `backend.model.item`, `backend.model.kinds`

- `class SourceCard` (14)

### `backend/model/credit.py` — 23 строк

Человек или студия в роли на карточке.

Зависит от: `backend.model.kinds`

- `class Credit` (15)

### `backend/model/denied.py` — 50 строк

Отказ операции: занятое имя, занятая идентичность, негодная картинка.

Зависит от: —

- `class Denied(Exception)` (2)
- `class ItemExists(Denied)` (4)
- `class TagExists(Denied)` (2)
- `class WrongTagKind(Denied)` (2)
- `class IdentityTaken(Denied)` (2)
- `class BadImage(Denied)` (2)
- `class Dangling(Denied)` (12)

### `backend/model/external.py` — 19 строк

Что знают о карточке чужие источники.

Зависит от: `backend.model.kinds`

- `class ExternalId` (3)
- `class ExternalRating` (4)

### `backend/model/genre.py` — 30 строк

Жанр на границе слоёв и правило, которое к нему ведёт.

Зависит от: `backend.model.kinds`

- `class Genre` (4)
- `class GenreRule` (15)

### `backend/model/item.py` — 56 строк

Карточка любого типа содержимого на границе слоёв.

Зависит от: `backend.model.kinds`

- `class Item` (16)
- `class SeriesCounts` (5)
- `def new_source_id() -> str` (5)
- `def new_manual_item(kind: Kind, title: str, **fields) -> Item` (13)

### `backend/model/kinds.py` — 69 строк

Закрытые наборы значений, которыми описывается карточка.

Зависит от: —

- `class Kind(StrEnum)` (4)
- `class Source(StrEnum)` (8)
- `class GenreSource(StrEnum)` (8)
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

### `backend/model/outcome.py` — 45 строк

Чем может кончиться запрос к источнику: находкой, честным «нет» или отказом.

Зависит от: —

- `class Reason(StrEnum)` (6)
- `class Found` (2)
- `class Missing` (3)
- `class Refusal` (8)
- `Outcome: TypeAlias = Found | Missing | Refusal`

### `backend/model/query.py` — 97 строк

Язык, которым лента разговаривает с базой о разделах.

Зависит от: `backend.model.kinds`

- `class Section(StrEnum)` (6)
- `class Sort(StrEnum)` (11)
- `class Order` (6)
- `class Filters` (23)
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

### `backend/model/results.py` — 50 строк

Что ответила чужая база и как её выдача складывается со своей.

Зависит от: `backend.model.kinds`, `backend.model.outcome`, `backend.model.view`

- `class ExternalSearch` (11)
- `def merge_results(local: list[CardView], external: list[CardView]) -> list[CardView]` (23)

### `backend/model/search.py` — 49 строк

Кандидат в выдаче поиска — то, чем карточка ещё не стала.

Зависит от: `backend.model.kinds`

- `class SearchHit` (27)
- `class PersonHit` (11)

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

### `backend/service/asking.py` — 39 строк

Запрос к источнику, из которого не вылетает исключение.

Зависит от: `backend.sources.errors`

- `async def answered(awaitable, source: str)` (14)
- `async def answered_all(requests: Iterable[tuple]) -> list` (12)

### `backend/service/card_parts.py` — 52 строк

Общая основа записи карточки в базу.

Зависит от: `backend.model`, `backend.service.posters`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`

- `class CardParts` (39)
  - `async def _attach_credits(self, repository: CreditRepository, item_id: int, credits: tuple[Credit, ...]) -> None` (6)
  - `async def _write_external(self, item_id: int, card: SourceCard) -> None` (6)

### `backend/service/cards.py` — 91 строк

Карточка источника строками базы.

Зависит от: `backend.model`, `backend.service.card_parts`, `backend.service.creation`, `backend.service.genres`, `backend.service.removal`, `backend.sources.errors`

- `class CardWriter(CardParts)` (76)
  - `async def save(self, card: SourceCard, poster: bytes | None) -> int | Refusal` (40)
  - `async def _started(self, card: SourceCard) -> int | Refusal` (16)
  - `async def _write_the_rest(self, item_id: int, card: SourceCard, poster: bytes | None) -> None` (13)

### `backend/service/creation.py` — 52 строк

Заведение карточки в обоих файлах базы.

Зависит от: `backend.model`, `backend.service.posters`, `backend.storage.repository.library`

- `async def fresh_item(library: LibraryRepository, posters: PosterService, item: Item) -> int` (34)

### `backend/service/enrich.py` — 154 строк

Чужие оценки у карточки.

Зависит от: `backend.model`, `backend.service.asking`, `backend.sources.registry`, `backend.storage.repository.external`, `backend.unique`

- `class _Harvest` (10)
- `class Enricher` (113)
  - `async def enrich(self, item_id: int, kind: Kind) -> list[ExternalRating]` (27)
  - `def expected(self, kind: Kind) -> list[RatingSource]` (9)
  - `async def _imdb_id(self, item_id: int) -> str | None` (5)
  - `async def _harvested(self, item_id: int, asked: list, outcomes: list) -> _Harvest` (16)
  - `def _take(harvest: _Harvest, values: tuple[ExternalRating, ...], provides: tuple[RatingSource, ...]) -> None` (16)
  - `async def _record(self, item_id: int, harvest: _Harvest, stale: list[RatingSource], now: datetime) -> None` (13)
  - `async def _keep(self, item_id: int, external: ExternalId) -> None` (5)

### `backend/service/filmography.py` — 71 строк

Чужие работы человека: спросить о них источник.

Зависит от: `backend.model`, `backend.service.asking`, `backend.service.hits`, `backend.sources.registry`

- `class Filmographies` (57)
  - `async def of_person(self, source_id: str, kind: Kind) -> tuple[list[list[SearchHit]], list[Refusal]]` (9)
  - `async def of_name(self, name: str, kind: Kind) -> tuple[list[list[SearchHit]], list[Refusal]]` (20)
  - `async def _works(self, client, person_ids: list[str], kind: Kind) -> tuple[list[list[SearchHit]], list[Refusal]]` (19)

### `backend/service/genres.py` — 69 строк

Чужие метки жанров в наши жанры.

Зависит от: `backend.model`, `backend.storage.repository.genres`, `backend.unique`

- `def _fires(rule: GenreRule, marks: frozenset[str], known: frozenset[str]) -> bool` (4)
- `def matched(rules: tuple[GenreRule, ...], marks: Iterable[str]) -> list[Genre]` (19)
- `async def book_for(genres: GenresRepository, spaces: Iterable[GenreSource]) -> Book` (7)
- `def genres_of(book: Book, marked: Marked) -> tuple[Genre, ...]` (14)
- `async def resolved_genres(genres: GenresRepository, marked: Marked) -> list[int]` (5)

### `backend/service/hits.py` — 113 строк

Приведение того, что ответили источники, к тому виду, в котором это

Зависит от: `backend.model`, `backend.service.genres`, `backend.sources.convert`, `backend.storage.repository.genres`, `backend.storage.repository.removed`, `backend.unique`

- `def once(refusals: list[Refusal]) -> list[Refusal]` (10)
- `def split(outcomes: Iterable[Outcome]) -> tuple[list[list[SearchHit]], list[Refusal]]` (19)
- `def mark_of(hit: SearchHit) -> tuple[Kind, Source, str]` (7)
- `async def without_removed(removed: RemovedRepository, answers: list[list[SearchHit]]) -> list[list[SearchHit]]` (24)
- `async def to_views(hits: list[SearchHit], genres: GenresRepository, clock: Callable[[], datetime]) -> list[CardView]` (15)

### `backend/service/images.py` — 49 строк

Приведение залитой с диска картинки к виду обложки.

Зависит от: `backend.model`

- `def _centred_box(width: int, height: int) -> tuple[int, int, int, int]` (11)
- `def crop_to_cover(data: bytes) -> bytes` (20)

### `backend/service/library.py` — 41 строк

Что показывает раздел.

Зависит от: `backend.model`, `backend.storage.repository.sections`, `backend.storage.repository.views`

- `class LibraryService` (30)
  - `async def page(self, feed: Feed, offset: int=0, limit: int=PAGE_SIZE) -> list[CardView]` (4)
  - `async def views_of(self, item_ids: list[int]) -> list[CardView]` (8)
  - `async def histogram(self, kind: Kind, filters: Filters) -> Histogram` (2)

### `backend/service/linking.py` — 125 строк

Привязка карточки к внешнему источнику: внешнее заполняет только пустое.

Зависит от: `backend.model`, `backend.service.card_parts`, `backend.service.genres`, `backend.storage.repository.credits`

- `def merge_fields(existing: Item, incoming: Item) -> Item` (7)
- `def overwrite_fields(existing: Item, incoming: Item) -> Item` (14)
- `class Linker(CardParts)` (76)
  - `async def link(self, item_id: int, card: SourceCard, now: datetime, overwrite: bool=False) -> None` (24)
  - `async def _check_identifiers(self, item_id: int, card: SourceCard) -> None` (11)
  - `async def _fill_genres(self, item_id: int, card: SourceCard, overwrite: bool) -> None` (11)
  - `async def _fill(self, repository: CreditRepository, item_id: int, credits: tuple[Credit, ...], overwrite: bool) -> None` (12)
  - `async def _fill_poster(self, item_id: int, item: Item, overwrite: bool) -> None` (11)

### `backend/service/loading.py` — 159 строк

Кандидат превращается в карточку.

Зависит от: `backend.language`, `backend.model`, `backend.service.asking`, `backend.service.cards`, `backend.service.posters`, `backend.sources.registry`, `backend.storage.repository.library`

- `def _from_both(card: SourceCard, view: CardView) -> SourceCard` (31)
- `class Loader` (99)
  - `def _catalog(self, source: Source, action: str)` (12)
  - `async def ensure(self, view: CardView) -> int | Missing | Refusal` (37)
  - `async def _second_try(self, card: SourceCard, asked: str) -> bytes | None | Refusal` (12)
  - `async def card_for_link(self, link: ExternalLink) -> SourceCard | Missing | Refusal` (20)

### `backend/service/merging.py` — 302 строк ⚠ подошёл к 300

Одна игра — одна строка выдачи.

Зависит от: `backend.language`, `backend.model`, `backend.service.titles`, `backend.unique`

- `def _a_set(hit: SearchHit) -> bool` (2)
- `def _asked_for(hit: SearchHit, asked: list[str]) -> bool` (11)
- `def _keys(hit: SearchHit, *, alone: bool) -> list[str]` (20)
- `def _dressed(hit: SearchHit) -> bool` (5)
- `def _rank(hit: SearchHit) -> tuple` (6)
- `class _Groups` (66)
  - `def head(self, one: int) -> int` (4)
  - `def _shown(self, head: int) -> dict[Source, set[str]]` (7)
  - `def _years(self, head: int) -> list[int]` (3)
  - `def _too_far(self, one: int, other: int) -> bool` (12)
  - `def _joinable(self, one: int, other: int) -> bool` (14)
  - `def join(self, one: int, other: int) -> None` (6)
- `def _other_name(winner: SearchHit, group: list[SearchHit]) -> str` (29)
- `def _earliest_year(group: list[SearchHit]) -> int | None` (17)
- `def _completed(winner: SearchHit, group: list[SearchHit]) -> SearchHit` (4)
- `def _grouped(flat: list[SearchHit]) -> list[int]` (27)
- `def _without_sets(answers: list[list[SearchHit]], query: str) -> list[list[SearchHit]]` (12)
- `def merged(answers: list[list[SearchHit]], query: str) -> list[list[SearchHit]]` (36)

### `backend/service/people.py` — 84 строк

Что найдётся по человеку или студии.

Зависит от: `backend.model`, `backend.service.filmography`, `backend.service.hits`, `backend.service.search`, `backend.sources.registry`, `backend.storage.repository.credits`, `backend.storage.repository.views`

- `class PeopleSearch` (58)
  - `async def by_entity(self, domain: str, entity_id: int, kind: Kind) -> ExternalSearch` (17)
  - `async def _own(self, repository: CreditRepository, entity_id: int, kind: Kind) -> list[CardView]` (7)
  - `async def _outside(self, domain: str, identity: tuple[str, str | None], kind: Kind) -> tuple[list[SearchHit], list[Refusal]]` (17)

### `backend/service/posters.py` — 154 строк

Путь обложки от источника до хранилища.

Зависит от: `backend.model`, `backend.service.asking`, `backend.service.images`, `backend.sources.errors`, `backend.sources.http`, `backend.storage.posters`

- `class PosterService` (121)
  - `async def fetch(self, source: Source, url: str) -> bytes | None | Refusal` (7)
  - `async def _fetched(self, source: Source, url: str) -> bytes | None | Refusal` (16)
  - `def _picture(self, source: Source, url: str, response: httpx.Response) -> bytes | None | Refusal` (30)
  - `def _name(source: Source) -> str` (4)
  - `def _refuse(self, source: Source, detail: str) -> Refusal` (6)
  - `async def poster_for(self, item_id: int | None, source: Source, url: str, now: datetime) -> bytes | None | Refusal` (19)
  - `async def save(self, item_id: int, data: bytes, now: datetime) -> None` (2)
  - `async def delete(self, item_id: int) -> None` (4)
  - `async def has(self, item_id: int) -> bool` (4)
  - `async def store_upload(self, item_id: int, data: bytes, now: datetime) -> None` (5)
  - `async def aclose(self) -> None` (4)

### `backend/service/relevance.py` — 85 строк

Строка выдачи обязана знать, о чём её спросили.

Зависит от: `backend.model`, `backend.service.titles`

Отдаёт наружу: `relevant`

- `def _asked(query: str) -> set[str]` (8)
- `def _knows(hit: SearchHit, asked: set[str]) -> bool` (23)
- `def relevant(answers: list[list[SearchHit]], query: str) -> list[list[SearchHit]]` (29)

### `backend/service/removal.py` — 55 строк

Удаление карточки из обоих файлов базы, двумя путями.

Зависит от: `backend.service.posters`, `backend.storage.repository.library`, `backend.storage.repository.removed`

- `async def discard_card(library: LibraryRepository, posters: PosterService, removed: RemovedRepository, item_id: int) -> None` (19)
- `async def remove_card(library: LibraryRepository, posters: PosterService, item_id: int) -> None` (24)

### `backend/service/search.py` — 182 строк

Что найдётся по запросу.

Зависит от: `backend.model`, `backend.service.asking`, `backend.service.filmography`, `backend.service.hits`, `backend.service.merging`, `backend.service.relevance`, `backend.sources.registry`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.removed`, `backend.storage.repository.views`, `backend.unique`

- `def _asks_for_removed(query: str) -> bool` (13)
- `def _weave(answers: list[list[SearchHit]]) -> list[SearchHit]` (18)
- `class SearchParts` (12)
- `class SearchService` (92)
  - `async def local(self, kind: Kind, query: str) -> list[CardView]` (8)
  - `async def external(self, kind: Kind, query: str) -> ExternalSearch` (40)
  - `async def _narrowed(self, answers: list[list[SearchHit]], together: list[SearchHit], query: str) -> list[SearchHit]` (24)

### `backend/service/series.py` — 62 строк

Перезапрос сериала по сроку годности.

Зависит от: `backend.model`, `backend.service.asking`, `backend.sources.registry`, `backend.storage.repository.library`

- `def _kept(fresh: int | None, stored: int | None) -> int | None` (4)
- `class SeriesRefresh` (38)
  - `async def refresh(self, item_id: int) -> None` (28)

### `backend/service/titles.py` — 98 строк

Приведение чужого названия к сравнимому виду.

Зависит от: —

- `def flattened(name: str) -> str` (17)
- `def without_edition(name: str) -> str` (12)

### `backend/sources/backoff.py` — 31 строк

Отказ, закрывающий источник на срок.

Зависит от: `backend.model`, `backend.sources.http`

- `def refuse_until(http: SourceHttp, reason: Reason, delay: timedelta, source: str | None=None) -> Refusal` (23)

### `backend/sources/build.py` — 54 строк

Семь клиентов источников, поднятых из настроек.

Зависит от: `backend.config`, `backend.model`, `backend.sources.gog.client`, `backend.sources.http`, `backend.sources.oldgames.client`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`, `backend.sources.registry`, `backend.sources.steam.client`, `backend.sources.tmdb.client`

- `def build_sources(config: Config, transport: httpx.AsyncBaseTransport | None=None) -> Sources` (35)
  - `def http(name: str) -> SourceHttp` (13)

### `backend/sources/convert.py` — 104 строк

Куски чужого ответа, которые все источники переводят одинаково.

Зависит от: `backend.model`

- `def identifier(source: IdSource, value) -> tuple[ExternalId, ...]` (12)
- `def genres(space: GenreSource, rows: list[dict], key: str='id') -> tuple[tuple[GenreSource, str], ...]` (10)
- `def year(value: str | None) -> int | None` (5)
- `def year_in_text(value: str | None) -> int | None` (13)
- `def companies(payload: dict) -> tuple[Credit, ...]` (11)
- `def from_search(source: Source, value: float | None, now: datetime) -> tuple[ExternalRating, ...]` (5)
- `def rating(source: RatingSource, value: float | int | None, now: datetime) -> tuple[ExternalRating, ...]` (10)

### `backend/sources/errors.py` — 95 строк

Как источник отвечает, когда верить ответу нельзя.

Зависит от: `backend.model`

- `def broken(source: str, error: Exception) -> Refusal` (4)
- `def absent(response: httpx.Response, source: str) -> Missing | Refusal` (15)
- `def refuse_code(source: str, status: int) -> Refusal` (5)
- `def is_json(response: httpx.Response) -> bool` (12)
- `def parsed(log: Logger, source: str, note: str, produce: Callable[[], T]) -> T | Refusal` (18)
- `def parsed_or(log: Logger, source: str, note: str, produce: Callable[[], T], fallback: T) -> T` (12)

### `backend/sources/gog/client.py` — 182 строк

Разговор с GOG по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.gog.parse`, `backend.sources.http`, `backend.sources.undocumented`, `backend.unique`

- `class GogClient` (146)
  - `def name(self) -> str` (4)
  - `async def _payload(self, query: str, product_types: str | None=None) -> dict | Refusal` (18)
  - `async def _catalog(self, query: str, product_types: str | None=None) -> list | Refusal` (7)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (8)
  - `async def _title(self, source_id: str) -> str | Outcome` (20)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (27)
  - `async def resolve_slug(self, slug: str) -> Outcome` (33)
  - `async def aclose(self) -> None` (2)

### `backend/sources/gog/parse.py` — 131 строк

Перевод ответов GOG в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`, `backend.unique`

- `def _marks(row: dict) -> tuple[tuple[GenreSource, str], ...]` (12)
- `def parse_catalog(payload: dict) -> list[SourceCard]` (27)
- `def to_hit(card: SourceCard, slug: str='') -> SearchHit` (18)
- `def parse_hits(payload: dict) -> list[SearchHit]` (10)
- `def find_slug(payload: dict, slug: str) -> str | None` (8)
- `def title_of(payload: dict) -> str` (12)

### `backend/sources/http.py` — 150 строк

Общая дверь в сеть для всех источников.

Зависит от: `backend.model`

- `def poster_name(source: Source) -> str` (3)
- `def _limit(name: str) -> int | None` (4)
- `class Breaker` (28)
  - `def is_open(self) -> bool` (7)
  - `def trip(self, delay: timedelta, reason: Reason=Reason.QUOTA) -> None` (7)
  - `def reason(self) -> Reason` (2)
- `class SourceHttp` (56)
  - `async def get(self, url: str, params: Mapping[str, object] | None=None, headers: Mapping[str, str] | None=None) -> httpx.Response | Refusal` (13)
  - `async def _fetched(self, url: str, params: Mapping[str, object] | None, headers: Mapping[str, str] | None) -> httpx.Response | Refusal` (14)
  - `async def aclose(self) -> None` (2)

### `backend/sources/oldgames/client.py` — 88 строк

Разговор с old-games.ru по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.oldgames.parse`, `backend.sources.undocumented`

- `class OldGamesClient` (58)
  - `def name(self) -> str` (2)
  - `async def _page(self, url: str, params: dict | None=None) -> str | Refusal` (19)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (11)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (6)
  - `async def aclose(self) -> None` (2)

### `backend/sources/oldgames/parse.py` — 174 строк

Перевод страниц old-games.ru в наши типы.

Зависит от: `backend.language`, `backend.model`, `backend.sources.convert`

- `def _soup(page: str) -> BeautifulSoup` (2)
- `def _text(node: Tag | None) -> str` (4)
- `def _hit(row: Tag) -> SearchHit` (28)
- `def parse_search(page: str) -> list[SearchHit]` (11)
- `def _labelled(scope: Tag, label: str) -> str` (7)
- `def _companies(scope: Tag) -> tuple[Credit, ...]` (7)
- `def _synopsis(soup: BeautifulSoup) -> str` (3)
- `def _cover(soup: BeautifulSoup) -> str` (4)
- `def parse_card(page: str, source_id: str) -> SourceCard` (34)

### `backend/sources/ratings/kinopoisk/client.py` — 45 строк

Кинопоиск снаружи: одно имя над двумя зеркалами.

Зависит от: `backend.model`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`

- `class KinopoiskClient` (32)
  - `def name(self) -> str` (4)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (11)
  - `async def aclose(self) -> None` (3)

### `backend/sources/ratings/kinopoisk/mirror.py` — 50 строк

Общее у двух зеркал Кинопоиска.

Зависит от: `backend.model`, `backend.sources.backoff`, `backend.sources.errors`, `backend.sources.http`

- `def refuse_quota(http: SourceHttp) -> Refusal` (2)
- `def refuse_rate(http: SourceHttp) -> Refusal` (4)
- `def refuse_key() -> Refusal` (3)
- `def refuse_code(status: int) -> Refusal` (3)
- `def answered(answer: Ratings) -> Outcome` (7)

### `backend/sources/ratings/kinopoisk/parse.py` — 57 строк

Перевод ответов обоих зеркал Кинопоиска в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `def _rating(value, now: datetime) -> tuple[ExternalRating, ...]` (8)
- `def _first_row(payload: dict, key: str) -> dict | None` (8)
- `def parse_poiskkino(payload: dict) -> Ratings` (10)
- `def parse_unofficial(payload: dict) -> Ratings` (6)
- `def parse_unofficial_card(row: dict) -> Ratings` (9)

### `backend/sources/ratings/kinopoisk/poiskkino.py` — 68 строк

Основное зеркало Кинопоиска.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.parse`

- `class PoiskkinoClient` (42)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (9)
  - `def _verdict(self, response: httpx.Response) -> Outcome` (16)
  - `def _answer(self, response: httpx.Response) -> Outcome` (3)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/kinopoisk/unofficial.py` — 103 строк

Запасное зеркало Кинопоиска.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.parse`

- `def _needs_the_card(ratings: Ratings) -> bool` (4)
- `class UnofficialClient` (67)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (13)
  - `async def _card(self, listed: Ratings) -> Outcome` (29)
  - `def _verdict(self, response: httpx.Response, parse: Callable[[dict], Ratings]) -> Outcome` (15)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/mdblist/client.py` — 95 строк

Разговор с MDBList по сети.

Зависит от: `backend.model`, `backend.sources.backoff`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.mdblist.parse`

- `def _retry_after(response: httpx.Response) -> timedelta | None` (3)
- `class MdbListClient` (67)
  - `def name(self) -> str` (4)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (8)
  - `def _verdict(self, response: httpx.Response) -> Outcome` (20)
  - `def _denied(self, response: httpx.Response) -> Refusal` (14)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/mdblist/parse.py` — 35 строк

Перевод ответов MDBList в наши типы.

Зависит от: `backend.model`

- `def parse_ratings(payload: dict) -> Ratings` (18)

### `backend/sources/ratings/omdb/client.py` — 98 строк

Разговор с OMDB по сети.

Зависит от: `backend.model`, `backend.sources.backoff`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.ratings.omdb.parse`

- `def until_midnight(now: datetime) -> timedelta` (7)
- `class OmdbClient` (70)
  - `def name(self) -> str` (4)
  - `async def ratings(self, imdb_id: str, kind: Kind) -> Outcome` (24)
  - `def _answer(self, payload: dict) -> Outcome` (8)
  - `def _denied(self, payload: dict) -> Refusal` (16)
  - `async def aclose(self) -> None` (2)

### `backend/sources/ratings/omdb/parse.py` — 46 строк

Перевод ответов OMDB в наши типы.

Зависит от: `backend.model`

- `def _number(raw: str | None) -> float | None` (10)
- `def parse_ratings(payload: dict) -> Ratings` (21)

### `backend/sources/registry.py` — 75 строк

Кто отвечает за какой тип содержимого.

Зависит от: `backend.model`, `backend.sources.gog.client`, `backend.sources.http`, `backend.sources.oldgames.client`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`, `backend.sources.steam.client`, `backend.sources.tmdb.client`

- `class Sources` (56)
  - `def catalog_for(self, kind: Kind) -> list` (12)
  - `def people_for(self, kind: Kind) -> TmdbClient | None` (6)
  - `def client_for(self, source: Source)` (9)
  - `def rating_sources(self, kind: Kind) -> list` (6)
  - `async def aclose(self) -> None` (3)

### `backend/sources/steam/client.py` — 185 строк

Разговор со Steam по сети.

Зависит от: `backend.model`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.steam.parse`, `backend.sources.undocumented`

- `class SteamClient` (135)
  - `def name(self) -> str` (4)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (13)
  - `async def _narrowed(self, hits: list[SearchHit]) -> list[SearchHit]` (14)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (40)
  - `async def _items(self, appids: list[str], wanted: dict) -> dict | None` (28)
  - `async def _beyond_details(self, source_id: str) -> tuple[tuple[tuple[GenreSource, str], ...], str, int | None]` (20)
  - `async def aclose(self) -> None` (2)

### `backend/sources/steam/parse.py` — 241 строк

Перевод ответов Steam в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`

- `def poster_url(appid: str) -> str` (7)
- `def parse_search(payload: list[dict]) -> list[SearchHit]` (11)
- `def released_in(payload: dict, source_id: str) -> int | None` (22)
- `def _store_items(payload: dict) -> list[dict]` (10)
- `def _poster(row: dict, appid: str) -> str` (16)
- `def _answered(payload: dict) -> dict[str, dict]` (10)
- `def sifted(hits: list[SearchHit], payload: dict) -> list[SearchHit]` (18)
- `def cover_of(payload: dict, appid: str) -> str` (8)
- `def _genres(data: dict) -> tuple[tuple[GenreSource, str], ...]` (6)
- `def _metascore(data: dict, now: datetime) -> tuple[ExternalRating, ...]` (5)
- `def parse_card(data: dict) -> SourceCard` (25)
- `def parse_tags(payload: dict, appid: str) -> tuple[tuple[GenreSource, str], ...]` (34)

### `backend/sources/tmdb/client.py` — 158 строк

Разговор с TMDB по сети.

Зависит от: `backend.model`, `backend.sources.backoff`, `backend.sources.errors`, `backend.sources.http`, `backend.sources.tmdb.parse`

- `def classify(response: httpx.Response) -> Missing | Refusal | None` (23)
- `class TmdbClient` (100)
  - `def name(self) -> str` (4)
  - `def _params(self, **extra: object) -> dict` (2)
  - `def _verdict(self, response: httpx.Response) -> Missing | Refusal | None` (12)
  - `async def _asked(self, url: str, **extra: object) -> httpx.Response | Missing | Refusal` (13)
  - `async def _taken(self, url: str, complaint: str, parse: Callable[[dict], object], **extra: object) -> Outcome` (12)
  - `async def search(self, query: str, kind: Kind) -> Outcome` (5)
  - `async def credits_of(self, person_id: str, kind: Kind) -> Outcome` (10)
  - `async def find_people(self, name: str) -> Outcome` (6)
  - `async def card(self, source_id: str, kind: Kind) -> Outcome` (6)
  - `async def series_counts(self, source_id: str) -> Outcome` (6)
  - `async def aclose(self) -> None` (2)

### `backend/sources/tmdb/parse.py` — 226 строк

Перевод ответов TMDB в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`, `backend.unique`

- `class Incomplete(ValueError)` (9)
- `def _released(value: str | None) -> date | None` (7)
- `def _poster(payload: dict) -> str` (3)
- `def _genres(payload: dict) -> tuple[tuple[GenreSource, str], ...]` (2)
- `def _hundred(value: float | None) -> float | None` (2)
- `def _own_rating(payload: dict, now: datetime) -> tuple[ExternalRating, ...]` (2)
- `def _person(row: dict, role: PersonRole, position: int | None=None) -> Credit` (10)
- `def _cast(rows: list[dict]) -> list[Credit]` (5)
- `def _required(payload: dict, block: str) -> dict` (9)
- `def _item(payload: dict, kind: Kind, now: datetime, **extra) -> Item` (20)
- `def parse_search(payload: dict, kind: Kind) -> list[SearchHit]` (2)
- `def parse_credits(payload: dict, kind: Kind) -> list[SearchHit]` (11)
- `def parse_people(payload: dict) -> list[PersonHit]` (5)
- `def _hits(rows: list[dict], kind: Kind) -> list[SearchHit]` (25)
- `def parse_movie(payload: dict) -> SourceCard` (18)
- `def parse_series_counts(payload: dict) -> SeriesCounts` (7)
- `def parse_series(payload: dict) -> SourceCard` (19)

### `backend/sources/undocumented.py` — 42 строк

Разговор с магазином, который своих лимитов не объявляет.

Зависит от: `backend.model`, `backend.sources.backoff`, `backend.sources.errors`, `backend.sources.http`

- `def refuse_undocumented(http: SourceHttp, status: int) -> Refusal` (6)
- `async def asked(http: SourceHttp, url: str, params: dict | None=None) -> httpx.Response | Refusal` (17)

### `backend/startup.py` — 76 строк

Всё, чего не хватает приложению до первого запроса: рабочая папка с файлом

Зависит от: —

- `def ensure_env(data_dir: Path, template: Path) -> None` (22)
- `def upgrade_schema(base_dir: Path | None=None) -> None` (22)

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

### `backend/storage/repository/base.py` — 102 строк

Общее у репозиториев: сессия и способы с ней обойтись.

Зависит от: `backend.model`

- `class Repository` (84)
  - `async def _row(self, statement: Executable) -> Row | None` (3)
  - `async def _rows(self, statement: Executable) -> list[Row]` (3)
  - `async def _mapped(self, statement: Executable, make: Callable[[Row], object])` (3)
  - `async def _maybe(self, statement: Executable, make: Callable[[Row], object])` (6)
  - `async def _has_item(self, table: Table, item_id: int) -> bool` (8)
  - `async def _created(self, statement: Executable, taken: Exception) -> int` (15)
  - `async def _written(self, statement: Executable, taken: Exception) -> None` (7)
  - `async def _run(self, *statements: Executable) -> None` (23)

### `backend/storage/repository/credits.py` — 290 строк

Один репозиторий на людей и на студий — различает их только описатель.

Зависит от: `backend.model`, `backend.storage.entity`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.session`, `backend.storage.statements`, `backend.storage.tables`

- `def _outer(row) -> str | None` (14)
- `class CreditRepository(Repository)` (235)
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
  - `async def ensure(self, credit: Credit) -> int` (7)
  - `async def _identified(self, credit: Credit) -> int` (20)
  - `async def attach(self, item_id: int, entity_id: int, role: PersonRole | CompanyRole, position: int | None=None) -> None` (13)
  - `async def detach_all(self, item_id: int) -> None` (2)
  - `async def credits_of(self, item_id: int) -> list[Credit]` (17)
  - `async def identity_of(self, entity_id: int) -> tuple[str, str | None] | None` (13)
  - `async def items_of(self, entity_id: int, kind: Kind) -> list[int]` (25)
  - `async def suggest(self, name: str, limit: int=10, offset: int=0) -> list[Suggestion]` (21)
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

### `backend/storage/repository/genres.py` — 86 строк

Жанры в базе: свои, и правила из чужих меток, ведущие к ним.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.statements`, `backend.storage.tables`

- `def _rule(marks: list[Row]) -> GenreRule` (9)
- `class GenresRepository(Repository)` (60)
  - `async def rules(self, source: GenreSource) -> tuple[GenreRule, ...]` (24)
  - `async def set_for_item(self, item_id: int, genre_ids: list[int]) -> None` (14)
  - `async def genres_of(self, item_id: int) -> list[Genre]` (8)
  - `async def list_for_kind(self, kind: GenreKind) -> list[Genre]` (10)

### `backend/storage/repository/library.py` — 218 строк

Карточки библиотеки.

Зависит от: `backend.model`, `backend.storage.entity`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.session`, `backend.storage.tables`

- `def _named(entity: Entity, needle: str)` (13)
- `def _values(item: Item) -> dict` (6)
- `class LibraryRepository(Repository)` (171)
  - `async def _one(self, statement: Select) -> Item | None` (2)
  - `async def create(self, item: Item) -> int` (5)
  - `async def get(self, item_id: int) -> Item | None` (2)
  - `async def find_by_source(self, kind: Kind, source: Source, source_id: str) -> Item | None` (11)
  - `async def list_by_kind(self, kind: Kind, limit: int, offset: int) -> list[Item]` (18)
  - `async def find_by_title(self, kind: Kind, title: str) -> list[Item]` (16)
  - `async def search(self, kind: Kind, query: str, limit: int) -> list[int]` (37)
  - `async def deletion_summary(self, item_id: int) -> dict[str, int | bool]` (12)
  - `async def delete(self, item_id: int) -> None` (5)
  - `async def refresh_series_counts(self, item_id: int, seasons_count: int | None, episodes_count: int | None, now: datetime) -> None` (14)
  - `async def replace_fields(self, item_id: int, item: Item) -> None` (13)
  - `async def link(self, item_id: int, source: Source, source_id: str, now: datetime) -> None` (15)
  - `async def unlink(self, item_id: int) -> None` (8)

### `backend/storage/repository/ratings.py` — 68 строк

Моя оценка карточки.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.statements`, `backend.storage.tables`

- `class RatingsRepository(Repository)` (54)
  - `async def _write(self, item_id: int, values: dict, now: datetime) -> None` (19)
  - `async def set_score(self, item_id: int, score: float | None, now: datetime) -> None` (3)
  - `async def set_aspects(self, item_id: int, visual: int | None, narrative: int | None, gameplay: int | None, now: datetime) -> float | None` (16)
  - `async def set_review(self, item_id: int, review: str, now: datetime) -> None` (2)
  - `async def get(self, item_id: int) -> Rating | None` (5)
  - `async def clear(self, item_id: int) -> None` (3)

### `backend/storage/repository/removed.py` — 85 строк

Что человек убрал из выдачи насовсем.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.tables`

- `class RemovedRepository(Repository)` (75)
  - `async def remember(self, item: Item) -> None` (14)
  - `async def listing(self, kind: Kind) -> list[CardView]` (19)
  - `async def forget(self, kind: Kind, source: Source, source_id: str) -> None` (14)
  - `async def known(self, marks: list[tuple[Kind, Source, str]]) -> set[tuple[str, str, str]]` (20)

### `backend/storage/repository/sections.py` — 201 строк

Вопросы к отфильтрованному набору раздела.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.session`, `backend.storage.tables`

- `def _carrying(link: Table, key: Column, ids: tuple[int, ...]) -> Select` (6)
- `def _carrying_all(link: Table, key: Column, ids: tuple[int, ...]) -> Select` (16)
- `def _included(query: Select, filters: Filters) -> Select` (18)
- `def _excluded(query: Select, filters: Filters) -> Select` (23)
- `class SectionsRepository(Repository)` (84)
  - `async def ids(self, feed: Feed, limit: int, offset: int) -> list[int]` (15)
  - `async def histogram(self, kind: Kind, filters: Filters) -> Histogram` (35)
  - `def _narrow(self, query: Select, section: Section, kind: Kind, filters: Filters) -> Select` (16)

### `backend/storage/repository/tags.py` — 110 строк

Мои теги в базе.

Зависит от: `backend.model`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.tables`

- `class TagsRepository(Repository)` (97)
  - `async def create(self, kind: Kind, name: str) -> int` (17)
  - `async def list_for_kind(self, kind: Kind) -> list[Tag]` (7)
  - `async def reorder(self, kind: Kind, tag_ids: list[int]) -> None` (10)
  - `async def rename(self, tag_id: int, name: str) -> None` (6)
  - `async def usage(self, tag_id: int) -> int` (11)
  - `async def delete(self, tag_id: int) -> None` (2)
  - `async def assign(self, item_id: int, tag_id: int) -> None` (20)
  - `async def unassign(self, item_id: int, tag_id: int) -> None` (7)
  - `async def tags_of(self, item_id: int) -> list[Tag]` (8)

### `backend/storage/repository/views.py` — 183 строк

Пачечное чтение карточек для показа.

Зависит от: `backend.model`, `backend.storage.entity`, `backend.storage.repository.base`, `backend.storage.rows`, `backend.storage.tables`

- `class ViewsRepository(Repository)` (150)
  - `async def views_for(self, item_ids: list[int]) -> dict[int, CardView]` (5)
  - `async def in_order(self, item_ids: list[int]) -> list[CardView]` (9)
  - `async def _fetch_all(self, session: AsyncSession, item_ids: list[int]) -> dict[int, CardView]` (35)
  - `async def _genres(self, session, item_ids)` (9)
  - `async def _tags(self, session, item_ids)` (9)
  - `async def _credits(self, session, item_ids, entity: Entity)` (22)
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

### `backend/storage/rescale.py` — 79 строк

Приведение хранимых оценок к настроенной шкале.

Зависит от: `backend.config`, `backend.model`, `backend.storage.tables`

- `def rescaled(value: float | None, scale: int) -> int | None` (11)
- `async def apply_scale(sessions: async_sessionmaker[AsyncSession], scale: int) -> None` (30)
- `def _moved(row, scale: int) -> dict` (10)

### `backend/storage/rows.py` — 121 строк

Строки базы в типы границы слоёв.

Зависит от: `backend.model`, `backend.storage.entity`

- `def to_item(row: Row) -> Item` (20)
- `def to_genre(row: Row) -> Genre` (2)
- `def to_external_id(row: Row) -> ExternalId` (2)
- `def to_external_rating(row: Row) -> ExternalRating` (4)
- `def to_rating(row: Row) -> Rating` (11)
- `def to_tag(row: Row) -> Tag` (7)
- `def grouped(rows, column: str, make: Callable[[Row], object]) -> defaultdict[object, list]` (12)
- `def to_credit(row: Row, entity: Entity) -> Credit` (20)

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

### `backend/storage/tables/__init__.py` — 37 строк

Поверхность схемы: отсюда таблицы берут репозитории.

Зависит от: `backend.storage.tables.base`, `backend.storage.tables.catalog`, `backend.storage.tables.mine`

Отдаёт наружу: `company`, `company_credit`, `external_id`, `external_rating`, `genre`, `genre_rule`, `genre_rule_mark`, `item`, `item_genre`, `item_tag`, `metadata`, `person`, `person_credit`, `rating`, `removed`, `tag`, `wishlist`


### `backend/storage/tables/base.py` — 32 строк

Общее для всех объявлений схемы.

Зависит от: —

- `def item_fk(**kwargs: Any) -> Column` (6)
- `def genre_fk(**kwargs: Any) -> Column` (5)

### `backend/storage/tables/catalog.py` — 145 строк

Таблицы каталога: то, что наполняется из источников.

Зависит от: `backend.storage.tables.base`


### `backend/storage/tables/mine.py` — 80 строк

Таблицы моих данных: то, что заводит и правит человек.

Зависит от: `backend.storage.tables.base`


### `backend/unique.py` — 32 строк

Снятие повторов с сохранением порядка.

Зависит от: —

- `def unique(items: Iterable[T]) -> list[T]` (11)
- `def unique_by(items: Iterable[T], key: Callable[[T], Hashable]) -> list[T]` (14)

## bridge — 14 модулей

### `bridge/answer.py` — 71 строк

Оболочка вызова моста: срок, отказ, один формат ответа.

Зависит от: `backend.model`, `bridge.thread`, `bridge.wire`

- `def stale() -> dict` (5)
- `def kebab(name: str) -> str` (4)
- `class Domain` (39)
  - `def _reply(self, factory, op: int | None=None) -> dict` (30)

### `bridge/api.py` — 40 строк

Поверхность моста: семь доменов и отмена.

Зависит от: `bridge.answer`, `bridge.covers`, `bridge.feed`, `bridge.library`, `bridge.marks`, `bridge.refs`, `bridge.search`, `bridge.world`

- `class Api(Domain)` (24)
  - `def cancel(self, ops: list) -> dict` (3)
  - `async def _cancelled(self, ops: list) -> None` (2)

### `bridge/covers.py` — 37 строк

Мост: обложки — заливка своей картинки и наличие.

Зависит от: `backend.model`, `bridge.answer`

- `class Covers(Domain)` (11)
  - `def store_upload(self, item_id: int, data: str) -> dict` (7)
  - `def has(self, item_id: int) -> dict` (2)
- `def _picture(data: str) -> bytes` (11)

### `bridge/feed.py` — 55 строк

Мост: лента — страницы разделов и гистограмма.

Зависит от: `backend.model`, `bridge.answer`

- `class FeedBridge(Domain)` (25)
  - `def page(self, op: int, feed: dict, offset: int, limit: int) -> dict` (3)
  - `def views_of(self, op: int, item_ids: list) -> dict` (3)
  - `def histogram(self, op: int, kind: str, filters: dict) -> dict` (5)
- `def _feed(feed: dict) -> Feed` (10)
- `def _filters(filters: dict) -> Filters` (5)

### `bridge/kept.py` — 31 строк

То, что не пролезает обратно через JSON.

Зависит от: —

- `class Kept` (20)
  - `def put(self, op: int, value) -> None` (10)
  - `def taken(self, op: int)` (4)

### `bridge/library.py` — 103 строк

Мост: карточка целиком — заведение, правка, отвязка, удаление.

Зависит от: `backend.model`, `bridge.answer`

- `class Library(Domain)` (58)
  - `def create(self, fields: dict) -> dict` (15)
  - `def replace(self, item_id: int, fields: dict) -> dict` (10)
  - `def same_title(self, kind: str, title: str) -> dict` (5)
  - `def unlink(self, item_id: int) -> dict` (2)
  - `def deletion_summary(self, item_id: int) -> dict` (2)
  - `def delete(self, item_id: int) -> dict` (5)
  - `def restore(self, kind: str, source: str, source_id: str) -> dict` (8)
- `async def _over(back, item_id: int, fields: dict) -> None` (9)
- `def _known(fields: dict) -> dict` (16)
- `def _manual(fields: dict)` (5)

### `bridge/marks.py` — 66 строк

Мост: свои отметки — оценки, теги, закладки.

Зависит от: `backend.model`, `bridge.answer`

- `class Marks(Domain)` (55)
  - `def score(self, item_id: int, score: float | None) -> dict` (4)
  - `def aspects(self, item_id: int, visual: int | None, narrative: int | None, gameplay: int | None) -> dict` (8)
  - `def review(self, item_id: int, text: str) -> dict` (4)
  - `def clear_rating(self, item_id: int) -> dict` (2)
  - `def create_tag(self, kind: str, name: str) -> dict` (2)
  - `def tags(self, kind: str) -> dict` (2)
  - `def reorder_tags(self, kind: str, tag_ids: list) -> dict` (2)
  - `def rename_tag(self, tag_id: int, name: str) -> dict` (2)
  - `def tag_usage(self, tag_id: int) -> dict` (4)
  - `def delete_tag(self, tag_id: int) -> dict` (2)
  - `def assign(self, item_id: int, tag_id: int) -> dict` (2)
  - `def unassign(self, item_id: int, tag_id: int) -> dict` (2)
  - `def wish(self, item_id: int) -> dict` (3)
  - `def unwish(self, item_id: int) -> dict` (2)

### `bridge/refs.py` — 86 строк

Мост: справочники — жанры, люди, студии и шкала оценок.

Зависит от: `backend.model`, `bridge.answer`

- `class Refs(Domain)` (51)
  - `def genres(self, genre_kind: str) -> dict` (5)
  - `def suggest(self, domain: str, name: str, offset: int=0) -> dict` (8)
  - `def set_genres(self, item_id: int, genre_ids: list) -> dict` (7)
  - `def detach_all(self, domain: str, item_id: int) -> dict` (5)
  - `def attach(self, domain: str, item_id: int, entity_id: int, role: str, position: int) -> dict` (7)
  - `def scale(self) -> dict` (7)
  - `def create_person(self, domain: str, name: str) -> dict` (5)
- `async def _scale(back) -> int` (2)
- `def _role(domain: str, role: str)` (4)
- `def _of(backend, domain: str)` (7)

### `bridge/search.py` — 110 строк

Мост: поиск — своё, чужое, складывание, заведение найденного.

Зависит от: `backend.model`, `bridge.answer`, `bridge.kept`, `bridge.wire`

- `class Search(Domain)` (89)
  - `def local(self, op: int, kind: str, query: str) -> dict` (12)
  - `def external(self, op: int) -> dict` (18)
  - `def by_person(self, op: int, domain: str, entity_id: int, kind: str) -> dict` (11)
  - `def ensure(self, op: int, source: str, source_id: str) -> dict` (8)
  - `async def _own(self, back, op, kind, query)` (6)
  - `async def _outer(self, back, op, kind, query)` (15)
  - `async def _person(self, back, op, domain, entity_id, kind)` (4)
  - `async def _added(self, back, candidate)` (2)
- `def _found(views, source: str, source_id: str)` (7)

### `bridge/serve.py` — 147 строк

Страница, ресурсы и обложки по HTTP.

Зависит от: `backend.model`, `bridge.thread`

- `class Page` (70)
  - `def __call__(self, environ, start_response)` (6)
  - `def _file(self, path: str, start_response)` (23)
  - `def _poster(self, query: dict, start_response)` (32)
- `async def _fetched(back, item, source, url)` (12)
- `def _looks_like(picture: bytes) -> str` (5)
- `def _single(query: dict, name: str) -> str | None` (3)
- `def _answer(start_response, status: str, kind: str, body: bytes, cache: str | None=None)` (7)

### `bridge/thread.py` — 189 строк

Поток бэкенда: свой цикл asyncio, список живых задач, отмена всех разом.

Зависит от: —

- `class Closed(Exception)` (2)
- `class BackendThread` (160)
  - `def start(self) -> None` (5)
  - `def run(self, factory: Callable[[Any], Coroutine], op: int | None=None) -> concurrent.futures.Future` (10)
  - `def cancel(self, ops) -> None` (16)
  - `def close(self) -> None` (13)
  - `def _live(self) -> None` (21)
  - `def _refuse(self, error: BaseException) -> None` (6)
  - `def _begin(self, factory, op, answer) -> None` (23)
  - `def _end(self, task, op, answer) -> None` (15)
  - `def _finish(self, done) -> None` (6)
  - `async def _shutdown(self, done) -> None` (17)

### `bridge/window.py` — 69 строк

Окно приложения и проверка того, чем оно рисует.

Зависит от: `bridge.api`, `bridge.serve`

- `def supported(renderer: str | None) -> bool` (2)
- `def open_window(thread, debug: bool=False) -> None` (16)
- `def _check_renderer() -> None` (6)

### `bridge/wire.py` — 55 строк

Значения границы в то, что переживёт `json.dumps`.

Зависит от: `backend.model`

- `def to_wire(value)` (29)
- `def outcome(value) -> dict` (11)

### `bridge/world.py` — 134 строк

Мост: всё, что смотрит наружу, — привязка по ссылке, перезапрос сериала,

Зависит от: `backend.model`, `bridge.answer`, `bridge.kept`, `bridge.wire`

- `class BadLink(Denied)` (6)
- `class ForeignScheme(Denied)` (5)
- `class World(Domain)` (71)
  - `def parse(self, raw: str, kind: str | None) -> dict` (10)
  - `def card_for_link(self, op: int, raw: str, kind: str | None) -> dict` (4)
  - `def link(self, op: int, item_id: int, overwrite: bool) -> dict` (10)
  - `def refresh_series(self, op: int, item_id: int) -> dict` (4)
  - `def enrich(self, op: int, item_id: int, kind: str) -> dict` (5)
  - `def expected(self, op: int, kind: str) -> dict` (9)
  - `def open(self, url: str) -> dict` (8)
  - `async def _asked(self, back, op, raw, kind)` (9)
- `async def _parsed(raw: str, kind: str | None)` (2)
- `async def _expected(back, kind: str)` (2)
- `async def _opened(url: str) -> None` (9)
- `def _link(raw: str, kind: str | None)` (8)
- `def _kind(kind: str | None) -> Kind | None` (4)

## migrations — 9 модулей

### `migrations/env.py` — 62 строк

Точка входа Alembic: адрес базы и соединение под миграции.

Зависит от: `backend.config`, `backend.storage.session`, `backend.storage.tables`

- `def database_path() -> Path` (7)
- `def database_url() -> str` (7)
- `def migrate() -> None` (15)
  - `def prepare(dbapi_connection, _record)` (2)

### `migrations/reference/gog.py` — 134 строк

Соответствия GOG: жанры и теги магазина одним пространством.

Зависит от: `migrations.reference.rule`


### `migrations/reference/names.py` — 20 строк

Имена наших жанров: два набора, кино и игры.

Зависит от: —


### `migrations/reference/old_games.py` — 26 строк

Соответствия old-games.ru: пятнадцать жанров на весь сайт, у игры один.

Зависит от: `migrations.reference.rule`


### `migrations/reference/rule.py` — 29 строк

Форма правила справочника: как оно записано в объявлениях.

Зависит от: —

- `class Rule(NamedTuple)` (20)
  - `def required(self) -> list[str]` (2)
  - `def forbidden(self) -> list[str]` (2)
- `def _split(written: str) -> list[str]` (2)

### `migrations/reference/steam.py` — 252 строк

Соответствия Steam: жанры и теги магазина одним пространством.

Зависит от: `migrations.reference.rule`


### `migrations/reference/tmdb.py` — 40 строк

Соответствия TMDB: чужой номер жанра — наш киножанр.

Зависит от: `migrations.reference.rule`


### `migrations/versions/0001_schema.py` — 195 строк

Схема целиком: шестнадцать таблиц каталога и моих данных.

Зависит от: —

- `def upgrade() -> None` (147)
- `def downgrade() -> None` (27)

### `migrations/versions/0002_genres.py` — 76 строк

Справочник жанров и правила, ведущие к ним.

Зависит от: `migrations.reference.gog`, `migrations.reference.names`, `migrations.reference.old_games`, `migrations.reference.steam`, `migrations.reference.tmdb`

- `def upgrade() -> None` (23)
- `def _marks(connection, rule_id: int, rule) -> None` (10)
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

### `scripts/record_fixtures.py` — 281 строк

Разовая запись живых ответов источников в tests/fixtures/.

Зависит от: `backend.config`, `backend.sources.http`, `backend.sources.steam.client`

- `def save(source: str, case: str, response: httpx.Response) -> None` (23)
- `async def record_tmdb(client: httpx.AsyncClient, key: str) -> None` (34)
- `async def record_steam(client: httpx.AsyncClient) -> None` (14)
- `async def record_steam_items(client: httpx.AsyncClient) -> None` (38)
  - `def ask(appids: list[int], wanted: dict) -> str` (7)
- `async def record_gog(client: httpx.AsyncClient) -> None` (24)
- `async def record_mdblist(client: httpx.AsyncClient, key: str) -> None` (11)
- `async def record_omdb(client: httpx.AsyncClient, key: str) -> None` (13)
- `async def record_kinopoisk_unofficial(client: httpx.AsyncClient, key: str) -> None` (19)
- `async def record_oldgames(client: httpx.AsyncClient) -> None` (16)
- `async def main() -> None` (22)

## tests — 102 модулей

### `tests/alembic_runner.py` — 21 строк

Запуск миграций из теста.

Зависит от: —

- `def alembic(db_path: Path, *command: str) -> None` (10)

### `tests/backend/conftest.py` — 49 строк

Фикстуры проверок бэкенда, общие у соседних модулей.

Зависит от: `backend.model`, `backend.service.enrich`, `backend.storage.repository.external`, `backend.storage.repository.library`, `tests.conftest`, `tests.wiring`

- `async def item_id(sessions)` (8)
- `async def service(sessions)` (5)
- `async def enrich(sessions)` (12)
  - `def build(*clients) -> Enricher` (7)

### `tests/backend/enriching.py` — 48 строк

Общее у проверок третьего круга: подставные оценочные клиенты и карточка.

Зависит от: `backend.model`, `backend.storage.repository.external`, `tests.conftest`

- `class FakeRatings(FakeClient)` (11)
  - `async def ratings(self, imdb_id: str, kind: Kind)` (3)
- `class Breaking(FakeRatings)` (7)
  - `async def ratings(self, imdb_id: str, kind: Kind)` (3)
- `def found(*pairs) -> Found` (4)
- `async def stored_ratings(sessions, item_id) -> dict` (3)

### `tests/backend/sources/conftest.py` — 82 строк

Записанные ответы источников: живьём тесты не ходят никуда.

Зависит от: `tests.builders`

- `def _meta(relative: str) -> dict` (3)
- `def fixture()` (3)
- `def meta()` (2)
- `def gog_catalog()` (21)
  - `def handler(request: httpx.Request) -> httpx.Response` (6)
- `def replay()` (33)
  - `def build(*relatives: str) -> httpx.MockTransport` (21)
    - `def handler(request: httpx.Request) -> httpx.Response` (7)

### `tests/backend/sources/test_convert.py` — 124 строк

Общее у разборов: перевод чужих кусков ответа в наши типы.

Зависит от: `backend.model`, `backend.sources.convert`, `tests.conftest`

Тестов: 14


### `tests/backend/sources/test_gog.py` — 495 строк ⚠ подошёл к 300

GOG: поиск не умеет отвечать «не найдено», и отрицательный факт отсюда не

Зависит от: `backend.model`, `backend.sources.gog.client`, `backend.sources.gog.parse`, `backend.sources.http`, `tests.conftest`

Тестов: 32

- `def answering(body) -> SourceHttp` (3)

### `tests/backend/sources/test_gog_slug.py` — 161 строк

Слаг из адреса GOG в номер каталога.

Зависит от: `backend.model`, `backend.sources.gog.client`, `backend.sources.gog.parse`, `backend.sources.http`

Тестов: 15

- `def client(handler) -> GogClient` (2)

### `tests/backend/sources/test_http.py` — 445 строк ⚠ подошёл к 300

Общая дверь в сеть: заголовок, таймауты и предохранитель.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.undocumented`, `tests.conftest`

Тестов: 26


### `tests/backend/sources/test_kinopoisk.py` — 360 строк ⚠ подошёл к 300

Кинопоиск: два зеркала под одним именем, и телу здесь верить нельзя.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.kinopoisk.poiskkino`, `backend.sources.ratings.kinopoisk.unofficial`, `tests.conftest`

Тестов: 22

- `def primary(transport) -> PoiskkinoClient` (2)
- `def fallback(transport) -> UnofficialClient` (2)

### `tests/backend/sources/test_kinopoisk_unofficial.py` — 174 строк

Запасное зеркало Кинопоиска: оценка, отказы и дозапрос карточки.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.ratings.kinopoisk.mirror`, `backend.sources.ratings.kinopoisk.unofficial`, `tests.conftest`

Тестов: 11

- `def fallback(transport) -> UnofficialClient` (2)

### `tests/backend/sources/test_mdblist.py` — 255 строк

MDBList: квота, битый ключ и чужой периметр — три разные беды.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.mdblist.parse`, `tests.conftest`

Тестов: 21

- `async def ask(transport, kind=Kind.MOVIE)` (5)

### `tests/backend/sources/test_oldgames.py` — 461 строк ⚠ подошёл к 300

Разбор страниц old-games.ru: выдача и карточка.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.oldgames.client`, `backend.sources.oldgames.parse`, `tests.conftest`

Тестов: 34

- `async def searched(transport: httpx.MockTransport, query: str='dune')` (7)
- `def busy(page: str, times: int)` (14)
  - `def handler(request: httpx.Request) -> httpx.Response` (5)

### `tests/backend/sources/test_omdb.py` — 290 строк

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

### `tests/backend/sources/test_registry.py` — 290 строк

Реестр держится на том, что контракт у всех клиентов один.

Зависит от: `backend.config`, `backend.model`, `backend.sources.build`, `backend.sources.gog.client`, `backend.sources.oldgames.client`, `backend.sources.ratings.kinopoisk.client`, `backend.sources.ratings.mdblist.client`, `backend.sources.ratings.omdb.client`, `backend.sources.steam.client`, `backend.sources.tmdb.client`, `tests.conftest`

Тестов: 17

- `def sources()` (4)
- `async def registry()` (9)
- `def keyed()` (12)

### `tests/backend/sources/test_steam.py` — 303 строк ⚠ подошёл к 300

Steam: отсутствие игры приходит под кодом 200, а теги — вторым запросом.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.steam.client`, `backend.sources.steam.parse`, `tests.conftest`

Тестов: 23

- `def block_of(payload: dict) -> dict` (2)

### `tests/backend/sources/test_steam_items.py` — 452 строк ⚠ подошёл к 300

Ответ `GetItems`: род товара в выдаче и настоящий адрес обложки.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.steam.client`, `backend.sources.steam.parse`

Тестов: 22

- `def two_answers(first: list | dict, items, opens: str='SearchApps')` (13)
  - `def handler(request: httpx.Request) -> httpx.Response` (5)
- `async def searched(transport: httpx.MockTransport, query: str='arcanum')` (5)
- `def assets_of(payload: dict, appid: str) -> dict` (4)

### `tests/backend/sources/test_steam_tags.py` — 218 строк

Теги Steam: отдельный запрос, три состояния ответа и сверка номера.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.steam.client`, `backend.sources.steam.parse`

Тестов: 11


### `tests/backend/sources/test_tmdb_card.py` — 429 строк ⚠ подошёл к 300

Второй круг загрузки: карточка, которую уже можно записать.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.tmdb.client`, `backend.sources.tmdb.parse`

Тестов: 33


### `tests/backend/sources/test_tmdb_failures.py` — 187 строк

Отказ TMDB отличается от «такого у меня нет» — и то, и другое от успеха.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.tmdb.client`, `tests.conftest`

Тестов: 15

- `async def ask(transport: httpx.MockTransport)` (5)

### `tests/backend/sources/test_tmdb_people.py` — 170 строк

Фильмография человека и поиск человека по имени.

Зависит от: `backend.model`, `backend.sources.http`, `backend.sources.tmdb.client`, `backend.sources.tmdb.parse`, `tests.conftest`

Тестов: 13


### `tests/backend/sources/test_tmdb_search.py` — 187 строк

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

### `tests/backend/test_by_credit.py` — 155 строк

Всё с этим человеком и с этой студией.

Зависит от: `backend.model`, `backend.service.library`, `backend.storage.repository.credits`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 10


### `tests/backend/test_card_writer.py` — 414 строк ⚠ подошёл к 300

Запись карточки источника в базу целиком — или ничего.

Зависит от: `backend.model`, `backend.service.cards`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 22

- `def source_card(**overrides) -> SourceCard` (17)
- `def game_card(source_id: str='292030', **overrides) -> SourceCard` (10)
- `def another_movie(source_id: str, **overrides) -> SourceCard` (9)
- `async def build(sessions, engine, posters, transport=None) -> CardWriter` (9)
- `async def writer(sessions, engine, posters)` (4)

### `tests/backend/test_config.py` — 87 строк

Чтение настроек из окружения и путей к файлам данных.

Зависит от: `backend.config`

Тестов: 11


### `tests/backend/test_cover_reads.py` — 93 строк

Обложка видимой карточки: лежащая отдаётся, недостающая скачивается.

Зависит от: `backend.model`, `tests.conftest`

Тестов: 7

- `async def covers(posters)` (5)

### `tests/backend/test_credit_search.py` — 106 строк

Строка поиска: широкий общий поиск по людям, названию и оригинальному.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.library`, `tests.builders`

Тестов: 6


### `tests/backend/test_credits.py` — 377 строк ⚠ подошёл к 300

Люди и студии: одна реализация на две сущности, и различает их идентичность.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.library`

Тестов: 28


### `tests/backend/test_dangling.py` — 55 строк

Карточку удалили, пока по ней шла работа: что делает доехавшая запись.

Зависит от: `backend.model`, `backend.storage.repository.external`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 3


### `tests/backend/test_delete.py` — 156 строк

Удаление карточки из двух файлов базы и что пропадает вместе с ней.

Зависит от: `backend.model`, `backend.service.posters`, `backend.service.removal`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 9

- `async def service(posters)` (8)
- `async def furnished(sessions, posters, item_id: int, tag: str='пересмотреть') -> int` (9)

### `tests/backend/test_denied.py` — 78 строк

Отказ операции — нормальный ход событий, и клиент обязан их различать.

Зависит от: `backend.model`, `backend.service.images`, `backend.storage.posters`, `backend.storage.repository.external`, `backend.storage.repository.tags`

Тестов: 5


### `tests/backend/test_enrich.py` — 365 строк ⚠ подошёл к 300

Третий круг: оценки агрегаторов и сроки их годности.

Зависит от: `backend.model`, `backend.storage.repository.external`, `backend.storage.repository.library`, `tests.backend.enriching`, `tests.conftest`

Тестов: 23


### `tests/backend/test_enrich_identifiers.py` — 105 строк

Чем спрашивают агрегаторов и что запоминают из их ответа.

Зависит от: `backend.model`, `backend.storage.repository.external`, `backend.storage.repository.library`, `tests.backend.enriching`, `tests.conftest`

Тестов: 4


### `tests/backend/test_external_ids.py` — 120 строк

Внешние идентификаторы: всё, что не основной источник карточки.

Зависит от: `backend.model`, `backend.storage.repository.external`, `backend.storage.repository.library`

Тестов: 8


### `tests/backend/test_external_ratings.py` — 234 строк

Оценки агрегаторов: три состояния и сроки годности.

Зависит от: `backend.model`, `backend.storage.repository.external`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 14


### `tests/backend/test_feed.py` — 132 строк

Страница раздела и перерисовка одной карточки.

Зависит от: `backend.model`, `backend.service.library`, `backend.storage.repository.tags`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 9

- `async def feed(sessions, sections)` (2)
- `class Forgetful(ViewsRepository)` (13)
  - `async def views_for(self, item_ids: list[int]) -> dict` (4)

### `tests/backend/test_filters.py` — 295 строк

Отбор ленты фильтрами: включённые, исключённые и их сочетания.

Зависит от: `backend.model`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 13

- `async def library(sessions)` (2)

### `tests/backend/test_genre_reference.py` — 236 строк

Справочник жанров из миграции против записанного эталона.

Зависит от: `tests.alembic_runner`

Тестов: 11

- `def named(connection, source: str, ext_id: str) -> set[str]` (14)
- `def counted(connection, table: str, where: str='') -> int` (4)
- `def declared_in_migration() -> dict[str, list[list]]` (8)

### `tests/backend/test_genre_resolution.py` — 100 строк

Разрешение чужих меток карточки: то, что видно в самом списке наших номеров.

Зависит от: `backend.model`, `backend.service.genres`, `backend.storage.repository.genres`, `tests.conftest`

Тестов: 6

- `async def genres(engine, sessions)` (3)

### `tests/backend/test_genre_rules.py` — 247 строк

Правила справочника: набор чужих меток на входе, набор наших жанров на выходе.

Зависит от: `backend.model`, `backend.service.genres`, `backend.sources.gog.parse`, `backend.sources.steam.parse`, `backend.storage.repository.genres`, `backend.storage.session`, `tests.alembic_runner`

Тестов: 21

- `def stocked(tmp_path_factory)` (7)
- `async def book(stocked)` (6)
- `def names(genres) -> list[str]` (2)

### `tests/backend/test_genres.py` — 155 строк

Жанры карточки в базе: чтение справочника и запись набора.

Зависит от: `backend.model`, `backend.service.genres`, `backend.storage.repository.genres`

Тестов: 12


### `tests/backend/test_histogram.py` — 226 строк

Гистограмма своих оценок по отфильтрованному набору.

Зависит от: `backend.model`, `backend.storage.repository.genres`, `backend.storage.repository.sections`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 19

- `async def columns(sections, kind: Kind=Kind.MOVIE, **filters) -> dict[int, int]` (3)

### `tests/backend/test_images.py` — 135 строк

Обрезка залитой руками картинки до формы обложки.

Зависит от: `backend.service.images`, `tests.conftest`

Тестов: 15

- `def painted(size: tuple[int, int], band: tuple[int, int, int, int]) -> bytes` (7)
- `def size_of(data: bytes) -> tuple[int, int]` (2)
- `def red_box(data: bytes) -> tuple[int, int, int, int] | None` (6)

### `tests/backend/test_language.py` — 83 строк

На каком языке написано название.

Зависит от: `backend.language`

Тестов: 7


### `tests/backend/test_layers.py` — 124 строк

Граница слоёв: кто кого имеет право импортировать.

Зависит от: —

Тестов: 5

- `def imported_modules(path: Path)` (10)
- `def imported_roots(path: Path)` (4)
- `def python_files(package: str) -> list[Path]` (7)
- `def offenders(package: str, banned: set[str]) -> list[str]` (7)
- `def reaching_backend(package: str, allowed: set[str]) -> list[str]` (14)

### `tests/backend/test_library.py` — 402 строк ⚠ подошёл к 300

Репозиторий библиотеки: карточка, окна и поиск по названию.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 26

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

### `tests/backend/test_linking.py` — 447 строк ⚠ подошёл к 300

Привязка ручной карточки к внешней базе и правила слияния.

Зависит от: `backend.model`, `backend.service.linking`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `tests.conftest`

Тестов: 29

- `def incoming(**overrides) -> SourceCard` (12)
- `def mine(**fields) -> Item` (4)
- `async def linker(sessions, engine, posters)` (5)
- `async def manual_card(sessions, **fields) -> int` (5)

### `tests/backend/test_links.py` — 136 строк

Разбор вставленной ссылки на карточку источника.

Зависит от: `backend.model`, `backend.model.link`

Тестов: 14


### `tests/backend/test_loading.py` — 515 строк ⚠ за пределом 500

Три круга загрузки: кандидат становится карточкой в базе.

Зависит от: `backend.model`, `backend.service.cards`, `backend.service.loading`, `backend.service.posters`, `backend.storage.repository.library`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 25

- `def candidate(source_id='157336', poster=SEARCH_COVER) -> CardView` (6)
- `def source_card(source_id='157336', poster=DETAIL_COVER) -> SourceCard` (7)
- `class Rig` (8)
- `async def loader(sessions, posters)` (19)
  - `def build(outcome, poster_status: int=200) -> Rig` (13)

### `tests/backend/test_manual_cards.py` — 213 строк

Ручная карточка: заведение, правка и отвязка от источника.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `tests.conftest`

Тестов: 14


### `tests/backend/test_merge_results.py` — 92 строк

Складывание своей выдачи с чужой: порядок половин и снятие близнецов.

Зависит от: `backend.model`, `tests.conftest`

Тестов: 8

- `def local_view(source_id='157336', title='Интерстеллар') -> CardView` (3)

### `tests/backend/test_merging.py` — 260 строк

Что склеивается в одну строку выдачи, а что остаётся порознь.

Зависит от: `backend.model`, `backend.service.merging`, `tests.builders`

Тестов: 17


### `tests/backend/test_merging_sets.py` — 92 строк

Сборники в выдачу не попадают — кроме того, который спросили прямо.

Зависит от: `backend.model`, `backend.service.merging`, `tests.builders`

Тестов: 6


### `tests/backend/test_merging_winner.py` — 179 строк

Кто побеждает в группе склейки и что забирает у проигравших.

Зависит от: `backend.model`, `backend.service.merging`, `tests.builders`

Тестов: 10


### `tests/backend/test_migrations.py` — 126 строк

Схема из миграций против схемы из объявлений.

Зависит от: `backend.storage.tables`, `tests.alembic_runner`, `tests.conftest`

Тестов: 4

- `def declared(db_path: Path) -> None` (5)
- `def table_shape(inspector, name: str) -> dict` (29)
- `def shape(db_path: Path) -> dict` (12)
- `def stamped(db_path: Path) -> list[str]` (8)

### `tests/backend/test_model.py` — 171 строк

Типы границы слоёв: их поля, значения и неизменность.

Зависит от: `backend`, `backend.model`, `tests.conftest`

Тестов: 10

- `def boundary_dataclasses()` (15)
- `def boundary_denials()` (14)

### `tests/backend/test_offline.py` — 456 строк ⚠ подошёл к 300

Главное обещание приложения: без сети работает всё, кроме поиска чужого.

Зависит от: `backend.app`, `backend.config`, `backend.model`, `backend.service.posters`, `backend.storage.posters`, `backend.storage.repository.external`, `backend.storage.session`, `backend.storage.tables`, `tests.conftest`

Тестов: 23

- `def mine(title: str, **fields)` (4)
- `async def assemble(tmp_path, transport=None)` (8)
- `async def offline(tmp_path)` (4)

### `tests/backend/test_outcome.py` — 43 строк

Три исхода запроса к источнику: что обязательно, что неизменно и как причина

Зависит от: `backend.model`

Тестов: 3


### `tests/backend/test_people_search.py` — 416 строк ⚠ подошёл к 300

Клик по человеку и студии: внутренняя половина и внешняя.

Зависит от: `backend.model`, `backend.service.people`, `backend.service.search`, `backend.storage.repository.credits`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.removed`, `backend.storage.repository.views`, `tests.conftest`

Тестов: 22

- `def parts(sessions)` (9)
- `def finder_on(parts, client) -> PeopleSearch` (5)
- `async def a_person(parts, name='Кристофер Нолан', source_id=None) -> int` (6)
- `def outside_questions(asked: list[tuple]) -> list[tuple]` (4)

### `tests/backend/test_poster_service.py` — 261 строк

Путь обложки от источника до хранилища.

Зависит от: `backend.model`, `backend.service.images`, `backend.service.posters`, `backend.sources.http`, `backend.storage.posters`, `tests.conftest`

Тестов: 19

- `async def service(posters)` (4)

### `tests/backend/test_posters.py` — 195 строк

Хранилище постеров вторым файлом базы.

Зависит от: `backend.storage.posters`, `backend.storage.session`, `tests.conftest`

Тестов: 16


### `tests/backend/test_ratings.py` — 258 строк

Своя оценка карточки и её пересчёт.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.tables`, `tests.conftest`

Тестов: 19

- `async def _rated_at(engine, item_id)` (8)

### `tests/backend/test_relevance.py` — 218 строк

Строка выдачи обязана знать, о чём её спросили.

Зависит от: `backend.model`, `backend.service.relevance`, `backend.service.search`, `tests.builders`, `tests.conftest`, `tests.wiring`

Тестов: 12

- `def row(title: str, *, original_title: str='', aliases: tuple[str, ...]=()) -> SearchHit` (5)

### `tests/backend/test_removed.py` — 276 строк

Удалённое не возвращается: карточка уходит, а память о ней остаётся.

Зависит от: `backend.model`, `backend.service.hits`, `backend.service.removal`, `backend.service.search`, `backend.storage.repository.library`, `backend.storage.repository.removed`, `tests.conftest`, `tests.wiring`

Тестов: 17

- `async def removed(sessions)` (2)
- `def a_game(source_id: str='38410', title: str='Fallout 2', source: Source=Source.STEAM)` (3)
- `async def rows(engine) -> list[tuple]` (7)

### `tests/backend/test_rescale.py` — 172 строк

Приведение хранимых оценок к настроенной шкале.

Зависит от: `backend.app`, `backend.config`, `backend.model`, `backend.storage`, `backend.storage.repository.ratings`, `backend.storage.rescale`, `backend.storage.session`, `backend.storage.tables`, `tests.conftest`

Тестов: 10

- `async def game_with_aspects(sessions, visual, narrative, gameplay) -> int` (8)
- `async def stored_mark(sessions) -> int` (3)
- `async def built_on(tmp_path, scale: str)` (6)

### `tests/backend/test_restore.py` — 149 строк

Список убранного: шесть слов в строке поиска показывают его вместо выдачи.

Зависит от: `backend.model`, `backend.storage.repository.removed`, `tests.conftest`, `tests.wiring`

Тестов: 8

- `async def removed(sessions)` (2)
- `def a_game(source_id: str='38410', title: str='Fallout 2', source: Source=Source.STEAM)` (3)

### `tests/backend/test_search.py` — 446 строк ⚠ подошёл к 300

Поиск по чужим базам: выдача, отказы и переплетение выдач — как двух

Зависит от: `backend.model`, `backend.service.search`, `tests.conftest`

Тестов: 27


### `tests/backend/test_search_genres.py` — 161 строк

Жанры кандидата: чужие метки разворачиваются нашим справочником.

Зависит от: `backend.model`, `backend.storage.repository.genres`, `tests.conftest`

Тестов: 9


### `tests/backend/test_search_local.py` — 157 строк

Поиск по своей базе — единственный, который работает без сети.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.tags`, `tests.conftest`, `tests.wiring`

Тестов: 12

- `async def search(sessions)` (4)

### `tests/backend/test_sections.py` — 343 строк ⚠ подошёл к 300

Запросы разделов: что раздел показывает, в каком порядке и какой порцией.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 18

- `async def library(sessions)` (2)
- `async def _rated_then_changed(sessions, library) -> list[int]` (18)

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

### `tests/backend/test_startup.py` — 161 строк

Запуск готовит рабочую папку сам: папка, файл настроек и схема базы.

Зависит от: `backend.config`, `backend.startup`

Тестов: 8

- `def a_template(folder: Path) -> Path` (4)
- `def _read_by_settings() -> set[str]` (6)
- `def _genres_in(path: Path) -> int` (8)
- `def _variables_of(text: str) -> set[str]` (3)

### `tests/backend/test_suggestions.py` — 229 строк

Подсказка при вводе имени: тёзок различают по узнаваемой карточке.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.ratings`, `backend.storage.repository.wishlist`, `backend.storage.tables`, `tests.conftest`

Тестов: 16

- `async def person_with(sessions, name: str, item_ids: list[int]) -> int` (6)

### `tests/backend/test_tables.py` — 208 строк

Объявленная схема: таблицы, индексы, ключи и ограничения.

Зависит от: `backend.storage.tables`, `tests.conftest`

Тестов: 10

- `async def counted(engine, table_name: str) -> int` (5)
- `async def put(engine, table_name: str, **values) -> None` (4)

### `tests/backend/test_tags.py` — 359 строк ⚠ подошёл к 300

Свои теги: заведение, привязка к карточке и порядок.

Зависит от: `backend.model`, `backend.storage.repository.tags`

Тестов: 28


### `tests/backend/test_titles.py` — 114 строк

Приведение чужого названия к сравнимому виду.

Зависит от: `backend.service.titles`

Тестов: 9


### `tests/backend/test_view_types.py` — 110 строк

Карточка для показа: сборка из кандидата и из строки базы.

Зависит от: `backend.model`, `tests.conftest`

Тестов: 9


### `tests/backend/test_views.py` — 374 строк ⚠ подошёл к 300

Пачечное чтение страницы: девять запросов на любое число карточек.

Зависит от: `backend.model`, `backend.storage.repository.credits`, `backend.storage.repository.external`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.ratings`, `backend.storage.repository.tags`, `backend.storage.repository.views`, `backend.storage.repository.wishlist`, `tests.conftest`

Тестов: 20

- `async def item_id(sessions)` (4)

### `tests/backend/test_wishlist.py` — 128 строк

Список запланированного: закладка, порядок и порции.

Зависит от: `backend.storage.repository.wishlist`, `backend.storage.tables`, `tests.conftest`

Тестов: 10


### `tests/bridge/conftest.py` — 203 строк

Двойники бэкенда и потоки на них.

Зависит от: `bridge.thread`

- `class FakeBackend` (66)
  - `async def echo(self, value)` (2)
  - `async def where(self)` (2)
  - `async def moment(self)` (4)
  - `async def ident(self)` (2)
  - `async def boom(self)` (2)
  - `async def slow(self)` (7)
  - `async def held(self)` (9)
  - `async def release(self)` (2)
  - `async def together(self, total)` (7)
  - `async def aclose(self)` (6)
- `async def ready(value)` (3)
- `def wait_until(condition, timeout=5.0)` (8)
- `class Asked` (33)
  - `def __getattr__(self, name)` (2)
  - `def __call__(self, *args, **kwargs)` (9)
  - `async def aclose(self)` (3)
- `async def _raising(error)` (2)
- `def backend()` (2)
- `def asked()` (3)
- `def spy(asked)` (4)
- `class Watched(BackendThread)` (14)
  - `def run(self, factory, op=None)` (3)
- `def _running(running)` (7)
- `def thread(backend)` (3)
- `class Scaled` (11)
  - `async def aclose(self) -> None` (2)
- `def scaled()` (3)

### `tests/bridge/test_answer.py` — 108 строк

Один формат ответа на все операции: `{"ok": ...}` либо `{"fail": ...}`.

Зависит от: `backend.model`, `bridge.answer`, `tests.bridge.conftest`

Тестов: 10

- `class Probe(Domain)` (5)
  - `def ask(self, what, op=None)` (2)

### `tests/bridge/test_bridge_covers.py` — 52 строк

Мост: обложки — заливка своей картинки и наличие.

Зависит от: `backend.model`, `bridge.covers`

Тестов: 4


### `tests/bridge/test_bridge_feed.py` — 163 строк

Мост: лента — страницы разделов и гистограмма.

Зависит от: `backend.model`, `bridge.feed`

Тестов: 11


### `tests/bridge/test_bridge_library.py` — 193 строк

Мост: карточка целиком — заведение, правка, отвязка, удаление.

Зависит от: `backend.model`, `bridge.library`, `tests.builders`

Тестов: 13


### `tests/bridge/test_bridge_marks.py` — 200 строк

Мост: свои отметки — оценки, теги, закладки.

Зависит от: `backend.model`, `bridge.marks`

Тестов: 15


### `tests/bridge/test_bridge_refs.py` — 134 строк

Мост: справочники — жанры, люди, студии.

Зависит от: `backend.model`, `bridge.refs`

Тестов: 11


### `tests/bridge/test_bridge_search.py` — 377 строк ⚠ подошёл к 300

Мост: поиск — своё, чужое, складывание, заведение найденного.

Зависит от: `backend.model`, `bridge.search`

Тестов: 21

- `def a_view(source_id, item_id=None, title='Одиссея', source=Source.TMDB)` (3)

### `tests/bridge/test_bridge_surface.py` — 216 строк

Каждый вызов, который мост делает бэкенду, обязан ему подходить.

Зависит от: `backend.app`, `bridge.api`, `bridge.refs`

Тестов: 9

- `def chain(node)` (16)
- `def _chooses(node) -> bool` (5)
- `def calls() -> dict[str, dict[str, tuple]]` (15)
- `def fields_read() -> set[str]` (16)
- `def flat() -> list[tuple]` (4)
- `def surface(api) -> set[str]` (13)
- `def _behind(where, step)` (6)

### `tests/bridge/test_bridge_world.py` — 203 строк

Мост: внешний мир — привязка, перезапрос, оценки агрегаторов.

Зависит от: `backend.model`, `bridge.world`

Тестов: 15


### `tests/bridge/test_kept.py` — 60 строк

То, что не пролезает обратно через JSON, мост помнит у себя.

Зависит от: `bridge.kept`

Тестов: 5


### `tests/bridge/test_page_contract.py` — 400 строк ⚠ подошёл к 300

Имена, которые страница и мост обязаны называть одинаково.

Зависит от: `backend.config`, `backend.model`, `bridge.answer`, `bridge.api`, `bridge.feed`

Тестов: 23

- `def source(path: str) -> str` (2)
- `def named_in_chosen() -> set[str]` (4)
- `def values_of(table: str, text: str) -> set[str]` (4)
- `def body_of(table: str, text: str) -> str` (14)
- `def keys_of(table: str, text: str) -> set[str]` (2)
- `def keys_and_values(table: str, text: str) -> dict[str, str]` (6)
- `def paths_of_the_page(domains: set[str]) -> set[tuple[str, str]]` (8)

### `tests/bridge/test_serve.py` — 226 строк

Отдача страницы, ресурсов и обложек.

Зависит от: `backend.model`, `bridge.serve`

Тестов: 16

- `def call(page, path, query='')` (10)
  - `def start(status, headers)` (3)

### `tests/bridge/test_thread.py` — 285 строк

Граница потоков: что обязано быть правдой у стыка двух циклов.

Зависит от: `bridge.thread`, `tests.bridge.conftest`

Тестов: 22


### `tests/bridge/test_window.py` — 126 строк

Решение по рендереру и настройка лога. Окно здесь не поднимается ни разу.

Зависит от: `bridge.api`, `bridge.serve`, `bridge.thread`, `bridge.window`

Тестов: 8


### `tests/bridge/test_wire.py` — 143 строк

Перевод значений границы в то, что переживёт `json.dumps` без своего

Зависит от: `backend.model`, `bridge.wire`

Тестов: 15


### `tests/builders.py` — 116 строк

Строители данных для тестов: карточки, кандидаты, картинки, записанное.

Зависит от: `backend.model`, `backend.storage.repository.library`, `backend.storage.repository.ratings`

- `def recorded(relative: str)` (9)
- `def an_item(source_id: str, title: str, **fields) -> Item` (15)
- `async def rated(sessions, source_id: str, score: float | None, **fields) -> int` (12)
- `def picture(width: int, height: int, fmt: str='PNG') -> bytes` (6)
- `def hit(source_id: str='157336', title: str='Интерстеллар', **fields) -> SearchHit` (16)
- `def row(source: Source, source_id: str, title: str, **fields) -> SearchHit` (8)
- `def titles(answers: list[list[SearchHit]]) -> list[str]` (3)

### `tests/conftest.py` — 257 строк

Фикстуры тестов и поверхность общего.

Зависит от: `backend.config`, `backend.model`, `backend.storage.posters`, `backend.storage.repository.library`, `backend.storage.repository.sections`, `backend.storage.session`, `backend.storage.tables`, `tests.alembic_runner`, `tests.builders`, `tests.fakes`, `tests.wiring`

Отдаёт наружу: `LATER`, `MOMENT`, `PICTURE`, `POSTER`, `POSTER_SOURCES`, `FakeCatalog`, `FakeClient`, `FakeClock`, `FakeSearch`, `FakeSources`, `an_item`, `capture`, `card_parts`, `counting`, `hit`, `picture`, `poster_service`, `rated`, `recorded`, `responding`, `unreachable`

- `def ours(caplog) -> list[str]` (8)
- `async def film_genres(engine) -> None` (13)
- `async def seed(engine, *statements: str) -> None` (7)
- `def migrated(tmp_path)` (16)
- `async def engine(tmp_path)` (8)
- `async def sections(sessions)` (4)
- `async def reference(engine)` (23)
- `async def sessions(engine)` (4)
- `async def posters(tmp_path)` (6)
- `async def card(sessions)` (11)
  - `async def make(kind: Kind=Kind.MOVIE, source_id: str='1', title: str='карточка') -> int` (5)
- `async def stored(engine)` (12)
  - `async def put(name: str, **values) -> int` (7)

### `tests/fakes.py` — 175 строк

Подставные заменители внешнего мира: клиенты источников, транспорты, часы.

Зависит от: `backend.model`

- `class FakeClient` (12)
- `class FakeCatalog(FakeClient)` (7)
  - `async def card(self, source_id: str, kind: Kind)` (3)
- `class FakeSearch(FakeClient)` (36)
  - `async def search(self, query: str, kind: Kind)` (7)
  - `async def find_people(self, name: str)` (5)
  - `async def credits_of(self, person_id: str, kind: Kind)` (7)
- `class FakeSources` (30)
  - `def catalog_for(self, _kind: Kind) -> list` (4)
  - `def people_for(self, kind: Kind)` (6)
  - `def client_for(self, _source: Source)` (4)
  - `def rating_sources(self, kind: Kind) -> list` (5)
- `class FakeClock` (12)
  - `def __call__(self) -> datetime` (2)
  - `def advance(self, delta: timedelta) -> None` (2)
- `def responding(status: int=200, *, json=None, text=None, content=None, headers=None)` (14)
- `def counting(transport: httpx.MockTransport)` (16)
  - `def handler(request: httpx.Request) -> httpx.Response` (3)
- `def unreachable() -> httpx.MockTransport` (7)
  - `def handler(request: httpx.Request) -> httpx.Response` (2)
- `def capture(*, content: bytes | None=None, status: int=200)` (11)

### `tests/wiring.py` — 52 строк

Части карточки и сервис обложек, собранные для теста на подставном транспорте.

Зависит от: `backend.app`, `backend.service.posters`, `backend.service.search`, `backend.sources.http`, `backend.storage.posters`, `backend.storage.repository.genres`, `backend.storage.repository.library`, `backend.storage.repository.removed`, `backend.storage.repository.views`, `tests.builders`, `tests.fakes`

- `def poster_service(store: PosterStore, transport: httpx.MockTransport) -> PosterService` (7)
- `def card_parts(sessions, store: PosterStore, transport: httpx.MockTransport) -> dict` (8)
- `def search_service(sessions, *clients) -> SearchService` (13)

## Абстракции с одной реализацией

- `BackendThread` — наследник один: `Watched`
- `Base` — наследник один: `Note`
- `FakeCatalog` — наследник один: `FakeCatalogWithSlug`
- `FakeRatings` — наследник один: `Breaking`
- `FakeSearch` — наследник один: `Broken`
- `ViewsRepository` — наследник один: `Forgetful`
