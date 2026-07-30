# План 5. Каркас клиента

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** окно, которое показывает библиотеку. Тема, стык потоков, шапка,
лента с пулом переиспользуемых карточек, сама карточка и плашка сообщений.
После этого плана приложение запускается, ищет, показывает ленту и принимает
оценки; модалки, статистика и окно карточки — план 6.

**Архитектура:** одна дверь между слоями — `client/runtime.py`: страница отдаёт
задачу, получает результат сигналом Qt уже в главном потоке. Всё оформление
собрано в `client/theme/`, и это единственное место, где есть цвет. Виджеты не
знают, откуда данные: карточка получает готовый `CardView` методом `bind`.

**Стек:** PySide6, плюс **pytest-qt** для тестов — без него QApplication в
тестах поднимается руками, а очередь событий не прокручивается.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от планов 1–4.** Бэкенд закончен: `build_backend(config)` собирает
  его целиком, `Backend` отдаёт репозитории и сервисы, типы границы лежат в
  `backend/model/`.
- **Макет — источник истины.** `docs/design/index.html` и `docs/design/styles/` сделаны
  тщательнее спек; при расхождении прав макет. Исключение одно: **данные в
  макете рыба**, на них не ссылаемся.
- **`client` не импортирует `sqlalchemy` и `httpx`.** Тест из плана 1 это
  стережёт.
- **Граница слоёв — граница потоков.** В главном потоке нет ни одного обращения
  к сети или диску. Через границу ходят только простые данные; постер приезжает
  байтами, `QPixmap` из них делает интерфейс.
- **Ни один объект бэкенда не хранит ссылку на виджет.** Единственный объект Qt,
  живущий в двух потоках, — `Call` из `runtime.py`, и это объявлено.
- **Карточка принимает данные методом `bind`,** а не собирается в конструкторе.
  Без этого пул невозможен.
- **Состояние живёт в данных, а не в виджете.** Свёрнута карточка или нет —
  принадлежит строке ленты, а не тому виджету, который её сейчас показывает.
- **Цвет объявлен один раз.** В `client/theme/`, и нигде больше: ни
  шестнадцатеричных значений по виджетам, ни цвета внутри `.qss`.
- **Внешний вид тестами не покрываем.** Проверяем поведение, геометрию и
  состояние: привязку пула, освобождение, распорки, прокрутку в обе стороны,
  перебор сортировки, арифметику звёзд. Цвет кнопки дешевле увидеть глазами.
- **Молча не глотаем ничего.** Пойманное исключение ведёт либо к показу, либо к
  записи в лог — минимум одно из двух.
- **Байтовые литералы только ASCII.** `b"текст"` с кириллицей — это
  `SyntaxError` на сборе, который валит весь прогон.
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ main.py                        собирает зависимости и поднимает окно
├─ client/
│  ├─ theme/
│  │  ├─ palette.py               цвета и шкала оценок
│  │  ├─ typography.py            начертания из макета
│  │  ├─ metrics.py               радиусы, отступы, размеры
│  │  ├─ icons.py                 Material Symbols, ось FILL
│  │  ├─ qss.py                   стили с подстановкой токенов
│  │  ├─ styles/*.qss             сами стили, без единого цвета
│  │  └─ assets/*.ttf             шрифты
│  ├─ runtime.py                  поток бэкенда и доставка результата
│  ├─ widgets/
│  │  ├─ neon.py                  кромка окна и свечение
│  │  ├─ search.py                строка поиска
│  │  ├─ segmented.py             переключатель типа содержимого
│  │  ├─ toolbar.py               ряд круглых кнопок
│  │  ├─ topbar.py                шапка целиком, замер ширины
│  │  ├─ stars.py                 ряд звёзд и вердикт
│  │  ├─ chips.py                 жанры, теги, «± Тег»
│  │  ├─ facts.py                 состав, длительность, синопсис
│  │  ├─ aggregates.py            чужие оценки и кольцо ожидания
│  │  ├─ card.py                  карточка целиком, bind
│  │  ├─ feed.py                  пул, распорки, прокрутка
│  │  ├─ topbar.py                шапка целиком и её замеры
│  │  └─ snack.py                 плашка сообщений
│  ├─ pages/
│  │  ├─ feed.py                  одна лента на поиск, оценённые и отложенные
│  │  └─ stats.py                 заглушка, наполняет план 6
│  └─ window.py                   окно, стопка страниц, переход
└─ tests/client/
   ├─ conftest.py                 общая фикстура темы
   ├─ test_palette.py             test_typography.py
   ├─ test_icons.py               test_qss.py
   ├─ test_runtime.py             test_window.py
   ├─ test_search_field.py        test_segmented.py
   ├─ test_toolbar.py             test_stars.py
   ├─ test_flow.py                test_chips.py
   ├─ test_aggregates.py          test_card.py
   ├─ test_feed_pool.py           test_topbar.py
   └─ test_pages.py
```

`docs/specs/2026-07-27-code-structure.md:33` перечисляет в `pages/` четыре модуля —
`search`, `rated`, `wish`, `stats`. Первые три отличаются только тем, что
спрашивают у бэкенда и в каком порядке показывают, поэтому здесь это **один**
`FeedPage` с параметром, а не три файла по десять строк. Список в спеке
иллюстративный; правило «страницы тонкие» соблюдено.

---

### Задача 1: Каркас клиента и граница слоёв

Пакеты, зависимость и тест, который стережёт договорённость. Тест границы из
плана 1 проверял только `backend`; теперь появляется вторая половина правила.

**Файлы:**
- Создать: `tests/client/conftest.py`
- Изменить: `tests/backend/test_layers.py`, `pytest.ini`, `Pipfile`

**Интерфейсы:**
- Потребляет: `offenders` из `tests/backend/test_layers.py` (план 1, задача 1).
- Отдаёт: пакеты `client.theme`, `client.widgets`, `client.pages`;
  автоматическую фикстуру `theme` в `tests/client/conftest.py` — на ней стоят
  все остальные задачи.

- [ ] **Шаг 1: Поставить pytest-qt**

```bash
pipenv install --dev pytest-qt
```

- [ ] **Шаг 2: Расширить существующего сторожа границы**

`tests/backend/test_layers.py` уже написан планом 1, задача 1: там разбор
импортов через `ast`, набор `BANNED_IN_CLIENT` и помощник
`offenders(package, banned)` с проверкой существования каталога. Переписывать
его руками не нужно и вредно — наивный поиск подстроки `import PIL` не поймает
`from PIL import Image`.

Дописать в тот же файл:

```python
def test_client_does_not_import_the_image_library():
    """Картинки обрабатывает бэкенд: обрезка в главном потоке — ровно то, от
    чего окно замирает. Постер приезжает байтами."""
    assert offenders("client", {"PIL"}) == []


def test_backend_does_not_import_qt():
    """Бэкенд тестируется без окна — прямое следствие того, что он живёт в
    своём потоке."""
    assert offenders("backend", {"PySide6"}) == []
```

**Красной фазы у этих двух нет, и это нормально.** Они не добавляют поведение,
а расширяют сторожа: нарушений, которые они ловят, в коде нет и быть не должно.
Красную фазу здесь давала бы только намеренная порча.

- [ ] **Шаг 3: Завести пакеты и общую фикстуру**

Маркеры пакета не заводим: с PEP 420 папка с `.py` и так пакет.
`client/__init__.py` план 1 завёл по другой причине — пустую папку git не
хранит, а тест границы слоёв требует, чтобы пакет существовал.

Создать `tests/client/conftest.py`:

```python
import pytest
from PySide6.QtWidgets import QWidget

_NOTHING = object()


@pytest.fixture(scope="session", autouse=True)
def theme(qapp):
    """Тема ставится один раз на весь прогон: шрифты подгружаются с диска, и
    делать это на каждый тест незачем.

    autouse — чтобы результат не зависел от того, попросил ли тест фикстуру:
    без загруженных шрифтов метрики поедут, и высоты карточек в ленте окажутся
    другими.

    Импорт внутри и под `try`. Фикстура autouse срабатывает перед **любым**
    тестом каталога, включая задачи 2 и 3, где `client/theme/__init__.py` ещё
    пуст: `apply_theme` появляется только в задаче 4. Без этого `ImportError`
    падал бы на подготовке и валил тесты, которым тема не нужна вовсе, — а
    план обещает им PASS."""
    try:
        from client.theme import apply_theme
    except ImportError:
        # Задачи 2–3: темы ещё нет, и она им не нужна.
        return qapp

    apply_theme(qapp)
    return qapp


class Slot:
    """Сигнал-заглушка, который помнит последнее значение.

    Настоящий Call испускает done из потока бэкенда, и подключиться к нему
    успевают всегда: запуск отложен на круг цикла. У заглушки работа делается
    синхронно внутри call(), то есть до connect, — поэтому пришедшее значение
    отдаётся новому слушателю сразу."""

    def __init__(self):
        self.slots = []
        self._value = _NOTHING

    def connect(self, slot):
        self.slots.append(slot)
        if self._value is not _NOTHING:
            slot(self._value)

    def emit(self, value):
        self._value = value
        for slot in list(self.slots):
            slot(value)


class SpyCall:
    """Вместо настоящего Call: запоминает, отменяли ли его."""

    def __init__(self):
        self.cancelled = False
        self.done = Slot()
        self.failed = Slot()

    def cancel(self):
        self.cancelled = True


class SpyRepo:
    """Фасад репозитория: запоминает вызов и отдаёт заготовленный ответ."""

    def __init__(self, spy, name):
        self._spy = spy
        self._name = name

    def __getattr__(self, method):
        def remember(*args, **fields):
            key = f"{self._name}.{method}"
            self._spy.asked.append((key, args, fields))
            return self._spy.answers.get(key)
        return remember


class SpyBackend:
    """Бэкенд целиком. Фасады заводятся по требованию: их семнадцать, и
    перечислять поимённо значит забыть половину."""

    def __init__(self, runtime):
        self.asked = runtime.asked
        self.answers = runtime.answers

    def __getattr__(self, name):
        return SpyRepo(self, name)


class FakeRuntime:
    """Выполняет задачу сразу и доставляет ответ так же, как настоящий, —
    сигналом done, а не полем: поля result у Call нет вовсе."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.asked = []
        self.calls = []

    def call(self, work):
        call = SpyCall()
        self.calls.append(call)
        call.done.emit(work(SpyBackend(self)))
        return call

    def close(self):
        pass


_HOSTS: list[QWidget] = []


def host(width: int = 900, height: int = 600) -> QWidget:
    """Окно-родитель для модалок.

    Хранить его обязательно: `qtbot` держит только слабую ссылку, и окно,
    созданное выражением, собирается мусором вместе со всеми детьми —
    `RuntimeError: Internal C++ object already deleted`. Ссылку держит список
    выше, а чистит его фикстура ниже."""
    window = QWidget()
    window.resize(width, height)
    window.show()
    _HOSTS.append(window)
    return window


@pytest.fixture(autouse=True)
def _forget_hosts():
    yield
    for window in _HOSTS:
        window.close()
    _HOSTS.clear()
```

**`qtbot` держит виджет слабой ссылкой** — это проверено прогоном: окно,
переданное выражением (`Modal(host())`), умирает до первой строки теста, и
тест падает `RuntimeError: libshiboken: Internal C++ object (Modal) already
deleted`. Поэтому ссылка живёт в списке модуля.

**`host` — обычная функция, а не фикстура**, и просить её параметром не надо.
Половина вызовов в плане 6 сидит внутри вспомогательных функций (`opened`,
`window`, `picker`), куда фикстура не доходит в принципе, — и каждая такая
строка давала бы `NameError: name 'host' is not defined`. Функция работает
отовсюду, а уборка вынесена в autouse-фикстуру, которой параметры не нужны.

В `pytest.ini` `testpaths` — это `tests`, отдельной строки под `tests/client`
не нужно.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/backend/test_layers.py -v`
Ожидается: PASS, четыре теста — два из плана 1 и два новых.

- [ ] **Шаг 5: Коммит**

```bash
git add client tests/client tests/backend/test_layers.py Pipfile Pipfile.lock
git commit -m "feat: каркас клиента и тест границы слоёв в обе стороны"
```

---

### Задача 2: Цвета и шкала оценок

**Единственное место, где есть цвет.** Всё из `docs/design/styles/tokens.css`,
один в один.

**Шкала из десяти цветов — общая нотация.** Один и тот же цвет закреплён за
значением и повторяется в трёх местах: звёзды в карточке, столбцы гистограммы,
строки фильтра по оценке. Меняется только здесь.

**Чужая оценка приводится к десятибалльной.** У IMDb шкала 0–10, у Rotten
Tomatoes 0–100 — цвет берётся из той же нотации, что и своя оценка, поэтому
значение сначала переводится в ступень от 1 до 10.

**Файлы:**
- Создать: `client/theme/palette.py`
- Создать: `tests/client/test_palette.py`

**Интерфейсы:**
- Отдаёт: `BACKGROUND`, `PRIMARY`, `ERROR`, `TEXT`, `TEXT_BRIGHT`, `GLASS`,
  `GLASS_ERROR`, `GLASS_PRIMARY`, `SURFACE_POP`, `SCALE` (кортеж из десяти),
  `score_color(step: int) -> str`,
  `scale_color(value: float, maximum: float) -> str`,
  `mix(color: str, percent: int) -> str` — все цвета строками `#rrggbb` или
  `rgba(...)`, пригодными и для QSS, и для `QColor`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_palette.py`:

```python
import pytest

from client.theme import palette


def test_the_scale_has_ten_steps():
    """Столбцов десять, и цвет закреплён за значением."""
    assert len(palette.SCALE) == 10


def test_the_two_empty_stars_stay_different():
    """В макете звезда карточки и звезда строки фильтра разной прозрачности.
    Свести их — правка макета, а не вынос дубля."""
    assert palette.STAR_EMPTY != palette.STAR_EMPTY_SMALL


def test_the_dim_under_a_modal_is_translucent():
    """Сквозь затемнение видно ленту — иначе это не модалка, а страница.
    Проверяем разобранный цвет, а не строку: `QColor` записи `rgba(...)` не
    понимает и молча отдаёт непрозрачный чёрный."""
    assert palette.qcolor(palette.OVERLAY_DIM).alpha() < 255


def test_every_colour_of_the_palette_survives_the_trip_to_qcolor():
    """Всё, что рисуется вручную — иконки, затемнение, нить кромки, — идёт
    через QColor. Он не понимает записи `rgba(...)` и на невалидной строке
    молча отдаёт непрозрачный чёрный: иконка станет чёрной на чёрном, и ни
    один тест этого не увидит, потому что внешний вид мы не покрываем."""
    for name, value in vars(palette).items():
        if not name.isupper() or not isinstance(value, str):
            continue
        made = palette.qcolor(value)
        assert made.isValid(), name
        if "rgba" in value:
            assert made.alpha() < 255, name


def test_red_at_one_and_blue_at_ten():
    assert palette.score_color(1) == "#F44336"
    assert palette.score_color(10) == "#2196F3"


def test_a_step_outside_the_scale_is_clamped():
    """Дробная оценка округляется вниз, и у 0.4 целая часть — ноль. Цвет
    всё равно нужен: строка в ленте не должна остаться без него."""
    assert palette.score_color(0) == palette.score_color(1)
    assert palette.score_color(99) == palette.score_color(10)


def test_a_fractional_score_gets_a_colour():
    """Rating.score — это float, и у игры он дробный. Без приведения типа
    кортеж индексируется вещественным числом и падает TypeError."""
    assert palette.score_color(7.33) == palette.score_color(7)
    assert palette.score_color(9.0) == palette.score_color(9)


def test_a_scale_without_a_top_still_gives_a_colour():
    """Ранний возврат: делить на ноль нечем, но цвет строке нужен."""
    assert palette.scale_color(5, 0) == palette.score_color(1)


@pytest.mark.parametrize(
    "value, maximum, step",
    [
        (8.6, 10, 9),      # IMDb
        (86, 100, 9),      # Rotten Tomatoes
        (7.4, 10, 8),      # TMDB, вверх до ступени
        (0.1, 10, 1),      # почти ноль — но не ниже первой ступени
        (100, 100, 10),
    ],
)
def test_any_scale_becomes_the_same_ten_steps(value, maximum, step):
    """Цвет чужой оценки берётся из той же нотации, что и своей."""
    assert palette.scale_color(value, maximum) == palette.score_color(step)


def test_the_accent_is_the_only_source_of_the_highlight():
    """От него идут и рамка фокуса, и выделение текста, и все цветные
    элементы экранов."""
    assert palette.PRIMARY == "#84e310"


def test_a_mix_keeps_the_colour_and_changes_the_alpha():
    """color-mix из макета: цвет тот же, прозрачность разная."""
    assert palette.mix(palette.PRIMARY, 14) == "rgba(132, 227, 16, 0.14)"


def test_glass_is_translucent():
    """Стекло — подложка под размытием, и оно обязано быть полупрозрачным."""
    for name in ("GLASS", "GLASS_ERROR", "GLASS_PRIMARY", "SURFACE_POP"):
        assert getattr(palette, name).startswith("rgba("), name


def test_every_colour_is_written_once():
    """Дублей в палитре быть не должно: цвет меняется в одном месте."""
    named = {name: value for name, value in vars(palette).items()
             if name.isupper() and isinstance(value, str)}
    duplicates = [v for v in named.values() if list(named.values()).count(v) > 1]
    assert duplicates == []
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_palette.py -v`
Ожидается: FAIL — `ImportError: cannot import name 'palette'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/theme/palette.py`:

```python
"""Цвета приложения. Единственное место, где они есть.

Строковая форма выбрана нарочно: она годится и для QSS, и для QColor, а
обратный перевод из QColor в строку каждый раз терял бы прозрачность."""

BACKGROUND = "#0a0a0a"

# Единственный источник акцента: от него идут и рамка фокуса, и выделение
# текста, и все цветные элементы экранов.
PRIMARY = "#84e310"

# Красный на всё, что сообщает о беде или необратимо: плашка сообщений,
# корзина на карточке, крестик у исключённого.
ERROR = "#ff4a45"

TEXT = "rgba(255, 255, 255, 0.90)"
TEXT_BRIGHT = "#ffffff"

# Полупрозрачные подложки под размытием. Тон подсказывает смысл: нейтральное,
# тревожное, подтверждающее.
GLASS = "rgba(30, 30, 32, 0.55)"
GLASS_ERROR = "rgba(39, 15, 15, 0.55)"
GLASS_PRIMARY = "rgba(41, 58, 15, 0.64)"

# Всплывающее поверх содержимого — список совпадений. Почти непрозрачное:
# сквозь него читать нечего.
SURFACE_POP = "rgba(14, 16, 19, 0.98)"

# Лестница белого по прозрачности. Всё, что в макете написано как
# rgba(255,255,255,·), объявлено здесь и только здесь: подложки капсул, их
# рамки, приглушённый и совсем бледный текст.
def white(alpha: float) -> str:
    return f"rgba(255, 255, 255, {alpha})"


PILL = white(0.035)          # подложка капсулы
PILL_BORDER = white(0.06)    # её рамка
PILL_HOVER = white(0.05)     # подложка под курсором
PILL_BORDER_HOVER = white(0.10)
FILM_BORDER = white(0.07)    # рамка карточки в ленте
BRIGHT = white(0.75)         # текст под курсором
MUTED = white(0.45)          # подписи и выключенные иконки
FAINT = white(0.30)          # «± Тег» и прочее едва заметное
STAR_EMPTY = white(0.16)     # незажжённая звезда
# Она же в строке фильтра: там звезда мельче (17 px против 21) и темнее. В
# макете это два разных значения, и сводить их в одно нельзя — это была бы
# правка макета, а не вынос дубля.
STAR_EMPTY_SMALL = white(0.14)

# Затемнение под модалкой: сквозь него видно ленту, иначе это не модалка, а
# страница.
OVERLAY_DIM = "rgba(0, 0, 0, 0.32)"

# Красный трёхпозиционного переключателя. Он ярче общего ERROR, и это не
# описка: в макете у крестика исключения свой оттенок.
ERROR_BOX = "#ef4444"

# Шкала оценок. Цвет закреплён за значением и одинаков везде — в фильтре, на
# звёздах, в столбцах статистики. Индекс в кортеже на единицу меньше оценки.
SCALE = (
    "#F44336",  # 1
    "#FF5722",  # 2
    "#FF9800",  # 3
    "#FFC107",  # 4
    "#FFEB3B",  # 5
    "#CDDC39",  # 6
    "#8BC34A",  # 7
    "#4CAF50",  # 8
    "#00BCD4",  # 9
    "#2196F3",  # 10
)


def score_color(step: float) -> str:
    """Цвет ступени. Дробное приходит прямо из базы — у игр score это среднее
    трёх шкал, — и округляется вниз, как везде в показе. Значение вне шкалы
    прижимается к краю: строка в ленте не должна остаться без цвета."""
    return SCALE[min(10, max(1, int(step))) - 1]


def scale_color(value: float, maximum: float) -> str:
    """Любая чужая шкала приводится к десятибалльной. Округляем вверх: 7.4 из
    десяти — это восьмая ступень, как в макете."""
    if maximum <= 0:
        return score_color(1)
    return score_color(ceil(value / maximum * 10))


def mix(color: str, percent: int) -> str:
    """Аналог color-mix из макета: тот же цвет, другая прозрачность."""
    text = color.lstrip("#")
    red, green, blue = (int(text[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {percent / 100:.2f})"


def qcolor(color: str) -> QColor:
    """Строка палитры в QColor — для всего, что рисуется вручную.

    `QColor("rgba(255, 255, 255, 0.90)")` **невалиден**: конструктор понимает
    именованные цвета и `#rrggbb`, но не запись CSS. Молча, без исключения, он
    даёт при этом непрозрачный чёрный — чёрную иконку на чёрном фоне и глухую
    заливку вместо полупрозрачного затемнения. Правило «внешний вид тестами не
    покрываем» от такого не защищает, поэтому разбираем сами."""
    text = color.strip()
    if not text.startswith("rgb"):
        return QColor(text)

    parts = text[text.index("(") + 1:text.rindex(")")].split(",")
    red, green, blue = (int(part) for part in parts[:3])
    alpha = float(parts[3]) if len(parts) > 3 else 1.0
    return QColor(red, green, blue, round(alpha * 255))
```

В шапку файла добавить `from math import ceil` и
`from PySide6.QtGui import QColor`.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_palette.py -v`
Ожидается: PASS, семнадцать тестов — двенадцать своих и пять случаев
параметризации.

- [ ] **Шаг 5: Коммит**

```bash
git add client/theme/palette.py tests/client/test_palette.py
git commit -m "feat: палитра и шкала оценок одним объявлением"
```

---

### Задача 3: Типографика и размеры

Остальные токены макета: начертания, радиусы, отступы, размеры элементов.
Отдельно от цвета, потому что меняются по другим поводам.

**Начертания записаны как в CSS.** `--body-l: 400 16px/24px` — это вес,
размер и межстрочный интервал; в Qt первые два ложатся в `QFont`, третий — в
`QSS` и в раскладку, поэтому храним все три.

**Файлы:**
- Создать: `client/theme/typography.py`, `client/theme/metrics.py`
- Создать: `tests/client/test_typography.py`

**Интерфейсы:**
- Отдаёт: `Face(weight, size, line)` и константы `TITLE_L`, `TITLE_S`,
  `BODY_L`, `BODY_M`, `LABEL_L`, `LABEL_M`, `FAMILY`;
  `font(face: Face) -> QFont`;
  в `metrics.py` — `R_CARD` (20), `R_FULL` (999), `R_FILM` (14),
  `TOPBAR_GAP` (18), `CORNER` (24), `PILL_H` (42), `TOOL_BTN` (34),
  `POSTER_W` (158), `FEED_GAP` (12), `MIN_W` (480), `MIN_H` (460).

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_typography.py`:

```python
from PySide6.QtGui import QFont

from client.theme import metrics, typography


def test_faces_carry_all_three_numbers():
    """400 16px/24px — вес, размер и межстрочный. Последний в QFont не
    ложится, но нужен раскладке."""
    assert (typography.BODY_L.weight, typography.BODY_L.size,
            typography.BODY_L.line) == (400, 16, 24)


def test_a_face_becomes_a_qfont(theme):
    made = typography.font(typography.TITLE_L)

    assert isinstance(made, QFont)
    assert made.pointSizeF() == -1, "размеры в макете пиксельные"
    assert made.pixelSize() == typography.TITLE_L.size
    assert made.weight() == QFont.Weight.Normal


def test_the_medium_weight_survives_the_translation(theme):
    """--title-s и --label-* объявлены пятисотыми: в Qt это Medium."""
    assert typography.font(typography.TITLE_S).weight() == QFont.Weight.Medium


def test_the_family_is_the_one_from_the_mockup():
    assert typography.FAMILY == "Roboto"


def test_the_pill_height_matches_the_switch():
    """Строка поиска, переключатель и ряд кнопок стоят вровень."""
    assert metrics.PILL_H == 42
    assert metrics.TOOL_BTN + 2 * metrics.PILL_PAD + 2 * metrics.PILL_BORDER == (
        metrics.PILL_H
    )


def test_the_poster_keeps_the_two_to_three_ratio():
    """158 × 1.5 = 237 — высота текстовой колонки карточки."""
    assert metrics.POSTER_W == 158
    assert metrics.POSTER_H == 237


def test_the_window_has_a_floor_but_no_ceiling():
    assert (metrics.MIN_W, metrics.MIN_H) == (480, 460)
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_typography.py -v`
Ожидается: FAIL — `ImportError: cannot import name 'typography'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/theme/typography.py`:

```python
"""Начертания из макета. Запись повторяет CSS: вес, размер, межстрочный."""

from dataclasses import dataclass

from PySide6.QtGui import QFont

FAMILY = "Roboto"

# Вес в CSS числом, в Qt — перечислением. Переводим таблицей, а не делением:
# у Qt шкала своя и не линейная.
_WEIGHTS = {400: QFont.Weight.Normal, 500: QFont.Weight.Medium,
            600: QFont.Weight.DemiBold, 700: QFont.Weight.Bold}


@dataclass(frozen=True, slots=True)
class Face:
    """Одно объявление шрифта. line в QFont не ложится — он нужен раскладке
    и подставляется в QSS как line-height."""

    weight: int
    size: int
    line: int


TITLE_L = Face(weight=400, size=22, line=28)
TITLE_S = Face(weight=500, size=14, line=20)
BODY_L = Face(weight=400, size=16, line=24)
BODY_M = Face(weight=400, size=14, line=20)
LABEL_L = Face(weight=500, size=14, line=20)
LABEL_M = Face(weight=500, size=12, line=16)


def font(face: Face) -> QFont:
    """Размеры в макете пиксельные, поэтому setPixelSize, а не setPointSize:
    при масштабе 125% точки поехали бы, а пиксели Qt пересчитает сам."""
    made = QFont(FAMILY)
    made.setPixelSize(face.size)
    made.setWeight(_WEIGHTS[face.weight])
    return made
```

Создать `client/theme/metrics.py`:

```python
"""Радиусы, отступы и размеры. Всё из макета."""

R_CARD = 20      # модалка
R_FILM = 14      # карточка ленты
R_POSTER = 8
R_FULL = 999     # капсула

# Шапка: три блока одной ширины, зазор между ними и отступ от края окна.
TOPBAR_GAP = 18
CORNER = 24

# Капсула шапки: кнопка 34 плюс по 3 отступа и по 1 рамке с каждой стороны.
PILL_H = 42
PILL_PAD = 3
PILL_BORDER = 1
TOOL_BTN = 34

# Карточка ленты.
POSTER_W = 158
POSTER_H = 237   # 158 × 1.5 — пропорция афиши 2:3
FILM_GUTTER = 52   # колонка под угловые иконки: шеврон сверху, закладка снизу
FILM_ICON_INSET = 14
FEED_GAP = 12
# Подпись стороны оценки у игр. Ширина общая, чтобы звёзды в трёх строках
# стояли по одной вертикали.
ASPECT_W = 86

# Настоящий минимум ширины считает шапка замером; это запас до первого замера.
MIN_W = 480
MIN_H = 460
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_typography.py -v`
Ожидается: PASS, семь тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/theme/typography.py client/theme/metrics.py \
        tests/client/test_typography.py
git commit -m "feat: типографика и размеры из макета"
```

---

### Задача 4: Иконочный шрифт и ось FILL

**Контур в покое, заливка во включённом состоянии.** В Material Symbols это
ось `FILL` переменного шрифта.

**Заводится ли она в Qt — выясняется прогоном, а не по документации.** Это
второе место во всём проекте, которое собирается опытом: первое было игровой
половиной справочника жанров. `docs/specs/2026-07-27-code-structure.md:107` уже
называет запасной путь — два статических начертания, — и правило от выбора не
меняется.

**Файлы:**
- Создать: `scripts/probe_fill_axis.py`
- Создать: `client/theme/assets/` со шрифтами
- Создать: `client/theme/icons.py`, `client/theme/__init__.py` (с реэкспортом)
- Создать: `tests/client/test_icons.py`

**Интерфейсы:**
- Отдаёт: `ICON_FAMILY`, `icon_font(size: int, filled: bool = False) -> QFont`,
  `loaded_families()` — что загружено нами, а не системой,
  `GLYPHS` — имена лигатур, которыми пользуются виджеты;
  `apply_theme(app: QApplication) -> None` в `client.theme` — грузит шрифты и
  вешает стили.

- [ ] **Шаг 1: Положить шрифты**

Скачать и положить в `client/theme/assets/`:

- `MaterialSymbolsOutlined.ttf` — переменный, с осями `FILL`, `wght`, `GRAD`,
  `opsz`;
- `Roboto-Regular.ttf`, `Roboto-Medium.ttf`, `Roboto-SemiBold.ttf`.

Система ресурсов Qt не используется: она требует отдельного шага компиляции при
каждом изменении, а выигрыша здесь не даёт — упаковка решается на этапе сборки
исполняемого файла.

- [ ] **Шаг 2: Выяснить прогоном, работает ли ось**

Создать `scripts/probe_fill_axis.py`:

```python
"""Заводится ли ось FILL переменного шрифта в этой сборке Qt.

Разовый скрипт, в client не импортируется. Печатает ответ и ширину глифа в
обоих состояниях: если ось не работает, обе метрики совпадут."""

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF
from PySide6.QtWidgets import QApplication

ASSETS = Path(__file__).resolve().parent.parent / "client" / "theme" / "assets"


def main() -> int:
    app = QApplication(sys.argv)

    loaded = QFontDatabase.addApplicationFont(
        str(ASSETS / "MaterialSymbolsOutlined.ttf")
    )
    if loaded == -1:
        print("шрифт не загрузился")
        return 1

    family = QFontDatabase.applicationFontFamilies(loaded)[0]
    print("семейство:", family)
    print("есть setVariableAxis:", hasattr(QFont, "setVariableAxis"))

    for fill in (0, 1):
        made = QFont(family)
        made.setPixelSize(48)
        if hasattr(QFont, "setVariableAxis"):
            made.setVariableAxis(QFont.Tag("FILL"), float(fill))
        metrics = QFontMetricsF(made)
        # star — лигатура Material Symbols; у закрашенной и контурной версий
        # рисунок разный, а ширина одна. Сравниваем не ширину, а картинку.
        print(f"FILL={fill}: ширина star = {metrics.horizontalAdvance('star'):.2f}")

    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Запустить: `pipenv run python scripts/probe_fill_axis.py`

**Ширина глифа тут ничего не докажет** — у контурной и закрашенной звезды она
одинакова. Решает `hasattr(QFont, "setVariableAxis")`: метод появился в Qt 6.7,
и если он есть, ось задаётся им. Записать ответ строкой в
`docs/specs/2026-07-27-code-structure.md`, рядом с абзацем про ось FILL.

Если метода нет — скачать вдобавок `MaterialSymbolsOutlined-Filled.ttf`
(статический экземпляр с `FILL=1`) и дальше идти запасным путём.

- [ ] **Шаг 3: Написать падающий тест**

Создать `tests/client/test_icons.py`:

```python
from PySide6.QtGui import QFont, QFontDatabase

from client.theme import icons


def test_the_icon_family_is_loaded(theme):
    """Без шрифта на месте иконок будут прямоугольники, и заметить это в
    тесте дешевле, чем разглядывать окно."""
    assert icons.ICON_FAMILY in QFontDatabase.families()


def test_the_text_family_comes_from_our_file(theme):
    """Roboto может стоять и в системе — проверено на живой машине. Сверяем с
    тем, что вернул applicationFontFamilies, иначе тест зелёный и при
    незагруженном файле."""
    from client.theme import typography

    assert typography.FAMILY in icons.loaded_families()


def test_the_two_states_draw_differently(theme):
    """Контур в покое, заливка во включённом. Чем это сделано — осью или
    вторым начертанием — виджету знать незачем, а вот что рисунок правда
    разный, проверить надо: два QFont отличаются значением оси даже если шрифт
    её не поддерживает."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter

    def draw(glyph: str, filled: bool) -> QImage:
        image = QImage(48, 48, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setFont(icons.icon_font(40, filled=filled))
        painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
        painter.end()
        return image

    star = icons.GLYPHS["score"]
    assert draw(star, False) != draw(star, True)
    # И сама лигатура существует: иначе оба раза рисуется пустой прямоугольник
    # и картинки совпали бы по другой причине.
    assert draw(star, False) != draw("zzz_no_such_glyph", False)


def test_the_size_is_the_one_asked_for(theme):
    assert icons.icon_font(19).pixelSize() == 19


def test_every_glyph_really_draws_something(theme):
    """Опечатка в имени лигатуры даёт пустой прямоугольник, и найти её потом
    по коду тяжело. Сверять список со списком бесполезно — он его же копия;
    рисуем и сравниваем с заведомо несуществующей."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter

    def draw(glyph: str) -> QImage:
        image = QImage(48, 48, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setFont(icons.icon_font(40))
        painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
        painter.end()
        return image

    nothing = draw("zzz_no_such_glyph")
    for name, glyph in icons.GLYPHS.items():
        assert draw(glyph) != nothing, f"{name}: {glyph}"
```

- [ ] **Шаг 4: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_icons.py -v`
Ожидается: FAIL — `ImportError: cannot import name 'icons'`.

- [ ] **Шаг 5: Реализовать**

Создать `client/theme/icons.py`:

```python
"""Material Symbols. Правило одно: контур в покое, заливка во включённом.

Держится оно на оси FILL переменного шрифта; если ось в этой сборке Qt не
заводится, вместо неё ставится второе статическое начертание. Наружу разницы
нет — виджет просит icon_font(size, filled)."""

import logging
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent / "assets"

ICON_FAMILY = ""
_FILLED_FAMILY = ""
_HAS_AXIS = hasattr(QFont, "setVariableAxis")

# Имена лигатур в одном месте: опечатка даёт пустой прямоугольник, и искать
# её по коду потом тяжело.
GLYPHS = {
    "search": "search",
    "clear": "close",
    "movies": "movie",
    "series": "live_tv",
    "games": "sports_esports",
    "rated": "thumb_up",
    "wish": "bookmark",
    "genres": "category",
    "tags": "label",
    "score": "star",
    "collapse": "unfold_less",
    "expand": "unfold_more",
    "down": "arrow_downward",
    "up": "arrow_upward",
    "add": "add",
    # Два глифа, а не один с поворотом: transform в QSS Qt не понимает.
    "chevron_up": "expand_less",
    "chevron_down": "expand_more",
    "rated_at": "history",
    "year": "event",
    "alphabet": "sort_by_alpha",
    "edit": "edit",
    "delete": "delete",
    "ok": "check",
    "photo": "photo_camera",
    "waiting": "progress_activity",
}


def load_fonts() -> None:
    """Зовётся один раз при старте. Повторный вызов безвреден: Qt тот же файл
    второй раз не регистрирует, но и не ломается."""
    global ICON_FAMILY, _FILLED_FAMILY

    _LOADED.clear()
    ICON_FAMILY = _load("MaterialSymbolsOutlined.ttf")
    for name in ("Roboto-Regular.ttf", "Roboto-Medium.ttf",
                 "Roboto-SemiBold.ttf"):
        _load(name)

    if not _HAS_AXIS:
        # Запасной путь: ось не заводится, ставим второе начертание.
        _FILLED_FAMILY = _load("MaterialSymbolsOutlined-Filled.ttf")


_LOADED: set[str] = set()


def loaded_families() -> set[str]:
    """Что мы загрузили сами. Roboto может стоять и в системе, поэтому общий
    список семейств тут ничего не докажет."""
    return set(_LOADED)


def _load(name: str) -> str:
    path = ASSETS / name
    handle = QFontDatabase.addApplicationFont(str(path))
    if handle == -1:
        logger.error("шрифт не загрузился: %s", path)
        return ""
    families = QFontDatabase.applicationFontFamilies(handle)
    _LOADED.update(families)
    return families[0] if families else ""


def icon_font(size: int, filled: bool = False) -> QFont:
    """Начертание иконки. Размер пиксельный, как во всём макете."""
    if not ICON_FAMILY:
        # Молча не глотаем: без шрифта на месте иконок будут прямоугольники, а
        # метрики поедут вместе с высотами карточек.
        logger.error("иконочный шрифт не загружен")
    family = _FILLED_FAMILY if (filled and _FILLED_FAMILY) else ICON_FAMILY
    made = QFont(family)
    made.setPixelSize(size)
    if _HAS_AXIS:
        made.setVariableAxis(QFont.Tag("FILL"), 1.0 if filled else 0.0)
    return made
```

- [ ] **Шаг 6: Собрать тему в одну дверь**

Создать `client/theme/__init__.py`:

```python
"""Оформление приложения. Единственное место, где есть цвет."""

from PySide6.QtWidgets import QApplication

from client.theme import icons, metrics, palette, typography
from client.theme.icons import GLYPHS, icon_font
from client.theme.qss import load_styles
from client.theme.typography import font

__all__ = [
    "GLYPHS", "apply_theme", "font", "icon_font", "icons", "metrics",
    "palette", "typography",
]


def apply_theme(app: QApplication) -> None:
    """Шрифты с диска и стили на приложение. Зовётся один раз из main."""
    icons.load_fonts()
    app.setFont(font(typography.BODY_M))
    app.setStyleSheet(load_styles())
```

`load_styles` появляется в задаче 5; до неё импорт не разрешится, и это
нормально — задача 5 идёт следом.

- [ ] **Шаг 7: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_icons.py -v`
Ожидается: PASS, пять тестов. Пока `qss.py` нет, тесты не соберутся — этот шаг
выполняется после задачи 5, и порядок в ней указан.

- [ ] **Шаг 8: Коммит**

```bash
git add client/theme/icons.py client/theme/assets scripts/probe_fill_axis.py \
        tests/client/test_icons.py docs/specs/2026-07-27-code-structure.md
git commit -m "feat: иконочный шрифт и правило контур-заливка"
```

---

### Задача 5: Стили с подстановкой токенов

**В QSS переменных нет.** Поэтому файлы пишутся с подстановками вида
`{primary}`, а значения приходят из `client/theme/` при запуске. Цвет объявлен
один раз, а не повторён шестнадцатью шестнадцатеричными значениями по файлам.

**Цвета нет нигде, кроме палитры.** Это и проверяется тестом: любое `#rrggbb`
или `rgba(` в `.qss`, в `qss.py` или в любом виджете — ошибка. Проверять только
файлы стилей мало: мимо них цвет утекает и в `tokens()`, и в строку для
`setStyleSheet`.

**Файлы:**
- Создать: `client/theme/qss.py`, `client/theme/styles/app.qss`
- Создать: `tests/client/test_qss.py`

**Интерфейсы:**
- Потребляет: `palette`, `typography`, `metrics`.
- Отдаёт: `tokens() -> dict[str, str]` и `load_styles() -> str` — все файлы
  из `styles/` в порядке имён, склеенные и с подставленными токенами.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_qss.py`:

```python
import re
from pathlib import Path

import pytest

import client
from client.theme import palette, qss

STYLES = Path(qss.__file__).resolve().parent / "styles"


def test_every_placeholder_has_a_value():
    """Незакрытая подстановка тихо оставляет в стиле фигурные скобки, и Qt
    молча выбрасывает всё правило целиком."""
    names = set()
    for path in STYLES.glob("*.qss"):
        names |= set(re.findall(r"\{([a-z_0-9]+)\}", path.read_text("utf-8")))

    assert names, "подстановок не нашлось вовсе — проверь шаблон поиска"
    assert names <= set(qss.tokens())


def test_no_colour_is_written_in_the_styles():
    """Цвет объявлен один раз, в palette.py. В .qss его быть не должно."""
    for path in STYLES.glob("*.qss"):
        text = path.read_text("utf-8")
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", text), path
        assert "rgba(" not in text, path
        assert "rgb(" not in text, path


def test_no_colour_is_written_anywhere_but_the_palette():
    """Та же проверка, но по всему `client/`, а не только по `.qss`.

    Проверка выше стерегла файлы стилей, а цвет утекал мимо них: полтора
    десятка `rgba(...)` жили прямо в `tokens()`, ещё пара — в виджетах строкой
    для `setStyleSheet`. Одно значение из-за этого уже задвоилось."""
    root = Path(client.__file__).resolve().parent
    palette_file = Path(palette.__file__).resolve()

    for path in root.rglob("*.py"):
        if path.resolve() == palette_file:
            continue
        text = path.read_text("utf-8")
        assert not re.search(r"\brgba?\(\s*\d", text), path
        assert not re.search(r"[\"']#[0-9a-fA-F]{3,8}[\"']", text), path


def test_the_result_has_no_braces_left():
    made = qss.load_styles()

    assert "{" in made, "это всё-таки QSS, скобки правил на месте"
    assert not re.search(r"\{[a-z_0-9]+\}", made)


def test_the_accent_reaches_the_styles():
    assert palette.PRIMARY in qss.load_styles()


def test_an_unknown_token_is_loud():
    """Опечатка в имени подстановки не должна проходить молча."""
    with pytest.raises(KeyError, match="нет_такого"):
        qss.substitute("QWidget { color: {нет_такого} }")


def test_the_braces_of_the_rules_are_left_alone():
    """Скобки тела правила — не подстановка. str.format спотыкался бы о них
    на первом же файле."""
    assert qss.substitute("QWidget { color: {primary} }") == (
        f"QWidget {{ color: {palette.PRIMARY} }}"
    )


def test_files_are_joined_in_the_order_of_their_names():
    """Порядок в QSS решает: правило ниже перебивает правило выше."""
    made = qss.load_styles()
    names = sorted(path.stem for path in STYLES.glob("*.qss"))

    positions = [made.find(f"/* {name} */") for name in names]
    assert positions == sorted(positions)
    assert -1 not in positions, "каждый файл помечен своим заголовком"
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_qss.py -v`
Ожидается: FAIL — `ImportError: cannot import name 'qss'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/theme/qss.py`:

```python
"""Стили с подстановкой токенов.

В QSS переменных нет, поэтому файлы пишутся с {именами}, а значения приходят
отсюда. Цвет объявлен один раз — в palette.py."""

