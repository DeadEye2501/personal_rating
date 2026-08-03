# Шкала оценок: десять или пять

> Исполняется обычным порядком проекта: слайс — одна задача, ревью отдельными
> агентами до коммита, потом следующая без паузы.

**Цель:** переменная `SCALE_X2` в `.env` переключает свою шкалу между десятью и
пятью ступенями, а уже выставленные оценки пересчитываются на старте.

**Замысел:** число ступеней читается из окружения и живёт в `Config`; прежнее
значение помнит сама база в `PRAGMA user_version`; расхождение лечится одним
пересчётом в одной транзакции; число ступеней доезжает до страницы мостом, и
страница спрашивает его до первой отрисовки.

**Спека:** `docs/specs/2026-08-03-rating-scale.md`. Она главнее этого плана: при
расхождении права спека.

## Общие условия

- Умолчание — десять ступеней. Пустое окружение, отсутствующая переменная и
  любое значение, кроме строки `0`, дают десять.
- Существующие тесты не переписываются: они идут с умолчанием.
- Схема, миграции и палитра не трогаются.
- Оценки агрегаторов от своей шкалы не зависят вовсе — всегда десять ступеней.
- Пересчёт затирает старые значения, обратимости нет. Это решение пользователя.

---

## Задача 1. Настройка и пересчёт

Настройка, чистая функция пересчёта, приведение базы к шкале и вызов в сборке.

**Файлы:**
- Изменить: `backend/config.py` — поле `scale` в `Config` и его чтение
- Создать: `backend/storage/rescale.py` — пересчёт и отметка
- Изменить: `backend/app.py:144-145` — вызов в `build_backend`
- Изменить: `.env.example` — переменная с умолчанием
- Создать: `tests/backend/test_rescale.py`

**Что отдаёт наружу:**
- `Config.scale: int` — 10 или 5
- `rescaled(value: float | None, scale: int) -> int | None`
- `async def apply_scale(sessions, scale: int) -> None`

### Шаг 1. Тесты, до кода

`PRAGMA user_version` в чистой базе равен нулю, и ноль означает «база старше
этой настройки, в ней десятибалльная шкала». Это отдельный тест, потому что
ошибка тут удваивает оценки существующей библиотеки молча.

Фикстуры `sessions`, `library`, `ratings` и константа `MOMENT` берутся из
`tests/backend/conftest.py` как есть, новых не заводится; заведение карточки в
пробах ниже показано многоточием — пишется тем же вызовом, каким его пишут
соседние проверки того же файла.

```python
"""Приведение хранимых оценок к настроенной шкале."""

import pytest
from sqlalchemy import text

from backend.storage.rescale import apply_scale, rescaled


@pytest.mark.parametrize("value, expected", [
    (10, 5), (9, 5), (8, 4), (7, 4), (6, 3), (5, 3), (4, 2), (3, 2), (2, 1),
    (1, 1), (None, None),
])
def test_ten_becomes_five(value, expected):
    assert rescaled(value, 5) == expected


@pytest.mark.parametrize("value, expected", [
    (5, 10), (4, 8), (3, 6), (2, 4), (1, 2), (None, None),
])
def test_five_becomes_ten(value, expected):
    assert rescaled(value, 10) == expected


async def test_ratings_are_converted(sessions, library, ratings):
    """Оценка кино пересчитывается по таблице."""
    item_id = await library.create(...)  # обычная фикстура карточки
    await ratings.set_score(item_id, 9, MOMENT)

    await apply_scale(sessions, 5)

    assert (await ratings.get(item_id)).score == 5


async def test_the_game_average_is_rebuilt_from_its_sides(sessions, library,
                                                          ratings):
    """Средняя игры собирается из пересчитанных сторон, а не пересчитывается
    сама: 7, 8, 9 дают 8.0, и по таблице это 4, тогда как из 4, 4, 5 выходит
    4.33."""
    item_id = await library.create(...)
    await ratings.set_aspects(item_id, 7, 8, 9, MOMENT)

    await apply_scale(sessions, 5)

    got = await ratings.get(item_id)
    assert (got.visual, got.narrative, got.gameplay) == (4, 4, 5)
    assert got.score == pytest.approx(13 / 3)


async def test_a_second_start_changes_nothing(sessions, library, ratings):
    """Отметка не даёт делить пополам на каждом запуске."""
    item_id = await library.create(...)
    await ratings.set_score(item_id, 9, MOMENT)

    await apply_scale(sessions, 5)
    await apply_scale(sessions, 5)

    assert (await ratings.get(item_id)).score == 5


async def test_an_unmarked_base_is_already_on_ten(sessions, library, ratings):
    """Нулевая отметка — это база старше настройки, и оценки в ней уже
    десятибалльные. Приняв ноль за «неизвестно» и пересчитав, мы удвоили бы
    всю библиотеку при первом же запуске новой версии."""
    item_id = await library.create(...)
    await ratings.set_score(item_id, 9, MOMENT)

    await apply_scale(sessions, 10)

    assert (await ratings.get(item_id)).score == 9


async def test_the_mark_and_the_scores_move_together(sessions, library, ratings):
    """Отметка ставится той же транзакцией, что и оценки: иначе оборванный
    пересчёт оставил бы половину переведённой библиотеки под отметкой, которая
    утверждает, что переведена вся."""
    item_id = await library.create(...)
    await ratings.set_score(item_id, 9, MOMENT)

    await apply_scale(sessions, 5)

    async with sessions() as session:
        stored = (await session.execute(text("PRAGMA user_version"))).scalar_one()
    assert stored == 5
```

