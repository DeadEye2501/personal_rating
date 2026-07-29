# Ревью тестов — план 2, задача 8 (клиент GOG)

Измерение: тесты слайса. Только чтение, без мутаций живьём — опираюсь на
структуру кода и список из 16 мутаций, прогнанных исполнителем.

## Сильные стороны

- Центральное правило слайса — «`Missing` не возвращается ни из `search`, ни
  из `card`» — закреплено структурно и тестами одновременно:
  `backend/sources/gog/client.py` вообще не импортирует `Missing` (только
  `Found`, `Refusal`), и три теста бьют именно по границам этого правила:
  пустой каталог (`test_even_an_empty_catalog_answer_is_not_missing`),
  бессмыслица с полусотней несвязанных игр
  (`test_search_never_reports_nothing_found`) и ненайденный id в `card`
  (`test_card_that_the_catalog_did_not_return_is_not_a_negative_fact`).
  Верни кто-нибудь `Missing()` в любую из этих веток — тест упадёт по
  `isinstance`, не по значению.
- `tests/fixtures/gog/catalog.json` и `catalog_nonsense.json` — оба с парным
  `*.meta.json` (`status: 200`, реальный `content-type`), то есть записаны
  живьём, а не собраны руками. `catalog_nonsense.json` — 50 не связанных с
  запросом позиций (Legacy of Kain, Mortal Kombat 1+2+3 и т.д. на запрос
  `zzqqxxnotagame123`) — подтверждает описанное в спеке поведение GOG, а не
  придумывает его.
- Тест на слаг-опечатку (`fantasy` как жанр и как тег одновременно,
  `GenreSource.GOG` vs `GOG_TAG`) я сверил с сырыми данными фикстуры: `name`
  жанра/тега у GOG — локализованная строка (в дампе видна как мусор от
  кодировки), `slug` — `fantasy`. Значит проверка `(GenreSource.GOG,
  "fantasy") in card.genre_ext_ids` реально бьёт по выбору ключа `slug`, а не
  является совпадением с ожидаемым по случайности.
- Синтетические тела оправданы по списку исключений из задания: ноль отзывов
  (`test_a_game_nobody_reviewed_has_no_rating`), отсутствие оценки вовсе
  (`test_a_candidate_without_a_rating_carries_none`), пустой каталог, битый
  JSON, неожиданная форма (`products` строкой), 503 и 429 — ни троттлинг, ни
  «нулевые отзывы у реальной игры» вживую не записать.

## Находки

Критично: нет.

Важно: нет.

Мелочь:

- `test_rate_limit_trips_the_breaker` (`tests/backend/sources/test_gog.py:210`)
  проверяет `reason is Reason.RATE` и что второй запрос не ушёл в сеть, но не
  проверяет `retry_after == RATE_BACKOFF` (`backend/sources/gog/client.py:47`).
  Подмени `RATE_BACKOFF` на секунду вместо пяти минут — тест не заметит.
  Некритично: срок отката не часть правила «не Missing», но раз уж
  предохранитель проверяется, стоило бы закрыть и его длительность.
- `test_catalog_row_is_already_a_card` (`test_gog.py:20`) на треть проверяет
  жёстко прибитые константы (`kind is Kind.GAME`, `source is Source.GOG`,
  `parse.py:34-35`) — по правилу 13 манифеста это не проверка сама по себе,
  скорее smoke-тест «карточка вообще собралась». Вытягивают его в полноценный
  тест соседние по значению поля (`source_id`, `title`, `poster_url` —
  реально извлечённые из фикстуры значения), так что тест не бесполезен, но и
  не сторожит специфично ничего одного.
- Параметр `locale=ru-RU` в `_catalog` (`backend/sources/gog/client.py:41`) не
  проверен ни одним тестом. Пропажа локали не уронит ничего в этом слайсе.

## Прогон

```
& "$(pipenv --venv)\Scripts\python.exe" -m pytest tests/backend/sources -q --no-header
```
→ `131 passed in 0.41s` (весь `tests/backend/sources`, как задано командой).

Уточняющий прогон только по слайсу:
```
& "$(pipenv --venv)\Scripts\python.exe" -m pytest tests/backend/sources/test_gog.py -q --no-header
```
→ `20 passed in 0.09s`.

Время ревью: около 10 минут, в потолок уложился.

## По каждому тесту — следствие и ломающая строка

