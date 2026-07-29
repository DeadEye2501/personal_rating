# Ревью по повторам — план 2, задача 4 (поиск в TMDB)

Измерение: повторы во всём проекте, а не в диффе. Прочитаны целиком
`docs/module-map.md`, `docs/data-map.md`, `docs/not-duplicates.md`.

## Сильные стороны

- **`SearchHit` не переизобретает `Item`.** Поля пересекаются по имени
  (`kind`, `source`, `source_id`, `title`, `original_title`, `year`,
  `synopsis`, `poster_url`), но набор разный по смыслу и подтверждён спекой
  (`docs/specs/2026-07-27-search-and-loading.md`, раздел «Кандидат в выдаче —
  ещё не карточка»): `SearchHit` несёт то, чего у `Item` нет и не может быть
  до записи (`genre_ext_ids`, `source_rating`), и не несёт того, что есть
  только у карточки (`id`, `synced_at`, `runtime`, `seasons_count`,
  `episodes_count`). Отдельный тип — осознанное решение, а не забытый повтор.
- **Разбор ответа переиспользует уже заведённый словарь ошибок**, а не
  заводит свой: `parse_search`/`TmdbClient.search` возвращают `Refusal` и
  `Found` из `backend.sources.errors`, ничего не дублируя из `http.py`.
- **Чтение фикстур не повторяет ничего из `tests/conftest.py`.** Там нет
  функции, читающей файл с диска, — только фикстуры базы и хранилища
  постеров. `tests/backend/sources/conftest.py:_load` — первая и единственная
  реализация чтения записанных ответов источников.
- **`POSTER_BASE` и разбор года (`_year`) — первые реализации в проекте**,
  других мест со склейкой URL постера или разбором `YYYY-MM-DD` в год в коде
  нет (проверено `grep` по `isdigit`, `POSTER_BASE`, `poster_path`).

## Находки

Критичных и важных повторов не найдено.

### Мелочь (Nice to Have)

- `tests/backend/sources/test_tmdb_search.py:96-113` (`test_client_asks_the_right_endpoint_and_language`)
  и `tests/backend/sources/test_tmdb_search.py:116-129` (`test_series_search_goes_to_the_tv_endpoint`) —
  оба теста строят одинаковый по форме `handler`, оборачивают его в
  `httpx.MockTransport`, поднимают `TmdbClient` и читают `seen["url"]`.
  Разница — только фикстура (`search_movie.json` / `search_tv.json`) и
  ассерты после вызова. Слить с `capture()` из `test_http.py` нельзя без
  изменения самого `capture()` (её `handler` всегда отвечает `json={}`, а
  этим тестам нужен реальный ответ, иначе `Found(...).value` окажется пустым
  списком). Если появится третий тест с той же формой, стоит завести
  локальный `search_via(kind, fixture_name)`, который строит клиент и
  возвращает `(result, url)` — но заводить его ради двух тестов преждевременно.
  Оставить как есть; не блокирует.

## Разобранные пары

- `backend/model/search.py:SearchHit` ≠ `backend/model/item.py:Item` — поля
  пересекаются по имени, но `SearchHit` — кандидат до записи с
  `genre_ext_ids`/`source_rating`, которых у `Item` нет, а `Item` несёт
  `id`/`synced_at`/`runtime`/`seasons_count`/`episodes_count`, которых нет у
  кандидата; разделение явно описано в
  `docs/specs/2026-07-27-search-and-loading.md`
- `tests/backend/sources/conftest.py:_load` ≠ `tests/conftest.py` (весь модуль) —
  в `tests/conftest.py` нет функции, читающей файл с диска: там только
  фикстуры временной базы и хранилища постеров, предмет и транспорт разные
- `tests/backend/sources/test_tmdb_search.py:test_client_asks_the_right_endpoint_and_language` +
  `test_series_search_goes_to_the_tv_endpoint` ≠ `tests/backend/sources/test_http.py:capture` —
  `capture()` всегда отвечает `json={}` и не годится там, где нужен разбор
  настоящего тела ответа через `TmdbClient.search`; слить нельзя без правки
  самого `capture()`
- `backend/sources/tmdb/client.py:TmdbClient.search` ≠ `backend/sources/tmdb/parse.py:parse_search` —
  оба читают `kind is Kind.SERIES`, но ради разного: выбор пути `/search/tv`
  против `/search/movie` и выбор ключей полей (`name`/`title` и т. д.); общее —
  одно булево выражение, не логика, извлекать нечего
- `backend/sources/http.py:SourceHttp.get` ≠ `backend/sources/tmdb/client.py:TmdbClient.search` —
  оба ловят исключение и возвращают `Refusal`, но домены разные: сетевые
  ошибки транспорта (`httpx.HTTPError`) против ошибок разбора ответа
  (`ValueError`/`TypeError`/`KeyError`/`AttributeError`); общее — словарь
  `Refusal`, а не повторённая логика
- `tests/backend/sources/test_tmdb_search.py:test_a_refusal_from_the_wire_passes_through_untouched` ≠
  `tests/backend/sources/test_http.py:test_network_failure_becomes_a_refusal_not_an_exception` —
  одинаковая форма сценария (`httpx.ConnectError` в `handler`), но проверяют
  разный код: первый — что `TmdbClient.search` пропускает уже готовый отказ
  необработанным (ветка `if not isinstance(response, httpx.Response)`),
  второй — что сам `SourceHttp.get` формирует такой отказ

## Вердикт

**Готово к слиянию?** Да

**Обоснование:** новое не повторяет ни разбор года, ни склейку URL постера,
ни чтение фикстур, ни модель карточки — единственное найденное дублирование
формы (не сути) — два теста с одинаковым по форме `handler` в одном файле, и
это не блокирует слияние.
