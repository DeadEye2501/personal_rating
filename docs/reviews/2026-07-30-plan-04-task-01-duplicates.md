# Ревью повторов — план 4, задача 1 (типы чтения)

Дата: 30.07.2026. Измерение: повторы во всём проекте против нового кода
слайса. Дифф не читался — только карты и код целиком.

## Читал

- `docs/module-map.md`, `docs/data-map.md` целиком.
- `docs/not-duplicates.md` целиком — пары ниже, уже разобранные там, повторно
  не поднимались: `SearchHit ≠ Item`, `Suggestion ≠ SearchHit`.
- Новые файлы: `backend/model/view.py`, `backend/model/query.py`,
  `backend/model/__init__.py`, `tests/backend/test_view_types.py`.
- Для сравнения: `backend/model/item.py`, `backend/model/search.py`,
  `backend/model/card.py`, `backend/model/genre.py`,
  `backend/storage/repository/tags.py`,
  `backend/sources/convert.py`,
  `backend/sources/ratings/omdb/parse.py` (`OWNERS`),
  `backend/sources/ratings/mdblist/parse.py` (`OWNERS`),
  `backend/sources/tmdb/parse.py`, `backend/sources/gog/parse.py`
  (места, где заводится `RatingSource.TMDB` / `RatingSource.GOG`).

## Кандидаты

### 1. `CardView` (`backend/model/view.py`) против `Item` (`backend/model/item.py`)

Пересекается 12 из 14 полей `Item` (`kind`, `source`, `source_id`, `title`,
`original_title`, `year`, `synopsis`, `poster_url`, `runtime`,
`seasons_count`, `episodes_count`, `synced_at`); не совпадают `id`/`item_id`
(у `CardView` он опционален) и `released_at` (в `CardView` его нет вовсе).

Прочитал оба объявления и `view_from_item`. Разное — не только состав полей,
но и назначение и жизненный цикл: `Item` — строка базы (`LibraryRepository`
читает и пишет её целиком, `id` там всегда есть), `CardView` — то, чем лента
`bind`-ит карточку (правило слоёв из `CLAUDE.md`: карточка ленты принимает
данные `bind`, не строится под конкретный фильм). У `CardView` есть поля,
которых в `Item` нет вовсе и которые приходят из других таблиц и источников:
`genres`, `tags`, `people`, `companies`, `external`, `waiting`, `rating`,
`in_wishlist` — то, что `ViewsRepository` доливает поверх строки `item`
(комментарий в `view_from_item` это прямо говорит). Одновременно `CardView`
рассчитан жить и без `item_id` — как кандидат из поиска, которым `Item` в
принципе быть не может (`Item.id` не опционален).
Слить их значило бы сделать `id` у `Item` опциональным и протащить в строку
базы поля, которых там нет и не будет (`waiting`, `in_wishlist`) — то есть
разрушить оба смысла, ради которых типы разделены. **Не повтор.**

### 2. `CardView`/`view_from_hit` против `SearchHit` (`backend/model/search.py`)

Прочитал оба объявления и `view_from_hit`. Пересечение полей есть
(`kind`, `source`, `source_id`, `title`, `original_title`, `year`, `synopsis`,
`poster_url`), но это ровно та же граница, что уже зафиксирована в
`not-duplicates.md` для пары `SearchHit ≠ Item`: `SearchHit` — кандидат,
который в базу не попадает никогда, `CardView` — то, что рисует лента, и
`view_from_hit` — однонаправленный адаптер между ними (жанры разворачивает
из `genre_ext_ids` в `Genre`, бесплатную оценку заворачивает в
`ExternalRating`). Общий тип потребовал бы тащить в кандидат поля, которых у
него никогда не будет (`rating`, `in_wishlist`, `waiting`). **Не повтор.**

### 3. `CardView` против `SourceCard` (`backend/model/card.py`)

