# Ревью повторов — план 2, задача 6 (классификация отказов TMDB)

Измерение: повторы во всём проекте, а не в диффе задачи.

## Сильные стороны

- `classify(response)` и `SourceHttp.get` разведены по предмету буквально
  корректно: `get` не смотрит на `response.status_code` вообще — это
  подтверждает и тест `test_error_codes_are_not_swallowed_here` в
  `tests/backend/sources/test_http.py:295`, где 401 возвращается наружу как
  обычный `httpx.Response`. Классификация тела и кода — целиком новая
  ответственность, не отобранная у `SourceHttp`.
- `TmdbClient._verdict` не переизобретает `classify`, а составляет его с
  побочным эффектом (`breaker.trip`) — вынесено ровно там, где нужно, и не
  тянет взвод предохранителя в чистую функцию.
- Новые тестовые помощники `responding` и `ask` в
  `tests/backend/sources/test_tmdb_failures.py` не имеют одноимённых или
  структурно совпадающих собратьев в `test_tmdb_search.py`, `test_tmdb_card.py`
  и `test_http.py` — проверено гином по всему `tests/`.
- `replay`/`meta` в `conftest.py` — не переизобретение `fixture`: `fixture`
  отдаёт только тело, `replay` собирает целый транспорт с кодом и заголовками
  ответа. У них разный тип результата и разное назначение, использованы обе
  сразу в одном тесте (`test_recorded_missing_object_is_an_answer`).

## Находки

Ничего подтверждённого не найдено.

## Разобранные пары

Все кандидаты из задания при чтении обоих мест оказались не повторами:

- `backend/sources/tmdb/client.py:classify` ≠ `backend/sources/http.py:SourceHttp.get` —
  `get` реагирует на исключения транспорта (`httpx.HTTPError`) и на взведённый
  предохранитель, но никогда не читает `response.status_code`; `classify`
  работает только с уже полученным `httpx.Response` и телом. Общего кода нет,
  сливать нечего.
- `tests/backend/sources/test_tmdb_failures.py:responding` ≠ ничего в
  `test_tmdb_search.py` / `test_tmdb_card.py` — там ответы под конкретный код
  строятся инлайн (`httpx.MockTransport(lambda request: httpx.Response(...))`)
  без отдельного имени; именованного дубля не существует, сравнивать не с чем.
- `tests/backend/sources/test_tmdb_failures.py:responding` ≠
  `tests/backend/sources/test_http.py:capture` — `capture` запоминает ушедшие
  запросы и всегда отвечает 200; `responding` не хранит ничего и отвечает
  заданным кодом и телом. Разное направление данных (что ушло / что придёт).
- `tests/backend/sources/test_tmdb_failures.py:ask` ≠ повторяющийся в разных
  тестах паттерн «создать `TmdbClient`, вызвать `.card`/`.search`, закрыть» —
  паттерн нигде больше не вынесен в функцию, сравнивать `ask` не с чем;
  инлайновое повторение кода в телах тестов — не предмет этого измерения
  (это не два объявления, а одно объявление и голый код).
- `tests/backend/sources/conftest.py:replay` ≠ `tests/backend/sources/conftest.py:fixture` —
  `fixture` отдаёт разобранное тело, `replay` — целый `httpx.MockTransport` с
  кодом и заголовками из `.meta.json`; в `test_tmdb_failures.py` используются
  оба сразу, что и доказывает несовпадение ответственности.
- `backend/sources/tmdb/client.py:RATE_BACKOFF` ≠ ничего в `backend/sources/http.py` —
  единственное упоминание отката по частоте в проекте; второго источника со
  своим бэкоффом пока нет, сравнивать не с чем.

## Вердикт

**Да.** Повторов во всём проекте, связанных с задачей 6, не найдено — ни
между новым кодом и уже существующим `SourceHttp`, ни между новыми тестовыми
помощниками и уже имеющимися в соседних тестовых файлах. `docs/not-duplicates.md`
дополнять не нужно: ни одна из проверенных пар не была достаточно похожей,
чтобы годиться в кандидаты на слияние — они расходятся по видимой причине уже
при первом чтении.
