# Закрывающее ревью бэкенда: сборка с нуля в чистом клоне

**Дата:** 31.07.2026
**Коммит:** `1227049` — «chore: не раскладывать `__pycache__` по дереву проекта»
**Измерение:** поднимется ли проект на машине, где нет ничего, кроме репозитория
**Где проверялось:** `C:\Users\deade\AppData\Local\Temp\claude\build-check\clone`,
свой venv `C:\Users\deade\.virtualenvs\clone-C78KQmCk` — обе папки удалены после
проверки. Основной рабочий каталог и его venv не тронуты.

**Итог: собралось целиком, с первой попытки, ровно теми командами, что записаны в
`CLAUDE.md`. 905 тестов зелёные. Критических находок нет.**

---

## Сильные стороны (Strengths)

**Установка проходит одной документированной командой и берёт замок, а не
свежий разбор зависимостей.** `pipenv install --dev` поставил всё из
`Pipfile.lock (c7aa3a)`; `pipenv verify` отвечает `Pipfile.lock is up-to-date`,
то есть замок не отстал от `Pipfile`. Никаких доустановок руками не
потребовалось.

**Схема поднимается с нуля и повторяется в точности.** `alembic upgrade head` на
пустой папке завёл `data/` сам (`env.py` делает `mkdir(parents=True)` — это
записано там комментарием и работает), и дал ровно объявленное: **14 своих
таблиц** плюс `alembic_version`, **47 жанров**, **326 соответствий**, штамп
`0002`, 9 индексов, журнал `wal`. Повторный `upgrade head` проходит начисто;
`downgrade base` → `upgrade head` воспроизводит те же 14/47/326.

**Набор проходит без сети, без ключей и без `pipenv`.** 905 зелёных получены
четырьмя разными способами (см. ниже), в том числе с мёртвым прокси и вообще без
`.env`. Это не декларация «тесты офлайновые», а замер: ни один тест не заметил,
что сети нет.

**Проект не зависит от одноразовых папок.** `docs/` и `scripts/` удалены целиком
— миграции и 905 тестов после этого прошли так же. То, ради чего писался коммит
`b96d606`, держится.

**Бэкенд собирается живьём и работает офлайн.** Собран `build_backend` на чистой
базе без ключей: 22 игровых жанра и 25 киношных (в сумме 47), пустой локальный
поиск, а внешний поиск отдал не исключение, а
`ExternalSearch(views=(), refusals=(Refusal(source='tmdb', reason=Reason.KEY, …)))`
— отсутствие ключа опознано как отказ источника. `aclose()` закрыл оба файла базы
и транспорт без единого предупреждения.