import re
from pathlib import Path

from client.theme import metrics, palette, typography

STYLES = Path(__file__).resolve().parent / "styles"


def tokens() -> dict[str, str]:
    """Всё, на что можно сослаться из .qss."""
    made = {
        "bg": palette.BACKGROUND,
        "primary": palette.PRIMARY,
        "primary_soft": palette.mix(palette.PRIMARY, 14),
        "primary_hover": palette.mix(palette.PRIMARY, 20),
        "error": palette.ERROR,
        "text": palette.TEXT,
        "text_bright": palette.TEXT_BRIGHT,
        "glass": palette.GLASS,
        "glass_error": palette.GLASS_ERROR,
        "glass_primary": palette.GLASS_PRIMARY,
        "surface_pop": palette.SURFACE_POP,
        "pill": palette.PILL,
        "pill_border": palette.PILL_BORDER,
        "pill_hover": palette.PILL_HOVER,
        "muted": palette.MUTED,
        "faint": palette.FAINT,
        "family": typography.FAMILY,
        "r_full": f"{metrics.R_FULL}px",
        "r_card": f"{metrics.R_CARD}px",
        "r_film": f"{metrics.R_FILM}px",
        "pill_h": f"{metrics.PILL_H}px",
        "tool_btn": f"{metrics.TOOL_BTN}px",
    }
    # Шкала оценок: имена собираются циклом, как и в макете.
    for step in range(1, 11):
        made[f"score_{step}"] = palette.score_color(step)
    return made


_TOKEN = re.compile(r"\{(\w+)\}")


def substitute(text: str) -> str:
    """Своя подстановка, а не str.format.

    В QSS фигурные скобки уже заняты телами правил, и format принял бы
    `QWidget {` за начало поля — падает на первом же файле. Опечатка в имени
    поднимает KeyError, а не оставляет скобки в стиле: Qt на такое правило
    молча выбрасывает целиком."""
    values = tokens()

    def swap(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name not in values:
            raise KeyError(name)
        return values[name]

    return _TOKEN.sub(swap, text)


def load_styles() -> str:
    """Все файлы из styles/ в порядке имён. Порядок в QSS решает: правило
    ниже перебивает правило выше."""
    parts = []
    for path in sorted(STYLES.glob("*.qss")):
        parts.append(f"/* {path.stem} */")
        parts.append(substitute(path.read_text("utf-8")))
    return "\n".join(parts)
```

- [ ] **Шаг 4: Первый файл стилей**

Создать `client/theme/styles/app.qss`:

```css
QWidget {
    color: {text};
    font-family: "{family}";
}

QWidget#root {
    background: {bg};
}

/* Капсулы шапки: строка поиска, переключатель, ряд кнопок. */
QFrame#searchPill,
QFrame#segPill,
QFrame#toolsPill {
    background: {pill};
    border: 1px solid {pill_border};
    border-radius: {r_full};
}

QFrame#searchPill:hover {
    background: {pill_hover};
    border-color: {pill_border_hover};
}

QLineEdit#searchInput {
    border: none;
    background: transparent;
    color: {text};
    selection-background-color: {primary_soft};
    selection-color: {text_bright};
}

QToolButton[role="tool"],
QToolButton[role="seg"] {
    border: none;
    border-radius: {r_full};
    background: transparent;
    color: {muted};
}

QToolButton[role="tool"]:hover,
QToolButton[role="seg"]:hover {
    background: {pill_hover};
    color: {bright};
}

QToolButton[role="tool"][on="true"],
QToolButton[role="seg"][on="true"] {
    background: {primary_soft};
    color: {primary};
}

QToolButton[role="seg"][on="true"]:hover {
    background: {primary_hover};
}

/* Карточка ленты. */
QFrame#film {
    background: {pill};
    border: 1px solid {film_border};
    border-radius: {r_film};
}
```

**Ни одного цвета по месту.** Всё, что в макете написано как `rgba(...)`,
приходит подстановкой. Ключи `pill_border_hover`, `film_border` и `bright`
добавляются в `tokens()` рядом с остальными:

```
        "pill_border_hover": palette.PILL_BORDER_HOVER,
        "film_border": palette.FILM_BORDER,
        "bright": palette.BRIGHT,
```

а в `app.qss` вместо литералов стоят `{pill_border_hover}`, `{film_border}` и
`{bright}`. Тест `test_no_colour_is_written_in_the_styles` это и стережёт.

**Все значения — ссылками на палитру, ни одного литерала в `qss.py`.** Модуль
объявляет в докстроке, что цвет живёт только в `palette.py`, и держать в нём
полтора десятка `rgba(...)` значит завести вторую карту цветов рядом с первой.
Сторож этого не видел: он смотрит `*.qss` и `vars(palette)`, а `qss.py` — ни то
ни другое, из-за чего одно значение уже успело задвоиться.

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client -v`
Ожидается: PASS — палитра, типографика, иконки и стили. Здесь же становится
рабочим `apply_theme` из задачи 4.

- [ ] **Шаг 6: Коммит**

```bash
git add client/theme/qss.py client/theme/styles client/theme/__init__.py \
        tests/client/test_qss.py
git commit -m "feat: стили с подстановкой токенов, без цвета в самих файлах"
```

---

### Задача 6: `runtime.py` — одна дверь между потоками

**Бэкенд живёт в отдельном потоке со своим циклом asyncio.** Интерфейс остаётся
в главном потоке с циклом Qt. Между ними одна дверь: страница отдаёт задачу и
получает результат сигналом Qt, уже в главном потоке.

**Бэкенд собирается внутри потока.** Асинхронный движок SQLAlchemy привязан к
циклу, в котором создан, и передавать готовый `Backend` через границу нельзя.
Поэтому наружу он не выставляется вовсе: задача — это функция, которой его
передают.

**Задачи заводятся в одном месте.** Объект, владеющий циклом, ведёт список
живых и при закрытии отменяет все разом. Флагов «мы закрываемся» по коду не
разбрасываем.

**Отдельного сигнала об отказе источника нет.** Отказ приезжает полем в
результате. Сигнал `failed` — про другое: непредвиденный сбой, ошибка в нашем
коде. Он идёт в плашку и в лог.

**Файлы:**
- Создать: `client/runtime.py`
- Создать: `tests/client/test_runtime.py`

**Интерфейсы:**
- Потребляет: `build_backend`, `Config` из `backend`.
- Отдаёт: `Call(QObject)` с сигналами `done(object)` и `failed(object)` и
  методом `cancel()`;
  `Calls` — набор задач страницы с методом `cancel_all()`;
  `Runtime(QObject)` с `start()`, `call(work) -> Call`, `close()` и сигналами
  `ready()` и `broken(object)`. `work` — функция от `Backend`, возвращающая
  корутину. `start()` возвращается сразу, готовность приезжает сигналом.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_runtime.py`:

```python
import asyncio
import threading
import time

import pytest

from client.runtime import Calls, Runtime


