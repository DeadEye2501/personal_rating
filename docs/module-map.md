# Карта модулей

Собирается из кода: `pipenv run python scripts/module_map.py`.
Править руками нельзя — правки затрёт следующая сборка.
Число в скобках — сколько строк занимает объявление.

## backend — 9 модулей

### `backend/config.py` — 49 строк

Настройки приложения, прочитанные из окружения.

Зависит от: —

- `class Config` (20)
  - `def library_db(self) -> Path` (2)
  - `def posters_db(self) -> Path` (2)
  - `def log_file(self) -> Path` (2)
- `def value(env: Mapping[str, str], name: str) -> str` (4)
- `def load_config(env: Mapping[str, str], base_dir: Path) -> Config` (11)

### `backend/model/__init__.py` — 33 строк

Поверхность модели: отсюда типы границы слоёв импортирует клиент.

Зависит от: `backend.model.credit`, `backend.model.external`, `backend.model.genre`, `backend.model.item`, `backend.model.kinds`, `backend.model.rating`

Отдаёт наружу: `CompanyRole`, `Credit`, `ExternalId`, `ExternalRating`, `Genre`, `GenreKind`, `IdSource`, `Item`, `Kind`, `PersonRole`, `Rating`, `RatingSource`, `Source`, `average_score`


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

### `backend/model/item.py` — 25 строк

Карточка любого типа содержимого на границе слоёв.

Зависит от: `backend.model.kinds`

- `class Item` (16)

### `backend/model/kinds.py` — 58 строк

Закрытые наборы значений, которыми описывается карточка.

Зависит от: —

- `class Kind(StrEnum)` (4)
- `class Source(StrEnum)` (7)
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

### `backend/storage/session.py` — 37 строк

Доступ к основной базе.

Зависит от: —

- `def fold(value: str | None) -> str | None` (5)
- `def create_engine(path: Path) -> AsyncEngine` (13)
- `def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]` (2)

## client — 0 модулей

## Абстракции с одной реализацией

Нет.