Прочитал оба объявления. Общих полей по имени нет вовсе, кроме вложенного
`item: Item` у `SourceCard` (и то через один уровень). `SourceCard` — вход в
запись (что источник отдал для `CardWriter`/`Linker`), `CardView` — выход из
чтения (что видит лента). Разное направление потока данных, разный слой.
**Не повтор**, не подтверждён даже как кандидат первого порядка — исключил
после первого чтения.

### 4. `Tag` (`backend/model/view.py`) против `Genre` (`backend/model/genre.py`)

Прочитал оба объявления. `Tag`: `id`, `name` (2 поля). `Genre`: `id`, `name`,
`kind: GenreKind` (3 поля, третье — тип содержимого). Пересекаются `id` и
`name` по имени и типу, но это ровно граница, которую сам проект объявляет
решённой: «Жанры приходят снаружи, теги заводит только человек» — разные
таблицы (`tag`/`item_tag` против `genre`/`genre_map`/`item_genre`), разный
источник правды, и `GenresRepository`/`TagsRepository` в коде уже разделены
без общего предка. Слитый тип потребовал бы либо опционального `kind` у
жанра (бессмысленно — жанр без типа содержимого не бывает), либо тега с
чужим полем. **Не повтор.**

### 5. `_OWN_RATING` (`backend/model/view.py`) против `OWNERS` в
`backend/sources/ratings/omdb/parse.py` и
`backend/sources/ratings/mdblist/parse.py`

Прочитал все три словаря целиком. Форма похожа (`dict[..., RatingSource]`),
но ключи и назначение разные: `_OWN_RATING` — `dict[Source, RatingSource]`,
отвечает на вопрос «если это кандидат из каталога Source.TMDB/Source.GOG, чья
у него бесплатная оценка» — используется только в `view_from_hit` для
единственной цифры, которая уже приехала вместе с поиском. `OWNERS` у OMDB и
MDBList — `dict[str, RatingSource]`, разбирают человекочитаемое или
слаговое имя владельца оценки внутри чужого тела ответа (`"Rotten Tomatoes"`,
`"tomatoes"`) — множество значений и повод завести их разные (сами эти два
уже разведены в `not-duplicates.md`). Общей таблицы тут нет и не может быть:
`_OWN_RATING` не о разборе тела ответа вообще, а о том, какой источник
считается «родным» для кандидата поиска. **Не повтор.**

### 6. `view_from_hit`/`view_from_item` против источниковых конвертеров
(`tmdb/parse.py:parse_search`, `gog/parse.py:to_hit`,
`steam/parse.py:parse_search`, `backend/sources/convert.py`)

Прочитал сигнатуры и тела. Источниковые конвертеры переводят сырой ответ
API (`dict`/`list[dict]`) в `SearchHit`/`SourceCard` — работают на границе
сеть → наши типы. `view_from_hit`/`view_from_item` работают на границе
наши типы (`SearchHit`/`Item`) → `CardView` — граница чтение из базы/поиска →
показ. Разные входы (внешний JSON против уже разобранных дataclass-ов),
разные модули, разный слой (`backend/sources` против `backend/model`).
**Не повтор**, отклонён после первого чтения сигнатур.

### 7. `Section`/`Sort`/`Order`/`Filters`/`Bucket`/`Histogram`
(`backend/model/query.py`) против остального проекта

Прошёл `data-map.md` и `module-map.md` в поиске похожих перечислений и
датаклассов: `GenreKind` (`FILM`/`GAME`) не пересекается по значениям с
`Section` (`RATED`/`WISHLIST`) и с `Sort`; ни один существующий репозиторий
не принимает объект «критерий + сторона» или «набор фильтров» — везде голые
параметры (`limit`, `offset`, `kind`). Нового двойника этим типам в проекте
нет. **Не кандидат**, отклонён на этапе сбора карты — совпадений не нашлось.

## Вердикт

Рассмотрено кандидатов: 7. Подтверждённых повторов: 0.

Готово к коммиту: Да
