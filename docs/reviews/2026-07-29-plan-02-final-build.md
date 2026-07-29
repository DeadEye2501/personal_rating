# Финальное ревью плана 2 — сборка с нуля

Измерение: собирается ли проект с нуля у человека, у которого есть только
репозиторий и Python 3.13. Работа велась в отдельном клоне
`C:\Users\deade\AppData\Local\Temp\review-build`, основной каталог не тронут.

## Что проверено и как

**1. Зависимости.** Собраны корневые имена всех импортов из `backend`,
`scripts`, `migrations`, `tests`:

```
alembic ast asyncio backend collections dataclasses datetime dotenv enum
hashlib httpx inspect json logging module_map not_duplicates os pathlib
project_ast pytest re sqlalchemy subprocess sys tests typing urllib uuid
```

Внешние — `alembic`, `dotenv` (`python-dotenv`), `httpx`, `sqlalchemy`, `pytest`
— все перечислены в `Pipfile`, и каждый в правильной секции: `pytest` только в
`[dev-packages]`, и нигде не импортируется из `backend`/`scripts`/`migrations`
(проверено `grep`). `aiosqlite`, `greenlet`, `pyside6` в коде напрямую не
импортируются — `aiosqlite` используется through connection string SQLAlchemy,
`greenlet` требуется для `run_sync` асинхронного движка, `pyside6` заведён
заранее под клиентскую часть, которой в плане 2 ещё нет. Не лишние, не
отсутствующие.

**2. Секреты.** `git ls-files | grep -i "\.env"` — только `.env.example`,
самого `.env` в репозитории нет. `.gitignore` содержит `.env`. Сверил
`.env.example` с `backend/config.py::load_config`: `TMDB_API_KEY`,
`MDBLIST_API_KEY`, `OMDB_API_KEY`, `POISKKINO_API_KEY`,
`KINOPOISK_UNOFFICIAL_API_KEY`, `LOG_LEVEL`, `DATA_DIR` — совпадение полное в
обе стороны, лишних и недостающих переменных нет. Дополнительно прогнал
`git grep` по всему репозиторию на предмет заполненных значений
`*_API_KEY=<непусто>` — ничего, кроме имён переменных в самом `config.py`.

**3. Фикстуры на месте.** `tests/fixtures/` — 77 файлов, все отслежены git
(`git ls-files tests/fixtures | wc -l` совпало с файловым count). Есть все
шесть подпапок источников и `README.md`.

**4. Секретов в фикстурах нет.** Поручил отдельному форку независимую
проверку (`Grep` по `api_key|apikey|Authorization|Bearer|Set-Cookie|token|
secret` и по `.meta.json`). Найдено два совпадения: `mdblist/bad_key.json` и
`mdblist/no_key.json` — это тела ответов вида `{"error": "Invalid API key"}` и
текст, объясняющий формат авторизации, а не сам ключ. Сам проверил
`.meta.json` — там только `content-type`, `x-ratelimit-*`, как и заявлено в
`tests/fixtures/README.md`, который отдельно фиксирует, что все значения из
`.env` сверены со всеми файлами каталога и утечки нет.

**5. Прогон в клоне.** Пошёл штатным путём: `pipenv install --dev` в каталоге
клона отработал (использовал уже существующее окружение pipenv для этого
пути, но `Pipfile.lock` разрешился штатно, без предупреждений об устаревшем
lock-файле). Дальше:

```
pipenv run python -m pytest -q
479 passed in 37.44s
```

Отдельно прогнал `tests/backend/test_migrations.py` — все 4 теста прошли,
включая проверку, что миграция строит схему с нуля и что откат её убирает.

**6. База поднимается с нуля.** В клоне нет ни `data/`, ни `*.db` —
подтверждено поиском. Тесты миграций (пункт 5) поднимают схему в пустом
месте и проходят.

**7. Мусора нет.** `git status --porcelain` в клоне после прогона — пусто,
`__pycache__` в отслеживаемых файлах нет. Отдельно прогнал
`scripts/module_map.py --check` — «карты свежие, вердикты в силе», обе карты
(`docs/module-map.md`, `docs/data-map.md`) не отстали от кода. `docs/reviews/`
содержит только записанные ревью по слайсам и задачам плана — ничего похожего
на черновик не по месту.

Клон удалён по завершении.

## Находки

Критично: нет.

Важно: нет.

Мелочь: нет.

## Вердикт

**Собирается с нуля: да.** Зависимости в `Pipfile` полны и не смешаны между
основными и тестовыми, `.env` в репозиторий не попал и шаблон совпадает с
кодом, фикстуры на месте и без секретов, полный прогон (479 тестов) и
миграции с нуля проходят чисто, карты не отстали, следов мусора нет.