1. `test_catalog_row_is_already_a_card` — карточка собралась и заполнена; ломает `parse.py:33-41` (любое из `kind`/`source`/`source_id`/`title`/`poster_url`). Частично проверка констант (см. «Мелочь»).
2. `test_the_cover_is_the_vertical_one` — берётся именно вертикальная обложка; ломает `parse.py:41`.
3. `test_the_year_is_read_from_a_dotted_date` — год — голова даты, не хвост; ломает `backend/sources/convert.py:26`.
4. `test_genres_come_as_slugs` — оба пространства присутствуют, слаг не число; ломает `parse.py:22-24` (сам по себе слабый, усиливается тестом 5).
5. `test_a_genre_and_a_tag_with_the_same_slug_stay_apart` — жанр и тег с одним слагом не сливаются; ломает `parse.py:22-24` (перепутанный `key`, слитое пространство). Сверено с сырыми данными фикстуры.
6. `test_developers_and_publishers_are_companies` — обе роли присутствуют; ломает `convert.py:33-40` (пропавший `publishers`).
7. `test_studios_come_without_any_identity` — у студий нет `source`/`source_id`; ломает `convert.py:34`.
8. `test_player_rating_belongs_to_gog` — оценка из `reviewsRating`, значение 46; ломает `parse.py:47` (подмена на `row.get("ratings")` или чужой `RatingSource`).
9. `test_a_game_nobody_reviewed_has_no_rating` — ноль отзывов = пустой кортеж; ломает `convert.py:50` (`if not value` → `if value is None`).
10. `test_a_card_folds_into_a_candidate` — все поля кандидата 1:1 с карточкой; ломает `parse.py:53-64` (пропуск любого поля).
11. `test_a_candidate_without_a_rating_carries_none` — пустой список оценок не роняет по индексу; ломает `parse.py:63` (безусловный `card.ratings[0].value`).
12. `test_search_never_reports_nothing_found` — бессмыслица даёт `Found` с полусотней позиций; ломает добавление `if not cards: return Missing()` в `client.py:60-64`.
13. `test_even_an_empty_catalog_answer_is_not_missing` — пустой каталог тоже `Found([])`, не `Missing`; та же строка.
14. `test_search_asks_the_catalog_the_way_that_answers` — запрос идёт с `like:`; ломает `client.py:41`.
15. `test_card_picks_the_asked_identifier` — выбирается запрошенный id, не первый попавшийся; ломает `client.py:76-78`.
16. `test_card_that_the_catalog_did_not_return_is_not_a_negative_fact` — ненайденный id даёт `Refusal(BROKEN)`, не `Missing`; ломает `client.py:79-83`.
17. `test_server_failure_is_a_refusal` — 503 даёт `Refusal(BROKEN)`; ломает `client.py:48-53`.
18. `test_rate_limit_trips_the_breaker` — 429 взводит предохранитель, второй запрос не уходит в сеть; ломает `client.py:45-47` или `http.py:70-72`.
19. `test_non_json_body_does_not_crash_the_parser` — битый JSON даёт `Refusal`, не исключение; ломает `client.py:54-58` (сузить `except`).
20. `test_unexpected_shape_does_not_crash_the_parser` — `products` строкой не роняет парсер; та же строка.

## Догадки о непокрытом (не заказ на проверку)

- Длительность отката (`RATE_BACKOFF`, `client.py:47`) можно подменить на
  произвольное значение — ни один тест не заметит, значение `retry_after`
  нигде не сверяется.
- `locale="ru-RU"` в параметрах запроса (`client.py:41`) можно выкинуть без
  последствий для тестов.
- Причина отказа при сетевой ошибке (`Reason.NETWORK` из `SourceHttp.get`,
  `http.py:79-81`) для GOG отдельно не проверена — но это код общего
  `SourceHttp`, не специфика этого слайса.

## Вердикт

**Да.** Тесты слайса реально сторожат правило «GOG не возвращает `Missing`»
структурно и по границам (пустой каталог, бессмыслица, ненайденный id), у
каждого теста есть конкретная ломающая строка (кроме одного смок-теста с
частичной проверкой констант — не критично), фикстуры реальные и записаны
живьём там, где это вообще возможно, а синтетические тела ограничены
случаями, которые записать нельзя. Найденные мелочи (срок отката, локаль) не
требуют правок для прохождения ревью этого измерения.