**Ничего своего вне репозитория.** По всему коду ноль абсолютных путей
(`[A-Za-z]:\`, `/Users/`, `Program Files`, `AppData`) — искалось по `backend`,
`migrations`, `tests`, `scripts`. Ни один тест не потребовал артефакта, которого
нет в клоне: 495 файлов фикстур лежат в репозитории.

**`.env.example` совпадает с тем, что читает код, ровно.** `config.py` читает
семь имён — `DATA_DIR`, `TMDB_API_KEY`, `MDBLIST_API_KEY`, `OMDB_API_KEY`,
`POISKKINO_API_KEY`, `KINOPOISK_UNOFFICIAL_API_KEY`, `LOG_LEVEL` — и все семь в
шаблоне есть. Лишних нет, забытых нет.

**`ruff` объявлен, закреплён и ставится именно закреплённый.** В клоне встал
`ruff 0.14.14`, как и написано в `Pipfile`. Отдельно замерено: глобальный `ruff`
на этой машине — тоже `0.14.14`, то есть расхождения между тем, чем гоняет хук
(он берёт `ruff` из `PATH`), и тем, что закреплено, сегодня нет. `ruff check .`
с настройками по умолчанию — `All checks passed!`.

**Клон не мусорит.** После полного прогона `git status` в клоне чист:
`.pytest_cache` и `.ruff_cache` заводят себе собственный `.gitignore` с `*`,
`data/` перечислена в `.gitignore`, `__pycache__` под `pipenv run` не появляется
вовсе.

**`CLAUDE.md` в коммите актуален по стеку.** Раздел «Окружение» перечисляет
`pywebview`, `pillow` и остальное и прямо оговаривает, что `pyside6` и
`pytest-qt` сняты вместе с сиротами. Расхождения между документацией и `Pipfile`
нет ни в одну сторону.

---

## Что и как проверялось

### 1. Клон

```
$ git clone "d:/Projects/Python Scripts/Personal Rating/personal_rating" clone
Cloning into 'clone'...
done.
$ git log --oneline -1
1227049 chore: не раскладывать __pycache__ по дереву проекта
$ git status --porcelain
(пусто)
```

Содержимое клона: `.env.example`, `.gitignore`, `CLAUDE.md`, `Pipfile`,
`Pipfile.lock`, `alembic.ini`, `pytest.ini`, `backend/`, `client/`, `docs/`,
`migrations/`, `scripts/`, `tests/`. Папки `.claude/` в клоне нет — она в
`.gitignore` (см. находку 3).

### 2. Зависимости

```
$ pipenv install --dev
Creating a virtualenv for this project
Using D:/Programs/Development/Python/python.exe3.13.2 to create virtualenv...
Virtualenv location: C:\Users\deade\.virtualenvs\clone-C78KQmCk
Installing dependencies from Pipfile.lock (c7aa3a)...

$ pipenv verify
Pipfile.lock is up-to-date.
```

Поставилось 30 пакетов. Ключевые: `SQLAlchemy 2.0.51`, `aiosqlite 0.22.1`,
`alembic 1.18.5`, `greenlet 3.5.4`, `httpx 0.28.1`, `pillow 12.3.0`,
`pywebview 6.2.1`, `python-dotenv 1.2.2`, `pytest 9.1.1`,
`pytest-asyncio 1.4.0`, **`ruff 0.14.14`**. С `pywebview` приехали
`pythonnet 3.1.0`, `clr_loader`, `bottle`, `cffi`, `pycparser`, `proxy_tools`.
`import webview` в клоне проходит.

### 3. Настройки

```
$ cp .env.example .env
```

Ключи не заполнялись ни одного — все семь остались пустыми.

### 4. Схема с нуля

```
$ pipenv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, ...
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, ...

tables: 15
  alembic_version, company, company_credit, external_id, external_rating,
  genre, genre_map, item, item_genre, item_tag, person, person_credit,
  rating, tag, wishlist
genre: 47
genre_map: 326
version: [('0002',)]
journal_mode: ('wal',)
indexes: 9
```

**14 своих таблиц + `alembic_version` = 15. Совпало с объявленным.**

Повтор и откат:

```
$ pipenv run alembic upgrade head     # второй раз — начисто, без ошибок
$ pipenv run alembic downgrade base   # 0002 -> 0001 -> (пусто)
$ pipenv run alembic upgrade head
tables: 15   genre: 47   genre_map: 326
```

### 5. Набор тестов — четыре прогона

| Условие | Команда | Итог |
|---|---|---|
| как задокументировано | `pipenv run python -m pytest -q` | **905 passed in 62.23s** |
| без `.env`, прокси в никуда | `HTTP_PROXY=http://127.0.0.1:1 HTTPS_PROXY=… ALL_PROXY=… pipenv run python -m pytest -q` | **905 passed in 61.32s** |
| `docs/` и `scripts/` удалены | `pipenv run python -m pytest -q` | **905 passed in 55.55s** |
| без `pipenv` вовсе | `…/clone-C78KQmCk/Scripts/python.exe -m pytest -q` | **905 passed in 62.37s** |

Ни одного `skipped`, ни одного `xfail`. Мёртвый прокси — проверка того, что
клиенты источников не ходят в сеть даже случайно: `httpx` по умолчанию читает
`*_PROXY` из окружения, и живой запрос упёрся бы в `127.0.0.1:1`.

### 6. Живая сборка бэкенда

```python
cfg = load_config(os.environ, base_dir=Path.cwd())
b = await build_backend(cfg)
```

```
data_dir: …\clone\data   tmdb_key: ''
game genres: 22
screen genres: 25
local search: []
external search: ExternalSearch(views=(), refusals=(Refusal(source='tmdb',
    reason=<Reason.KEY: 'key'>, retry_after=None, detail=''),))
closed ok
```

`data/posters.db` завёлся вторым файлом сам, как и обещает докстринг
`build_backend`.

### 7. Независимость от того, чего в клоне нет

```
$ rm -rf docs scripts
$ ls
CLAUDE.md  Pipfile  Pipfile.lock  alembic.ini  backend  client  migrations
pytest.ini  tests
$ pipenv run alembic upgrade head   # прошло
$ pipenv run python -m pytest -q    # 905 passed
```

Абсолютные пути в коде — ноль совпадений:

```
$ grep -rniE "[A-Za-z]:\\\\|/Users/|Program Files|AppData" --include=*.py .
(пусто)
```

### 8. Линтер

```
$ pipenv run ruff --version
ruff 0.14.14
$ pipenv run ruff check .
All checks passed!
```

Своим набором правил (тем, что зашит в хук `check_edit.py`):

```
$ pipenv run ruff check --no-cache --isolated \
    --select F401,ARG002,C901,PLR0912,PLR0913,PLR0915,E402,RUF100 \
    --config lint.mccabe.max-complexity=8 --config lint.pylint.max-args=5 .
backend\service\card_parts.py:22:9: PLR0913 Too many arguments (7 > 5)
backend\sources\gog\client.py:58:40: ARG002 Unused method argument: `kind`
backend\sources\gog\client.py:64:42: ARG002 Unused method argument: `kind`
backend\sources\ratings\kinopoisk\poiskkino.py:36:43: ARG002 … `kind`
backend\sources\ratings\kinopoisk\unofficial.py:32:43: ARG002 … `kind`
backend\sources\ratings\omdb\client.py:45:43: ARG002 … `kind`
backend\sources\steam\client.py:56:40: ARG002 … `kind`
backend\sources\steam\client.py:67:42: ARG002 … `kind`
tests\backend\test_genres.py:36:11: PLR0913 Too many arguments (6 > 5)
tests\backend\test_views.py:336:9: PLR0913 Too many arguments (6 > 5)
Found 10 errors.
```

### 9. Уборка

Клон и venv `clone-C78KQmCk` удалены. В `~/.virtualenvs` остались только чужие,
включая рабочий `personal_rating-nun1_nuE`.

---

## Находки (Issues)

### Critical

Нет.

### Important

#### 1. Команды, поднимающей базу, нет ни в одном файле, который переживёт чистку

**Где:** `CLAUDE.md`, раздел «Окружение» (строки 555–568).

**Что не так.** Раздел «Окружение» даёт три команды: `pipenv install --dev`,
`pipenv run python <файл>`, `pipenv --venv`. Команды `alembic upgrade head` там
нет. Поиск по всему репозиторию:

```
$ grep -rn "alembic upgrade\|upgrade head" --include=*.md .
docs/plans/2026-07-27-reading.md:5700
docs/plans/2026-07-27-storage.md:1752, 2004, 2068
docs/reviews/… (13 попаданий)
```

Все до одного — в `docs/plans/` и `docs/reviews/`.

**Почему важно.** `docs/` объявлена одноразовой: «Временные папки одноразовы —
`scripts`, `docs`, `design` удаляются в любой момент». Удалив её, проект теряет
единственное место, где записано, как из клона получить базу. Причём без этого
шага не работает ничто: `build_backend` схему не создаёт и прямо отсылает к
миграциям («Схему база получает миграциями, а не отсюда: `alembic upgrade
head`») — но этот докстринг найдёт тот, кто уже читает код, а не тот, кто ставит
проект.

Сама по себе миграция при этом безупречна: папку заводит, повторяется, откат
работает.

**Как чинить.** Дописать в блок команд «Окружение» четвёртую строку:

```powershell
pipenv run alembic upgrade head   # поднять базу с нуля
```

#### 2. `.env` не читает ни одна строка своего кода, а `python-dotenv` объявлен и никем не импортирован

**Где:** `Pipfile`, `[packages]`; `CLAUDE.md`, раздел «Секреты».

**Что не так.**

```
$ grep -rn "dotenv" --include=*.py .
(пусто)
```

Ни `load_dotenv`, ни `dotenv_values` — нигде: ни в `backend/`, ни в
`migrations/env.py`, ни в `tests/`, ни в `scripts/`. `python-dotenv` числится в
`[packages]` (не в `[dev-packages]`) и не нужен ни одному импорту.

Ключи из `.env` доезжают до `load_config(os.environ, …)` **только потому, что их
подставляет `pipenv run`** — это его собственная работа, о которой видно по строке
`Loading .env environment variables...` в каждом прогоне. Замерено прямо: под
`pipenv run` ключи видны, под `…\Scripts\python.exe` — нет.

**Почему важно.** «Секреты» обещают: «Ключи API — только в `.env`». Сегодня это
верно с невысказанной оговоркой «и только если запускать через `pipenv run`».
Как только у приложения появится своя точка входа — а она появится с клиентом, и
тем более в собранном `.exe`, где `pipenv` нет вовсе, — ключи станут пустыми, и
проявится это не падением, а тихим `Refusal(reason=Reason.KEY)` на каждом
источнике. Это ровно тот класс, который ищет сборка с нуля: работает потому, что
рядом стоит инструмент разработчика.

**Как чинить.** Одно из двух, по выбору: (а) точка входа приложения зовёт
`load_dotenv()` первой строкой — тогда `python-dotenv` в `[packages]` оправдан;
(б) зависимость снимается, а в «Секретах» пишется, что `.env` подхватывает
`pipenv`, и запуск мимо него ключей не видит. Сегодня не выполнено ни то, ни
другое, и `[packages]` содержит пакет без единого потребителя — правило 8
манифеста.

#### 3. Оснастка, которой предписан порядок работы, в клон не попадает

**Где:** `.gitignore`, последняя строка `.claude/`; `CLAUDE.md`, раздел «Порядок
работы».

**Что не так.** `.gitignore` исключает `.claude/` целиком, с обоснованием
«Рабочие деревья агентов: там полная копия проекта». Но под `.claude/` лежат не
только `worktrees/`:

```
.claude/settings.json                                  — хуки
.claude/skills/keeping-code-clean/MANIFEST.md          — 16 правил
.claude/skills/keeping-code-clean/hooks/check_edit.py  — держит 7 правил из 16
.claude/skills/keeping-code-clean/hooks/duplicates.py  — машинная проверка дублей
.claude/skills/keeping-code-clean/tools/module_map.py  — собирает обе карты
```

В свежем клоне нет ничего из этого. При этом «Порядок работы» объявляет: «Перед
коммитом `--check` роняет сборку, если отстала любая из двух [карт], поэтому
забыть дописать в них нельзя». На чистом клоне забыть можно: нечем проверить.
`docs/module-map.md` и `docs/data-map.md` в репозитории есть, а инструмент,
который их сверяет, — нет.

**Почему важно.** Проект держит семь правил манифеста машиной, и это записано
как то, на что ревью может не смотреть. После клона машины нет, а запись
осталась. Отдельно: `check_edit.py` берёт `ruff` не из окружения проекта, а из
`PATH` (`shutil.which("ruff")`), так что закреплённая версия из `[dev-packages]`
на хук вообще не влияет. Сегодня это безвредно — замерено, глобальный `ruff` тоже
`0.14.14`, — но связь между закреплением и тем, что реально проверяет, нулевая.

**Как чинить.** Не разигнорировать `.claude/` (там правда лежат рабочие деревья),
а дописать в «Порядок работы» одну строку: где взять скилл на новой машине
(архив `D:\Projects\Claude Skills`) и что без него `--check` и хуки не работают.
Второе — либо звать `pipenv run ruff` из хука, либо снять из `CLAUDE.md`
утверждение, будто закрепление версии влияет на проверки.

### Minor

#### 4. `PYTHONDONTWRITEBYTECODE=1` в `.env.example` не делает ничего

**Где:** `.env.example`, раздел «Прочее»; коммит `1227049`.

**Что не так.** Комментарий объясняет: «Читается интерпретатором на старте,
поэтому и живёт здесь: pipenv загружает `.env` до запуска python». Рассуждение
верное, но переменную уже ставит сам `pipenv`, независимо от `.env`. Замерено в
клоне, с убранным `.env`:

```
$ mv .env .env.bak
$ env | grep -i python          # в окружении оболочки — ничего
$ …\Scripts\python.exe -c "import sys,os; print(sys.dont_write_bytecode, …)"
False None
$ pipenv run python -c "import sys,os; print(sys.dont_write_bytecode, …)"
True '1'
```

Реестр `HKCU\Environment` и `HKLM\…\Session Manager\Environment` переменной не
содержат — проверено перебором. То есть `1` приходит от `pipenv`, а не из `.env`
и не из системы.

Обратная половина замера: под голым `python` (`.env` не читается никем) кэш
раскладывается по дереву как раньше —

```
$ …\Scripts\python.exe -m pytest -q
905 passed in 62.37s
pycache after direct run: 18
```

**Почему это мелочь, а не Important.** Вреда нет: `__pycache__/` и `*.py[cod]` в
`.gitignore` с самого начала, в репозиторий кэш не попадает никогда. Но строка в
шаблоне утверждает, что решает задачу, которую не решает: под `pipenv` она
лишняя, мимо `pipenv` — не читается. Это код, который врёт о себе, только в
настройках.

**Как чинить.** Убрать строку и комментарий, либо переписать комментарий на
правду: «`pipenv run` ставит это сам; строка оставлена для запуска мимо него» —
но тогда надо, чтобы кто-то `.env` мимо `pipenv` действительно читал, а это
находка 2.

#### 5. Свой набор правил на всём дереве даёт 10 замечаний, и нигде не сказано, что так и задумано

**Где:** вывод в разделе «Что и как проверялось», пункт 8.

**Что не так.** Семь из десяти — `ARG002 Unused method argument: kind` у GOG,
Steam, OMDB и обоих зеркал Кинопоиска: единый вид метода у всех клиентов
источников, где `kind` части из них не нужен. Три — `PLR0913` на 6–7 параметрах
(`card_parts.py` и два теста).

**Почему мелочь.** Манифест прямо говорит: «Проверки считают только прирост:
унаследованный долг не вменяется», а хук смотрит один записываемый файл. По
правилам проекта это не нарушение.

**Почему всё-таки записано.** На чистом клоне это первое, что увидит любой, кто
прогонит проектный набор целиком, и ниоткуда не следует, что десять — ожидаемое
число, а не свежая поломка. Строчки в `docs/deferred.md` хватило бы.

#### 6. Четыре пакета в `[packages]` бэкенду не нужны

**Где:** `Pipfile`, `[packages]`.

**Что не так.** `pywebview` не импортирует ничто: `client/` — это один пустой
`__init__.py`. Вместе с ним в каждый клон ставятся `pythonnet`, `clr_loader`,
`bottle`, `proxy_tools`, `cffi`, `pycparser`.

**Почему мелочь.** Это задел под клиента, который начнут писать следующим, а не
мусор. Записано ради полноты картины: бэкенд закрывается с зависимостью, которой
он не касается, и на сборку она влияет — примерно шестая часть устанавливаемого.
Отдельно проверено, что она хотя бы работоспособна: `import webview` в клоне
проходит.

#### 7. Русские сообщения ревизий в консоли — мусор

**Где:** `migrations/versions/0001_schema.py`, `0002_genres.py`.

**Что не так.**

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, ����� �������: …
```

Alembic печатает `down_revision`-сообщение через `logging` в `sys.stderr`,
кодировка консоли на Windows этого не переживает.

**Почему мелочь.** Косметика, на результат не влияет: миграции проходят, штамп
верный. Но это то, что новый человек увидит первой же командой после установки, и
выглядит оно как поломка.

**Как чинить.** Либо оставить как есть осознанно (записав в `deferred.md`), либо
задать `PYTHONIOENCODING=utf-8` там же, где стоит `PYTHONDONTWRITEBYTECODE` — с
той же оговоркой про находку 4.

---

## Рекомендации (Recommendations)

1. **Одна строка в «Окружение» закрывает самую дорогую находку.** Порядок для
   чистой машины должен читаться подряд и целиком: `pipenv install --dev` →
   `cp .env.example .env` → `pipenv run alembic upgrade head` →
   `pipenv run python -m pytest`. Сегодня из четырёх шагов в `CLAUDE.md` есть
   два, и они не соседи.

2. **Решить про `.env` до того, как начнётся клиент, а не после.** Развилка
   короткая (`load_dotenv` на входе или снять зависимость), но если её не решить
   сейчас, она всплывёт первым же запуском собранного приложения — и всплывёт
   молча, отказами источников по ключу.

3. **Записать, где взять скилл.** Не переносить `.claude/` в репозиторий —
   назвать архив в «Порядке работы». Это дешевле любой альтернативы и снимает
   единственную настоящую зависимость проекта от машины автора.

4. **Проверка сети мёртвым прокси стоит того, чтобы её повторяли.** Прогон с
   `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY=http://127.0.0.1:1` — самый дешёвый способ
   доказать, что «тесты офлайновые» не декларация. Одна переменная окружения,
   ничего в коде.

5. **Число 905 стоит закрепить рядом с командой.** Оно уже названо в `CLAUDE.md`
   в разделе про смену стека; в «Окружении» его нет, а именно туда смотрит тот,
   кто ставит проект и хочет понять, всё ли встало.

---

## Вердикт (Assessment)

**Бэкенд можно закрывать?** **Да**

**Обоснование:** свежий клон коммита `1227049` встал документированными
командами с первой попытки, поднял схему в объявленное — 14 таблиц, 47 жанров,
326 соответствий — и дал 905 зелёных тестов в четырёх независимых условиях, в том
числе без сети, без ключей и без `pipenv`; собранный бэкенд отработал офлайн и
закрылся чисто. Ни одна из семи находок не касается кода бэкенда: три Important —
это недописанный шаг установки, необъявленный способ доставки ключей и оснастка,
живущая вне репозитория; все три чинятся правкой документации и одной строкой
кода в будущей точке входа.