class FakeBackend:
    def __init__(self):
        self.closed = False
        self.seen = []
        self.finished = []
        self.gate = None

    async def echo(self, value):
        self.seen.append(value)
        return value

    async def slow(self, value):
        """Считается заметное время. Нужна там, где отмена должна попасть в
        окно между вычислением и доставкой: у мгновенной задачи такого окна
        нет вовсе."""
        await asyncio.sleep(0.05)
        self.seen.append(value)
        return value

    async def boom(self):
        raise RuntimeError("сломалось")

    async def quick(self):
        """Успевает доехать за время, которое тест готов ждать. Отменённая
        задача обязана этого не сделать — на sleep(30) отмену не проверить:
        такой тест зелёный и с пустым cancel()."""
        await asyncio.sleep(0.05)
        self.finished.append(1)
        return "приехало"

    async def where(self):
        return threading.current_thread()

    async def together(self):
        """Пять таких доходят только если считаются разом: каждая ждёт, пока
        соберутся все. При очереди набор зависнет."""
        if self.gate is None:
            self.gate = asyncio.Event()
        self.seen.append(len(self.seen))
        if len(self.seen) == 5:
            self.gate.set()
        await asyncio.wait_for(self.gate.wait(), timeout=3)
        return len(self.seen)

    async def aclose(self):
        self.closed = True


@pytest.fixture
def runtime(qtbot):
    made = []

    async def build():
        backend = FakeBackend()
        made.append(backend)
        return backend

    runtime = Runtime(build)
    with qtbot.waitSignal(runtime.ready, timeout=5000):
        runtime.start()

    yield runtime, made[0]

    runtime.close()


def test_starting_does_not_block_the_main_thread(qtbot):
    """Пока строится бэкенд, открываются два файла базы. Ждать этого в
    главном потоке — ровно то, от чего окно замирает."""
    async def slow_build():
        await asyncio.sleep(0.3)
        return FakeBackend()

    service = Runtime(slow_build)
    started = time.monotonic()
    service.start()
    took = time.monotonic() - started

    assert took < 0.1
    with qtbot.waitSignal(service.ready, timeout=5000):
        pass
    service.close()


def test_a_failed_build_is_reported(qtbot):
    """Иначе окно выглядит живым и не отвечает."""
    async def broken_build():
        raise OSError("нет прав на папку данных")

    service = Runtime(broken_build)

    with qtbot.waitSignal(service.broken, timeout=5000) as blocker:
        service.start()

    assert isinstance(blocker.args[0], OSError)
    service.close()


def test_a_result_arrives_in_the_main_thread(qtbot, runtime):
    """Ради этого runtime и существует: результат приезжает туда, где живут
    виджеты."""
    service, _ = runtime
    seen = {}

    call = service.call(lambda backend: backend.echo(42))
    call.done.connect(lambda value: seen.update(
        value=value, thread=threading.current_thread()
    ))

    qtbot.waitUntil(lambda: "value" in seen, timeout=5000)

    assert seen["value"] == 42
    assert seen["thread"] is threading.main_thread()


def test_the_work_itself_runs_in_the_other_thread(qtbot, runtime):
    """Проверяем поведение, а не отсутствие атрибута: движок SQLAlchemy
    обязан крутиться в том потоке, в котором создан."""
    service, _ = runtime
    seen = []

    call = service.call(lambda backend: backend.where())
    call.done.connect(seen.append)

    qtbot.waitUntil(lambda: bool(seen), timeout=5000)

    assert seen[0] is not threading.main_thread()


def test_a_broken_task_reports_and_does_not_kill_the_thread(qtbot, runtime,
                                                            caplog):
    """Молча не глотаем ничего: сбой идёт и в сигнал, и в лог."""
    service, _ = runtime
    broke, heard = [], []

    with caplog.at_level("ERROR"):
        call = service.call(lambda backend: backend.boom())
        call.failed.connect(broke.append)
        qtbot.waitUntil(lambda: bool(broke), timeout=5000)

    assert isinstance(broke[0], RuntimeError)
    assert "сломалось" in caplog.text

    # Поток жив: следующая задача проходит.
    again = service.call(lambda backend: backend.echo("живой"))
    again.done.connect(heard.append)
    qtbot.waitUntil(lambda: bool(heard), timeout=5000)
    assert heard == ["живой"]


def test_a_cancelled_call_stays_silent(qtbot, runtime):
    """Ушли со страницы — её задачи оборваны, а не досчитываются в пустоту.

    Задача нарочно быстрая: на sleep(30) этот тест был бы зелёным и с пустым
    cancel(), потому что за отведённое время всё равно ничего не приезжает."""
    service, backend = runtime
    heard = []

    call = service.call(lambda backend: backend.quick())
    call.done.connect(heard.append)
    call.cancel()

    qtbot.wait(300)

    assert heard == []
    assert backend.finished == [], "задача должна быть оборвана, а не доиграна"


def test_a_late_answer_of_a_cancelled_call_is_dropped(qtbot, runtime):
    """Отмена приходит, когда ответ уже посчитан, но ещё не доставлен.
    blockSignals в этот момент бесполезен — проверено прогоном: значение
    доезжает. Спасает только флаг, читаемый в момент доставки.

    Ждём `time.sleep`, а не `qtbot.wait`: второй крутит цикл Qt, а значит сам
    же и разбирает очередь доставки — сигнал уходит до отмены, и проверяемое
    поведение становится недостижимым. Задача считается в чужом потоке, цикл
    Qt ей не нужен."""
    service, _ = runtime
    heard = []

    call = service.call(lambda backend: backend.slow("поздно"))
    call.done.connect(heard.append)
    time.sleep(0.12)         # задача посчиталась, доставка ещё впереди
    call.cancel()

    qtbot.wait(200)

    assert heard == []


def test_a_page_cancels_everything_it_started(qtbot, runtime):
    service, backend = runtime
    tasks = Calls()
    heard = []

    for _ in range(3):
        call = service.call(lambda backend: backend.quick())
        call.done.connect(heard.append)
        tasks.add(call)

    tasks.cancel_all()

    qtbot.wait(300)
    assert heard == []
    assert backend.finished == []


def test_several_tasks_run_at_once(qtbot, runtime):
    """Стережём, что задачи не выстроились в очередь: каждая ждёт, пока
    соберутся все пять. При последовательном исполнении набор зависнет."""
    service, backend = runtime
    heard, kept = [], []

    for _ in range(5):
        call = service.call(lambda backend: backend.together())
        call.done.connect(heard.append)
        kept.append(call)      # без ссылки Call соберёт сборщик мусора

    qtbot.waitUntil(lambda: len(heard) == 5, timeout=5000)

    assert sorted(backend.seen) == [0, 1, 2, 3, 4]


def test_a_call_survives_without_a_reference_from_the_caller(qtbot, runtime):
    """Владеет вызовом рантайм. Без родителя сборщик мусора уносил бы Call
    вместе с результатом — проверено прогоном."""
    service, _ = runtime
    import gc

    heard = []
    service.call(lambda backend: backend.echo("жив")).done.connect(heard.append)
    gc.collect()

    qtbot.waitUntil(lambda: bool(heard), timeout=5000)

    assert heard == ["жив"]


def test_closing_cancels_the_hanging_and_shuts_the_backend(qtbot, runtime):
    service, backend = runtime
    call = service.call(lambda backend: backend.quick())
    qtbot.wait(10)

    started = time.monotonic()
    service.close()
    took = time.monotonic() - started

    assert backend.closed is True
    assert took < 2, "close не должен ждать висящую задачу десять секунд"
    # Оборвана, а не доиграна. Без этой строки тест зелен и у закрытия, которое
    # честно дожидается всех задач: `quick` укладывается в порог, а
    # `_future.done()` после ожидания истинно.
    assert backend.finished == [], "задача должна быть оборвана, а не доиграна"
    assert call._future is not None and call._future.cancelled()


def test_closing_while_the_backend_is_still_building_does_not_hang(qtbot):
    """Окно можно закрыть, пока идут миграции первого запуска. `_quit`
    создаётся только после сборки, и без флага будить было бы некого: главный
    поток занят на весь таймаут, а поток бэкенда остаётся жить."""
    async def slow_build():
        await asyncio.sleep(0.4)
        return FakeBackend()

    service = Runtime(slow_build)
    service.start()
    qtbot.wait(50)

    started = time.monotonic()
    service.close()
    took = time.monotonic() - started

    assert took < 2
    assert not service._worker.isRunning()


def test_a_call_after_closing_is_quiet(qtbot, runtime, caplog):
    """Живой сценарий: closeEvent погасил рантайм, а отложенный таймер
    страницы дёрнул call()."""
    service, _ = runtime
    service.close()

    with caplog.at_level("ERROR"):
        call = service.call(lambda backend: backend.echo(1))
        qtbot.wait(50)

    assert call._future is None
    assert "закрытия" in caplog.text


def test_closing_twice_is_quiet(qtbot, runtime):
    service, _ = runtime

    service.close()
    service.close()

    assert not service._worker.isRunning()
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_runtime.py -v`
Ожидается: FAIL — `No module named 'client.runtime'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/runtime.py`:

```python
"""Стык asyncio с циклом Qt.

Одна дверь между слоями: страница отдаёт задачу и получает результат сигналом
Qt, уже в главном потоке. Общих изменяемых данных у потоков нет, блокировок в
коде нет — их роль играет очередь сообщений Qt, которая для этого и сделана."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal

logger = logging.getLogger(__name__)

Work = Callable[[Any], Coroutine[Any, Any, Any]]


class Call(QObject):
    """Одна задача. Создаётся в главном потоке, сигнал испускает из потока
    бэкенда — единственный объект Qt, живущий в двух потоках. Так и задумано:
    доставка идёт очередью и оказывается в главном потоке.

    Наружу торчат `done` и `failed`; внутренние `_arrived` и `_broke` нужны,
    чтобы отменённый результат отсеивался в момент доставки, а не отправки."""

    done = Signal(object)
    failed = Signal(object)

    _arrived = Signal(object)
    _broke = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._future = None
        self._cancelled = False
        self._arrived.connect(self._deliver)
        self._broke.connect(self._deliver_failure)

    def cancel(self) -> None:
        """Обрываем задачу и помечаем её ненужной.

        `blockSignals` тут не помогает: событие, положенное в очередь при
        emit, доставляется как ни в чём не бывало — проверено прогоном.
        Поэтому флаг читается в момент доставки."""
        self._cancelled = True
        if self._future is not None:
            self._future.cancel()

    def _deliver(self, result) -> None:
        if not self._cancelled:
            self.done.emit(result)

    def _deliver_failure(self, error) -> None:
        if not self._cancelled:
            self.failed.emit(error)


class Calls:
    """Что запустила страница, она же и обрывает при уходе. Отдельного флага
    «мы закрываемся» по коду не разбрасываем."""

    def __init__(self) -> None:
        self._calls: list[Call] = []

    def add(self, call: Call) -> Call:
        self._calls.append(call)
        return call

    def cancel_all(self) -> None:
        for call in self._calls:
            call.cancel()
        self._calls.clear()


class _Worker(QThread):
    def __init__(self, runtime: "Runtime") -> None:
        super().__init__()
        self._runtime = runtime

    def run(self) -> None:
        asyncio.run(self._runtime._serve())


class Runtime(QObject):
    """Владеет потоком, циклом и бэкендом. Наружу бэкенд не выставляется:
    асинхронный движок SQLAlchemy привязан к своему циклу."""

    ready = Signal()
    broken = Signal(object)

    def __init__(self, build, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._build = build
        self._loop: asyncio.AbstractEventLoop | None = None
        self._backend = None
        self._quit = None
        self._closed = False
        self._worker = _Worker(self)

    def start(self) -> None:
        """Возвращается сразу. Готовность приезжает сигналом `ready`.

        Ждать её в главном потоке нельзя: пока строится бэкенд, открываются
        два файла базы и гоняются миграции, а это ровно то обращение к диску
        из главного потока, от которого окно и замирает."""
        self._worker.start()

    def call(self, work: Work) -> Call:
        """`work` получает бэкенд и возвращает корутину. Сам бэкенд через
        границу не ходит.

        Владеет вызовом рантайм: без родителя `Call` уносит сборщик мусора
        вместе с результатом, если страница не сохранила ссылку."""
        call = Call(self)
        if self._loop is None or self._closed:
            logger.error("задача до готовности рантайма или после закрытия")
            return call

        async def run() -> None:
            try:
                result = await work(self._backend)
            except Exception as error:
                # Непредвиденный сбой: и в плашку, и в лог. Отказ источника
                # сюда не попадает — он приезжает полем в результате.
                # CancelledError сюда не заходит: она от BaseException.
                logger.exception("сбой в задаче бэкенда")
                call._broke.emit(error)
            else:
                call._arrived.emit(result)

        def launch() -> None:
            # Запуск откладывается на следующий круг главного цикла: иначе
            # быстрая задача успевает испустить сигнал раньше, чем позвавший
            # к нему подключился, и результат теряется молча. Проверено
            # прогоном: без отсрочки терялось восемь ответов из двадцати.
            if call._cancelled or self._closed or self._loop is None:
                return
            call._future = asyncio.run_coroutine_threadsafe(run(), self._loop)

        QTimer.singleShot(0, launch)
        return call

    def close(self) -> None:
        if self._closed:
            return
        # Флаг ставится раньше всего и читается в `_serve` сразу после сборки.
        # Окно можно закрыть, пока идут миграции первого запуска, а `_quit`
        # создаётся только после них: без флага будить было бы некого, поток
        # ушёл бы в вечное ожидание, а `wait` внизу занял бы главный поток на
        # все десять секунд и вернулся ни с чем — с живым потоком.
        self._closed = True
        if self._loop is not None and self._quit is not None:
            self._loop.call_soon_threadsafe(self._quit.set_result, None)
        self._worker.wait(10_000)

    async def _serve(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            self._backend = await self._build()
        except Exception as error:
            # Нет прав на папку данных, битый файл базы. Окно должно узнать,
            # а не выглядеть живым и не отвечать.
            logger.exception("бэкенд не собрался")
            self.broken.emit(error)
            return

        if self._closed:
            # Закрылись, пока собирались. Ждать нечего и некого.
            await self._backend.aclose()
            return

        self._quit = loop.create_future()
        self._loop = loop
        # Перечитываем флаг. Между проверкой выше и этой строкой остаётся
        # зазор, и попавший в него `close()` не нашёл бы ни `_loop`, ни
        # `_quit`, кого будить: главный поток простоял бы весь таймаут и
        # вернулся с живым потоком. `close()` ставит `_closed` раньше, чем
        # читает `_loop`, поэтому перечтение зазор и закрывает.
        if self._closed:
            self._quit.set_result(None)
        self.ready.emit()

        try:
            await self._quit
        finally:
            # Одно место, где отменяется всё разом.
            live = [task for task in asyncio.all_tasks(loop)
                    if task is not asyncio.current_task()]
            for task in live:
                task.cancel()
            if live:
                await asyncio.gather(*live, return_exceptions=True)
            await self._backend.aclose()
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_runtime.py -v`
Ожидается: PASS, четырнадцать тестов.

Прогнать трижды подряд: гонки видно только на повторе.

- [ ] **Шаг 5: Коммит**

```bash
git add client/runtime.py tests/client/test_runtime.py
git commit -m "feat: стык asyncio с циклом Qt одной дверью"
```

---

### Задача 7: Окно и неоновая кромка

Корень приложения: тёмный фон с тихим свечением сверху и светящаяся нить по
верхней кромке содержимого.

**Рамка окна системная.** Заголовок, кнопки, перетаскивание, растягивание,
прилипание к краям и `Win+←` — всё даром от Windows. Неоновая кромка идёт по
верху содержимого, под заголовком.

**Гало рисуется градиентом, а не размытием.** В макете это `filter: blur(12px)`
поверх полосы; `QGraphicsBlurEffect` на каждый кадр стоит дорого и на 4K
заметен. Вертикальный градиент от кромки вниз даёт ту же картинку дешевле.
Решение помечено в «правилах, взятых не из спек» — если глазами разница видна,
меняется здесь одним классом.

**Файлы:**
- Создать: `client/widgets/neon.py`
- Создать: `client/window.py`
- Создать: `tests/client/test_window.py`

**Интерфейсы:**
- Потребляет: `palette`, `metrics`.
- Отдаёт: `NeonEdge(QWidget)` — накладка на всю ширину, рисует нить и гало,
  мышь сквозь неё проходит;
  `MainWindow(QWidget)` с полем `root`, минимальным размером и наложенной
  кромкой; `MainWindow.closeEvent` гасит рантайм.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_window.py`:

```python
from PySide6.QtCore import Qt

from client.theme import metrics
from client.widgets.neon import NeonEdge
from client.window import MainWindow


def test_the_window_does_not_shrink_below_the_floor(qtbot, theme):
    """Проверяем поведением, а не сверкой константы с её же копией."""
    window = MainWindow(runtime=None)
    qtbot.addWidget(window)

    window.resize(100, 100)

    assert (window.width(), window.height()) == (metrics.MIN_W, metrics.MIN_H)


def test_the_edge_lets_the_mouse_through(qtbot, theme):
    """Накладка лежит поверх содержимого: если она ловит мышь, верхний ряд
    кнопок перестанет нажиматься."""
    edge = NeonEdge()
    qtbot.addWidget(edge)


    assert edge.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def test_the_edge_spans_the_whole_width(qtbot, theme):
    window = MainWindow(runtime=None)
    qtbot.addWidget(window)
    window.resize(900, 600)
    window.show()
    qtbot.waitExposed(window)

    assert window.edge.width() == window.width()
    assert window.edge.y() == 0


def test_the_edge_stays_on_top_after_a_resize(qtbot, theme):
    """Дети, добавленные позже, легли бы поверх накладки и закрыли нить.
    Ровно это и делает задача 15, добавляя стопку страниц."""
    from PySide6.QtWidgets import QWidget

    window = MainWindow(runtime=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    late = QWidget(window)          # ребёнок, появившийся после накладки
    late.show()

    window.resize(1200, 700)
    qtbot.wait(50)

    assert window.edge.width() == window.width()
    assert window.children()[-1] is window.edge


def test_closing_shuts_the_runtime(qtbot, theme):
    class FakeRuntime:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    runtime = FakeRuntime()
    window = MainWindow(runtime=runtime)
    qtbot.addWidget(window)

    window.close()

    assert runtime.closed is True
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_window.py -v`
Ожидается: FAIL — `No module named 'client.widgets.neon'`.

- [ ] **Шаг 3: Кромка**

Создать `client/widgets/neon.py`:

```python
"""Неоновая кромка. Нить в один пиксель и гало под ней.

Гало — вертикальный градиент, а не размытие: QGraphicsBlurEffect на каждый
кадр стоит дорого, а картинка получается та же."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from client.theme import palette

# Нить гаснет к краям: в макете сплошной цвет держится с 22% до 78% ширины.
_FADE_LEFT = 0.22
_FADE_RIGHT = 0.78

THREAD_H = 1
HALO_H = 16


class NeonEdge(QWidget):
    """Накладка поверх содержимого. Мышь сквозь неё проходит: иначе верхний
    ряд кнопок перестал бы нажиматься."""

    def __init__(self, color: str = palette.PRIMARY,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = palette.qcolor(color)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedHeight(THREAD_H + HALO_H)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()

        halo = QLinearGradient(0, 0, 0, THREAD_H + HALO_H)
        bright = QColor(self._color)
        bright.setAlphaF(0.38)
        halo.setColorAt(0.0, bright)
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, width, THREAD_H + HALO_H, halo)

        thread = QLinearGradient(0, 0, width, 0)
        thread.setColorAt(0.0, QColor(0, 0, 0, 0))
        thread.setColorAt(_FADE_LEFT, self._color)
        thread.setColorAt(_FADE_RIGHT, self._color)
        thread.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, width, THREAD_H, thread)
```

- [ ] **Шаг 4: Окно**

Создать `client/window.py`:

```python
"""Окно приложения. Рамка системная: перетаскивание, размер и прилипание к
краям даёт Windows, и переписывать это руками незачем."""

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QVBoxLayout, QWidget

from client.theme import metrics, palette
from client.widgets.neon import NeonEdge


class MainWindow(QWidget):
    def __init__(self, runtime, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runtime = runtime

        self.setObjectName("window")
        self.setWindowTitle("Personal Rating")
        self.setMinimumSize(metrics.MIN_W, metrics.MIN_H)

        self.root = QWidget(self)
        self.root.setObjectName("root")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.root)

        # Накладка не в раскладке: она лежит поверх содержимого и места не
        # занимает.
        self.edge = NeonEdge(palette.PRIMARY, self)
        self.edge.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.edge.setGeometry(0, 0, self.width(), self.edge.height())
        # Дети, добавленные позже, легли бы поверх и закрыли нить.
        self.edge.raise_()

    def paintEvent(self, event) -> None:
        """Тихое свечение от верхней кромки — стеклу есть что преломлять."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), palette.qcolor(palette.BACKGROUND))

        centre = QPoint(self.width() // 2, int(self.height() * 0.05))
        glow = QRadialGradient(centre, self.width() * 0.55)
        tint = palette.qcolor(palette.PRIMARY)
        tint.setAlphaF(0.03)
        glow.setColorAt(0.0, tint)
        glow.setColorAt(0.45, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow)

    def closeEvent(self, event) -> None:
        if self._runtime is not None:
            self._runtime.close()
        super().closeEvent(event)
```

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_window.py -v`
Ожидается: PASS, пять тестов. Файлы шрифтов к этому моменту уже лежат — без
них фикстура `theme` поднимется, но метрики поедут.

- [ ] **Шаг 6: Коммит**

```bash
git add client/widgets/neon.py client/window.py tests/client/test_window.py
git commit -m "feat: окно с системной рамкой и неоновой кромкой"
```

---

### Задача 8: Строка поиска

**Одна строка, срабатывает по Enter или по нажатию на лупу — не на каждую
букву.** Кнопка очистки появляется, только когда есть что очищать: своя, а не
системная — та рисуется цветом операционной системы.

**Файлы:**
- Создать: `client/widgets/search.py`
- Создать: `tests/client/test_search_field.py`

**Интерфейсы:**
- Потребляет: `metrics`, `icons`.
- Отдаёт: `SearchField(QFrame)` с сигналом `submitted(str)`, методами
  `text()`, `clear()` и полем `input` — для тестов и для фокуса при запуске.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_search_field.py`:

```python
from PySide6.QtCore import Qt

from client.widgets.search import SearchField


# qtbot.keyClicks гонит символы через ASCII-таблицу Qt и на кириллице роняет
# ПРОЦЕСС ЦЕЛИКОМ: ASSERT в qasciikey.cpp, код выхода 0xC0000409, прогон
# обрывается без сводки. Проверено запуском. Поэтому русский текст ставим
# setText — он тоже поднимает textChanged и тоже не поднимает returnPressed, —
# а настоящий набор клавишами проверяем латиницей.


def test_typing_alone_does_not_search(qtbot, theme):
    """Срабатывает по Enter или по лупе — не на каждую букву. Иначе каждая
    буква стоила бы запроса к TMDB."""
    field = SearchField()
    qtbot.addWidget(field)
    heard = []
    field.submitted.connect(heard.append)

    qtbot.keyClicks(field.input, "interstellar")

    assert heard == []
    assert field.input.text() == "interstellar", "набор клавишами доходит"


def test_enter_searches(qtbot, theme):
    field = SearchField()
    qtbot.addWidget(field)
    heard = []
    field.submitted.connect(heard.append)

    field.input.setText("интерстеллар")
    qtbot.keyClick(field.input, Qt.Key.Key_Return)

    assert heard == ["интерстеллар"]


def test_the_magnifier_searches_too(qtbot, theme):
    field = SearchField()
    qtbot.addWidget(field)
    heard = []
    field.submitted.connect(heard.append)

    field.input.setText("андор")
    qtbot.mouseClick(field.magnifier, Qt.MouseButton.LeftButton)

    assert heard == ["андор"]


def test_the_query_is_trimmed(qtbot, theme):
    field = SearchField()
    qtbot.addWidget(field)
    heard = []
    field.submitted.connect(heard.append)

    field.input.setText("  андор  ")
    qtbot.keyClick(field.input, Qt.Key.Key_Return)

    assert heard == ["андор"]


def test_the_clear_button_appears_only_when_there_is_something_to_clear(
    qtbot, theme
):
    """Спрятанная кнопка — ловушка; пустая кнопка — мусор."""
    field = SearchField()
    qtbot.addWidget(field)
    field.show()
    qtbot.waitExposed(field)

    assert field.clear_button.isHidden()

    field.input.setText("а")
    assert not field.clear_button.isHidden()

    qtbot.mouseClick(field.clear_button, Qt.MouseButton.LeftButton)
    assert field.input.text() == ""
    assert field.clear_button.isHidden()


def test_clearing_returns_the_focus_to_the_input(qtbot, theme):
    """Иначе после очистки надо снова целиться мышью в поле.

    Смотрим focusWidget окна, а не hasFocus: последний истинен только когда
    окно активно, и тест краснел бы от того, что во время прогона фокус ушёл
    в чужое окно."""
    field = SearchField()
    qtbot.addWidget(field)
    field.show()
    qtbot.waitExposed(field)

    field.input.setText("а")
    qtbot.mouseClick(field.clear_button, Qt.MouseButton.LeftButton)

    assert field.focusWidget() is field.input


def test_an_empty_query_is_not_submitted(qtbot, theme):
    """До первого запроса лента пуста, и пустой Enter её не наполняет."""
    field = SearchField()
    qtbot.addWidget(field)
    heard = []
    field.submitted.connect(heard.append)

    qtbot.keyClick(field.input, Qt.Key.Key_Return)
    field.input.setText("   ")
    qtbot.keyClick(field.input, Qt.Key.Key_Return)

    assert heard == []
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_search_field.py -v`
Ожидается: FAIL — `No module named 'client.widgets.search'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/search.py`:

```python
"""Строка поиска. Одна на всё приложение."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QToolButton