### Шаг 2. Прогнать и увидеть красное

`pipenv run pytest tests/backend/test_rescale.py -q`
Ожидается: `ModuleNotFoundError: backend.storage.rescale`.

### Шаг 3. Замерить, а не предположить

Утверждение «`PRAGMA user_version` откатывается вместе с транзакцией» взято из
рассуждения, и до кода его надо проверить руками:

```powershell
pipenv run python -c "import sqlite3; c=sqlite3.connect(':memory:'); c.execute('BEGIN'); c.execute('PRAGMA user_version = 5'); c.rollback(); print(c.execute('PRAGMA user_version').fetchone())"
```

Вышло `(0,)` — откатывается, задача пишется как задумано. Вышло `(5,)` — отметка
транзакции не подчиняется, и тогда порядок обратный: сначала оценки, отметка
последней, а тест выше переписывается на «оборванный пересчёт повторяется».
Что вышло — записать в отчёт слайса.

### Шаг 4. Настройка

`backend/config.py`, поле в `Config` и строка в `load_config`:

```python
    log_level: str
    scale: int
```

```python
        log_level=value(env, "LOG_LEVEL") or "INFO",
        # Ступеней всегда десять, кроме единственного явного «нет»: опечатка в
        # переменной обязана оставить шкалу привычной, а не переписать
        # библиотеку.
        scale=FIVE if value(env, "SCALE_X2") == "0" else TEN,
```

`TEN = 10` и `FIVE = 5` объявляются там же, рядом с `DEFAULT_DATA_DIR`.

### Шаг 5. Пересчёт

`backend/storage/rescale.py`:

```python
"""Приведение хранимых оценок к настроенной шкале.

Живёт в `storage/`, а не в `service/`: предмет здесь — содержимое одной таблицы
и отметка в заголовке файла базы, и ни одного решения о том, что показывать.

Зовётся из сборки, потому что там движок: пересчёт обязан случиться до первого
запроса, а сборка — единственное место, где база уже открыта, а спросить её ещё
никто не успел.
"""

import logging

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.config import TEN
from backend.model import average_score
from backend.storage.tables import rating

logger = logging.getLogger(__name__)


def rescaled(value: float | None, scale: int) -> int | None:
    """Оценка в новой шкале.

    Вниз — округлением вверх: девятка и десятка обе становятся пятёркой, так
    решил пользователь. Вверх — умножением на два, и нечётные значения после
    круга туда-обратно не восстанавливаются.
    """
    if value is None:
        return None
    whole = int(value)
    return whole * 2 if scale == TEN else (whole + 1) // 2


async def apply_scale(sessions: async_sessionmaker[AsyncSession],
                      scale: int) -> None:
    """Привести оценки к шкале из настроек, если она сменилась.

    Сравнивать `.env` не с чем: база про свою шкалу не знает, а вывести шкалу из
    данных нельзя — библиотека из одних троек выглядит одинаково в обеих.
    Поэтому базе она и записывается.
    """
    async with sessions() as session:
        # Ноль — это база, заведённая до появления настройки: шкала в ней
        # десятибалльная. Прими мы ноль за «неизвестно», первый же запуск новой
        # версии удвоил бы всю библиотеку.
        stored = (await session.execute(
            text("PRAGMA user_version"))).scalar_one() or TEN
        if stored == scale:
            return

        for row in (await session.execute(select(rating))).all():
            await session.execute(
                update(rating).where(rating.c.item_id == row.item_id)
                .values(**_moved(row, scale)))
        # Подстановкой, а не параметром: PRAGMA связанных значений не
        # принимает. Число сюда приходит из настроек и бывает ровно двух видов.
        await session.execute(text(f"PRAGMA user_version = {scale}"))
        await session.commit()
    logger.info("оценки переведены на шкалу из %s ступеней", scale)


def _moved(row, scale: int) -> dict:
    """Три стороны игры и оценка. Средняя игры собирается из пересчитанных
    сторон: пересчитанная сама, она разошлась бы со сторонами, которые стоят с
    ней в одной строке карточки."""
    sides = {name: rescaled(getattr(row, name), scale)
             for name in ("visual", "narrative", "gameplay")}
    average = average_score(**sides)
    return {**sides,
            "score": average if average is not None
            else rescaled(row.score, scale)}
```

### Шаг 6. Вызов в сборке

`backend/app.py`, сразу после фабрики сессий и до всего остального:

```python
    engine = create_engine(config.library_db)
    sessions = session_factory(engine)
    # До первого запроса: шкала могла смениться, и лента, гистограмма и звёзды
    # обязаны увидеть уже переведённые оценки.
    await apply_scale(sessions, config.scale)
```

### Шаг 7. Шаблон настроек

`.env.example`, с объяснением — файл этот человек правит руками:

```
# Ступеней в своей оценке: 1 — десять, 0 — пять.
# Смена пересчитывает уже выставленные оценки и стирает прежние значения.
SCALE_X2=1
```

### Шаг 8. Зелёное и коммит

`pipenv run pytest -q` — весь набор, а не только новый файл: `Config` получил
поле, и собирается он в трёх десятках тестов.

```bash
git add backend/config.py backend/storage/rescale.py backend/app.py .env.example tests/backend/test_rescale.py
git commit -m "feat: своя шкала переключается между десятью и пятью ступенями"
```

---

## Задача 2. Гистограмма и мост

Столбцов столько, сколько ступеней, и число ступеней уезжает странице.

**Файлы:**
- Изменить: `backend/storage/repository/sections.py:127-160` — столбцы по шкале
- Изменить: `backend/app.py` — `SectionsRepository` получает шкалу, `Backend`
  отдаёт её наружу
- Изменить: `bridge/refs.py` — метод `scale`
- Изменить: `tests/bridge/test_page_contract.py` — сторож пары
- Создать/изменить: `tests/backend/test_histogram.py`, `tests/bridge/test_bridge_refs.py`

**Что отдаёт наружу:**
- `SectionsRepository(sessions, scale)` — второй довод обязателен
- `Backend.scale: int`
- `Refs.scale() -> dict` — обычный ответ моста с числом в `ok`

### Шаг 1. Тесты, до кода

```python
async def test_the_histogram_has_a_column_per_step(sessions, library, ratings):
    """Столбцов столько, сколько ступеней в шкале: десять на пятибалльной
    базе означали бы пять пустых столбцов справа навсегда."""
    sections = SectionsRepository(sessions, 5)
    item_id = await library.create(...)
    await ratings.set_score(item_id, 3, MOMENT)

    histogram = await sections.histogram(Kind.MOVIE, Filters())

    assert [b.score for b in histogram.buckets] == [1, 2, 3, 4, 5]
    assert next(b.count for b in histogram.buckets if b.score == 3) == 1
```

```python
def test_the_page_is_told_the_scale(spy, asked):
    """Страница рисует ряд звёзд по этому числу, и взять его больше неоткуда."""
    answers["refs.scale"] = None

    Refs(spy).scale()

    assert asked[0] == "refs.scale"
```

