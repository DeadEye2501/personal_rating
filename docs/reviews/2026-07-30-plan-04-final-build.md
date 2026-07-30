# План 4, финальное ревью — сборка с нуля

Дата: 2026-07-30. Коммит клона: `fa4782a20c11c0aec11dc9e4921e102a0458f148`
(main, 2026-07-30 07:44:38 +0400).

Измерение: собирается ли проект с нуля в чистом клоне — только из того, что
закоммичено. Работа велась в отдельной временной папке
(`.../scratchpad/pr-check`), в основное дерево ничего не менялось; клонировано
командой `git clone "D:/Projects/Python Scripts/Personal Rating/personal_rating" pr-check`.
Интерпретатор — существующее venv-окружение,
`C:\Users\deade\.virtualenvs\personal_rating-nun1_nuE\Scripts\python.exe`.

## 1. Зависимости объявлены

Собраны все top-level импорты из `backend/`, `client/`, `tests/`, `scripts/`,
`migrations/` регуляркой по `import`/`from`. Сторонние из найденного:
`PIL` (Pillow), `alembic`, `dotenv` (python-dotenv), `httpx`, `sqlalchemy`,
`pytest`. Все объявлены в `Pipfile` (`[packages]`: pyside6, sqlalchemy[asyncio],
aiosqlite, alembic, greenlet, httpx, python-dotenv, pillow;
`[dev-packages]`: pytest, pytest-asyncio, ruff==0.14.14).

`PySide6` и `pytest-asyncio` в код напрямую не импортируются: `client/`
пока пуст (`client/__init__.py` — единственный файл, каркас клиента не начат,
план 4 — только бэкенд), `aiosqlite`/`greenlet` используются sqlalchemy async
неявно, а `pytest-asyncio` подключается через `pytest.ini`/маркеры, а не
`import`. Расхождений «использую, но не объявил» не найдено.

Версии в `Pipfile` не закреплены нигде, кроме ruby ruff — это по спеке
(`CLAUDE.md`: «ruff объявлен... с закреплённой версией», остальное «меняется
свободно, пока не начата реализация»). Не находка.

## 2. Секретов в репозитории нет

- В клоне нет `.env` (в `.gitignore` есть, и в дереве клона файла
  действительно нет — значит и в основном репозитории он не закоммичен).
- `.env.example` присутствует, все переменные ключей пустые
  (`TMDB_API_KEY=`, `MDBLIST_API_KEY=`, `OMDB_API_KEY=`, `POISKKINO_API_KEY=`,
  `KINOPOISK_UNOFFICIAL_API_KEY=`).
- Поиск по клону (код, тесты, `tests/fixtures/`) на длинные шестнадцатеричные
  строки (`[0-9a-fA-F]{24,}`, отдельно `{32}`) и на `api_key=`/`token=`/
  `secret=` с непустым значением. Единственные совпадения — хэши в именах
  файлов CDN-картинок GOG в `tests/fixtures/gog/catalog.json`
  (`https://images.gog-statics.com/<hash>_{formatter}.jpg`) — это публичные
  URL из зафиксированного ответа магазина, не ключи. JWT-подобных строк
  (`eyJ...`) не найдено. Паттерн `key/token/secret = "..."` — ноль совпадений.

Находок нет.

## 3. База поднимается миграциями с нуля

`python -m alembic -x db=./scratch_test.db upgrade head` в клоне — прошла
без ошибок, две миграции (`0001`, `0002`) применены по порядку.

- Таблиц в базе: **14** — `company`, `company_credit`, `external_id`,
  `external_rating`, `genre`, `genre_map`, `item`, `item_genre`, `item_tag`,
  `person`, `person_credit`, `rating`, `tag`, `wishlist`. Ровно столько же
  объявлено `Table(...)` в `backend/storage/tables/catalog.py` (9) и
  `backend/storage/tables/mine.py` (4 — но с учётом `item` совместно с
  catalog.py и т.д.; всего по обоим файлам 13 `Table()`-вызовов +
  `alembic_version`, которую создаёт сам alembic и которая не в счёте
  «14»). Числа совпали построчным сравнением списка таблиц с
  файлами модуля — расхождений нет.
- Справочник жанров засеян: **47 строк в `genre`**, **326 строк в
  `genre_map`** — совпадает с числом, названным в `CLAUDE.md`
  («47 жанров, 326 соответствий»).

Тестовая база удалена после проверки, в клон не коммитилась (её там и не
было — `git status` в клоне после проверки чист).

## 4. Тесты проходят в клоне

`python -m pytest -q` из клона: **909 passed** за ~75 секунд, без единого
сетевого обращения (все внешние клиенты в тестах бьют по фикстурам, отдельных
таймаутов/ошибок сети не возникло). Число совпадает с ожидаемым «около 909».

## 5. Проверки проекта в клоне

- `python -m ruff check .` — **All checks passed!** Версия — `ruff 0.14.14`,
  как и закреплено в `Pipfile`.
- `python scripts/module_map.py --check` — **«карты свежие, вердикты в
  силе»**, код возврата 0.

## 6. Ничего лишнего не закоммичено

- `git ls-files` не содержит `__pycache__`, `*.pyc`, `*.db`, `*.db-wal`,
  `*.db-shm`, `*.log` — поиск по расширениям пуст.
- `git status --short` в клоне после всех прогонов (pytest, ruff,
  module_map, alembic) — чист: сгенерированные `__pycache__/`,
  `.pytest_cache/`, `.ruff_cache/` остались untracked и покрыты
  `.gitignore` (проверено `git clean -ndx`).
- `docs/reviews/` содержит только отчёты по слайсам и планам — по одному
  измерению на файл, это ожидаемая история ревью по «Порядку работы» из
  `CLAUDE.md`, не черновики.
- `scripts/` содержит только именованные рабочие инструменты
  (`collect_game_genres.py`, `genre_map.py`, `module_map.py`,
  `not_duplicates.py`, `project_ast.py`, `record_fixtures.py`) — ни одного
  файла вида `tmp_*`, `test_scratch*`, `debug_*`.
- `client/` — только `__init__.py`, что соответствует состоянию проекта
  (клиентский каркас ещё не начат).

Находок нет.

## Вердикт

Собирается с нуля: **Да**.