from client.theme import GLYPHS, icon_font, metrics


class SearchField(QFrame):
    """Срабатывает по Enter или по нажатию на лупу — не на каждую букву:
    каждая буква стоила бы запроса к внешней базе."""

    submitted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("searchPill")
        self.setFixedHeight(metrics.PILL_H)

        self.magnifier = QToolButton(self)
        self.magnifier.setObjectName("searchIcon")
        self.magnifier.setFont(icon_font(20))
        self.magnifier.setText(GLYPHS["search"])
        self.magnifier.setCursor(Qt.CursorShape.PointingHandCursor)

        self.input = QLineEdit(self)
        self.input.setObjectName("searchInput")
        self.input.setPlaceholderText("Поиск")
        self.input.setFrame(False)

        self.clear_button = QToolButton(self)
        self.clear_button.setObjectName("searchClear")
        self.clear_button.setFont(icon_font(18))
        self.clear_button.setText(GLYPHS["clear"])
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 10, 0)
        layout.setSpacing(10)
        layout.addWidget(self.magnifier)
        layout.addWidget(self.input, 1)
        layout.addWidget(self.clear_button)

        self.input.textChanged.connect(self._sync_clear)
        self.input.returnPressed.connect(self._submit)
        self.magnifier.clicked.connect(self._submit)
        self.clear_button.clicked.connect(self._clear)

    def text(self) -> str:
        return self.input.text().strip()

    def clear(self) -> None:
        self.input.clear()

    def _sync_clear(self, text: str) -> None:
        self.clear_button.setVisible(bool(text))

    def _submit(self) -> None:
        query = self.text()
        if query:
            self.submitted.emit(query)

    def _clear(self) -> None:
        self.input.clear()
        # Иначе после очистки надо снова целиться мышью в поле.
        self.input.setFocus()
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_search_field.py -v`
Ожидается: PASS, семь тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/search.py tests/client/test_search_field.py
git commit -m "feat: строка поиска по Enter и по лупе"
```

---

### Задача 9: Переключатель типа содержимого

Три кнопки в капсуле: фильмы, сериалы, игры. Взаимоисключающие, активна ровно
одна. **Тип содержимого переключается отдельно и не зависит от раздела.**

**Смена типа сбрасывает все фильтры.** Наборы тегов у трёх типов независимы, и
фильтр по тегу после переключения указывал бы на строки, которых в новом наборе
нет вовсе. Сам сброс делает окно; переключатель только сообщает о смене.

**Файлы:**
- Создать: `client/widgets/segmented.py`
- Создать: `tests/client/test_segmented.py`

**Интерфейсы:**
- Потребляет: `Kind` из `backend.model`; `metrics`, `icons`, `typography`.
- Отдаёт: `KindSwitch(QFrame)` с сигналом `changed(object)` (в нём `Kind`),
  свойством `kind` и методом `buttons()` — для замера ширины в шапке.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_segmented.py`:

```python
from PySide6.QtCore import Qt

from backend.model import Kind
from client.widgets.segmented import KindSwitch


def test_films_are_shown_first(qtbot, theme):
    """Приложение открывается на фильмах."""
    switch = KindSwitch()
    qtbot.addWidget(switch)

    assert switch.kind is Kind.MOVIE


def test_exactly_one_is_active(qtbot, theme):
    switch = KindSwitch()
    qtbot.addWidget(switch)

    for kind in (Kind.SERIES, Kind.GAME, Kind.MOVIE):
        switch.set_kind(kind)
        on = [b for b in switch.buttons() if b.property("on") == "true"]
        assert len(on) == 1, kind


def test_a_click_changes_the_kind(qtbot, theme):
    switch = KindSwitch()
    qtbot.addWidget(switch)
    heard = []
    switch.changed.connect(heard.append)

    qtbot.mouseClick(switch.button(Kind.GAME), Qt.MouseButton.LeftButton)

    assert switch.kind is Kind.GAME
    assert heard == [Kind.GAME]


def test_clicking_the_active_one_changes_nothing(qtbot, theme):
    """Иначе фильтры сбрасывались бы от промаха мимо соседней кнопки."""
    switch = KindSwitch()
    qtbot.addWidget(switch)
    heard = []
    switch.changed.connect(heard.append)

    qtbot.mouseClick(switch.button(Kind.MOVIE), Qt.MouseButton.LeftButton)

    assert heard == []


def test_setting_the_kind_from_outside_is_silent(qtbot, theme):
    """Восстановление состояния не должно выглядеть как нажатие человека."""
    switch = KindSwitch()
    qtbot.addWidget(switch)
    heard = []
    switch.changed.connect(heard.append)

    switch.set_kind(Kind.SERIES)

    assert switch.kind is Kind.SERIES
    assert heard == []


def test_every_kind_has_its_own_button(qtbot, theme):
    switch = KindSwitch()
    qtbot.addWidget(switch)

    assert len(switch.buttons()) == 3
    assert {b.text() for b in switch.buttons()} == {"Фильмы", "Сериалы", "Игры"}
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_segmented.py -v`
Ожидается: FAIL — `No module named 'client.widgets.segmented'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/segmented.py`:

```python
"""Переключатель типа содержимого. Тип не зависит от раздела и живёт своей
жизнью: раздел показывает срез, тип решает, чей это срез."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton

from backend.model import Kind
from client.theme import GLYPHS, font, icon_font, metrics, palette, typography

_KINDS = (
    (Kind.MOVIE, "Фильмы", GLYPHS["movies"]),
    (Kind.SERIES, "Сериалы", GLYPHS["series"]),
    (Kind.GAME, "Игры", GLYPHS["games"]),
)


def glyph_icon(glyph: str, color: str, filled: bool = False,
               size: int = 19) -> QIcon:
    """Глиф иконочного шрифта в QIcon.

    У кнопки шрифт один, а нам нужны два: иконочный для глифа и текстовый для
    подписи. QSS красит текст, но не готовый растр, поэтому цвет приходит
    аргументом и картинка перерисовывается при смене состояния."""
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setFont(icon_font(size, filled=filled))
    painter.setPen(palette.qcolor(color))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
    painter.end()

    return QIcon(pixmap)


class KindSwitch(QFrame):
    changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("segPill")
        self.setFixedHeight(metrics.PILL_H)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(metrics.PILL_PAD, metrics.PILL_PAD,
                                  metrics.PILL_PAD, metrics.PILL_PAD)
        layout.setSpacing(2)

        self._glyphs: dict[Kind, str] = {}
        self._buttons: dict[Kind, QToolButton] = {}
        for kind, label, glyph in _KINDS:
            button = QToolButton(self)
            button.setProperty("role", "seg")
            button.setText(label)
            button.setFont(font(typography.TITLE_S))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            button.clicked.connect(lambda _=False, k=kind: self._pick(k))
            layout.addWidget(button, 1)
            self._buttons[kind] = button
            self._glyphs[kind] = glyph

        self._kind = Kind.MOVIE
        self._paint()

    @property
    def kind(self) -> Kind:
        return self._kind

    def button(self, kind: Kind) -> QToolButton:
        return self._buttons[kind]

    def buttons(self) -> list[QToolButton]:
        return list(self._buttons.values())

    def set_kind(self, kind: Kind) -> None:
        """Тихо: восстановление состояния не должно выглядеть как нажатие."""
        self._kind = kind
        self._paint()

    def _pick(self, kind: Kind) -> None:
        if kind is self._kind:
            # Промах мимо соседней кнопки не должен сбрасывать фильтры.
            return
        self.set_kind(kind)
        self.changed.emit(kind)

    def _paint(self) -> None:
        for kind, button in self._buttons.items():
            on = kind is self._kind
            button.setProperty("on", "true" if on else "false")
            # Иконка перерисовывается вместе с состоянием: QSS красит текст,
            # но не готовый растр, а включённая кнопка акцентна целиком.
            # Здесь же и правило «контур в покое, заливка во включённом».
            button.setIcon(glyph_icon(
                self._glyphs[kind],
                color=palette.PRIMARY if on else palette.TEXT,
                filled=on,
            ))
            button.style().unpolish(button)
            button.style().polish(button)
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_segmented.py -v`
Ожидается: PASS, шесть тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/segmented.py tests/client/test_segmented.py
git commit -m "feat: переключатель типа содержимого"
```

---

### Задача 10: Ряд кнопок — четыре поведения

Восемь круглых кнопок в одной капсуле, и ведут они себя по-разному:

| Роль | Поведение |
|---|---|
| `view` | взаимоисключающие; повторное нажатие возвращает обычный список |
| `filter` | независимые; горят пока фильтр задан, повторное нажатие сбрасывает |
| `collapse` | переключатель с двумя иконками, подсветки нет |
| `sort` | перебор восьми состояний по кругу, подсветки нет |

**Сортировка и сворачивание состояние показывают иконкой, а не подсветкой.**
У сортировки критерий крупной иконкой, направление — стрелкой в углу.

**Восемь состояний сортировки:** четыре критерия в две стороны. Дата
добавления в переборе не участвует — это порядок по умолчанию в «Хочу
посмотреть».

**Файлы:**
- Создать: `client/widgets/toolbar.py`
- Создать: `tests/client/test_toolbar.py`

**Интерфейсы:**
- Потребляет: `Order`, `Sort`, `Kind` из `backend.model`; `icons`, `metrics`.
- Отдаёт: `View` (`RATED`, `WISHLIST`, `STATS`) и `SECTIONS` — перевод в
  `Section`; `SORT_STATES` — восемь состояний; `chart_icon(color)`;
  `Toolbar(QFrame)` с сигналами `view_changed(object)` (`View | None`),
  `filter_clicked(str)`, `filter_reset(str)`, `collapse_toggled(bool)`,
  `order_changed(object)`, `add_clicked()`;
  методами `view_button(view)`, `filter_button(name)`,
  `set_filter_active(name, on)`, `set_kind(kind)` и свойством `order`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_toolbar.py`:

```python
from PySide6.QtCore import Qt

from backend.model import Kind, Sort
from client.widgets.toolbar import SORT_STATES, Toolbar, View


def click(qtbot, button):
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


def test_the_sort_cycles_four_criteria_in_two_directions(qtbot, theme):
    """Проверяем инвариант, а не переписываем таблицу: тест-копия краснеет от
    любой редактуры и не ловит настоящую поломку — дубль или потерянную
    сторону."""
    assert len(SORT_STATES) == 8
    assert len({state.order for state in SORT_STATES}) == 8, "дублей нет"

    sides = {}
    for state in SORT_STATES:
        sides.setdefault(state.order.key, set()).add(state.order.descending)

    assert set(sides) == {Sort.SCORE, Sort.RATED_AT, Sort.YEAR, Sort.TITLE}
    assert all(both == {True, False} for both in sides.values())


def test_neighbours_in_the_cycle_are_the_two_sides_of_one_criterion(qtbot, theme):
    """Нажал второй раз — перевернул тот же порядок, а не уехал в другой."""
    pairs = list(zip(SORT_STATES[::2], SORT_STATES[1::2]))

    assert all(first.order.key is second.order.key for first, second in pairs)
    assert all(first.order.descending != second.order.descending
               for first, second in pairs)


def test_the_date_added_is_not_in_the_cycle(qtbot, theme):
    """Это порядок по умолчанию в «Хочу посмотреть», а не состояние кнопки."""
    assert Sort.ADDED_AT not in [state.order.key for state in SORT_STATES]


def test_the_first_state_is_the_high_scores(qtbot, theme):
    bar = Toolbar()
    qtbot.addWidget(bar)

    assert bar.order == SORT_STATES[0].order


def test_clicking_the_sort_moves_along_the_cycle(qtbot, theme):
    bar = Toolbar()
    qtbot.addWidget(bar)
    heard = []
    bar.order_changed.connect(heard.append)

    click(qtbot, bar.sort_button)

    assert bar.order == SORT_STATES[1].order
    assert heard == [SORT_STATES[1].order]


def test_the_cycle_closes(qtbot, theme):
    bar = Toolbar()
    qtbot.addWidget(bar)

    for _ in SORT_STATES:
        click(qtbot, bar.sort_button)

    assert bar.order == SORT_STATES[0].order


def test_views_are_mutually_exclusive(qtbot, theme):
    bar = Toolbar()
    qtbot.addWidget(bar)

    click(qtbot, bar.view_button(View.RATED))
    click(qtbot, bar.view_button(View.WISHLIST))

    assert bar.view_button(View.RATED).property("on") == "false"
    assert bar.view_button(View.WISHLIST).property("on") == "true"


def test_the_statistics_is_in_the_same_group(qtbot, theme):
    """В макете это полноправная третья кнопка группы: она гасит соседей и
    возвращает обычный список повторным нажатием."""
    bar = Toolbar()
    qtbot.addWidget(bar)
    heard = []
    bar.view_changed.connect(heard.append)

    click(qtbot, bar.view_button(View.RATED))
    click(qtbot, bar.view_button(View.STATS))

    assert bar.view_button(View.RATED).property("on") == "false"
    assert bar.view_button(View.STATS).property("on") == "true"
    assert heard == [View.RATED, View.STATS]


def test_the_statistics_button_is_not_a_star(qtbot, theme):
    """Звезда уже занята фильтром по оценке и сортировкой — три одинаковые
    кнопки в одном ряду. В макете это три столбика, и они не глиф шрифта:
    у иконки шрифта нет частей, а столбики растут поодиночке."""
    bar = Toolbar()
    qtbot.addWidget(bar)

    assert bar.view_button(View.STATS).text() == ""
    assert not bar.view_button(View.STATS).icon().isNull()


def test_clicking_the_active_view_returns_the_plain_list(qtbot, theme):
    """Отдельной кнопки под обычный список нет."""
    bar = Toolbar()
    qtbot.addWidget(bar)
    heard = []
    bar.view_changed.connect(heard.append)

    click(qtbot, bar.view_button(View.RATED))
    click(qtbot, bar.view_button(View.RATED))

    assert heard == [View.RATED, None]
    assert bar.view_button(View.RATED).property("on") == "false"


def test_a_filter_button_asks_to_open_while_it_is_dark(qtbot, theme):
    bar = Toolbar()
    qtbot.addWidget(bar)
    opened, reset = [], []
    bar.filter_clicked.connect(opened.append)
    bar.filter_reset.connect(reset.append)

    click(qtbot, bar.filter_button("genres"))

    assert opened == ["genres"] and reset == []


def test_a_lit_filter_button_resets_instead_of_opening(qtbot, theme):
    """Горит — значит фильтр задан, и повторное нажатие его сбрасывает."""
    bar = Toolbar()
    qtbot.addWidget(bar)
    opened, reset = [], []
    bar.filter_clicked.connect(opened.append)
    bar.filter_reset.connect(reset.append)

    bar.set_filter_active("genres", True)
    click(qtbot, bar.filter_button("genres"))

    assert reset == ["genres"] and opened == []


def test_filters_are_independent(qtbot, theme):
    bar = Toolbar()
    qtbot.addWidget(bar)

    bar.set_filter_active("genres", True)
    bar.set_filter_active("tags", True)

    assert bar.filter_button("genres").property("on") == "true"
    assert bar.filter_button("tags").property("on") == "true"


def test_the_collapse_toggle_swaps_its_glyph_both_ways(qtbot, theme):
    """Подсветки нет: состояние сообщает иконка. Обратный ход тоже."""
    bar = Toolbar()
    qtbot.addWidget(bar)
    heard = []
    bar.collapse_toggled.connect(heard.append)

    before = bar.collapse_button.text()
    click(qtbot, bar.collapse_button)
    folded = bar.collapse_button.text()
    click(qtbot, bar.collapse_button)

    assert heard == [True, False]
    assert folded != before
    assert bar.collapse_button.text() == before
    assert bar.collapse_button.property("on") in (None, "false")


def test_the_bookmark_is_named_differently_for_games(qtbot, theme):
    """Отложенное для игр называется иначе."""
    bar = Toolbar()
    qtbot.addWidget(bar)

    bar.set_kind(Kind.MOVIE)
    assert bar.view_button(View.WISHLIST).toolTip() == "Хочу посмотреть"

    bar.set_kind(Kind.GAME)
    assert bar.view_button(View.WISHLIST).toolTip() == "Хочу поиграть"


def test_the_plus_asks_for_a_new_card(qtbot, theme):
    bar = Toolbar()
    qtbot.addWidget(bar)
    heard = []
    bar.add_clicked.connect(lambda: heard.append(True))

    click(qtbot, bar.add_button)

    assert heard == [True]
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_toolbar.py -v`
Ожидается: FAIL — `No module named 'client.widgets.toolbar'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/toolbar.py`:

```python
"""Ряд круглых кнопок. Четыре поведения в одной капсуле."""

from dataclasses import dataclass
from enum import StrEnum

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton

from backend.model import Kind, Order, Section, Sort
from client.theme import GLYPHS, icon_font, metrics, palette


class View(StrEnum):
    """Что показано вместо обычного списка. Своё, а не Section: статистика в
    базу не ходит и разделом запроса не является, но кнопка у неё в том же
    ряду и в той же группе взаимоисключения."""

    RATED = "rated"
    WISHLIST = "wishlist"
    STATS = "stats"


# Значения совпадают со значениями Section — перевод получается даром.
SECTIONS = {View.RATED: Section.RATED, View.WISHLIST: Section.WISHLIST}

# Столбики гистограммы из макета: 24×24, три прямоугольника разной высоты.
# Это не глиф шрифта нарочно — у иконки шрифта нет частей, а столбики должны
# расти поодиночке.
_CHART_BARS = ((4, 9, 4, 11), (10, 4, 4, 16), (16, 13, 4, 7))


def chart_icon(color: str, size: int = 19) -> QIcon:
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(palette.qcolor(color))
    scale = size / 24
    for x, y, width, height in _CHART_BARS:
        painter.drawRect(QRectF(x * scale, y * scale,
                                width * scale, height * scale))
    painter.end()

    return QIcon(pixmap)


@dataclass(frozen=True, slots=True)
class SortState:
    order: Order
    glyph: str
    arrow: str
    label: str


# Восемь состояний: четыре критерия в две стороны. Дата добавления в переборе
# не участвует — это порядок по умолчанию в «Хочу посмотреть».
SORT_STATES = (
    SortState(Order(Sort.SCORE, True), GLYPHS["score"], GLYPHS["down"],
              "по оценке, сначала высокие"),
    SortState(Order(Sort.SCORE, False), GLYPHS["score"], GLYPHS["up"],
              "по оценке, сначала низкие"),
    SortState(Order(Sort.RATED_AT, True), GLYPHS["rated_at"], GLYPHS["down"],
              "по времени оценки, сначала свежие"),
    SortState(Order(Sort.RATED_AT, False), GLYPHS["rated_at"], GLYPHS["up"],
              "по времени оценки, сначала давние"),
    SortState(Order(Sort.YEAR, True), GLYPHS["year"], GLYPHS["down"],
              "по дате выхода, сначала новые"),
    SortState(Order(Sort.YEAR, False), GLYPHS["year"], GLYPHS["up"],
              "по дате выхода, сначала старые"),
    SortState(Order(Sort.TITLE, False), GLYPHS["alphabet"], GLYPHS["down"],
              "по алфавиту, А → Я"),
    SortState(Order(Sort.TITLE, True), GLYPHS["alphabet"], GLYPHS["up"],
              "по алфавиту, Я → А"),
)

_VIEWS = (
    (View.RATED, GLYPHS["rated"], "Оценённые"),
    (View.WISHLIST, GLYPHS["wish"], "Хочу посмотреть"),
    (View.STATS, None, "Статистика"),      # у статистики иконка рисованная
)

_FILTERS = (
    ("genres", GLYPHS["genres"], "Жанры"),
    ("tags", GLYPHS["tags"], "Теги"),
    ("scores", GLYPHS["score"], "Фильтр по оценке"),
)


class Toolbar(QFrame):
    view_changed = Signal(object)      # View или None — обычный список
    filter_clicked = Signal(str)
    filter_reset = Signal(str)
    collapse_toggled = Signal(bool)
    order_changed = Signal(object)
    add_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("toolsPill")
        self.setFixedHeight(metrics.PILL_H)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(metrics.PILL_PAD, metrics.PILL_PAD,
                                  metrics.PILL_PAD, metrics.PILL_PAD)
        layout.setSpacing(0)

        self._views: dict[View, QToolButton] = {}
        self._filters: dict[str, QToolButton] = {}
        self._view: View | None = None
        self._sort = 0
        self._collapsed = False

        # Статистика — такая же кнопка группы: она гасит соседей, а повторное
        # нажатие возвращает обычный список.
        for view, glyph, hint in _VIEWS:
            button = self._make(glyph, hint)
            button.clicked.connect(lambda _=False, v=view: self._pick(v))
            self._views[view] = button
            layout.addWidget(button)
        self.stats_button = self._views[View.STATS]

        for name, glyph, hint in _FILTERS:
            button = self._make(glyph, hint)
            button.clicked.connect(lambda _=False, n=name: self._filter(n))
            self._filters[name] = button
            layout.addWidget(button)

        self.collapse_button = self._make(GLYPHS["collapse"], "Свернуть всё")
        self.collapse_button.clicked.connect(self._collapse)
        layout.addWidget(self.collapse_button)

        self.sort_button = self._make(GLYPHS["score"], "Сортировка")
        self.sort_button.clicked.connect(self._next_sort)
        layout.addWidget(self.sort_button)

        self.add_button = self._make(GLYPHS["add"], "Завести карточку")
        self.add_button.clicked.connect(self.add_clicked)
        layout.addWidget(self.add_button)

        self._paint_sort()

    @property
    def order(self) -> Order:
        return SORT_STATES[self._sort].order

    def view_button(self, view: View) -> QToolButton:
        return self._views[view]

    def filter_button(self, name: str) -> QToolButton:
        return self._filters[name]

    def set_filter_active(self, name: str, on: bool) -> None:
        self._light(self._filters[name], on)

    def set_kind(self, kind: Kind) -> None:
        """Отложенное для игр называется иначе."""
        hint = "Хочу поиграть" if kind is Kind.GAME else "Хочу посмотреть"
        self._views[View.WISHLIST].setToolTip(hint)

    def _make(self, glyph: str | None, hint: str) -> QToolButton:
        button = QToolButton(self)
        button.setProperty("role", "tool")
        button.setProperty("on", "false")
        button.setToolTip(hint)
        button.setFixedSize(metrics.TOOL_BTN, metrics.TOOL_BTN)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("glyph", glyph)
        if glyph is None:
            button.setIcon(chart_icon(palette.TEXT))
        else:
            button.setFont(icon_font(19))
            button.setText(glyph)
        return button

    def _light(self, button: QToolButton, on: bool) -> None:
        button.setProperty("on", "true" if on else "false")
        glyph = button.property("glyph")
        if glyph is None:
            # Рисованную иконку QSS не красит — перерисовываем.
            button.setIcon(chart_icon(palette.PRIMARY if on else palette.TEXT))
        else:
            button.setFont(icon_font(19, filled=on))
        button.style().unpolish(button)
        button.style().polish(button)

    def _pick(self, view: View) -> None:
        # Повторное нажатие гасит переключатель и возвращает обычный список —
        # отдельной кнопки под него нет.
        target = None if view is self._view else view
        self._view = target
        for known, button in self._views.items():
            self._light(button, known is target)
        self.view_changed.emit(target)

    def _filter(self, name: str) -> None:
        # Горит — значит фильтр задан, и повторное нажатие его сбрасывает.
        if self._filters[name].property("on") == "true":
            self.filter_reset.emit(name)
        else:
            self.filter_clicked.emit(name)

    def _collapse(self) -> None:
        self._collapsed = not self._collapsed
        glyph = GLYPHS["expand"] if self._collapsed else GLYPHS["collapse"]
        self.collapse_button.setText(glyph)
        self.collapse_button.setToolTip(
            "Развернуть всё" if self._collapsed else "Свернуть всё"
        )
        self.collapse_toggled.emit(self._collapsed)

    def _next_sort(self) -> None:
        self._sort = (self._sort + 1) % len(SORT_STATES)
        self._paint_sort()
        self.order_changed.emit(self.order)

    def _paint_sort(self) -> None:
        state = SORT_STATES[self._sort]
        self.sort_button.setText(state.glyph)
        self.sort_button.setToolTip("Сортировка: " + state.label)
```

**Стрелка направления** в макете сидит отдельным маленьким глифом в правом
нижнем углу кнопки. В Qt это второй `QLabel` поверх кнопки: создаётся в `_make`
для кнопки сортировки, позиционируется в `resizeEvent` и меняет текст в
`_paint_sort` на `state.arrow`. Ставится тем же `icon_font(13)`.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_toolbar.py -v`
Ожидается: PASS, шестнадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/toolbar.py tests/client/test_toolbar.py
git commit -m "feat: ряд кнопок шапки с четырьмя поведениями"
```

---

### Задача 11: Звёзды и вердикт

**Клик по уже выставленной оценке снимает её** — отдельной кнопки нет.

**У игры три шкалы, и в свёрнутом виде они складываются в одну усреднённую.**
Средняя дробная: цвет берётся по целой части, остаток дорисовывается частично
закрашенной звездой.

**Файлы:**
- Создать: `client/widgets/stars.py`
- Создать: `tests/client/test_stars.py`

**Интерфейсы:**
- Потребляет: `palette`, `icons`, `typography`.
- Отдаёт: `VERDICTS` — десять ярлыков; `StarRow(QWidget)` с `bind(score)`,
  сигналом `picked(int)` (ноль — оценка снята) и полем `stars`;
  `AverageRow(QWidget)` с `bind(value: float)` — только показ, без нажатий;
  `verdict(score: int) -> str`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_stars.py`:

```python
import pytest
from PySide6.QtCore import Qt

from client.theme import palette
from client.widgets.stars import AverageRow, StarRow, verdict


def test_there_are_always_ten_stars(qtbot, theme):
    row = StarRow()
    qtbot.addWidget(row)

    assert len(row.stars) == 10


def test_a_score_lights_the_stars_up_to_it(qtbot, theme):
    row = StarRow()
    qtbot.addWidget(row)

    row.bind(7)

    assert [star.property("on") == "true" for star in row.stars] == (
        [True] * 7 + [False] * 3
    )


def test_clicking_a_star_picks_that_score(qtbot, theme):
    row = StarRow()
    qtbot.addWidget(row)
    heard = []
    row.picked.connect(heard.append)

    qtbot.mouseClick(row.stars[8], Qt.MouseButton.LeftButton)

    assert heard == [9]


def test_clicking_the_current_score_takes_it_away(qtbot, theme):
    """Отдельной кнопки под снятие оценки нет."""
    row = StarRow()
    qtbot.addWidget(row)
    row.bind(9)
    heard = []
    row.picked.connect(heard.append)

    qtbot.mouseClick(row.stars[8], Qt.MouseButton.LeftButton)

    assert heard == [0]


def test_an_unrated_row_is_empty(qtbot, theme):
    row = StarRow()
    qtbot.addWidget(row)

    row.bind(0)

    assert not any(star.property("on") == "true" for star in row.stars)
    assert row.verdict_label.text() == ""


def test_the_verdict_follows_the_score(qtbot, theme):
    assert verdict(10) == "Шедевр"
    assert verdict(1) == "Отвратительно"
    assert verdict(0) == ""


def test_the_verdict_is_painted_by_the_same_scale(qtbot, theme):
    row = StarRow()
    qtbot.addWidget(row)

    row.bind(3)

    assert palette.score_color(3) in row.verdict_label.styleSheet()


@pytest.mark.parametrize(
    "value, whole, part",
    [(7.33, 7, 0.33), (9.0, 9, 0.0), (10.0, 10, 0.0), (0.5, 0, 0.5)],
)
def test_the_average_splits_into_whole_and_part(qtbot, theme, value, whole, part):
    """Цвет по целой части, остаток — частично закрашенной звездой."""
    row = AverageRow()
    qtbot.addWidget(row)

    row.bind(value)

    assert row.whole == whole
    assert row.part == pytest.approx(part, abs=1e-6)


def test_the_average_row_is_not_clickable(qtbot, theme):
    """Она показывает то, что посчитано из трёх шкал; править её нечем."""
    row = AverageRow()
    qtbot.addWidget(row)

    assert not hasattr(row, "picked")
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_stars.py -v`
Ожидается: FAIL — `No module named 'client.widgets.stars'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/stars.py`:

```python
"""Ряд звёзд и ярлык оценки.