### Шаг 2. Прогнать и увидеть красное

`pipenv run pytest tests/backend/test_histogram.py tests/bridge/test_bridge_refs.py -q`
Ожидается: `TypeError` про лишний довод у `SectionsRepository` и
`AttributeError: scale` у `Refs`.

### Шаг 3. Столбцы по шкале

`sections.py`:

```python
class SectionsRepository(Repository):
    def __init__(self, sessions, scale: int) -> None:
        super().__init__(sessions)
        self._scale = scale
```

В `histogram` два места с `range(1, 11)` заменяются на `range(1, self._scale + 1)`,
а докстринг «Десять столбцов всегда» — на «Столбец на каждую ступень».

### Шаг 4. Шкала в сборке и в мосте

`backend/app.py`: поле `scale: int` в `Backend`, `SectionsRepository(sessions,
config.scale)` в `LibraryService`, `scale=config.scale` в конструкторе.

`bridge/refs.py`:

```python
    def scale(self) -> dict:
        """Ступеней в своей оценке. Спрашивается один раз при загрузке
        страницы: без него ряд звёзд рисовать нечем.

        Обёрнуто в корутину, как и `world.expected`: поток кладёт фабрику в
        `create_task`, а тот от числа поднимает `TypeError`."""
        return self._reply(lambda back: _scale(back))


async def _scale(backend) -> int:
    return backend.scale
```

### Шаг 5. Сторож границы

`tests/bridge/test_page_contract.py` — тринадцатая пара: число ступеней, которое
питон отдаёт, и то, которое страница умеет показать. Сторож сверяет, что набор
поддержанных страницей шкал (`NOTATION` из `state/scores.js`) включает оба
значения, которые способен вернуть `Config.scale`.

Без него переменная `SCALE_X2=0` дала бы страницу без единого ярлыка: питон
ответил бы пятёркой, а страница знала бы только десятку — и молча, потому что
`LABELS[score]` на неизвестной ступени отдаёт `undefined`, а не отказ.

### Шаг 6. Зелёное и коммит

`pipenv run pytest -q`

```bash
git add backend/storage/repository/sections.py backend/app.py bridge/refs.py tests/
git commit -m "feat: столбцов гистограммы столько же, сколько ступеней"
```

---

## Задача 3. Страница

Вторая нотация, отвязанные агрегаторы и вопрос до первой отрисовки.

**Файлы:**
- Изменить: `client/state/scores.js` — нотация на обе шкалы
- Изменить: `client/main.js` — вопрос до `mount`
- Изменить: `client/components/Stars.svelte:54`, `client/components/ScoreRow.svelte:5,11,18,22`,
  `client/app/FiltersModal.svelte:15,21` — `SCALE` становится вызовом
- Изменить: `tests/web/scores.test.js`

**Что отдаёт наружу:**
- `setScale(steps)` — зовётся один раз, при загрузке
- `scale()` — массив ступеней по порядку
- `labelOf(step)` — ярлык словом
- `colorOf(step)` — переменная цвета; подпись прежняя

### Шаг 1. Тесты, до кода

```js
describe('две шкалы', () => {
  it('на пяти ступенях отдаёт свои ярлыки и свои цвета', () => {
    setScale(5)

    expect(scale()).toEqual([1, 2, 3, 4, 5])
    expect(labelOf(3)).toBe('средне')
    // Цвета берутся из тех же десяти: новых в палитру не добавлялось.
    expect(colorOf(4)).toBe('var(--score-8)')
    expect(colorOf(5)).toBe('var(--score-10)')
  })

  it('на десяти ступенях всё как было', () => {
    setScale(10)

    expect(scale()).toHaveLength(10)
    expect(labelOf(10)).toBe('Шедевр')
    expect(colorOf(4)).toBe('var(--score-4)')
  })

  it('оценки агрегаторов от своей шкалы не зависят', () => {
    // Иначе IMDb 7.4 и 7.9 слиплись бы в один цвет вместе с переключением
    // своей шкалы, а пользователь решил, что у агрегаторов не меняется ничто.
    setScale(5)

    expect(stepOf(8.6, 10)).toBe(9)
    expect(stepOf(46, 100)).toBe(5)
  })
})
```