Цвет берётся из той же нотации, что и в статистике и в фильтре: он закреплён
за значением."""

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget

from client.theme import GLYPHS, font, icon_font, palette, typography

VERDICTS = {
    10: "Шедевр", 9: "Отлично", 8: "Хорошо", 7: "Интересно", 6: "Неплохо",
    5: "Средне", 4: "Посредственно", 3: "Уныло", 2: "Плохо",
    1: "Отвратительно",
}

STAR_SIZE = 21


def verdict(score: int) -> str:
    """Ноль — это «не оценено», а не оценка: ярлыка у него нет."""
    return VERDICTS.get(score, "")


class StarRow(QWidget):
    """Десять звёзд и ярлык. Клик по уже выставленной оценке снимает её."""

    picked = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._score = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.stars: list[QToolButton] = []
        for step in range(1, 11):
            star = QToolButton(self)
            star.setProperty("role", "star")
            star.setProperty("on", "false")
            star.setText(GLYPHS["score"])
            star.setFont(icon_font(STAR_SIZE))
            star.setCursor(Qt.CursorShape.PointingHandCursor)
            star.clicked.connect(lambda _=False, s=step: self._pick(s))
            layout.addWidget(star)
            self.stars.append(star)

        self.verdict_label = QLabel(self)
        self.verdict_label.setFont(font(typography.TITLE_S))
        layout.addSpacing(8)
        layout.addWidget(self.verdict_label)
        layout.addStretch(1)

    def bind(self, score: int) -> None:
        self._score = score
        color = palette.score_color(score) if score else palette.TEXT
        for step, star in enumerate(self.stars, start=1):
            on = step <= score
            star.setProperty("on", "true" if on else "false")
            star.setFont(icon_font(STAR_SIZE, filled=on))
            star.setStyleSheet(
                f"color: {color};" if on else f"color: {palette.STAR_EMPTY};"
            )
        self.verdict_label.setText(verdict(score))
        self.verdict_label.setStyleSheet(f"color: {color};")

    def _pick(self, step: int) -> None:
        # Клик по текущей оценке снимает её: отдельной кнопки нет.
        self.picked.emit(0 if step == self._score else step)


class AverageRow(QWidget):
    """Средняя трёх шкал. Только показ: править её нечем, она посчитана."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.whole = 0
        self.part = 0.0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.stars: list[QLabel] = []
        for _ in range(10):
            star = QLabel(self)
            star.setFont(icon_font(STAR_SIZE))
            star.setText(GLYPHS["score"])
            layout.addWidget(star)
            self.stars.append(star)

        self.verdict_label = QLabel(self)
        self.verdict_label.setFont(font(typography.TITLE_S))
        layout.addSpacing(8)
        layout.addWidget(self.verdict_label)
        layout.addStretch(1)

    def bind(self, value: float) -> None:
        self.whole = math.floor(value)
        self.part = value - self.whole
        color = palette.score_color(max(1, self.whole))

        for step, star in enumerate(self.stars, start=1):
            filled = step <= self.whole
            star.setFont(icon_font(STAR_SIZE, filled=filled))
            star.setStyleSheet(
                f"color: {color};" if filled else f"color: {palette.STAR_EMPTY};"
            )

        self.verdict_label.setText(verdict(self.whole))
        self.verdict_label.setStyleSheet(f"color: {color};")
```

**Дробная звезда** в макете — контурная, поверх которой лежит закрашенная,
обрезанная по ширине. В Qt это отдельный виджет: `QLabel` с
переопределённым `paintEvent`, который рисует контурный глиф целиком, затем
ставит `setClipRect` шириной `part` и рисует закрашенный. Реализуется в
`AverageRow` заменой `self.stars[self.whole]` на такой виджет; `part == 0`
оставляет обычную контурную звезду.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_stars.py -v`
Ожидается: PASS, двенадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/stars.py tests/client/test_stars.py
git commit -m "feat: звёзды, вердикт и средняя оценка"
```

---

### Задача 12: Раскладка в поток, чипы и чужие оценки

Три строки карточки, которые переносятся по ширине: жанры с тегами, состав и
оценки агрегаторов. У Qt раскладки в поток нет — пишем свою, один раз на все
три места.

**Шкала чужой оценки выводится из имени источника.** В базе значение лежит как
пришло: IMDb десятибалльный, Rotten Tomatoes стобалльный. Где какая шкала и где
нужен процент — знает только показ.

**Не приехавшая оценка — кольцо на месте числа.** Имя источника остаётся, чтобы
строка не прыгала, когда цифра приедет.

**Файлы:**
- Создать: `client/widgets/flow.py`, `client/widgets/chips.py`,
  `client/widgets/aggregates.py`
- Создать: `tests/client/test_flow.py`, `tests/client/test_chips.py`,
  `tests/client/test_aggregates.py`

**Интерфейсы:**
- Потребляет: `CardView`, `Genre`, `Tag`, `ExternalRating`, `RatingSource`;
  `palette`, `icons`.
- Отдаёт: `FlowLayout(QLayout)` — перенос по ширине, с честным `sizeHint`;
  `ChipRow(QWidget)` с `bind(genres, tags)`, `count_chips()` и сигналами
  `genre_clicked(int)`, `tag_clicked(int)`, `add_tag_clicked()`;
  `SOURCE_NAMES`, `SOURCE_SCALE`, `SOURCE_SUFFIX`;
  `AggregateRow(QWidget)` с `bind(ratings, waiting)`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_flow.py`:

```python
from PySide6.QtWidgets import QLabel, QWidget

from client.widgets.flow import FlowLayout


def test_items_wrap_when_the_width_runs_out(qtbot, theme):
    """У Qt раскладки в поток нет, а жанры, состав и чужие оценки переносятся
    все три."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = FlowLayout(host, spacing=8)
    for _ in range(6):
        label = QLabel("Приключения")
        label.setFixedSize(100, 20)
        layout.addWidget(label)

    host.setFixedWidth(220)
    host.show()
    qtbot.waitExposed(host)

    rows = {label.y() for label in host.findChildren(QLabel)}
    assert len(rows) == 3, "по две штуки в ряд"


def test_a_wider_host_needs_fewer_rows(qtbot, theme):
    host = QWidget()
    qtbot.addWidget(host)
    layout = FlowLayout(host, spacing=8)
    for _ in range(6):
        label = QLabel("Приключения")
        label.setFixedSize(100, 20)
        layout.addWidget(label)

    host.setFixedWidth(560)
    host.show()
    qtbot.waitExposed(host)

    rows = {label.y() for label in host.findChildren(QLabel)}
    assert len(rows) == 2


def test_the_height_depends_on_the_width(qtbot, theme):
    """Ради этого раскладка и своя: высота карточки в ленте считается по
    настоящей высоте её строк."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = FlowLayout(host, spacing=8)
    for _ in range(6):
        label = QLabel("Приключения")
        label.setFixedSize(100, 20)
        layout.addWidget(label)

    assert layout.heightForWidth(220) > layout.heightForWidth(560)
    assert layout.hasHeightForWidth()


def test_an_empty_layout_takes_no_height(qtbot, theme):
    host = QWidget()
    qtbot.addWidget(host)
    layout = FlowLayout(host, spacing=8)

    assert layout.heightForWidth(300) == 0
    assert layout.minimumSize().isValid(), "QSize() без значений недействителен"


def test_the_host_gets_the_height_the_layout_asked_for(qtbot, theme):
    """От этой высоты считается высота карточки, а от неё — все распорки
    ленты. Если sizeHint отдаёт высоту одной строки, лента поедет целиком."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = FlowLayout(host, spacing=8)
    for _ in range(6):
        label = QLabel("Приключения")
        label.setFixedSize(100, 20)
        layout.addWidget(label)

    host.setFixedWidth(220)
    host.adjustSize()

    assert host.height() >= layout.heightForWidth(220)


def test_clearing_and_binding_again_leaves_nothing(qtbot, theme):
    """Так чистят раскладку ChipRow и AggregateRow при переиспользовании
    карточки: цикл while count() не должен зацикливаться."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = FlowLayout(host, spacing=8)
    for _ in range(5):
        layout.addWidget(QLabel("метка"))

    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()

    assert layout.count() == 0
    assert layout.itemAt(0) is None
    layout.addWidget(QLabel("новая"))
    assert layout.count() == 1
```

Создать `tests/client/test_chips.py`:

```python
from PySide6.QtCore import Qt

from backend.model import Genre, GenreKind, Tag
from client.widgets.chips import ChipRow

DRAMA = Genre(id=1, name="драма", kind=GenreKind.FILM)
RPG = Genre(id=2, name="RPG", kind=GenreKind.GAME)
MINE = Tag(id=7, name="пересмотреть")


def test_genres_tags_and_the_button(qtbot, theme):
    row = ChipRow()
    qtbot.addWidget(row)

    row.bind((DRAMA,), (MINE,))

    assert row.count_chips() == 3, "жанр, тег и «± Тег»"


def test_only_the_first_letter_is_raised(qtbot, theme):
    """Внешняя база отдаёт жанры строчными. capitalize опустил бы остальные:
    «RPG» стал бы «Rpg»."""
    row = ChipRow()
    qtbot.addWidget(row)

    row.bind((DRAMA, RPG), ())

    shown = [chip.text() for chip in row.findChildren(row.chip_type())]
    assert "Драма" in shown
    assert "RPG" in shown


def test_rebinding_leaves_nothing_of_the_previous_card(qtbot, theme):
    """Главная опасность пула: чужие чипы в переиспользованной карточке."""
    row = ChipRow()
    qtbot.addWidget(row)
    row.bind((DRAMA,), (MINE,))

    row.bind((), ())

    assert row.count_chips() == 1, "остаётся только «± Тег»"


def test_the_add_button_is_always_last(qtbot, theme):
    """Видна всегда и приглушённой: спрятанная кнопка — ловушка, про которую
    надо догадаться."""
    row = ChipRow()
    qtbot.addWidget(row)

    row.bind((DRAMA,), (MINE,))

    assert row.chips()[-1].text() == "± Тег"


def test_a_chip_reports_which_one_it_is(qtbot, theme):
    row = ChipRow()
    qtbot.addWidget(row)
    row.bind((DRAMA,), (MINE,))
    genres, tags, added = [], [], []
    row.genre_clicked.connect(genres.append)
    row.tag_clicked.connect(tags.append)
    row.add_tag_clicked.connect(lambda: added.append(True))

    for chip in row.chips():
        qtbot.mouseClick(chip, Qt.MouseButton.LeftButton)

    assert genres == [DRAMA.id]
    assert tags == [MINE.id]
    assert added == [True]


def test_tags_are_told_apart_from_genres(qtbot, theme):
    """Свои теги отличаются от жанров из внешней базы — цвет ставит QSS по
    свойству, и оно должно быть проставлено."""
    row = ChipRow()
    qtbot.addWidget(row)

    row.bind((DRAMA,), (MINE,))

    roles = [chip.property("chip") for chip in row.chips()]
    assert roles == ["genre", "tag", "add"]
```

Метод `chips()` возвращает `self._made`, `chip_type()` — класс кнопки; оба
добавляются в `ChipRow` рядом с `count_chips`.

Создать `tests/client/test_aggregates.py`:

```python
from datetime import datetime

from backend.model import ExternalRating, RatingSource
from client.theme import palette
from client.widgets.aggregates import (
    SOURCE_NAMES,
    SOURCE_SCALE,
    AggregateRow,
)

WHEN = datetime(2026, 7, 27, 12, 0)


def test_every_source_has_a_name_and_a_scale():
    """Шкала выводится из имени источника: в базе значение лежит как пришло."""
    for source in RatingSource:
        assert source in SOURCE_NAMES, source
        assert source in SOURCE_SCALE, source


def test_the_ten_point_and_the_hundred_point_sources_are_told_apart():
    assert SOURCE_SCALE[RatingSource.IMDB] == 10
    assert SOURCE_SCALE[RatingSource.ROTTEN] == 100


def test_a_value_is_shown_with_its_source(qtbot, theme):
    row = AggregateRow()
    qtbot.addWidget(row)

    row.bind((ExternalRating(RatingSource.IMDB, 8.6, WHEN),), waiting=())

    assert row.text_of(RatingSource.IMDB) == "8.6"


def test_a_percentage_source_carries_its_sign(qtbot, theme):
    row = AggregateRow()
    qtbot.addWidget(row)

    row.bind((ExternalRating(RatingSource.ROTTEN, 86.0, WHEN),), waiting=())

    assert row.text_of(RatingSource.ROTTEN) == "86%"


def test_a_hundred_point_value_without_a_sign(qtbot, theme):
    """Metascore — просто число, процентов там нет."""
    row = AggregateRow()
    qtbot.addWidget(row)

    row.bind((ExternalRating(RatingSource.METACRITIC, 71.0, WHEN),), waiting=())

    assert row.text_of(RatingSource.METACRITIC) == "71"


def test_the_colour_comes_from_the_same_ten_steps(qtbot, theme):
    """86 из ста и 8.6 из десяти — одна и та же ступень."""
    row = AggregateRow()
    qtbot.addWidget(row)

    row.bind((ExternalRating(RatingSource.IMDB, 8.6, WHEN),
              ExternalRating(RatingSource.ROTTEN, 86.0, WHEN)), waiting=())

    assert row.color_of(RatingSource.IMDB) == row.color_of(RatingSource.ROTTEN)
    assert row.color_of(RatingSource.IMDB) == palette.score_color(9)


def test_an_empty_value_shows_nothing_and_says_nothing(qtbot, theme):
    """Спрашивали, у источника нет. Пусто вместо цифры, без ошибки."""
    row = AggregateRow()
    qtbot.addWidget(row)

    row.bind((ExternalRating(RatingSource.IMDB, None, WHEN),), waiting=())

    assert row.text_of(RatingSource.IMDB) == ""


def test_a_source_still_on_the_way_shows_a_ring(qtbot, theme):
    """Имя остаётся на месте, число заменено кольцом — так строка не прыгает,
    когда цифра приедет."""
    row = AggregateRow()
    qtbot.addWidget(row)

    row.bind((), waiting=(RatingSource.IMDB,))

    assert row.is_waiting(RatingSource.IMDB)
    assert row.text_of(RatingSource.IMDB) == ""
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

Запустить: `pipenv run pytest tests/client/test_flow.py tests/client/test_aggregates.py -v`
Ожидается: FAIL — `No module named 'client.widgets.flow'`.

- [ ] **Шаг 3: Раскладка в поток**

Создать `client/widgets/flow.py`:

```python
"""Раскладка в поток: элементы идут в ряд и переносятся по ширине.

В Qt такой нет, а нужна она трижды: жанры с тегами, состав и чужие оценки.
Общее выносим сразу."""

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QWidget


def follow_width(widget: QWidget) -> None:
    """Проставить виджету политику размера «высота зависит от ширины».

    Решает задачу не она, а `FlowLayout.hasHeightForWidth` ниже: `QWidget`
    спрашивает про высоту от ширины **свою раскладку**, и к политике размера
    обращается только тогда, когда раскладки нет. Проверено прогоном: с
    `follow_width` и без него ряд одинаково просит 46 вместо завышенных 242.

    Функция оставлена страховкой на случай виджета без раскладки и ради того,
    чтобы политика не врала о самом виджете. Зовут её оба обитателя потока —
    ряд чипов и ряд чужих оценок."""
    policy = widget.sizePolicy()
    policy.setHeightForWidth(True)
    widget.setSizePolicy(policy)


class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing: int = 8,
                 line_spacing: int | None = None) -> None:
        super().__init__(parent)
        self._items = []
        self._spacing = spacing
        self._line_spacing = spacing if line_spacing is None else line_spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def heightForWidth(self, width: int) -> int:
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def hasHeightForWidth(self) -> bool:
        return True

    def sizeHint(self) -> QSize:
        """Ширину берём по самому широкому, высоту — настоящую, с переносами.

        Без этого виджет с раскладкой получал бы высоту одной строки, а от неё
        считается высота карточки и, значит, все распорки ленты.

        Высота здесь посчитана для **минимальной** ширины, то есть заведомо
        завышена: восемь жанров в одну колонку вместо одной строки — это впятеро
        больше. Настоящую высоту знает только `heightForWidth`, и чтобы
        родительская раскладка спрашивала именно его, виджет-хозяин обязан
        объявить `sizePolicy().setHeightForWidth(True)`. Об этом — в конструкторах
        `ChipRow` и `AggregateRow`."""
        width = self.minimumSize().width()
        return QSize(width, self.heightForWidth(max(width, 1)))

    def minimumSize(self) -> QSize:
        size = QSize(0, 0)
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _arrange(self, rect: QRect, apply: bool) -> int:
        if not self._items:
            return 0

        x, y = rect.x(), rect.y()
        line = 0

        for item in self._items:
            hint = item.sizeHint()
            if line and x + hint.width() > rect.right() + 1:
                x = rect.x()
                y += line + self._line_spacing
                line = 0

            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x += hint.width() + self._spacing
            line = max(line, hint.height())

        return y + line - rect.y()
```

- [ ] **Шаг 4: Чипы и чужие оценки**

Создать `client/widgets/chips.py`:

```python
"""Жанры, теги и кнопка «± Тег».

Свои теги отличаются от жанров из внешней базы цветом; кнопка видна всегда и
приглушённой — спрятанная кнопка это ловушка, про которую надо догадаться."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QToolButton, QWidget

from client.theme import font, typography
from client.widgets.flow import FlowLayout, follow_width


class ChipRow(QWidget):
    genre_clicked = Signal(int)
    tag_clicked = Signal(int)
    add_tag_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Оправа вылезает за слово, поэтому по горизонтали зазор шире.
        self._layout = FlowLayout(self, spacing=24, line_spacing=8)
        self._made: list[QToolButton] = []
        follow_width(self)

    def bind(self, genres, tags) -> None:
        self._clear()
        for genre in genres:
            # Только первая буква, как ::first-letter в макете: capitalize
            # опустил бы остальные и превратил «RPG» в «Rpg».
            shown = genre.name[:1].upper() + genre.name[1:]
            self._add(shown, "genre",
                      lambda _=False, i=genre.id: self.genre_clicked.emit(i))
        for tag in tags:
            self._add(tag.name, "tag",
                      lambda _=False, i=tag.id: self.tag_clicked.emit(i))
        self._add("± Тег", "add", lambda _=False: self.add_tag_clicked.emit())

    def _add(self, text: str, role: str, slot) -> None:
        chip = QToolButton(self)
        chip.setProperty("role", "chip")
        chip.setProperty("chip", role)
        chip.setText(text)
        chip.setFont(font(typography.LABEL_M))
        chip.setCursor(Qt.CursorShape.PointingHandCursor)
        chip.clicked.connect(slot)
        self._layout.addWidget(chip)
        self._made.append(chip)

    def count_chips(self) -> int:
        return len(self._made)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._made.clear()
```

Создать `client/widgets/aggregates.py`:

```python
"""Чужие оценки. Шкала выводится из имени источника: в базе значение лежит в
том виде, в каком его отдал источник."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from backend.model import RatingSource
from client.theme import font, palette, typography
from client.widgets.flow import FlowLayout, follow_width

SOURCE_NAMES = {
    RatingSource.KINOPOISK: "КП",
    RatingSource.IMDB: "IMDB",
    RatingSource.TMDB: "TMDB",
    RatingSource.ROTTEN: "RT",
    RatingSource.METACRITIC: "MC",
    RatingSource.STEAM: "Steam",
    RatingSource.GOG: "GOG",
}

SOURCE_SCALE = {
    RatingSource.KINOPOISK: 10,
    RatingSource.IMDB: 10,
    RatingSource.TMDB: 10,
    RatingSource.ROTTEN: 100,
    RatingSource.METACRITIC: 100,
    RatingSource.STEAM: 100,
    RatingSource.GOG: 100,
}

# Доля положительных отзывов — это проценты; Metascore — просто число.
SOURCE_SUFFIX = {RatingSource.ROTTEN: "%", RatingSource.STEAM: "%"}


class AggregateRow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = FlowLayout(self, spacing=14)
        self._values: dict[RatingSource, QLabel] = {}
        self._waiting: set[RatingSource] = set()
        follow_width(self)

    def bind(self, ratings, waiting=()) -> None:
        self._clear()
        self._waiting = set(waiting)

        known = {rating.source: rating for rating in ratings}
        for source in list(known) + [s for s in waiting if s not in known]:
            self._add(source, known.get(source))

    def text_of(self, source: RatingSource) -> str:
        label = self._values.get(source)
        return label.text() if label is not None else ""

    def color_of(self, source: RatingSource) -> str:
        label = self._values.get(source)
        return label.property("score") if label is not None else ""

    def is_waiting(self, source: RatingSource) -> bool:
        return source in self._waiting

    def _add(self, source: RatingSource, rating) -> None:
        holder = QWidget(self)
        line = QHBoxLayout(holder)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(5)

        name = QLabel(SOURCE_NAMES[source], holder)
        name.setFont(font(typography.BODY_M))
        name.setCursor(Qt.CursorShape.PointingHandCursor)
        line.addWidget(name)

        value = QLabel(holder)
        value.setFont(font(typography.BODY_M))
        if rating is not None and rating.value is not None:
            maximum = SOURCE_SCALE[source]
            shown = f"{rating.value:g}{SOURCE_SUFFIX.get(source, '')}"
            color = palette.scale_color(rating.value, maximum)
            value.setText(shown)
            value.setProperty("score", color)
            value.setStyleSheet(f"color: {color}; font-weight: 600;")
        line.addWidget(value)

        self._values[source] = value
        self._layout.addWidget(holder)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._values.clear()
```

**Кольцо ожидания** — глиф `progress_activity` под вращением: `QLabel` с
`QVariantAnimation` на угол и `paintEvent`, который поворачивает холст.
Ставится вместо `value`, когда источник в `waiting`. Одна анимация на карточку,
а не на источник: их до пяти в строке, и пять таймеров на карточку при пуле в
дюжину карточек — шестьдесят таймеров.

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_flow.py tests/client/test_chips.py tests/client/test_aggregates.py -v`
Ожидается: PASS, двадцать тестов — шесть на раскладку, шесть на чипы и восемь
на чужие оценки.

- [ ] **Шаг 6: Коммит**

```bash
git add client/widgets/flow.py client/widgets/chips.py \
        client/widgets/aggregates.py tests/client/test_flow.py \
        tests/client/test_chips.py tests/client/test_aggregates.py
git commit -m "feat: раскладка в поток, чипы и чужие оценки"
```

---

### Задача 13: Карточка целиком

**Карточка принимает данные в уже созданный виджет.** Метод `bind`, а не
сборка в конструкторе. Без этого пул невозможен, и это главное требование к
карточке.

**Состояние живёт в данных, а не в виджете.** Свёрнута карточка или нет —
принадлежит строке ленты; виджет — временное окно в данные и при
переиспользовании обязан показать чужое состояние целиком.

**Свёрнутая карточка — одна строка:** название и оценка. У игры три шкалы при
этом складываются в одну усреднённую.

**Файлы:**
- Создать: `client/widgets/facts.py`, `client/widgets/card.py`
- Создать: `tests/client/test_card.py`

**Интерфейсы:**
- Потребляет: `CardView`, `Kind`, `PersonRole`, `CompanyRole`; всё из
  задач 11–12.
- Отдаёт: `FactsBlock(QWidget)` с `bind(view)` и сигналом `person_clicked(str)`;
  `FilmCard(QFrame)` с `bind(view, collapsed)`, `set_poster(data)`,
  сигналами `toggled(bool)`, `score_picked(int, int)` (шкала и значение),
  `wish_toggled(bool)`, `edit_clicked()`, `delete_clicked()`,
  `add_tag_clicked()`, `person_clicked(str)`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_card.py`:

```python
from datetime import datetime

import pytest

from backend.model import (
    CardView,
    CompanyRole,
    Credit,
    ExternalRating,
    Genre,
    GenreKind,
    Kind,
    PersonRole,
    Rating,
    RatingSource,
    Source,
    Tag,
)
from client.widgets.card import FilmCard

WHEN = datetime(2026, 7, 27, 12, 0)


def movie(**fields) -> CardView:
    base = dict(
        item_id=1, kind=Kind.MOVIE, source=Source.TMDB, source_id="157336",
        title="Интерстеллар", year=2014, runtime=169,
        synopsis="про кукурузу и чёрную дыру",
        genres=(Genre(id=1, name="драма", kind=GenreKind.FILM),),
        tags=(Tag(id=1, name="пересмотреть"),),
        people=(Credit("Кристофер Нолан", PersonRole.DIRECTOR),),
        external=(ExternalRating(RatingSource.IMDB, 8.6, WHEN),),
        rating=Rating(item_id=1, score=9.0),
    )
    return CardView(**(base | fields))


def game(**fields) -> CardView:
    base = dict(
        item_id=2, kind=Kind.GAME, source=Source.STEAM, source_id="292030",
        title="The Witcher 3",
        companies=(Credit("CD Projekt RED", CompanyRole.DEVELOPER),),
        rating=Rating(item_id=2, score=9.0, visual=10, narrative=9, gameplay=8),
    )
    return CardView(**(base | fields))


def test_binding_fills_the_card(qtbot, theme):
    card = FilmCard()
    qtbot.addWidget(card)

    card.bind(movie(), collapsed=False)

    assert card.title.text() == "Интерстеллар"
    assert "169" in card.facts.runtime.text()


def test_a_series_shows_seasons_instead_of_minutes(qtbot, theme):
    """Показываем «2 сезона, 24 серии» — оба числа приходят с карточкой."""
    card = FilmCard()
    qtbot.addWidget(card)

    card.bind(movie(kind=Kind.SERIES, runtime=None, seasons_count=2,
                    episodes_count=24), collapsed=False)

    assert card.facts.runtime.text() == "2 сезона, 24 серии"


@pytest.mark.parametrize(
    "seasons, episodes, expected",
    [(1, 5, "1 сезон, 5 серий"), (2, 24, "2 сезона, 24 серии"),
     (5, 41, "5 сезонов, 41 серия"), (11, 112, "11 сезонов, 112 серий")],
)
def test_the_numbers_are_declined(qtbot, theme, seasons, episodes, expected):
    """1 сезон, 2 сезона, 5 сезонов — иначе подпись выглядит машинной."""
    card = FilmCard()
    qtbot.addWidget(card)

    card.bind(movie(kind=Kind.SERIES, runtime=None, seasons_count=seasons,
                    episodes_count=episodes), collapsed=False)

    assert card.facts.runtime.text() == expected


def test_rebinding_leaves_nothing_of_the_previous_card(qtbot, theme):
    """Главная опасность пула: чужие данные в карточке."""
    card = FilmCard()
    qtbot.addWidget(card)

    card.bind(movie(), collapsed=False)
    card.bind(movie(item_id=7, title="Начало", genres=(), tags=(),
                    people=(), external=(), rating=None, synopsis=""),
              collapsed=False)

    assert card.title.text() == "Начало"
    assert card.chips.count_chips() == 1, "остаётся только «± Тег»"
    assert card.aggregates.text_of(RatingSource.IMDB) == ""
    assert not any(star.property("on") == "true" for star in card.stars.stars)


def test_the_collapsed_state_comes_from_the_data(qtbot, theme):
    """Состояние принадлежит строке ленты, а не виджету: при переиспользовании
    он обязан показать чужое."""
    card = FilmCard()
    qtbot.addWidget(card)

    card.bind(movie(), collapsed=True)
    assert card.poster.isHidden()

    card.bind(movie(item_id=7), collapsed=False)
    assert not card.poster.isHidden()


def test_a_collapsed_card_is_one_line(qtbot, theme):
    """Ряд действий уходит вместе с остальным содержимым: в свёрнутой
    карточке закладки нет."""
    card = FilmCard()
    qtbot.addWidget(card)
    card.show()
    qtbot.waitExposed(card)

    card.bind(movie(), collapsed=True)

    for hidden in (card.poster, card.chips, card.facts, card.synopsis,
                   card.aggregates, card.acts):
        assert hidden.isHidden(), hidden


def test_the_average_follows_the_scales(qtbot, theme):
    """Свернул карточку после правки нарратива — увидел бы старую среднюю."""
    card = FilmCard()
    qtbot.addWidget(card)
    card.show()
    qtbot.waitExposed(card)
    card.bind(game(), collapsed=False)
    before = card.average.whole

    card.aspect_rows[1].stars.picked.emit(3)

    assert card.average.whole != before


def test_a_poster_does_not_survive_a_rebind(qtbot, theme):
    """Иначе переиспользованная карточка покажет чужую обложку."""
    from PySide6.QtCore import QBuffer, QByteArray
    from PySide6.QtGui import QPixmap

    pixmap = QPixmap(20, 30)
    pixmap.fill()
    store = QByteArray()
    device = QBuffer(store)
    device.open(QBuffer.OpenModeFlag.WriteOnly)
    pixmap.toImage().save(device, "PNG")
    device.close()

    card = FilmCard()
    qtbot.addWidget(card)
    card.bind(movie(), collapsed=False)
    card.set_poster(bytes(store))

    card.bind(movie(item_id=7, title="Начало"), collapsed=False)

    assert card.poster.pixmap().isNull()


def test_a_collapsed_game_shows_one_average_row(qtbot, theme):
    """Три шкалы сворачиваются в одну усреднённую."""
    card = FilmCard()
    qtbot.addWidget(card)
    card.show()
    qtbot.waitExposed(card)

    card.bind(game(), collapsed=True)

    assert not card.average.isHidden()
    assert all(row.isHidden() for row in card.aspect_rows)


def test_an_expanded_game_shows_three_scales(qtbot, theme):
    card = FilmCard()
    qtbot.addWidget(card)
    card.show()
    qtbot.waitExposed(card)

    card.bind(game(), collapsed=False)

    assert card.average.isHidden()
    assert [row.isHidden() for row in card.aspect_rows] == [False] * 3


def test_a_film_has_no_aspect_rows(qtbot, theme):
    card = FilmCard()
    qtbot.addWidget(card)
    card.show()
    qtbot.waitExposed(card)

    card.bind(movie(), collapsed=False)

    assert all(row.isHidden() for row in card.aspect_rows)
    assert not card.stars.isHidden()


def test_the_chevron_asks_to_toggle(qtbot, theme):
    from PySide6.QtCore import Qt

    card = FilmCard()
    qtbot.addWidget(card)
    card.bind(movie(), collapsed=False)
    heard = []
    card.toggled.connect(heard.append)

    qtbot.mouseClick(card.chevron, Qt.MouseButton.LeftButton)

    assert heard == [True], "виджет просит, а решает лента"


def test_picking_a_score_names_the_scale(qtbot, theme):
    from PySide6.QtCore import Qt

    card = FilmCard()
    qtbot.addWidget(card)
    card.bind(game(), collapsed=False)
    heard = []
    card.score_picked.connect(lambda index, score: heard.append((index, score)))

    qtbot.mouseClick(card.aspect_rows[1].stars[6], Qt.MouseButton.LeftButton)

    assert heard == [(1, 7)]


def test_a_film_reports_the_single_scale(qtbot, theme):
    from PySide6.QtCore import Qt

    card = FilmCard()
    qtbot.addWidget(card)
    card.bind(movie(), collapsed=False)
    heard = []
    card.score_picked.connect(lambda index, score: heard.append((index, score)))

    qtbot.mouseClick(card.stars.stars[7], Qt.MouseButton.LeftButton)

    assert heard == [(-1, 8)], "минус один — «шкала одна»"


def test_a_poster_arrives_as_bytes(qtbot, theme):
    """Через границу постер едет байтами, QPixmap из них делает интерфейс."""
    from PySide6.QtGui import QPixmap

    pixmap = QPixmap(20, 30)
    pixmap.fill()
    buffer = pixmap.toImage()

    from PySide6.QtCore import QBuffer, QByteArray

    store = QByteArray()
    device = QBuffer(store)
    device.open(QBuffer.OpenModeFlag.WriteOnly)
    buffer.save(device, "PNG")
    device.close()

    card = FilmCard()
    qtbot.addWidget(card)
    card.bind(movie(), collapsed=False)

    card.set_poster(bytes(store))

    assert not card.poster.pixmap().isNull()


def test_no_poster_leaves_the_placeholder(qtbot, theme):
    card = FilmCard()
    qtbot.addWidget(card)

    card.bind(movie(), collapsed=False)
    card.set_poster(None)

    assert card.poster.pixmap().isNull()
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_card.py -v`
Ожидается: FAIL — `No module named 'client.widgets.card'`.

- [ ] **Шаг 3: Факты**

Создать `client/widgets/facts.py`:

```python
"""Состав и длительность. У фильма хронометраж, у сериала объём."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QToolButton, QWidget

from backend.model import CompanyRole, Kind, PersonRole
from client.theme import font, typography
from client.widgets.flow import FlowLayout

_ROLES = {
    PersonRole.DIRECTOR: "Режиссёр",
    PersonRole.SHOWRUNNER: "Шоураннер",
    PersonRole.ACTOR: "Актёры",
    CompanyRole.DEVELOPER: "Разработчик",
    CompanyRole.PUBLISHER: "Издатель",
}

# Порядок строк задан: сначала кто сделал, потом кто играл.
_ORDER = (PersonRole.DIRECTOR, PersonRole.SHOWRUNNER, CompanyRole.DEVELOPER,
          CompanyRole.PUBLISHER, PersonRole.ACTOR)

TOP_ACTORS = 5


def plural(count: int, one: str, few: str, many: str) -> str:
    """1 сезон, 2 сезона, 5 сезонов."""
    tens = count % 100
    if 11 <= tens <= 14:
        return many
    ones = count % 10
    if ones == 1:
        return one
    if 2 <= ones <= 4:
        return few
    return many


def runtime_text(view) -> str:
    """У фильма хронометраж, у сериала объём: сезоны и серии всего. Разбивку
    по сезонам и среднюю длину серии не показываем — они стоят запроса на
    каждый сезон."""
    if view.kind is Kind.SERIES:
        seasons, episodes = view.seasons_count, view.episodes_count
        if seasons is None or episodes is None:
            return ""
        return (f"{seasons} {plural(seasons, 'сезон', 'сезона', 'сезонов')}, "
                f"{episodes} {plural(episodes, 'серия', 'серии', 'серий')}")
    return f"{view.runtime} мин" if view.runtime else ""
```

Класс `FactsBlock` собирается на `QGridLayout` из двух колонок: слева подпись
роли, справа `FlowLayout` с именами-кнопками. Строка «Длительность» — последняя,
её значение лежит в `self.runtime`. Каждое имя — отдельная цель: по нему
дальше ищется всё с его участием, поэтому это `QToolButton`, а не текст. У
актёров показываются первые `TOP_ACTORS`, остальные прячет кнопка «… ещё».

- [ ] **Шаг 4: Карточка**

Создать `client/widgets/card.py`. Состав собирается в конструкторе один раз;
всё, что меняется, живёт в `bind`.

```python
ASPECTS = ("Визуал", "Нарратив", "Геймплей")


class FilmCard(QFrame):
    """Карточка ленты. Принимает данные методом bind — без этого пул
    невозможен, и это главное требование к ней.

    Сигналы карточка только испускает; решает лента. toggled просит свернуть,
    а не сворачивает: состояние принадлежит строке."""

    toggled = Signal(bool)
    score_picked = Signal(int, int)     # шкала (-1 — единственная), оценка
    wish_toggled = Signal(bool)
    edit_clicked = Signal()
    delete_clicked = Signal()
    add_tag_clicked = Signal()
    person_clicked = Signal(str)

    def bind(self, view: CardView, collapsed: bool) -> None:
        """Перезаполняет карточку целиком.

        Никакого «если то же самое — пропустить»: пул отдаёт виджет под чужие
        данные, и половинчатое обновление — ровно тот баг, от которого
        стережёт test_rebinding_leaves_nothing_of_the_previous_card."""
        self._view = view
        self.title.setText(view.title)
        self.chips.bind(view.genres, view.tags)
        self.facts.bind(view)
        self.synopsis.setText(view.synopsis)
        self.aggregates.bind(view.external, waiting=view.waiting)
        self.poster.clear()
        self.wish.setProperty("on", "true" if view.in_wishlist else "false")

        self._bind_scores(view)
        self._set_collapsed(collapsed)

    def _bind_scores(self, view: CardView) -> None:
        rating = view.rating
        game = view.kind is Kind.GAME

        for index, row in enumerate(self.aspect_rows):
            row.setVisible(game)
            if game:
                row.stars.bind(_aspect(rating, index) or 0)

        self.stars.setVisible(not game)
        if not game:
            self.stars.bind(int(rating.score) if rating and rating.score else 0)

        self.average.bind(rating.score if rating and rating.score else 0.0)

    def _set_collapsed(self, collapsed: bool) -> None:
        """Свёрнутая карточка — одна строка: название и оценка. Ряд действий
        уходит вместе с остальным содержимым: закладки там нет."""
        self.collapsed = collapsed
        game = self._view.kind is Kind.GAME

        for hidden in (self.poster, self.chips, self.facts, self.synopsis,
                       self.aggregates, self.acts):
            hidden.setVisible(not collapsed)

        # У игры три шкалы сворачиваются в одну усреднённую.
        self.average.setVisible(collapsed and game)
        for row in self.aspect_rows:
            row.setVisible(game and not collapsed)
        self.stars.setVisible(not game and not collapsed)

        self.title.setFont(font(typography.BODY_L if collapsed
                                else typography.TITLE_L))
        margins = 12 if collapsed else 18
        self.layout().setContentsMargins(18, margins, metrics.FILM_GUTTER,
                                         margins)
        # Шеврон переключается вторым глифом, а не поворотом первого: в QSS у
        # Qt свойства transform нет. Правило при этом не выбрасывает весь блок
        # — остальные объявления применяются, — поэтому поломка была бы совсем
        # незаметной: стрелка просто всегда смотрела бы вниз.
        self.chevron.setText(GLYPHS["chevron_down" if collapsed else "chevron_up"])

    def set_poster(self, data: bytes | None) -> None:
        """Через границу постер едет байтами, QPixmap из них делает интерфейс.

        None — это «постера нет»: заглушку надо вернуть, иначе переиспользо-
        ванная карточка покажет чужую обложку."""
        if not data:
            self.poster.clear()
            return
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.poster.setPixmap(pixmap.scaled(
                metrics.POSTER_W, metrics.POSTER_H,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            ))
        else:
            logger.warning("постер не разобрался, %s байт", len(data))
            self.poster.clear()
```

Остальное — сборка в конструкторе, по макету:

- **шеврон** в правом верхнем углу; в свёрнутом виде смотрит вниз. Меняется
  глиф, а не поворот: `transform` в QSS Qt не поддерживает и выбрасывает молча,
  оставляя остальные объявления правила в силе. Тем же приёмом уже сделана
  кнопка «Свернуть всё» в задаче 10;
- **постер** 158×237 слева, `align-self: flex-start`;
- **строки оценки**: у кино одна `StarRow`, у игры три с подписями шириной
  `metrics.ASPECT_W` — общая ширина нужна, чтобы звёзды в трёх строках стояли
  по одной вертикали, — плюс `AverageRow`;
- **ряд действий** `self.acts` вынесен из потока и лежит поверх последней
  строки оценки: он выше строки со звёздами и иначе разводил бы строки на
  разное расстояние. Правка и удаление показываются только под курсором,
  закладка видна всегда;
- каждая `StarRow` подключается к `score_picked` со своим номером, единственная
  — с `-1`;
- **средняя пересчитывается вместе со сторонами**: обработчик `score_picked`
  внутри карточки обновляет `self.average` до того, как сигнал уйдёт наружу.
  Иначе свернул карточку после правки нарратива — и увидел старую среднюю.

`_aspect(rating, index)` достаёт `visual`, `narrative`, `gameplay` по номеру.

`CardView.waiting` — источники, чьи оценки ещё едут. **Поле надо завести здесь:**
план 4 его объявлял, но ревью сняло по правилу «ничего на всякий случай» —
потребителя у него тогда не было, а теперь он и появляется. Строкой
`waiting: tuple[RatingSource, ...] = ()` в `CardView`, последней среди полей со
значением по умолчанию; `view_from_hit` и `view_from_item` не трогаются — у
кандидата и у прочитанной строки ждать нечего.

Наполняет поле показ, а не база: «ещё едет» — состояние клиента. Страница
берёт `backend.enricher.expected(kind)`, вычитает из него то, что уже в
`view.external`, и пересобирает вид через `dataclasses.replace`. Пока
обогащение не запущено, поле пустое, и кольца нет — это правильно: не
спрашивали, значит и ждать нечего.

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_card.py -v`
Ожидается: PASS, двадцать тестов.

- [ ] **Шаг 6: Коммит**

```bash
git add client/widgets/facts.py client/widgets/card.py tests/client/test_card.py
git commit -m "feat: карточка ленты с bind и сворачиванием"
```

---

### Задача 14: Лента — пул и распорки

Сердце плана. **Карточек существует ровно столько, сколько помещается в экран
с запасом; при прокрутке они переиспользуются под новые данные.** Цена
перестаёт зависеть от размера библиотеки.

**Лента не знает своей полной длины.** Она растёт порциями по мере прокрутки,
полоса прокрутки отражает загруженное. Отсюда главное следствие: **высоту
непоказанной карточки предсказывать не нужно никогда.** Известны высоты только
тех, что уже побывали на экране, и они измерены по-настоящему.

**Уехавшая вверх карточка возвращается в пул, а на её месте остаётся распорка
ровно той высоты, которую карточка занимала.** Вернулись назад — распорка снова
заполняется карточкой.

**При изменении размера окна измеренные высоты устаревают.** Распорки остаются
со старыми значениями и уточняются, когда карточка снова попадает на экран;
прокрутка при этом сдвигается на ту же разницу, чтобы видимое не дёргалось.

**Файлы:**
- Создать: `client/widgets/feed.py`
- Создать: `tests/client/test_feed_pool.py`

**Интерфейсы:**
- Потребляет: `CardView`; `FilmCard`; `metrics`.
- Отдаёт: `FeedRow` — `view`, `collapsed`, `height`, `card`, `top`;
  `CardPool` с `acquire()`, `release(card)` и `size`;
  `FeedView(QScrollArea)` с `set_rows(views)`, `append(views)`,
  `replace_row(index, view)`, `rows`, `live_cards()`, сигналами `wants_more()`,
  `row_toggled(int)`, `score_picked(int, int, int)`,
  `poster_wanted(int)`, `row_shown(int)` и методом `set_all_collapsed(bool)`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_feed_pool.py`:

```python
from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel

from backend.model import (
    CardView,
    ExternalRating,
    Genre,
    GenreKind,
    Kind,
    Rating,
    RatingSource,
    Source,
    Tag,
)
from client.widgets.feed import FeedView

WHEN = datetime(2026, 7, 27, 12, 0)
CARD_H = 240


class StubCard(QLabel):
    """Карточка известной высоты с тем же контрактом, что у настоящей.

    Пул проверяется на ней нарочно: с настоящей высота зависит от метрик
    шрифта, и арифметика теста плавала бы вместе с ними."""

    toggled = Signal(bool)
    score_picked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(CARD_H)
        self.bound = None
        self.collapsed = False

    def bind(self, view, collapsed):
        self.bound = view
        self.collapsed = collapsed
        self.setText(view.title)

    def sizeHint(self):
        size = super().sizeHint()
        size.setHeight(CARD_H)
        return size


def views(count: int):
    """Половина карточек «богатые»: иначе в переиспользованной карточке
    нечему протечь, кроме заголовка, и тест на чужие данные ничего не ловит."""
    made = []
    for n in range(count):
        rich = n % 2 == 0
        made.append(CardView(
            item_id=n, kind=Kind.MOVIE, source=Source.TMDB, source_id=str(n),
            title=f"Фильм {n}", year=2000 + n,
            synopsis="строка синопсиса " * 6,
            genres=(Genre(id=1, name="драма", kind=GenreKind.FILM),)
                   if rich else (),
            tags=(Tag(id=1, name="пересмотреть"),) if rich else (),
            external=(ExternalRating(RatingSource.IMDB, 8.6, WHEN),)
                     if rich else (),
            rating=Rating(item_id=n, score=float(n % 10 + 1)) if rich else None,
        ))
    return made


def feed(qtbot, count: int, height: int = 600) -> FeedView:
    made = FeedView(make=StubCard)
    qtbot.addWidget(made)
    made.resize(900, height)
    made.show()
    qtbot.waitExposed(made)
    made.set_rows(views(count))
    qtbot.wait(50)
    return made


def scroll_to(qtbot, made: FeedView, value: int) -> None:
    made.verticalScrollBar().setValue(value)
    qtbot.wait(50)


def scroll_to_bottom(qtbot, made: FeedView) -> None:
    """Лента растёт порциями — за один прыжок в «максимум» она отодвигает
    максимум на экран вперёд. Прыгаем, пока он не перестанет меняться."""
    bar = made.verticalScrollBar()
    for _ in range(40):
        before = bar.maximum()
        bar.setValue(before)
        qtbot.wait(30)
        if bar.maximum() == before:
            return


def test_a_card_shows_the_row_it_stands_on(qtbot, theme):
    made = feed(qtbot, 5)

    for row in made.rows:
        if row.card is not None:
            assert row.card.bound is row.view


def test_only_a_handful_of_cards_exist_for_a_long_feed(qtbot, theme):
    """Ради этого пул и заведён: цена перестаёт зависеть от размера
    библиотеки. Границу считаем от данных, а не подбираем числом."""
    made = feed(qtbot, 200)

    fits = made.viewport().height() // CARD_H + 1
    assert len(made.live_cards()) <= fits * 3
    assert len(made.live_cards()) < len(made.rows) / 5


def test_scrolling_down_releases_the_ones_left_above(qtbot, theme):
    made = feed(qtbot, 200)
    first = made.rows[0]

    scroll_to_bottom(qtbot, made)

    assert first.card is None
    assert first.height is not None, "распорка помнит высоту"


def test_the_spacer_keeps_the_place_exactly(qtbot, theme):
    """Иначе полоса прокрутки прыгала бы при каждом освобождении. Сверяем
    равенство: с «не меньше» тест зелёный и при потерянной распорке — высота
    просто перемерилась бы заново."""
    made = feed(qtbot, 60)
    scroll_to(qtbot, made, 400)
    height, top = made.content_height(), made.rows[5].top

    scroll_to(qtbot, made, 2000)
    scroll_to(qtbot, made, 400)

    assert made.rows[5].top == top
    assert made.content_height() == height


def test_coming_back_shows_the_same_thing(qtbot, theme):
    """Прокрутка в обе стороны — то, на чём пул чаще всего и ломается."""
    made = feed(qtbot, 60)
    expected = made.rows[0].view.title

    scroll_to(qtbot, made, 1500)
    scroll_to(qtbot, made, 0)

    assert made.rows[0].card is not None
    assert made.rows[0].card.bound.title == expected


def test_a_reused_card_carries_no_leftovers(qtbot, theme):
    """Половина карточек «богатая», половина пустая — они и стоят через одну,
    так что при переиспользовании протечь есть чему."""
    made = feed(qtbot, 60)

    scroll_to(qtbot, made, 2000)

    shown = [row for row in made.rows if row.card is not None]
    assert shown
    for row in shown:
        assert row.card.bound is row.view, "карточка привязана к своей строке"


def test_a_returned_row_asks_for_its_poster_again(qtbot, theme):
    """Карточку забрали под чужие данные — начатая загрузка этой строке
    больше не нужна, а вернувшись, постер надо просить заново."""
    made = feed(qtbot, 200)
    wanted = []
    made.poster_wanted.connect(wanted.append)

    scroll_to_bottom(qtbot, made)
    wanted.clear()
    scroll_to(qtbot, made, 0)

    assert 0 in wanted


def test_a_click_on_a_reused_card_reaches_the_right_row(qtbot, theme):
    """Сердце пула: связи ставятся один раз при создании карточки, а номер
    строки она носит свойством. Если вешать связи при каждой привязке, один
    клик доходил бы до дюжины строк сразу."""
    made = feed(qtbot, 60)
    heard = []
    made.row_toggled.connect(heard.append)

    scroll_to(qtbot, made, 1500)
    row = next(i for i, r in enumerate(made.rows) if r.card is not None)
    made.rows[row].card.toggled.emit(True)
    qtbot.wait(50)

    assert heard == [row]
    assert made.rows[row].collapsed is True
    assert sum(1 for r in made.rows if r.collapsed) == 1


def test_the_feed_asks_for_more_when_the_bottom_is_near(qtbot, theme):
    made = feed(qtbot, 30)
    heard = []
    made.wants_more.connect(lambda: heard.append(True))

    scroll_to_bottom(qtbot, made)

    assert heard


def test_the_feed_is_quiet_while_there_is_plenty_below(qtbot, theme):
    """Обратная сторона: голод считается по тому, что кончились строки, а не
    по тому, что мы измерили только пять из двухсот."""
    made = feed(qtbot, 200)
    heard = []
    made.wants_more.connect(lambda: heard.append(True))

    scroll_to(qtbot, made, 0)
    qtbot.wait(100)

    assert heard == []


def test_appending_does_not_disturb_what_is_shown(qtbot, theme):
    made = feed(qtbot, 30)
    scroll_to(qtbot, made, 600)
    before = made.verticalScrollBar().value()

    made.append(views(30))
    qtbot.wait(50)

    assert made.verticalScrollBar().value() == before
    assert len(made.rows) == 60


def test_the_collapsed_state_belongs_to_the_row(qtbot, theme):
    made = feed(qtbot, 10)

    made.set_all_collapsed(True)
    qtbot.wait(50)

    assert all(row.collapsed for row in made.rows)
    for row in made.rows:
        if row.card is not None:
            assert row.card.collapsed is True


def test_collapsing_survives_the_pool(qtbot, theme):
    """Карточка уехала, вернулась — и снова свёрнута: состояние в данных."""
    made = feed(qtbot, 60)
    made.set_all_collapsed(True)
    qtbot.wait(50)

    scroll_to(qtbot, made, 1200)
    scroll_to(qtbot, made, 0)

    assert made.rows[0].card is not None
    assert made.rows[0].card.collapsed is True


def test_toggling_one_card_touches_only_that_row(qtbot, theme):
    made = feed(qtbot, 10)

    made.toggle_row(0)
    qtbot.wait(50)

    assert made.rows[0].collapsed is True
    assert made.rows[1].collapsed is False


def test_the_feed_asks_for_a_poster_of_what_is_shown(qtbot, theme):
    """Постер грузится по требованию видимой карточки, а не всей ленты."""
    made = feed(qtbot, 200)
    wanted = []
    made.poster_wanted.connect(wanted.append)

    scroll_to(qtbot, made, 300)

    last_shown = max(i for i, r in enumerate(made.rows) if r.card is not None)
    assert wanted
    assert max(wanted) <= last_shown, "у невидимых постер не просят"


def test_a_resize_does_not_jump_the_scroll(qtbot, theme):
    """Текст перетекает, высоты устаревают — но видимое не должно дёргаться.
    Сверяем положение верхней видимой строки относительно окна, а не сам факт
    её существования."""
    made = feed(qtbot, 60)
    scroll_to(qtbot, made, 1500)

    bar = made.verticalScrollBar()
    anchor = next(row for row in made.rows
                  if row.card is not None and row.top >= bar.value())
    before = anchor.top - bar.value()

    made.resize(600, 600)
    qtbot.wait(80)

    assert anchor.card is not None
    assert abs((anchor.top - bar.value()) - before) < 12


def test_relayout_does_not_re_enter_itself(qtbot, theme):
    """Внутри раскладки двигается полоса прокрутки и меняется высота
    содержимого, а оба действия шлют valueChanged."""
    made = feed(qtbot, 60)
    depth, worst = 0, 0
    original = type(made)._lay

    def counting(self):
        nonlocal depth, worst
        depth += 1
        worst = max(worst, depth)
        try:
            return original(self)
        finally:
            depth -= 1

    type(made)._lay = counting
    try:
        scroll_to(qtbot, made, 900)
        made.resize(700, 500)
        qtbot.wait(80)
    finally:
        type(made)._lay = original

    assert worst == 1
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_feed_pool.py -v`
Ожидается: FAIL — `No module named 'client.widgets.feed'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/feed.py`:

```python
"""Лента с пулом переиспользуемых карточек.