### Шаг 2. Прогнать и увидеть красное

`cd client; npm test -- scores`
Ожидается: `setScale is not a function`.

### Шаг 3. Нотация

`client/state/scores.js`: `LABELS` уезжает внутрь `NOTATION`, где ключ — число
ступеней, а значение — ярлыки и ряд цветов.

```js
/* Нотация двух шкал. Ярлыки десятки — из макета, пятёрки — решение
   пользователя 03.08.2026 вместе с цветами: своих цветов у пятёрки нет, она
   берёт пять из тех же десяти. */
const NOTATION = {
  10: {
    labels: { 10: 'Шедевр', 9: 'Отлично', 8: 'Хорошо', 7: 'Интересно',
              6: 'Неплохо', 5: 'Средне', 4: 'Посредственно', 3: 'Уныло',
              2: 'Плохо', 1: 'Отвратительно' },
    colors: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  },
  5: {
    labels: { 5: 'отлично', 4: 'хорошо', 3: 'средне', 2: 'посредственно',
              1: 'плохо' },
    colors: [1, 3, 5, 8, 10],
  },
}

// Шкала агрегаторов постоянна и своей не касается: чужая оценка красится по
// десяти ступеням при любой настройке. Решение пользователя 03.08.2026.
const AGGREGATOR_STEPS = 10

let steps = AGGREGATOR_STEPS

/** Ступеней в своей оценке. Приезжает от питона один раз, до первой
 *  отрисовки: настройка живёт в `.env`, и на странице её взять неоткуда. */
export function setScale(value) {
  steps = value
}

export const scale = () => Array.from({ length: steps }, (_, at) => at + 1)

export const labelOf = (step) => NOTATION[steps].labels[step] ?? ''

export const colorOf = (step) =>
  `var(--score-${NOTATION[steps].colors[step - 1]})`
```

`stepOf` перестаёт читать `steps` и считает по `AGGREGATOR_STEPS`. `verdictOf`
зовёт `labelOf`. `toneOf` не меняется.

### Шаг 4. Вопрос до отрисовки

`client/main.js`, перед `mount`:

```js
// Ступени спрашиваются до отрисовки, а не в эффекте: приехав после первого
// кадра, они сменили бы десять звёзд на пять у человека на глазах.
//
// Отказ не мешает окну открыться — шкала остаётся десятибалльной, — но молчать
// о нём нельзя: ярлыки и цвета разошлись бы с базой, и понять почему было бы
// нечем.
try {
  setScale(await call('refs.scale'))
} catch (error) {
  console.error('шкала не приехала, остаёмся на десяти ступенях', error)
}

export default mount(App, { target: document.getElementById('root') })
```

### Шаг 5. Три места, где `SCALE` был константой

`Stars.svelte:54`, `ScoreRow.svelte:18`, `FiltersModal.svelte:21` — `SCALE`
становится `scale()`, `LABELS[score]` — `labelOf(score)`. В `FiltersModal`
`HIGH_FIRST` собирается как `scale().toReversed()`.

### Шаг 6. Живьём, а не только прогоном

Ни один тест фронта не открывает окна, и всё, что ниже, видно только глазами:

```powershell
cd client; npm run build
pipenv run python main.py
```

При `SCALE_X2=1` — десять звёзд, прежние ярлыки, десять столбцов. Потом
`SCALE_X2=0` в `.env` папки данных, перезапуск: пять звёзд, пять слов, пять
столбцов, оценки в библиотеке пересчитаны, цвета агрегаторов не изменились.
Снимки обоих — в отчёт слайса.

### Шаг 7. Зелёное и коммит

`cd client; npm test` и `pipenv run pytest -q`.

```bash
git add client/ tests/web/scores.test.js
git commit -m "feat: страница рисует ту шкалу, которая задана настройкой"
```

---

## Чего в плане нет намеренно

- **Окна настроек.** Переменная правится в `.env` руками, как ключи источников.
- **Проверки, что оценки влезают в шкалу.** После пересчёта они влезают по
  построению, а `rating.score` границ не знает и никогда не знал.
- **Пересчёта закладок, тегов и оценок агрегаторов.** Своя шкала их не касается.
- **Отдельной миграции.** Отметка живёт в заголовке файла базы, схема прежняя.