Карточек существует ровно столько, сколько помещается в экран с запасом.
Уехавшая карточка возвращается в пул, а на её месте остаётся распорка ровно
той высоты, которую она занимала."""

from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QScrollArea, QWidget

from backend.model import CardView
from client.theme import metrics
from client.widgets.card import FilmCard

# Запас за краем экрана: карточка готовится заранее, чтобы при прокрутке не
# было пустого места. Одна экранная высота — компромисс между рывками и
# числом живых виджетов.
OVERSCAN = 1.0

# Насколько близко к концу загруженного надо подобраться, чтобы попросить
# следующую порцию.
HUNGRY = 1.5


@dataclass(slots=True)
class FeedRow:
    """Строка ленты. Здесь и живёт состояние: виджет — временное окно."""

    view: CardView
    collapsed: bool = False
    height: int | None = None    # известна, только если карточка уже стояла
    card: FilmCard | None = None
    top: int = 0


class CardPool:
    """Свободные карточки. Новые создаются, только когда свободных нет.

    Сигналы подключаются один раз, при создании: если вешать их при каждой
    привязке, связи копились бы с каждым переиспользованием, и один клик
    доходил бы до дюжины строк сразу. Номер строки карточка носит свойством —
    оно переписывается на каждой привязке."""

    def __init__(self, wire, make=FilmCard) -> None:
        self._wire = wire
        self._make = make
        self._free: list[FilmCard] = []
        self.size = 0

    def acquire(self) -> FilmCard:
        if self._free:
            return self._free.pop()
        self.size += 1
        card = self._make()
        self._wire(card)
        return card

    def release(self, card: FilmCard) -> None:
        card.hide()
        self._free.append(card)


class FeedView(QScrollArea):
    wants_more = Signal()
    row_toggled = Signal(int)
    score_picked = Signal(int, int, int)   # строка, шкала, оценка
    poster_wanted = Signal(int)
    # Строка показалась впервые. Постер — не единственное, что грузится по
    # требованию видимого: сюда же подвешены второй и третий круги загрузки —
    # превращение кандидата выдачи в карточку, перезапрос счётчиков сериала и
    # оценки агрегаторов.
    row_shown = Signal(int)

    def __init__(self, parent=None, make=FilmCard) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._content = QWidget()
        self.setWidget(self._content)

        self.rows: list[FeedRow] = []
        # make внедряется ради тестов: с карточкой известной высоты арифметика
        # пула перестаёт зависеть от метрик шрифта.
        self._pool = CardPool(self._wire, make=make)
        self._height = 0
        self._asked: set[int] = set()
        self._laying = False
        self._asking = False

        self.verticalScrollBar().valueChanged.connect(lambda _: self._relayout())

    def set_rows(self, views) -> None:
        for row in self.rows:
            self._release(row)
        self.rows = [FeedRow(view=view) for view in views]
        self._asked.clear()
        self.verticalScrollBar().setValue(0)
        self._relayout()

    def append(self, views) -> None:
        self.rows.extend(FeedRow(view=view) for view in views)
        self._relayout()

    def replace_row(self, index: int, view) -> None:
        """Данные строки заменились на месте: кандидат выдачи стал карточкой и
        обзавёлся `item_id`. Высота могла измениться, поэтому строку
        перемеряем, а прокрутку не двигаем."""
        if not 0 <= index < len(self.rows):
            return
        row = self.rows[index]
        row.view = view
        row.height = 0
        if row.card is not None:
            row.card.bind(view, collapsed=row.collapsed)
        self._relayout()

    def live_cards(self) -> list[FilmCard]:
        return [row.card for row in self.rows if row.card is not None]

    def content_height(self) -> int:
        return self._height

    def set_all_collapsed(self, collapsed: bool) -> None:
        """Тумблер общий на всё приложение, а не настройка раздела."""
        for row in self.rows:
            row.collapsed = collapsed
            row.height = None      # высота меняется, мерить заново
        self._relayout()

    def toggle_row(self, index: int) -> None:
        row = self.rows[index]
        row.collapsed = not row.collapsed
        row.height = None
        self._relayout()
        self.row_toggled.emit(index)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Текст перетекает — измеренные высоты устарели. Уточняются они по
        # мере того, как карточки снова попадают на экран.
        self._relayout()

    def _relayout(self) -> None:
        # Защёлка от повторного входа: внутри мы двигаем полосу прокрутки и
        # меняем высоту содержимого, а оба действия шлют valueChanged.
        if self._laying:
            return
        self._laying = True
        try:
            self._lay()
        finally:
            self._laying = False

    def _lay(self) -> None:
        width = self.viewport().width()
        top = self.verticalScrollBar().value()
        bottom = top + self.viewport().height()
        margin = self.viewport().height() * OVERSCAN

        y = 0
        shift = 0
        for index, row in enumerate(self.rows):
            row.top = y

            if row.height is None:
                # Высоту непоказанной карточки не предсказываем: если до неё
                # ещё не дошли, дальше строить нечего.
                if y > bottom + margin:
                    break
                self._mount(row, index, width)
                row.height = row.card.height()
            elif y + row.height >= top - margin and y <= bottom + margin:
                measured = row.height
                self._mount(row, index, width)
                row.height = row.card.height()
                if row.height != measured and y + row.height < top:
                    # Строка целиком выше экрана: её изменение сдвинуло бы
                    # видимое, поэтому компенсируем прокруткой.
                    shift += row.height - measured
            else:
                self._release(row)

            y += row.height + metrics.FEED_GAP

        self._height = y
        self._content.setFixedHeight(y)

        if shift:
            bar = self.verticalScrollBar()
            bar.setValue(bar.value() + shift)

        # Просим догрузку, только когда измерили всё, что на руках: иначе
        # лента просит ещё, держа двести неразложенных строк.
        room_left = all(row.height is not None for row in self.rows)
        near_bottom = bool(y) and bottom + self.viewport().height() * HUNGRY >= y
        if room_left and near_bottom and not self._asking:
            # Через таймер: обработчик почти наверняка позовёт append, а тот —
            # снова раскладку. Прямой вызов уходил бы вглубь на восемь витков.
            self._asking = True
            QTimer.singleShot(0, self._ask_more)

    def _ask_more(self) -> None:
        self._asking = False
        self.wants_more.emit()

    def _wire(self, card: FilmCard) -> None:
        """Один раз на карточку. Номер строки читается из свойства: оно
        переписывается при каждой привязке."""
        card.toggled.connect(
            lambda _=False, c=card: self.toggle_row(c.property("row"))
        )
        card.score_picked.connect(
            lambda scale, score, c=card:
                self.score_picked.emit(c.property("row"), scale, score)
        )

    def _mount(self, row: FeedRow, index: int, width: int) -> None:
        if row.card is None:
            row.card = self._pool.acquire()
            row.card.setParent(self._content)
        row.card.setProperty("row", index)
        row.card.setFixedWidth(width)
        row.card.bind(row.view, collapsed=row.collapsed)
        row.card.adjustSize()
        row.card.move(0, row.top)
        row.card.show()

        if index not in self._asked:
            self._asked.add(index)
            self.poster_wanted.emit(index)
            self.row_shown.emit(index)

    def _release(self, row: FeedRow) -> None:
        if row.card is not None:
            index = row.card.property("row")
            if index is not None:
                # Карточку заберут под чужие данные, и начатая загрузка
                # постера этой строке больше не нужна. Вернёмся — попросим
                # заново.
                self._asked.discard(index)
            self._pool.release(row.card)
            row.card = None
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_feed_pool.py -v`
Ожидается: PASS, восемнадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/feed.py tests/client/test_feed_pool.py
git commit -m "feat: лента с пулом карточек и распорками"
```

---

### Задача 15: Шапка и её замеры

Три капсулы в ряд — и три числа, которые считаются замером, а не пишутся
константами.

**Ширину боковых блоков задаёт переключатель.** Поиск и ряд кнопок равны ему по
ширине, а его собственную задаёт самая длинная подпись. Поэтому не число в
метриках, а замер.

**По полосе от левого края поиска до правого края кнопок равняются лента и
гистограмма.** В макете это `--content-w`, и от него зависит, стоят ли карточки
вровень с шапкой.

**Минимум ширины окна тоже замер:** три блока по ширине переключателя, два
зазора между ними и отступы по краям. Считается **после готовности шрифтов** —
до них подписи меряются не тем начертанием.

**Файлы:**
- Создать: `client/widgets/topbar.py`
- Изменить: `client/window.py`
- Создать: `tests/client/test_topbar.py`

**Интерфейсы:**
- Потребляет: `SearchField`, `KindSwitch`, `Toolbar`, `metrics`.
- Отдаёт: `TopBar(QWidget)` с полями `search`, `kinds`, `tools`, сигналом
  `metrics_changed(int, int)` — ширина содержимого и минимальная ширина окна —
  и методом `remeasure()`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_topbar.py`:

```python
from backend.model import Kind
from client.theme import metrics
from client.widgets.topbar import TopBar


def shown(qtbot, width: int = 1200) -> TopBar:
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.resize(width, metrics.PILL_H + 28)
    bar.show()
    qtbot.waitExposed(bar)
    bar.remeasure()
    return bar


def test_all_three_blocks_are_there(qtbot, theme):
    bar = shown(qtbot)

    assert bar.search is not None
    assert bar.kinds is not None
    assert bar.tools is not None


def test_the_sides_are_as_wide_as_the_switch(qtbot, theme):
    """Ширину задаёт самая длинная подпись переключателя — отсюда замер, а не
    число в метриках."""
    bar = shown(qtbot)

    assert bar.search.width() == bar.kinds.width()
    assert bar.tools.width() == bar.kinds.width()


def test_the_switch_stays_in_the_middle_of_the_window(qtbot, theme):
    """Переключатель держится центра независимо от того, насколько длинное
    имя справа."""
    bar = shown(qtbot, width=1400)

    centre = bar.kinds.x() + bar.kinds.width() / 2
    assert abs(centre - bar.width() / 2) < 2


def test_the_content_width_spans_from_search_to_tools(qtbot, theme):
    """По этой полосе равняются лента и гистограмма."""
    heard = []
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.metrics_changed.connect(lambda content, floor: heard.append(content))
    bar.resize(1200, metrics.PILL_H + 28)
    bar.show()
    qtbot.waitExposed(bar)
    bar.remeasure()

    expected = bar.tools.x() + bar.tools.width() - bar.search.x()
    assert heard and heard[-1] == expected


def test_the_floor_holds_three_blocks_and_the_gaps(qtbot, theme):
    heard = []
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.metrics_changed.connect(lambda content, floor: heard.append(floor))
    bar.resize(1200, metrics.PILL_H + 28)
    bar.show()
    qtbot.waitExposed(bar)
    bar.remeasure()

    expected = (bar.kinds.width() * 3
                + metrics.TOPBAR_GAP * 2 + metrics.CORNER * 2)
    assert heard and heard[-1] == expected


def test_a_wider_window_does_not_widen_the_blocks(qtbot, theme):
    """Капсулы держат свою ширину; расходятся только промежутки."""
    bar = shown(qtbot, width=900)
    narrow = bar.kinds.width()

    bar.resize(1600, bar.height())
    bar.remeasure()

    assert bar.kinds.width() == narrow


def test_the_kind_reaches_the_tools(qtbot, theme):
    """Отложенное для игр называется иначе, и шапка это связывает сама."""
    bar = shown(qtbot)

    bar.kinds.set_kind(Kind.GAME)
    bar.on_kind_changed(Kind.GAME)

    from client.widgets.toolbar import View

    assert bar.tools.view_button(View.WISHLIST).toolTip() == "Хочу поиграть"
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_topbar.py -v`
Ожидается: FAIL — `No module named 'client.widgets.topbar'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/topbar.py`:

```python
"""Шапка: три капсулы в ряд и три числа, считаемые замером.

Числа не в метриках нарочно: ширину переключателя задаёт самая длинная
подпись, а её знает только шрифт."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from backend.model import Kind
from client.theme import metrics
from client.widgets.search import SearchField
from client.widgets.segmented import KindSwitch
from client.widgets.toolbar import Toolbar


class TopBar(QWidget):
    metrics_changed = Signal(int, int)   # ширина содержимого, минимум окна

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.search = SearchField(self)
        self.kinds = KindSwitch(self)
        self.tools = Toolbar(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(metrics.CORNER, 14, metrics.CORNER, 14)
        layout.setSpacing(metrics.TOPBAR_GAP)
        layout.addStretch(1)
        layout.addWidget(self.search)
        layout.addWidget(self.kinds)
        layout.addWidget(self.tools)
        layout.addStretch(1)

        self.kinds.changed.connect(self.on_kind_changed)

        # Первый замер откладывается на круг цикла: шрифт приезжает позже
        # разметки, а от него зависит ширина подписей.
        self._schedule_remeasure()

    def on_kind_changed(self, kind: Kind) -> None:
        self.tools.set_kind(kind)

    def remeasure(self) -> None:
        """Боковые блоки равны переключателю, полоса содержимого — от левого
        края поиска до правого края кнопок, минимум окна — три блока, два
        зазора и отступы."""
        # Сторона — максимум из трёх, а не ширина одного переключателя. Ряду
        # кнопок нужно место под девять круглых кнопок с промежутками; окажись
        # переключатель уже, Qt сожмёт шаг, и кнопки налезут друг на друга —
        # молча, без всякой ошибки, а последняя вылезет за капсулу.
        side = max(
            self.kinds.sizeHint().width(),
            self.tools.minimumSizeHint().width(),
            self.search.minimumSizeHint().width(),
        )
        self.search.setFixedWidth(side)
        self.tools.setFixedWidth(side)

        # Раскладку надо заставить пересчитаться до чтения координат:
        # setFixedWidth сам по себе её не двигает, и x() у детей остались бы от
        # прошлого прохода. Полоса содержимого уехала бы на десяток пикселей —
        # и тест, читающий те же координаты в тот же момент, этого не заметил
        # бы.
        self.layout().activate()

        content = self.tools.x() + self.tools.width() - self.search.x()
        floor = side * 3 + metrics.TOPBAR_GAP * 2 + metrics.CORNER * 2
        self.metrics_changed.emit(content, floor)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.remeasure()

    def _schedule_remeasure(self) -> None:
        from PySide6.QtCore import QTimer

        # Первый замер — следующим кругом цикла: до показа геометрия детей
        # ещё не посчитана, и полоса содержимого вышла бы нулевой.
        QTimer.singleShot(0, self, self.remeasure)
```

**У отложенного вызова обязателен владелец** — второй аргумент `singleShot`.
Без него таймер переживёт виджет, который его завёл, и выстрелит в удалённый
объект: `RuntimeError: Signal source has been deleted`. В прогоне это вылезает
не там, где ошибка: тесты зелены поодиночке и красны в пачке, потому что окно
успевает собраться сборщиком мусора между ними. Правило общее — оно же касается
столбцов гистограммы и любого таймера в модалках.

- [ ] **Шаг 4: Связать с окном**

Дописать в `MainWindow.__init__` (`client/window.py`): шапка кладётся первой в
раскладку `root`, а её замеры уходят в окно:

```python
        self.topbar = TopBar(self.root)
        self.topbar.metrics_changed.connect(self._apply_metrics)
```

```python
    def _apply_metrics(self, content: int, floor: int) -> None:
        """Ширина содержимого — лента и гистограмма равняются по шапке;
        минимум окна — чтобы капсулы не налезали друг на друга."""
        self.content_width = content
        self.setMinimumWidth(max(metrics.MIN_W, floor))
        for page in self._pages.values():
            if hasattr(page, "set_content_width"):
                page.set_content_width(content)
```

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_topbar.py tests/client/test_window.py -v`
Ожидается: PASS, двенадцать тестов.

- [ ] **Шаг 6: Коммит**

```bash
git add client/widgets/topbar.py client/window.py tests/client/test_topbar.py
git commit -m "feat: шапка и её замеры — ширина содержимого и минимум окна"
```

---

### Задача 16: Страницы, переход и запуск

Последняя задача плана: три раздела на одной ленте, статистика заглушкой,
переход проявлением и `main.py`, который всё это поднимает.

**Переход между страницами — проявление за 0.16 с.** Старая исчезает сразу,
новая проявляется из прозрачности. Это и есть «нативный переход»: страницы
лежат в стопке, никакой навигации по ссылкам.

**Здесь же закрываются два долга плана 1:** `load_dotenv()` и логирование в
файл, 5 МБ на файл и три файла по кругу.

**Файлы:**
- Создать: `client/pages/feed.py`, `client/pages/stats.py`,
  `client/widgets/snack.py`
- Изменить: `client/window.py`
- Создать: `main.py`
- Создать: `tests/client/test_pages.py`

**Интерфейсы:**
- Потребляет: всё, что построено задачами 1–15; `build_backend`, `load_config`,
  `upgrade` из плана 1; `merge_results` из `backend.model`.
- Отдаёт: `FeedPage(QWidget)` с `show_section`, `search`, `receive`, `leave`,
  `calls`, `request_id`, `feed`, `order` и сигналом `trouble(str)`;
  `StatsPage(QWidget)` — заглушка под гистограмму, наполняет план 6;
  `Snack(QLabel)` с `show_text(str)`;
  `MainWindow.show_page(name)`, `on_kind_changed`, `on_view_changed`, `filters`;
  `main()` в `main.py`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_pages.py`:

```python
from PySide6.QtCore import QAbstractAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect

from backend.model import CardView, Filters, Kind, Order, Section, Sort, Source
from backend.model import ExternalSearch
from client.pages.feed import FeedPage
from client.widgets.toolbar import View
from client.window import MainWindow
# Двойники объявлены классами, а не фикстурами: классы из conftest в модуль
# теста сами не подставляются, их надо импортировать.
from tests.client.conftest import FakeRuntime


def ready() -> FakeRuntime:
    """Рантайм с заготовленными ответами на всё, что страница спрашивает.

    Пустой FakeRuntime отдаёт None на любой запрос, а страница делает
    `list(views)` — шесть тестов падали бы на TypeError, не дойдя до своих
    утверждений."""
    return FakeRuntime({
        "feed.page": [],
        "search.local": [],
        "search.external": ExternalSearch(),
    })


def views(count: int):
    return [CardView(item_id=n, kind=Kind.MOVIE, source=Source.TMDB,
                     source_id=str(n), title=f"Фильм {n}")
            for n in range(count)]


def test_the_page_asks_for_what_it_was_told(qtbot, theme):
    """Единица в счётчике вызовов ничего не значит: она гарантирована тем, что
    вызов один и безусловный. Смотрим, о чём именно просят."""
    runtime = ready()
    page = FeedPage(runtime)
    qtbot.addWidget(page)
    filters = Filters(tag_ids=(3,))

    page.show_section(Section.WISHLIST, Kind.GAME, filters,
                      Order(Sort.ADDED_AT))

    name, args, _ = runtime.asked[0]
    assert name == "feed.page"
    assert args[:4] == (Section.WISHLIST, Kind.GAME, filters,
                        Order(Sort.ADDED_AT))


def test_a_candidate_in_sight_is_turned_into_a_card(qtbot, theme):
    """Второй круг загрузки. Без этого вызова найденное в поиске остаётся
    кандидатом с пустым `item_id`, а оценка, закладка и теги ходят по нему —
    то есть найденное нельзя ни оценить, ни отложить."""
    candidate = CardView(item_id=None, kind=Kind.MOVIE, source=Source.TMDB,
                         source_id="157336", title="Интерстеллар")
    runtime = ready()
    runtime.answers["loader.ensure"] = 7
    runtime.answers["feed.views_of"] = [
        CardView(item_id=7, kind=Kind.MOVIE, source=Source.TMDB,
                 source_id="157336", title="Интерстеллар")
    ]
    page = FeedPage(runtime)
    qtbot.addWidget(page)
    page.feed.set_rows([candidate])

    page._row_shown(0)
    qtbot.wait(30)

    assert any(name == "loader.ensure" for name, _, _ in runtime.asked)
    assert page.feed.rows[0].view.item_id == 7


def test_a_card_in_sight_asks_for_the_aggregate_scores(qtbot, theme):
    """Третий круг. Второе из трёх состояний `external_rating` производит
    только он: не позвать его — значит не получить чужих оценок никогда."""
    runtime = ready()
    runtime.answers["enricher.enrich"] = []
    page = FeedPage(runtime)
    qtbot.addWidget(page)
    page.feed.set_rows(views(1))

    page._row_shown(0)
    qtbot.wait(30)

    asked = [(name, args) for name, args, _ in runtime.asked]
    assert ("enricher.enrich", (0, Kind.MOVIE)) in asked


def test_a_search_asks_its_own_base_first_and_the_outside_too(qtbot, theme):
    """Своё показывается сразу, внешнее доливается по готовности."""
    runtime = ready()
    page = FeedPage(runtime)
    qtbot.addWidget(page)

    page.search("андор")

    names = [name for name, _, _ in runtime.asked]
    assert names == ["search.local", "search.external"]


def test_leaving_the_page_cancels_what_it_started(qtbot, theme):
    """Ушли со страницы — её задачи оборваны, а не досчитываются в пустоту."""
    runtime = ready()
    page = FeedPage(runtime)
    qtbot.addWidget(page)
    page.show_section(Section.RATED, Kind.MOVIE, Filters(), Order(Sort.SCORE))

    page.leave()

    assert runtime.calls
    assert all(call.cancelled for call in runtime.calls)


def test_a_stale_answer_does_not_overwrite_a_fresh_one(qtbot, theme):
    """У поиска свой номер запроса: набрал новое, пока летело старое — старое
    не должно затирать новое."""
    runtime = ready()
    page = FeedPage(runtime)
    qtbot.addWidget(page)

    page.search("интер")
    stale = page.request_id
    page.search("андор")

    page.receive(page.request_id, views(3))
    page.receive(stale, views(7))
    qtbot.wait(30)

    assert len(page.feed.rows) == 3


def test_a_refusal_of_the_outside_reaches_the_snack(qtbot, theme):
    """Без внешней базы человек не получит того, что искал, и должен понимать
    причину. Пустая выдача — не событие, отказ — событие."""
    from backend.model import Reason, Refusal

    runtime = ready()
    page = FeedPage(runtime)
    qtbot.addWidget(page)
    heard = []
    page.trouble.connect(heard.append)

    page.search("андор")
    page._got_external(page.request_id, ExternalSearch(
        views=(), refusals=(Refusal(source="tmdb", reason=Reason.NETWORK),)
    ))

    assert heard and "недоступна" in heard[0]


def test_an_empty_answer_of_the_outside_is_quiet(qtbot, theme):
    """Внешняя база ответила и ничего не нашла — сообщать не о чем."""

    runtime = ready()
    page = FeedPage(runtime)
    qtbot.addWidget(page)
    heard = []
    page.trouble.connect(heard.append)

    page.search("ничего такого")
    page._got_external(page.request_id, ExternalSearch())

    assert heard == []


def test_the_transition_fades_the_new_page_in(qtbot, theme):
    """Проверяем, что анимация правда идёт по этой странице.

    Сверять `duration()` с числом мало: это константа против своей же копии.
    А `QGraphicsOpacityEffect` рождается с `opacity == 1.0`, поэтому и
    проверка «в конце видно» зелена у реализации, которая анимацию вообще не
    запускала. Убери из `show_page` три последние строки — и решение
    «переходы проявлением за 0.16 с» исчезнет молча."""
    window = MainWindow(runtime=ready())
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    window.show_page("stats")

    effect = window.pages.currentWidget().graphicsEffect()
    assert isinstance(effect, QGraphicsOpacityEffect)
    assert window.fade.targetObject() is effect
    assert window.fade.state() == QAbstractAnimation.State.Running
    # start() сразу выставляет начальное значение: страница появляется из
    # прозрачности, а не готовой.
    assert effect.opacity() < 1.0


def test_the_transition_ends_fully_visible(qtbot, theme):
    window = MainWindow(runtime=ready())
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    with qtbot.waitSignal(window.fade.finished, timeout=2000):
        window.show_page("stats")

    assert window.pages.currentWidget().graphicsEffect().opacity() == 1.0


def test_switching_the_kind_clears_the_filters(qtbot, theme):
    """Наборы тегов у трёх типов независимы: фильтр по тегу после смены
    указывал бы на строки, которых в новом наборе нет вовсе."""
    window = MainWindow(runtime=ready())
    qtbot.addWidget(window)
    window.filters = Filters(tag_ids=(1,), excluded_genre_ids=(2,))

    window.on_kind_changed(Kind.GAME)

    assert window.filters == Filters()


def test_switching_the_section_keeps_the_filters(qtbot, theme):
    """Иначе отфильтрованную гистограмму не увидеть никогда."""
    window = MainWindow(runtime=ready())
    qtbot.addWidget(window)
    window.filters = Filters(tag_ids=(1,))

    window.on_view_changed(View.WISHLIST)

    assert window.filters == Filters(tag_ids=(1,))


def test_the_statistics_shows_instead_of_the_feed(qtbot, theme):
    """Такой же раздел, как остальные, просто вместо карточек гистограмма."""
    window = MainWindow(runtime=ready())
    qtbot.addWidget(window)

    window.on_view_changed(View.STATS)

    assert window.pages.currentWidget() is window._pages["stats"]

    window.on_view_changed(None)

    assert window.pages.currentWidget() is window._pages["list"]
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_pages.py -v`
Ожидается: FAIL — `No module named 'client.pages.feed'`.

- [ ] **Шаг 3: Страница ленты**

Создать `client/pages/feed.py`:

```python
"""Одна лента на поиск, оценённые и отложенные.

Страница тонкая: она знает, что спросить и в каком порядке, и больше ничего.
Виджет ленты и карточка о разделах не знают."""

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from backend.model import Filters, Kind, Order, Section, merge_results
from client.runtime import Calls
from client.widgets.feed import FeedView

logger = logging.getLogger(__name__)


class FeedPage(QWidget):
    """Свои задачи обрывает при уходе; ответ с устаревшим номером
    отбрасывает."""

    trouble = Signal(str)

    def __init__(self, runtime, parent=None) -> None:
        super().__init__(parent)
        self._runtime = runtime
        self.calls = Calls()

        self.feed = FeedView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.feed)

        self.order: Order | None = None
        self.request_id = 0
        self._kind = Kind.MOVIE
        self._query = ""
        self._local: list = []

        self.feed.poster_wanted.connect(self._want_poster)
        self.feed.row_shown.connect(self._row_shown)
        self.feed.wants_more.connect(self._want_more)

    def leave(self) -> None:
        """Ушли со страницы — её задачи оборваны, а не досчитываются в
        пустоту."""
        self.calls.cancel_all()

    def set_content_width(self, width: int) -> None:
        self.feed.setMaximumWidth(width)

    # ─── что спрашиваем ──────────────────────────────────────────────

    def show_section(self, section: Section, kind: Kind, filters: Filters,
                     order: Order) -> None:
        self.leave()
        self._kind, self.order, self._query = kind, order, ""
        token = self._next_token()

        self._ask(
            lambda backend: backend.feed.page(section, kind, filters, order),
            lambda views: self.receive(token, list(views)),
        )

    def search(self, query: str) -> None:
        """Своё показывается сразу, внешнее доливается по готовности:
        локальная база отвечает за миллисекунды, внешняя — за доли секунды."""
        self.leave()
        self._query = query
        self._local = []
        kind = self._kind
        token = self._next_token()

        self._ask(
            lambda backend: backend.search.local(kind, query),
            lambda views: self._got_local(token, list(views)),
        )
        self._ask(
            lambda backend: backend.search.external(kind, query),
            lambda answer: self._got_external(token, answer),
        )

    # ─── что делаем с ответом ────────────────────────────────────────

    def receive(self, token: int, views: list) -> None:
        """Номер запроса вместо погони за отменой уже отправленного: набрал
        новое, пока летело старое, — старое не затирает новое."""
        if token != self.request_id:
            return
        self.feed.set_rows(views)

    def _got_local(self, token: int, views: list) -> None:
        if token != self.request_id:
            return
        self._local = views
        self.feed.set_rows(views)

    def _got_external(self, token: int, answer) -> None:
        if token != self.request_id:
            return
        self.feed.set_rows(merge_results(self._local, list(answer.views)))
        if answer.refusals:
            # Без внешней базы человек не получит того, что искал, и должен
            # понимать причину. Отсутствующая оценка агрегатора — другое дело.
            self.trouble.emit("Внешняя база недоступна — показано только своё")

    # ─── по требованию ленты ─────────────────────────────────────────

    def _want_poster(self, index: int) -> None:
        row = self.feed.rows[index]
        view = row.view
        self._ask(
            lambda backend: backend.posters.poster_for(
                view.item_id, view.source, view.poster_url, _now()
            ),
            lambda data, i=index: self._got_poster(i, data),
        )

    def _got_poster(self, index: int, data) -> None:
        row = self.feed.rows[index] if index < len(self.feed.rows) else None
        # Карточку могли переиспользовать, пока постер ехал: результат пришёл
        # бы в неё уже с чужими данными.
        if row is None or row.card is None or not isinstance(data, bytes):
            return
        row.card.set_poster(data)

    def _row_shown(self, index: int) -> None:
        """Второй и третий круги загрузки — здесь, и больше нигде.

        План 4 их построил и вызов отдал сюда: без этого кандидат из выдачи
        никогда не станет карточкой (а значит, его нельзя ни оценить, ни
        отложить), оценки агрегаторов не приедут никогда, и число серий у
        растущего сериала останется тем, каким приехало в день добавления."""
        view = self.feed.rows[index].view

        if view.item_id is None:
            # Кандидат выдачи. Загрузка пишет его в базу и отдаёт номер строки.
            self._ask(
                lambda backend: backend.loader.ensure(view),
                lambda item_id, i=index: self._got_item(i, item_id),
            )
            return

        self._enrich(index, view.item_id, view.kind)

    def _got_item(self, index: int, item_id) -> None:
        """Кандидат стал карточкой. Перечитываем строку целиком: у неё теперь
        есть `item_id`, а с ним — оценка, теги и закладка."""
        if not isinstance(item_id, int):
            # Отказ источника: карточки не будет, кандидат остаётся кандидатом.
            return
        self._ask(
            lambda backend: backend.feed.views_of([item_id]),
            lambda found, i=index: self._rebind(i, found[0] if found else None),
        )

    def _rebind(self, index: int, view) -> None:
        row = self.feed.rows[index] if index < len(self.feed.rows) else None
        if row is None or view is None or row.view.source_id != view.source_id:
            # Карточку переиспользовали, пока ответ ехал.
            return
        self.feed.replace_row(index, view)
        self._enrich(index, view.item_id, view.kind)

    def _enrich(self, index: int, item_id: int, kind: Kind) -> None:
        """Третий круг и перезапрос счётчиков. Оба идут только по видимому и
        оба сами решают по срокам годности, надо ли вообще ходить в сеть."""
        self._ask(
            lambda backend: backend.enricher.enrich(item_id, kind),
            lambda ratings, i=index: self._got_ratings(i, ratings),
        )
        if kind is Kind.SERIES:
            self._ask(
                lambda backend: backend.loader.refresh(item_id),
                lambda _: None,
            )

    def _got_ratings(self, index: int, ratings) -> None:
        """Приехавшее проявляется в уже нарисованной карточке: кольца на местах
        неприехавших оценок заменяются числами."""
        row = self.feed.rows[index] if index < len(self.feed.rows) else None
        if row is None or row.card is None:
            return
        row.view = replace(row.view, external=tuple(ratings), waiting=())
        row.card.aggregates.bind(row.view.external, waiting=())

    def _want_more(self) -> None:
        if self._query:
            # У внешнего поиска порции нет: клиенты плана 2 номера страницы не
            # принимают. См. открытые вопросы плана 4.
            return
        # Всё, что нужно запросу, снимается здесь, в главном потоке. Лямбда
        # уезжает в чужой поток, и читать в ней self.feed.rows или self.order
        # значит трогать виджет оттуда — ровно то, от чего огорожена граница.
        section, kind = self._section, self._kind
        filters, order = self._filters, self.order
        offset = len(self.feed.rows)
        self._ask(
            lambda backend: backend.feed.page(section, kind, filters, order,
                                              offset=offset),
            lambda views: self.feed.append(list(views)),
        )

    # ─── общее ───────────────────────────────────────────────────────

    def _next_token(self) -> int:
        self.request_id += 1
        return self.request_id

    def _ask(self, work, on_done) -> None:
        call = self._runtime.call(work)
        call.done.connect(on_done)
        call.failed.connect(self._blame)
        self.calls.add(call)

    def _blame(self, error: Exception) -> None:
        # Непредвиденный сбой показывается той же плашкой и пишется в лог.
        # Рантайм уже записал; здесь только показ.
        self.trouble.emit("Что-то пошло не так")
```

Три заготовки в этом коде нужно свести с окружением, и все три видны сразу:
`_now()` — это `datetime.now()`, добавить импорт; `replace` — из `dataclasses`;
`self._section` и `self._filters` — запомнить их в `show_section` рядом с
`self._kind`, иначе догрузка следующей порции спрашивать нечем.

**Про `_row_shown` — почему второй и третий круги висят именно здесь.** План 4
построил `Loader.ensure`, `Loader.refresh` и `Enricher.enrich` и вызов отдал
клиенту: только он знает, что видно на экране. Пока их никто не звал, из двух
путей наполнения библиотеки — найти во внешней базе или завести руками —
работал лишь второй: у кандидата выдачи `item_id` пуст, а оценка, закладка и
теги ходят по нему.

Создать `client/pages/stats.py` заглушкой: `StatsPage(runtime, parent=None)` с
полем `histogram` и методами `set_content_width` и `show_for(kind, filters)`,
которые план 6 наполнит столбцами и подвалом. Подпись задаётся уже здесь, чтобы
плану 6 не пришлось её менять: рантайм первым аргументом, как у `FeedPage`.
Заглушка нужна уже сейчас — кнопка статистики в шапке есть, и нажатие не должно
упираться в пустоту.

- [ ] **Шаг 4: Плашка сообщений**

**Плашка — не модалка, и в план 6 её отложить нельзя.** Она живёт в корне окна
поверх всего, и без неё офлайновый поиск молча покажет обрезанную выдачу: отказ
источника приезжает полем в результате и в лог не попадает вовсе.

Создать `client/widgets/snack.py`: `Snack(QLabel)` поверх содержимого,
выезжает снизу по `show_text(str)`, держится четыре секунды и уезжает.
Движение — `QPropertyAnimation` по `pos`, 220 мс; повторный вызов до истечения
срока перезапускает таймер, а не ставит вторую плашку. Мышь сквозь неё не
проходит: по ней можно попасть, но и закрывать её нажатием не нужно.

`MainWindow` держит одну на всё приложение и подключает к ней `trouble`
страниц и `broken` рантайма.

- [ ] **Шаг 5: Стопка страниц и переход**

Дописать в шапку `client/window.py`:

```python
from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from backend.model import Filters, Kind, Section
from client.pages.feed import FeedPage
from client.pages.stats import StatsPage
from client.widgets.snack import Snack
from client.widgets.toolbar import SECTIONS, View
from client.widgets.topbar import TopBar
```

и в класс:

```python
    def _build_pages(self) -> None:
        """Три раздела — одна и та же лента с разным содержимым; статистика
        показывается вместо неё, а не рядом."""
        self.pages = QStackedWidget(self.root)
        self.filters = Filters()
        self._section: Section | None = None

        # Обе страницы получают рантайм первым аргументом: статистика ходит
        # за гистограммой сама, и подпись у них одна.
        self._pages = {
            "list": FeedPage(self._runtime, self.pages),
            "stats": StatsPage(self._runtime, self.pages),
        }
        for page in self._pages.values():
            self.pages.addWidget(page)

        self.fade = QPropertyAnimation(self)
        self.fade.setDuration(160)          # ровно столько же, сколько в макете
        # В CSS это ease-out; ближайшая кривая Qt — OutQuad, а не OutCubic.
        self.fade.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.fade.setStartValue(0.0)
        self.fade.setEndValue(1.0)

        self._pages["list"].trouble.connect(self.snack.show_text)
        self.topbar.tools.view_changed.connect(self.on_view_changed)
        self.topbar.kinds.changed.connect(self.on_kind_changed)
        self.topbar.search.submitted.connect(self._pages["list"].search)

    def show_page(self, name: str) -> None:
        """Старая исчезает сразу, новая проявляется. Это и есть нативный
        переход: страницы в стопке, никакой навигации по ссылкам."""
        page = self._pages[name]
        effect = page.graphicsEffect()
        if effect is None:
            effect = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(effect)

        self.pages.setCurrentWidget(page)
        self.fade.stop()
        self.fade.setTargetObject(effect)
        self.fade.setPropertyName(b"opacity")
        self.fade.start()

    def on_kind_changed(self, kind: Kind) -> None:
        """Смена типа сбрасывает все фильтры: наборы тегов у трёх типов
        независимы, и фильтр по тегу указывал бы на строки, которых в новом
        наборе нет вовсе."""
        self.filters = Filters()
        self._kind = kind
        self._refresh()

    def on_view_changed(self, view: View | None) -> None:
        """Разделы фильтры не трогают: иначе отфильтрованную гистограмму не
        увидеть никогда."""
        if view is View.STATS:
            self.show_page("stats")
            return
        self._section = SECTIONS.get(view) if view is not None else None
        self.show_page("list")
        self._refresh()

    def _refresh(self) -> None:
        page = self._pages["list"]
        if self._section is None:
            return          # обычный список — то, что уже показано
        page.show_section(self._section, self._kind, self.filters,
                          self.topbar.tools.order)
```

`_build_pages()` зовётся из `__init__` после того, как созданы `self.root`,
`self.topbar` и `self.snack`; `self._kind` заводится там же со значением
`Kind.MOVIE`.

- [ ] **Шаг 6: Запуск**

Создать `main.py`:

```python
"""Собирает зависимости и поднимает окно."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

from alembic import command
from alembic.config import Config as AlembicConfig

from backend.app import build_backend
from backend.config import load_config
from client.runtime import Runtime
from client.theme import apply_theme
from client.window import MainWindow

BASE = Path(__file__).resolve().parent


def setup_logging(config) -> None:
    """Лог лежит рядом с программой и не растёт бесконечно: 5 МБ на файл,
    три файла по кругу."""
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        config.log_file, maxBytes=5 * 1024 * 1024, backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    logging.basicConfig(level=config.log_level, handlers=[handler])


def upgrade(config) -> None:
    """Схему поднимают миграции, а не build_backend — он этого не делает
    намеренно. Без этого на чистой машине первый же запрос даёт «no such
    table: item», а справочник жанров остаётся пустым.

    Зовём Alembic напрямую, а не отдельным процессом: в собранном
    исполняемом файле `python -m alembic` взять неоткуда."""
    config.data_dir.mkdir(parents=True, exist_ok=True)
    alembic = AlembicConfig(str(BASE / "alembic.ini"))
    alembic.set_main_option("script_location", str(BASE / "migrations"))
    # env.py плана 1 берёт путь из -x db=…; программно это cmd_opts.x, и
    # другого способа его туда положить у Alembic нет.
    alembic.cmd_opts = SimpleNamespace(x=[f"db={config.library_db}"])
    command.upgrade(alembic, "head")


async def prepare(config):
    """Готовит и поднимает бэкенд в его же потоке: миграции ходят к диску,
    и главному потоку их ждать нельзя."""
    upgrade(config)
    return await build_backend(config)


def main() -> int:
    import os

    # Ключи живут в .env, и читает его ровно одно место.
    load_dotenv(BASE / ".env")
    config = load_config(os.environ, base_dir=BASE)
    setup_logging(config)

    app = QApplication(sys.argv)
    apply_theme(app)

    runtime = Runtime(lambda: prepare(config))
    window = MainWindow(runtime)

    # start() возвращается сразу; окно показывается, не дожидаясь баз.
    runtime.start()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Шаг 7: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_pages.py -v`
Ожидается: PASS, девять тестов.

- [ ] **Шаг 8: Прогнать всё целиком и посмотреть глазами**

Запустить: `pipenv run pytest -v`
Ожидается: PASS, весь набор планов 1–5.

Запустить: `pipenv run python main.py`
Ожидается: окно открывается на поиске, лента пуста, поиск по Enter приносит
кандидатов, оценка ставится и переживает перезапуск.

**Это первый раз, когда приложение видно глазами.** То, что тестами не
покрывается — цвета, отступы, вид кромки, — проверяется здесь и правится в
`client/theme/`.

- [ ] **Шаг 9: Коммит**

```bash
git add client/pages client/widgets/snack.py client/window.py main.py         tests/client/test_pages.py
git commit -m "feat: страницы, плашка, переход проявлением и запуск"
```

---

## Что этот план сознательно не делает

| Что | Куда |
|---|---|
| Модалки фильтров: жанры, теги, оценки | план 6 |
| Модалка тегов карточки и перетаскивание строк | план 6 |
| Окно создания и правки, поле с подсказкой | план 6 |
| Гистограмма: столбцы, подвал, анимация роста | план 6: здесь только заглушка страницы |
| Своя полоса прокрутки | план 6: она нужна модалкам, а лента обходится системной |
| Кнопка «… ещё» у синопсиса и у состава | план 6: в макете она и сама заглушка — «появляется только когда содержимое не поместилось; здесь показана всегда, для примера» |
| Удаление карточки с подтверждением | план 6: подтверждение — это модалка |
| Рекомендации | отложено спекой модели данных |

## Числа и правила, взятые не из спек

Решения этого плана. Ни одно ниоткуда не следует, менять свободно:

| Что | Значение | Почему так |
|---|---|---|
| Гало кромки — градиент, а не размытие | так | `QGraphicsBlurEffect` на каждый кадр дорог, а картинка та же |
| `OVERSCAN` | одна экранная высота | компромисс между рывками при прокрутке и числом живых виджетов |
| `HUNGRY` | полторы экранных высоты | столько же, сколько успевает приехать порция из базы |
| Короткие имена агрегаторов у всех типов | КП, IMDB, TMDB, RT, MC, Steam, GOG | в макете у кино короткие, у игр полные — но данные там рыба, а строка одна и та же |
| `%` у Rotten Tomatoes и Steam, без знака у Metacritic | так | в макете именно так; Metascore — просто число |
| Шкала GOG — стобалльная | так | живьём не проверена, см. открытые вопросы |
| Первые пять актёров, остальные под «… ещё» | 5 | «топ-5 актёров» назван в модели данных как повод для `position` |
| Порядок строк состава | режиссёр, шоураннер, разработчик, издатель, актёры | сначала кто сделал, потом кто играл; спека молчит |
| Номер строки карточка носит свойством | так | иначе связи копятся при каждом переиспользовании |
| `-1` как «шкала одна» в `score_picked` | так | у кино шкала одна и номера у неё нет |
| Кривая перехода | `OutQuad` | в макете `ease-out`; `OutCubic` заметно резче, `OutQuad` ближе. Длительность 160 мс — из макета |
| `waiting` считает страница, а не база | так | «ещё едет» — состояние клиента: база знает только три состояния строки `external_rating` |
| Запуск задачи откладывается на круг цикла | `QTimer.singleShot(0, …)` | без этого быстрая задача успевает испустить сигнал раньше, чем позвавший подключился, и ответ теряется молча. Проверено прогоном: терялось восемь из двадцати |
| Заголовок карточки в свёрнутом виде | `BODY_L` вместо `TITLE_L` | из макета |

## Открытые вопросы

**Ось `FILL` — вопрос закрыт прогоном.** В PySide6 6.11.1 (Qt 6.11.1)
`QFont.setVariableAxis` и `QFont.Tag` есть, и два начертания получаются разными
объектами. Запасной путь с двумя статическими файлами не нужен; ветка под него
в `icons.py` остаётся на случай отката версии, но скачивать второй файл не
надо. Скрипт `scripts/probe_fill_axis.py` сохраняется — он и есть запись
проверки.

**Чего он не доказывает:** одинаковая ширина глифа у контура и заливки ничего
не говорит о том, что рисунок разный. Настоящую проверку делает тест задачи 4,
сравнивая две отрисованные картинки.

**Шкала оценки GOG.** В `external_rating` значение лежит как пришло, а здесь
оно приводится к десяти ступеням — и для этого нужна её верхняя граница. У GOG
она живьём не проверена: план 2 брал оценку из `card.ratings[0].value`, не
разбираясь в диапазоне. Пока считаем стобалльной; проверяется первым же живым
запросом.

**Что показывает лента, пока едет первая порция.** Спека говорит, что до
первого запроса лента пуста, но про промежуток между запросом и ответом не
говорит ничего — ни индикатора, ни надписи в макете нет. Сейчас там просто
пусто.

**Ширина содержимого.** В макете её считает замер шапки: полоса от левого края
поиска до правого края кнопок, и по ней равняются лента и гистограмма. В Qt это
`resizeEvent` шапки, отдающий ширину окну. Задача 15 связывает их напрямую;
если окажется, что замер дёргается при первом показе, между ними встанет
однократный `QTimer.singleShot(0, ...)`.

