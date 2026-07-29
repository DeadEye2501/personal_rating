# План 6. Модалки и статистика

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** доделать приложение. Четыре модалки на общем каркасе, окно создания и
правки карточки, удаление с подтверждением, гистограмма со своим подвалом. После
этого плана работают все три главные задачи: ставить оценки, смотреть их с
фильтрами и вести список запланированного.

**Архитектура:** одна `Modal` на все окна — затемнение, стекло, неоновая кромка,
Esc и клик мимо. Поверх неё `RowListModal` со строками из трёхпозиционного
переключателя: жанры, теги, оценки и теги карточки отличаются только тем, что в
строке и сколько у переключателя состояний. Окно карточки стоит особняком: у него
своя раскладка и свои поля.

**Стек:** тот же, что в плане 5. Ни одной новой зависимости.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от планов 1–5.** Бэкенд закончен, каркас клиента собран: тема,
  `runtime.py`, окно со стопкой страниц, шапка, лента с пулом, карточка, плашка.
- **Макет — источник истины.** `docs/design/index.html` и `docs/design/styles/` сделаны
  тщательнее спек; при расхождении прав макет. Исключение одно: **данные в
  макете рыба**, на них не ссылаемся.
- **`client` не импортирует `sqlalchemy`, `httpx` и `PIL`.** Тест из плана 1 это
  стережёт в обе стороны.
- **Всё к бэкенду — через `runtime.call`.** В главном потоке нет ни одного
  обращения к сети или диску; залитая с диска обложка едет в бэкенд байтами, и
  обрезает её он.
- **Цвет объявлен один раз** — в `client/theme/palette.py`. Ни
  шестнадцатеричных значений по виджетам, ни цвета внутри `.qss`.
- **`qtbot.keyClicks` кириллицей не набирать.** Qt гонит символы через
  ASCII-таблицу и роняет **процесс целиком** — `ASSERT` в `qasciikey.cpp`, код
  выхода `0xC0000409`, прогон обрывается без сводки. Русский текст ставится
  `setText`, набор клавишами проверяется латиницей.
- **Подстановка в `.qss` — своя, а не `str.format`.** В QSS фигурные скобки
  заняты телами правил; `substitute` из плана 5 это уже умеет.
- **Тест обязан уметь падать.** Если поломка реализации оставляет тест зелёным,
  это не тест. Сверять состав, а не длину; поведение, а не имя атрибута.
- **Заготовок, которые чинит следующий шаг, не бывает.** Код в задаче пишется
  сразу рабочим.
- **Внешний вид тестами не покрываем.** Проверяем поведение, состояние и
  геометрию.
- **Молча не глотаем ничего.** Пойманное исключение ведёт либо к плашке, либо к
  записи в лог — минимум одно из двух.
- **Байтовые литералы только ASCII.**
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ client/
│  ├─ theme/styles/modals.qss     стили модалок, без единого цвета
│  ├─ widgets/
│  │  ├─ modal.py                 затемнение, стекло, кромка, Esc
│  │  ├─ scrollbar.py             своя полоса прокрутки
│  │  ├─ rowlist.py               строка с переключателем и список строк
│  │  ├─ field.py                 поле ввода с подчёркиванием
│  │  ├─ picker.py                поле с подсказкой и выбранным
│  │  ├─ confirm.py               подтверждение удаления
│  │  └─ more.py                  кнопка «… ещё»
│  ├─ modals/
│  │  ├─ filters.py               жанры, теги, оценки
│  │  ├─ item_tags.py             теги одной карточки
│  │  └─ card_window.py           создание и правка
│  └─ pages/stats.py              гистограмма и подвал
└─ tests/client/
   ├─ test_modal.py               test_scrollbar.py
   ├─ test_rowlist.py             test_filters.py
   ├─ test_item_tags.py           test_picker.py
   ├─ test_card_window.py         test_confirm.py
   ├─ test_more.py                test_stats.py
   └─ test_wiring.py
```

`client/modals/` рядом с `widgets/` и `pages/` — это не виджеты общего
назначения и не страницы: у каждого окна свой сценарий и свой разговор с
бэкендом. `widgets/` остаётся тем, из чего они собраны.

---

### Задача 1: Каркас модалки

Одна на все окна. Затемнение на всё окно приложения, по центру — панель из
тёмного стекла с неоновой нитью по верхней кромке.

**Закрывается тремя способами:** Esc, клик мимо панели, и своей кнопкой, если
она есть. Клик внутри панели не закрывает.

**Размытия под панелью не будет.** В макете это `backdrop-filter: blur(8px)`;
в Qt такого свойства нет, а снимать окно в картинку и размывать на каждое
открытие дорого. Панель остаётся тёмным полупрозрачным стеклом без размытия —
решение записано в «правилах, взятых не из спек», и это первое, на что стоит
посмотреть глазами.

**Файлы:**
- Создать: `client/widgets/modal.py`, `client/theme/styles/modals.qss`
- Изменить: `client/theme/qss.py`
- Создать: `tests/client/test_modal.py`

**Интерфейсы:**
- Потребляет: `palette`, `metrics`, `NeonEdge` из плана 5.
- Отдаёт: `Modal(QWidget)` — накладка на всё окно с полем `panel`, методами
  `open()`, `dismiss()`, сигналом `closed()`; `Modal.body` — куда класть
  содержимое.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_modal.py`:

```python
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLabel, QWidget

from client.widgets.modal import Modal
from tests.client.conftest import host


def test_a_modal_hides_again_after_it_is_dismissed(qtbot, theme):
    """Стартовую скрытость проверять бесполезно: ребёнок, созданный после
    показа родителя, скрыт и без нашей строки. А вот что окно уходит и
    сообщает об этом — настоящее поведение."""
    modal = Modal(host())
    heard = []
    modal.closed.connect(lambda: heard.append(True))

    modal.open()
    qtbot.wait(30)
    assert not modal.isHidden()

    modal.dismiss()

    assert modal.isHidden()
    assert heard == [True]


def test_opening_covers_the_whole_window(qtbot, theme):
    """Затемнение на всё окно: под ним ничего не должно нажиматься."""
    window = host()
    modal = Modal(window)

    modal.open()
    qtbot.wait(30)

    assert not modal.isHidden()
    assert modal.size() == window.size()


def test_the_panel_sits_in_the_middle(qtbot, theme):
    window = host()
    modal = Modal(window)
    modal.body.layout().addWidget(QLabel("что-нибудь"))

    modal.open()
    qtbot.wait(30)

    centre = modal.panel.x() + modal.panel.width() / 2
    assert abs(centre - modal.width() / 2) < 2


def test_escape_closes(qtbot, theme):
    modal = Modal(host())
    heard = []
    modal.closed.connect(lambda: heard.append(True))
    modal.open()
    qtbot.wait(30)

    qtbot.keyClick(modal, Qt.Key.Key_Escape)

    assert modal.isHidden()
    assert heard == [True]


def test_a_press_inside_the_panel_does_not_leak_upwards(qtbot, theme):
    """QFrame нажатие не принимает и пропускает вверх. Хват за полосу
    прокрутки или за ручку строки не должен закрывать окно."""
    modal = Modal(host())
    modal.open()
    qtbot.wait(30)

    inside = modal.panel.rect().center()
    qtbot.mousePress(modal.panel, Qt.MouseButton.LeftButton, pos=inside)
    qtbot.mouseRelease(modal.panel, Qt.MouseButton.LeftButton, pos=inside)

    assert not modal.isHidden()


def test_a_click_past_the_panel_closes(qtbot, theme):
    modal = Modal(host())
    modal.open()
    qtbot.wait(30)

    qtbot.mouseClick(modal, Qt.MouseButton.LeftButton, pos=QPoint(4, 4))

    assert modal.isHidden()


def test_a_click_inside_the_panel_does_not_close(qtbot, theme):
    """Иначе окно закрывалось бы от промаха мимо строки списка."""
    modal = Modal(host())
    modal.open()
    qtbot.wait(30)

    qtbot.mouseClick(modal.panel, Qt.MouseButton.LeftButton,
                     pos=QPoint(6, 6))

    assert not modal.isHidden()


def test_the_modal_follows_the_window(qtbot, theme):
    """Накладка не в раскладке — размер ей ставит окно."""
    window = host()
    modal = Modal(window)
    modal.open()
    qtbot.wait(30)

    window.resize(1200, 700)
    qtbot.wait(50)

    assert modal.size() == window.size()


def test_closing_twice_is_quiet(qtbot, theme):
    modal = Modal(host())
    heard = []
    modal.closed.connect(lambda: heard.append(True))
    modal.open()

    modal.dismiss()
    modal.dismiss()

    assert heard == [True], "второй раз сигнала быть не должно"
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_modal.py -v`
Ожидается: FAIL — `No module named 'client.widgets.modal'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/modal.py`:

```python
"""Каркас модального окна. Один на все окна приложения.

Затемнение — не отдельное окно, а накладка поверх содержимого: так она едет
вместе с окном, не мигает в панели задач и не теряет фокус при переключении."""

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from client.theme import palette
from client.widgets.neon import NeonEdge

# Цвет объявлен один раз — в палитре; здесь только перевод в QColor. Именно
# `palette.qcolor`, а не `QColor(...)`: конструктор записи `rgba(...)` не
# понимает и молча отдаёт непрозрачный чёрный — вместо затемнения получилась бы
# глухая заливка на всё окно.
DIM = palette.qcolor(palette.OVERLAY_DIM)

# На сколько панель выезжает снизу при появлении. Из макета.
RISE = 8


class Modal(QWidget):
    """Накладка на всё окно с панелью по центру."""

    closed = Signal()

    def __init__(self, parent: QWidget, width: int = 560) -> None:
        super().__init__(parent)
        self.setObjectName("overlay")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.panel = QFrame(self)
        self.panel.setObjectName("modalPanel")
        self.panel.setFixedWidth(width)

        self.body = QWidget(self.panel)
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(24, 22, 24, 18)
        panel_layout.setSpacing(0)
        panel_layout.addWidget(self.body)

        # Кромка живёт внутри панели, с отступом от её краёв, — как в макете:
        # нить не доходит до скруглений.
        self.edge = NeonEdge(palette.PRIMARY, self.panel)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)
        outer.addWidget(self.panel, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addStretch(1)

        self._open = False
        self.hide()
        parent.installEventFilter(self)

        # Появление — два движения, как в макете: затемнение проявляется за
        # 0.18 с, панель за 0.22 с выезжает снизу на 8 пикселей.
        self._fade = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fade)
        self._appear = QPropertyAnimation(self._fade, b"opacity", self)
        self._appear.setDuration(180)
        self._appear.setStartValue(0.0)
        self._appear.setEndValue(1.0)
        self._appear.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Рост панели с 0.94 в макете сделан через transform — в Qt его нет, и
        # масштабировать виджет нечем. Остаётся выезд; он записан и в разделе
        # «чего в плане нет, а в макете есть».
        self._rise = QPropertyAnimation(self.panel, b"pos", self)
        self._rise.setDuration(220)
        self._rise.setEasingCurve(QEasingCurve.Type.OutCubic)

    def open(self) -> None:
        self._open = True
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.setFocus()

        # Панель уже стоит на месте — раскладка её посчитала при show(), —
        # поэтому выезд считается от её конечного положения.
        self.layout().activate()
        settled = self.panel.pos()
        # Панель ставится в стартовую точку руками: QPropertyAnimation
        # применяет начальное значение только на первом тике, и первые
        # ~20 мс раскладка держала бы её уже на месте — вместо «появилась
        # ниже и поднялась» вышло бы «появилась, дёрнулась вниз, поднялась».
        self.panel.move(settled + QPoint(0, RISE))
        self._rise.setStartValue(settled + QPoint(0, RISE))
        self._rise.setEndValue(settled)

        self._appear.start()
        self._rise.start()

    def dismiss(self) -> None:
        """Своё имя, а не переопределённый close: у QWidget.close свой
        контракт — он возвращает bool и вызывается из C++ невиртуально, то
        есть наше переопределение он бы обошёл."""
        if not self._open:
            return
        self._open = False
        self.hide()
        self.closed.emit()

    def eventFilter(self, watched, event) -> bool:
        # Накладка не в раскладке родителя: размер ей ставим сами.
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.edge.setGeometry(24, 0, max(0, self.panel.width() - 48),
                              self.edge.height())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        # QFrame нажатие не принимает и пропускает его вверх, к нам, — поэтому
        # промах отличаем сами, по геометрии. Без этого окно закрывалось бы от
        # любого нажатия внутри: хвата за полосу прокрутки, за ручку строки.
        if not self.panel.geometry().contains(event.position().toPoint()):
            self.dismiss()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), DIM)
```

- [ ] **Шаг 4: Стили**

Создать `client/theme/styles/modals.qss`:

```css
QFrame#modalPanel {
    background: {glass_deep};
    border: 1px solid {panel_border};
    border-radius: {r_card};
}
```

Дописать в `tokens()` в `client/theme/qss.py`:

```
        "glass_deep": "rgba(6, 7, 9, 0.72)",
        "panel_border": "rgba(255, 255, 255, 0.09)",
```

Файл подхватится сам: `load_styles` берёт все `*.qss` из каталога в порядке
имён, а `modals` идёт после `app`.

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_modal.py tests/client/test_qss.py -v`
Ожидается: PASS — девять тестов модалки и семь тестов стилей.

- [ ] **Шаг 6: Коммит**

```bash
git add client/widgets/modal.py client/theme/styles/modals.qss \
        client/theme/qss.py tests/client/test_modal.py
git commit -m "feat: каркас модального окна"
```

---

### Задача 2: Своя полоса прокрутки

**Системную не берём.** Причина в макете названа прямо: Chromium не анимирует
переходы на `::-webkit-scrollbar`. В Qt причина другая, но вывод тот же —
системная полоса рисуется темой ОС и в тёмное стекло не вписывается.

**Появляется при наведении на область, тает через 700 мс после прокрутки.**
Ползунок не короче 28 пикселей и таскается мышью.

**Файлы:**
- Создать: `client/widgets/scrollbar.py`
- Изменить: `client/theme/styles/modals.qss`
- Создать: `tests/client/test_scrollbar.py`

**Интерфейсы:**
- Потребляет: `metrics`.
- Отдаёт: `ScrollArea(QWidget)` — область с содержимым и своей полосой;
  поля `view` (`QScrollArea`), `bar`; метод `set_content(widget)`;
  константы `MIN_THUMB` (28), `HIDE_AFTER` (700).

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_scrollbar.py`:

```python
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from client.widgets.scrollbar import HIDE_AFTER, MIN_THUMB, ScrollArea


def filled(qtbot, rows: int, height: int = 200) -> ScrollArea:
    area = ScrollArea()
    qtbot.addWidget(area)
    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(0, 0, 0, 0)
    for number in range(rows):
        row = QLabel(f"row {number}")
        row.setFixedHeight(30)
        layout.addWidget(row)
    area.set_content(inner)
    area.resize(300, height)
    area.show()
    qtbot.waitExposed(area)
    qtbot.wait(30)
    return area


def test_a_short_list_has_no_bar(qtbot, theme):
    """Полоса, которой нечего показывать, — мусор на экране."""
    area = filled(qtbot, rows=2)

    assert area.bar.isHidden()


def test_a_long_list_gets_a_bar(qtbot, theme):
    area = filled(qtbot, rows=40)

    assert not area.bar.isHidden()


def test_the_thumb_is_never_thinner_than_the_floor(qtbot, theme):
    """На тысяче строк честная доля дала бы полоску в пару пикселей."""
    area = filled(qtbot, rows=400)

    assert area.thumb.height() >= MIN_THUMB


def test_the_thumb_grows_with_the_visible_share(qtbot, theme):
    short = filled(qtbot, rows=12)
    long = filled(qtbot, rows=200)

    assert short.thumb.height() > long.thumb.height()


def test_scrolling_moves_the_thumb(qtbot, theme):
    area = filled(qtbot, rows=40)
    before = area.thumb.y()

    area.view.verticalScrollBar().setValue(300)
    qtbot.wait(30)

    assert area.thumb.y() > before


def test_the_thumb_reaches_the_bottom(qtbot, theme):
    """Иначе до конца списка не дотянуться перетаскиванием."""
    area = filled(qtbot, rows=40)
    bar = area.view.verticalScrollBar()

    bar.setValue(bar.maximum())
    qtbot.wait(30)

    travel = area.bar.height() - area.thumb.height()
    assert abs(area.thumb.y() - travel) <= 1


def test_dragging_the_thumb_scrolls(qtbot, theme):
    area = filled(qtbot, rows=40)
    before = area.view.verticalScrollBar().value()

    qtbot.mousePress(area.thumb, Qt.MouseButton.LeftButton,
                     pos=QPoint(4, 4))
    qtbot.mouseMove(area.thumb, QPoint(4, 60))
    qtbot.mouseRelease(area.thumb, Qt.MouseButton.LeftButton)
    qtbot.wait(30)

    assert area.view.verticalScrollBar().value() > before


def test_the_bar_shows_on_hover(qtbot, theme):
    area = filled(qtbot, rows=40)

    qtbot.mouseMove(area, area.rect().center())
    qtbot.wait(30)

    assert area.bar.property("shown") == "true"


def test_the_bar_fades_after_the_scrolling_stops(qtbot, theme):
    """HIDE_AFTER — заявленная константа: без этого теста её можно поменять
    на семь миллисекунд или на минуту, и никто не заметит."""
    area = filled(qtbot, rows=40)

    area.view.verticalScrollBar().setValue(200)
    qtbot.wait(HIDE_AFTER // 2)
    assert area.bar.property("shown") == "true"

    qtbot.wait(HIDE_AFTER)
    assert area.bar.property("shown") == "false"


def test_the_bar_does_not_fade_under_the_cursor(qtbot, theme):
    """В макете, пока курсор над списком, полоса висит."""
    area = filled(qtbot, rows=40)

    qtbot.mouseMove(area, area.rect().center())
    area.view.verticalScrollBar().setValue(200)
    qtbot.wait(HIDE_AFTER + 200)

    assert area.bar.property("shown") == "true"


def test_the_thumb_is_visible_when_the_bar_is_shown(qtbot, theme):
    """Правило висит на ползунке, а свойство ставится на полосе: без полировки
    самого ползунка своя полоса прокрутки не нарисуется ни разу."""
    from PySide6.QtGui import QColor

    area = filled(qtbot, rows=40)
    qtbot.mouseMove(area, area.rect().center())
    qtbot.wait(30)

    shown = area.thumb.grab().toImage()
    middle = QColor(shown.pixel(area.thumb.width() // 2,
                               area.thumb.height() // 2))
    assert middle.alpha() > 0
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_scrollbar.py -v`
Ожидается: FAIL — `No module named 'client.widgets.scrollbar'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/scrollbar.py`:

```python
"""Область прокрутки со своей полосой.

Системная рисуется темой операционной системы и в тёмное стекло не
вписывается; своя живёт поверх содержимого и места не занимает."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

MIN_THUMB = 28
HIDE_AFTER = 700       # мс после последней прокрутки
BAR_W = 8

# Список тянется по высоте окна, но не во всю: дальше он прокручивается.
# Оба числа из макета.
LIST_MAX_H = 640
LIST_ROOM = 140


class ScrollArea(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.view = QScrollArea(self)
        self.view.setWidgetResizable(True)
        self.view.setFrameShape(QScrollArea.Shape.NoFrame)
        self.view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, BAR_W + 6, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self.bar = QFrame(self)
        self.bar.setObjectName("scrollBar")
        self.bar.setFixedWidth(BAR_W)
        self.bar.setProperty("shown", "false")

        self.thumb = QFrame(self.bar)
        self.thumb.setObjectName("scrollThumb")
        self.thumb.setCursor(Qt.CursorShape.OpenHandCursor)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self._light(False))

        self._hovered = False
        self._grab = None
        self.view.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.view.verticalScrollBar().rangeChanged.connect(
            lambda *_: self.layout_bar()
        )

    def set_content(self, widget: QWidget) -> None:
        self.view.setWidget(widget)
        self.layout_bar()

    def layout_bar(self) -> None:
        bar = self.view.verticalScrollBar()
        # Высоту берём у окна просмотра, а не у полосы: QScrollArea правит
        # диапазон раньше шага, и в обработчике rangeChanged pageStep ещё от
        # прошлой раскладки — ползунок выродился бы в минимум.
        page = self.view.viewport().height()
        span = bar.maximum() - bar.minimum()

        if span <= 0 or page <= 0:
            self.bar.hide()
            return

        self.bar.show()
        self.bar.setGeometry(self.width() - BAR_W, 0, BAR_W, self.height())

        whole = span + page
        height = max(MIN_THUMB, int(self.bar.height() * page / whole))
        travel = self.bar.height() - height
        offset = int(travel * (bar.value() - bar.minimum()) / span)

        self.thumb.setGeometry(0, offset, BAR_W, height)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.layout_bar()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._timer.stop()
        self._light(True)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._timer.stop()
        self._light(False)

    def _on_scroll(self, _value: int) -> None:
        self.layout_bar()
        self._light(True)
        # Под курсором полоса висит и не тает — так в макете.
        if not self._hovered:
            self._timer.start(HIDE_AFTER)

    def _light(self, on: bool) -> None:
        self.bar.setProperty("shown", "true" if on else "false")
        # Полируем и ползунок: правило висит на нём, а Qt потомка сам не
        # пересчитывает — иначе полоса не появится ни разу.
        for widget in (self.bar, self.thumb):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    # ─── перетаскивание ползунка ─────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if self.thumb.geometry().translated(self.bar.pos()).contains(
            event.position().toPoint()
        ):
            self._grab = event.position().toPoint().y()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._grab is None:
            return
        bar = self.view.verticalScrollBar()
        travel = self.bar.height() - self.thumb.height()
        if travel <= 0:
            return
        moved = event.position().toPoint().y() - self._grab
        self._grab = event.position().toPoint().y()
        span = bar.maximum() - bar.minimum()
        bar.setValue(bar.value() + int(moved * span / travel))

    def mouseReleaseEvent(self, event) -> None:
        self._grab = None
```

**Перетаскивание слушает саму область, а не ползунок.** Ползунок при движении
переезжает под курсором, и захват указателя на нём срывается после первого же
шага — то же наблюдение записано и в макете, там про перетаскивание строк.
Поэтому тест давит мышью по `area.thumb`, а обрабатывает событие область:
координаты приходят в её системе, и `translated(self.bar.pos())` их сводит.

Дописать в `client/theme/styles/modals.qss`:

```css
QFrame#scrollBar {
    background: transparent;
}

QFrame#scrollBar[shown="false"] QFrame#scrollThumb {
    background: transparent;
}

QFrame#scrollThumb {
    border-radius: 4px;
    background: {thumb};
}

QFrame#scrollThumb:hover {
    background: {thumb_hover};
}
```

и в `tokens()`:

```
        "thumb": "rgba(255, 255, 255, 0.16)",
        "thumb_hover": "rgba(255, 255, 255, 0.28)",
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_scrollbar.py -v`
Ожидается: PASS, двенадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/scrollbar.py client/theme/styles/modals.qss \
        client/theme/qss.py tests/client/test_scrollbar.py
git commit -m "feat: своя полоса прокрутки"
```

---

### Задача 3: Строка списка с переключателем

Кирпич, из которого сложены все четыре модалки. Строка: ручка перетаскивания
(если список правится), кружок-переключатель, содержимое, корзина (если
правится).

**У переключателя два цикла.** В фильтрах три состояния — не выбран, включён,
исключён; при простановке тегов карточке два — есть и нет. Исключать тег у
конкретной карточки нечего.

**Состояние показано цветом и глифом:** пусто — пустой кружок в серой обводке,
включён — акцентный с галкой, исключён — красный с крестиком.

**Файлы:**
- Создать: `client/widgets/rowlist.py`
- Изменить: `client/theme/styles/modals.qss`
- Создать: `tests/client/test_rowlist.py`

**Интерфейсы:**
- Потребляет: `GLYPHS`, `icon_font`, `font`, `typography`; `ScrollArea`.
- Отдаёт: `BoxState` (`OFF`, `ON`, `EX`), `CYCLE_FILTER`, `CYCLE_TOGGLE`;
  `StateBox(QToolButton)` с `state`, `set_state`, сигналом `changed(str)`;
  `Row(QWidget)` с полями `box`, `grip`, `remove`, `body` и сигналом
  `state_changed(object, str)` — ключ строки и её новое состояние;
  `RowList(QWidget)` с `set_rows(items)`, `states()`, `order()`,
  `add(key, make_body)`, `reset()` и сигналами `changed()`,
  `state_changed(object, str)`, `reordered(list)`,
  `removed(object)`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_rowlist.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from client.widgets.rowlist import (
    CYCLE_FILTER,
    CYCLE_TOGGLE,
    BoxState,
    RowList,
    StateBox,
)


def label(text):
    return lambda: QLabel(text)


def listed(qtbot, names, cycle=CYCLE_FILTER, editable=False) -> RowList:
    made = RowList(cycle=cycle, editable=editable)
    qtbot.addWidget(made)
    made.set_rows([(name, label(name)) for name in names])
    made.resize(360, 300)
    made.show()
    qtbot.waitExposed(made)
    return made


def test_a_filter_box_walks_three_states(qtbot, theme):
    """Не выбран, включён, исключён — и по кругу."""
    box = StateBox(CYCLE_FILTER)
    qtbot.addWidget(box)

    seen = [box.state]
    for _ in range(3):
        qtbot.mouseClick(box, Qt.MouseButton.LeftButton)
        seen.append(box.state)

    assert seen == [BoxState.OFF, BoxState.ON, BoxState.EX, BoxState.OFF]


def test_a_toggle_box_walks_two(qtbot, theme):
    """Исключать тег у конкретной карточки нечего."""
    box = StateBox(CYCLE_TOGGLE)
    qtbot.addWidget(box)

    seen = [box.state]
    for _ in range(2):
        qtbot.mouseClick(box, Qt.MouseButton.LeftButton)
        seen.append(box.state)

    assert seen == [BoxState.OFF, BoxState.ON, BoxState.OFF]


def test_the_glyph_tells_the_state_apart(qtbot, theme):
    """Галка и крестик — не одно и то же, и цвет тоже разный."""
    box = StateBox(CYCLE_FILTER)
    qtbot.addWidget(box)

    box.set_state(BoxState.ON)
    on_glyph = box.text()
    box.set_state(BoxState.EX)

    assert box.text() != on_glyph
    assert box.property("state") == "ex"


def test_an_empty_box_shows_nothing(qtbot, theme):
    box = StateBox(CYCLE_FILTER)
    qtbot.addWidget(box)

    assert box.property("state") == "off"


def test_a_list_keeps_the_state_of_every_row(qtbot, theme):
    rows = listed(qtbot, ["Драма", "Ужасы", "Комедия"])

    rows.row("Драма").box.set_state(BoxState.ON)
    rows.row("Ужасы").box.set_state(BoxState.EX)

    assert rows.states() == {"Драма": BoxState.ON, "Ужасы": BoxState.EX}


def test_a_change_is_reported_at_once(qtbot, theme):
    """Фильтр вступает в силу сразу, кнопки «применить» нет."""
    rows = listed(qtbot, ["Драма"])
    heard = []
    rows.changed.connect(lambda: heard.append(True))

    qtbot.mouseClick(rows.row("Драма").box, Qt.MouseButton.LeftButton)

    assert heard == [True]


def test_reset_puts_everything_back(qtbot, theme):
    rows = listed(qtbot, ["Драма", "Ужасы"])
    rows.row("Драма").box.set_state(BoxState.ON)
    rows.row("Ужасы").box.set_state(BoxState.EX)

    rows.reset()

    assert rows.states() == {}


def test_a_plain_list_has_no_grip_and_no_bin(qtbot, theme):
    """Жанры приходят из внешней базы: ни создавать, ни удалять их нельзя."""
    rows = listed(qtbot, ["Драма"], editable=False)

    assert rows.row("Драма").grip is None
    assert rows.row("Драма").remove is None


def test_an_editable_list_has_both(qtbot, theme):
    rows = listed(qtbot, ["Пересмотреть"], editable=True)

    assert rows.row("Пересмотреть").grip is not None
    assert rows.row("Пересмотреть").remove is not None


def test_removing_a_row_reports_and_takes_it_out(qtbot, theme):
    rows = listed(qtbot, ["Первый", "Второй"], editable=True)
    heard = []
    rows.removed.connect(heard.append)

    qtbot.mouseClick(rows.row("Первый").remove, Qt.MouseButton.LeftButton)

    assert heard == ["Первый"]
    assert rows.order() == ["Второй"]


def test_adding_a_row_puts_it_last(qtbot, theme):
    rows = listed(qtbot, ["Первый"], editable=True)

    rows.add("Второй", label("Второй"))

    assert rows.order() == ["Первый", "Второй"]


def test_a_removed_row_takes_its_state_with_it(qtbot, theme):
    """Иначе удалённый тег продолжал бы фильтровать ленту."""
    rows = listed(qtbot, ["Первый", "Второй"], editable=True)
    rows.row("Первый").box.set_state(BoxState.ON)

    qtbot.mouseClick(rows.row("Первый").remove, Qt.MouseButton.LeftButton)

    assert rows.states() == {}
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_rowlist.py -v`
Ожидается: FAIL — `No module named 'client.widgets.rowlist'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/rowlist.py`:

```python
"""Список строк с переключателем. Кирпич всех четырёх модалок."""

from enum import StrEnum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from client.theme import GLYPHS, icon_font
from client.widgets.scrollbar import ScrollArea


class BoxState(StrEnum):
    OFF = "off"
    ON = "on"
    EX = "ex"


# Фильтрам нужно исключение, простановке тегов карточке — нет.
CYCLE_FILTER = (BoxState.OFF, BoxState.ON, BoxState.EX)
CYCLE_TOGGLE = (BoxState.OFF, BoxState.ON)

_GLYPHS = {BoxState.OFF: GLYPHS["ok"], BoxState.ON: GLYPHS["ok"],
           BoxState.EX: GLYPHS["clear"]}


class StateBox(QToolButton):
    """Кружок с тремя состояниями. Пустой прозрачен: глиф есть, но не виден —
    так кружок не меняет размер при переключении."""

    changed = Signal(str)

    def __init__(self, cycle=CYCLE_FILTER, parent=None) -> None:
        super().__init__(parent)
        self._cycle = tuple(cycle)
        self.state = BoxState.OFF
        self.setObjectName("stateBox")
        self.setFixedSize(20, 20)
        self.setFont(icon_font(15))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._next)
        self.set_state(BoxState.OFF)

    def set_state(self, state: BoxState) -> None:
        self.state = state
        self.setText(_GLYPHS[state])
        self.setProperty("state", str(state))
        self.style().unpolish(self)
        self.style().polish(self)
        self.changed.emit(str(state))

    def _next(self) -> None:
        place = self._cycle.index(self.state)
        self.set_state(self._cycle[(place + 1) % len(self._cycle)])


class Row(QWidget):
    # Ключ строки и её новое состояние. Модалке тегов карточки этого не
    # заменить общим `changed()`: она пишет `assign`/`unassign` ровно по одной
    # строке, а из «что-то поменялось» не видно, по какой именно.
    state_changed = Signal(object, str)

    def __init__(self, key, body: QWidget, cycle, editable: bool,
                 parent=None) -> None:
        super().__init__(parent)
        self.key = key
        self.setObjectName("tagRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        self.grip = None
        if editable:
            self.grip = QToolButton(self)
            self.grip.setObjectName("tagGrip")
            self.grip.setFixedSize(12, 16)
            self.grip.setCursor(Qt.CursorShape.OpenHandCursor)
            layout.addWidget(self.grip)

        self.box = StateBox(cycle, self)
        self.box.changed.connect(
            lambda state: self.state_changed.emit(self.key, state)
        )
        layout.addWidget(self.box)

        self.body = body
        layout.addWidget(body, 1)

        self.remove = None
        if editable:
            self.remove = QToolButton(self)
            self.remove.setObjectName("tagRemove")
            self.remove.setFixedSize(28, 28)
            self.remove.setFont(icon_font(18))
            self.remove.setText(GLYPHS["delete"])
            self.remove.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(self.remove)


class RowList(QWidget):
    changed = Signal()
    # То же, что у `Row`, но наружу: фильтрам нужен весь набор разом, модалке
    # тегов карточки — та единственная строка, которую тронули.
    state_changed = Signal(object, str)
    reordered = Signal(list)
    removed = Signal(object)

    def __init__(self, cycle=CYCLE_FILTER, editable: bool = False,
                 parent=None) -> None:
        super().__init__(parent)
        self._cycle = cycle
        self._editable = editable
        self._rows: dict = {}

        self.area = ScrollArea(self)
        self._inner = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._layout.addStretch(1)
        self.area.set_content(self._inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.area)

    def set_rows(self, items) -> None:
        for row in list(self._rows.values()):
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        for key, make_body in items:
            self.add(key, make_body)

    def add(self, key, make_body) -> None:
        row = Row(key, make_body(), self._cycle, self._editable, self._inner)
        row.state_changed.connect(lambda _k, _s: self.changed.emit())
        row.state_changed.connect(self.state_changed)
        if row.remove is not None:
            row.remove.clicked.connect(lambda _=False, k=key: self._take(k))
        # Перед распоркой: она держит строки прижатыми к верху.
        self._layout.insertWidget(self._layout.count() - 1, row)
        self._rows[key] = row

    def row(self, key) -> Row:
        return self._rows[key]

    def order(self) -> list:
        found = []
        for place in range(self._layout.count()):
            widget = self._layout.itemAt(place).widget()
            if isinstance(widget, Row):
                found.append(widget.key)
        return found

    def states(self) -> dict:
        """Только выбранное: пустых в фильтре не бывает."""
        return {key: row.box.state for key, row in self._rows.items()
                if row.box.state is not BoxState.OFF}

    def reset(self) -> None:
        for row in self._rows.values():
            row.box.blockSignals(True)
            row.box.set_state(BoxState.OFF)
            row.box.blockSignals(False)
        self.changed.emit()

    def _take(self, key) -> None:
        row = self._rows.pop(key)
        row.setParent(None)
        row.deleteLater()
        self.removed.emit(key)
        self.changed.emit()
```

Дописать в `client/theme/styles/modals.qss`:

```css
QToolButton#stateBox {
    border: 2px solid {box_border};
    border-radius: {r_full};
    background: transparent;
    color: transparent;
}

QToolButton#stateBox[state="on"] {
    border-color: {primary};
    background: {primary};
    color: {bg};
}

QToolButton#stateBox[state="ex"] {
    border-color: {error_box};
    background: {error_box};
    color: {bg};
}

QToolButton#tagRemove {
    border: none;
    border-radius: {r_full};
    background: transparent;
    color: {faint};
}

QToolButton#tagRemove:hover {
    background: {pill_hover};
    color: {bright};
}
```

и в `tokens()`:

```
        "box_border": "rgba(255, 255, 255, 0.25)",
        "error_box": palette.ERROR_BOX,
```

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_rowlist.py -v`
Ожидается: PASS, одиннадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/rowlist.py client/theme/styles/modals.qss \
        client/theme/qss.py tests/client/test_rowlist.py
git commit -m "feat: строка списка с трёхпозиционным переключателем"
```

---

### Задача 4: Перетаскивание строк

Порядок тегов ручной и должен пережить перезапуск: в схеме под это заведена
колонка `position`.

**Строка переставляется, как только курсор перешёл середину соседней** — без
подтверждения и без «зоны сброса».

**У краёв список подъезжает сам.** Иначе до дальнего конца длинного списка
одним движением не добраться.

**Файлы:**
- Изменить: `client/widgets/rowlist.py`
- Создать: `tests/client/test_rowdrag.py`

**Интерфейсы:**
- Потребляет: `RowList`, `Row` из задачи 3.
- Отдаёт: `EDGE_ZONE` (48), `EDGE_SPEED` (13);
  `RowList.start_drag(row, y)`, `RowList.drag_to(y)`, `RowList.end_drag()` —
  разложены на три метода нарочно: так порядок проверяется без мыши.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_rowdrag.py`:

```python
from PySide6.QtWidgets import QLabel

from client.widgets.rowlist import RowList


def label(text):
    return lambda: QLabel(text)


def listed(qtbot, names) -> RowList:
    made = RowList(editable=True)
    qtbot.addWidget(made)
    made.set_rows([(name, label(name)) for name in names])
    made.resize(360, 400)
    made.show()
    qtbot.waitExposed(made)
    qtbot.wait(30)
    return made


def middle_of(rows: RowList, key: str) -> int:
    row = rows.row(key)
    return row.mapTo(rows, row.rect().center()).y()


def test_dragging_past_the_middle_swaps(qtbot, theme):
    """Строка переставляется, как только курсор перешёл середину соседней."""
    rows = listed(qtbot, ["Первый", "Второй", "Третий"])

    rows.start_drag(rows.row("Первый"), middle_of(rows, "Первый"))
    rows.drag_to(middle_of(rows, "Второй") + 2)
    rows.end_drag()

    assert rows.order() == ["Второй", "Первый", "Третий"]


def test_stopping_short_of_the_middle_changes_nothing(qtbot, theme):
    rows = listed(qtbot, ["Первый", "Второй", "Третий"])

    rows.start_drag(rows.row("Первый"), middle_of(rows, "Первый"))
    rows.drag_to(middle_of(rows, "Первый") + 4)
    rows.end_drag()

    assert rows.order() == ["Первый", "Второй", "Третий"]


def test_dragging_to_the_end(qtbot, theme):
    rows = listed(qtbot, ["Первый", "Второй", "Третий"])

    rows.start_drag(rows.row("Первый"), middle_of(rows, "Первый"))
    rows.drag_to(middle_of(rows, "Третий") + 20)
    rows.end_drag()

    assert rows.order() == ["Второй", "Третий", "Первый"]


def test_dragging_back_to_the_top(qtbot, theme):
    rows = listed(qtbot, ["Первый", "Второй", "Третий"])

    rows.start_drag(rows.row("Третий"), middle_of(rows, "Третий"))
    rows.drag_to(middle_of(rows, "Первый") - 4)
    rows.end_drag()

    assert rows.order() == ["Третий", "Первый", "Второй"]


def test_the_new_order_is_reported_once_on_drop(qtbot, theme):
    """Порядок пишется в базу один раз, а не на каждое движение мыши."""
    rows = listed(qtbot, ["Первый", "Второй"])
    heard = []
    rows.reordered.connect(heard.append)

    rows.start_drag(rows.row("Первый"), middle_of(rows, "Первый"))
    rows.drag_to(middle_of(rows, "Второй") + 2)
    rows.drag_to(middle_of(rows, "Второй") + 4)
    rows.end_drag()

    assert heard == [["Второй", "Первый"]]


def test_a_drop_without_a_move_reports_nothing(qtbot, theme):
    """Промах по ручке не должен стоить записи в базу."""
    rows = listed(qtbot, ["Первый", "Второй"])
    heard = []
    rows.reordered.connect(heard.append)

    rows.start_drag(rows.row("Первый"), middle_of(rows, "Первый"))
    rows.end_drag()

    assert heard == []


def test_the_dragged_row_is_marked(qtbot, theme):
    """В макете она приглушена — это единственный признак, что её тащат."""
    rows = listed(qtbot, ["Первый", "Второй"])

    rows.start_drag(rows.row("Первый"), middle_of(rows, "Первый"))

    assert rows.row("Первый").property("dragging") == "true"

    rows.end_drag()

    assert rows.row("Первый").property("dragging") == "false"


def test_the_state_travels_with_the_row(qtbot, theme):
    """Переставили включённый тег — он остался включённым."""
    from client.widgets.rowlist import BoxState

    rows = listed(qtbot, ["Первый", "Второй"])
    rows.row("Первый").box.set_state(BoxState.ON)

    rows.start_drag(rows.row("Первый"), middle_of(rows, "Первый"))
    rows.drag_to(middle_of(rows, "Второй") + 2)
    rows.end_drag()

    assert rows.states() == {"Первый": BoxState.ON}
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_rowdrag.py -v`
Ожидается: FAIL — `AttributeError: 'RowList' object has no attribute 'start_drag'`.

- [ ] **Шаг 3: Реализовать**

Дописать в `client/widgets/rowlist.py` — модульные константы и три метода в
`RowList`:

```python
EDGE_ZONE = 48     # полоса у края, в которой список начинает ехать
EDGE_SPEED = 13    # пикселей за шаг на самой кромке
```

```python
    def start_drag(self, row: Row, y: int) -> None:
        self._dragged = row
        self._before = self.order()
        self._mark(row, True)

    def drag_to(self, y: int) -> None:
        """Строка переставляется, как только курсор перешёл середину
        соседней — без подтверждения и без зоны сброса."""
        if self._dragged is None:
            return

        self._creep(y)

        others = [self._layout.itemAt(place).widget()
                  for place in range(self._layout.count())]
        others = [w for w in others
                  if isinstance(w, Row) and w is not self._dragged]

        target = self._layout.count() - 1     # перед распоркой
        for place, other in enumerate(others):
            centre = other.mapTo(self, other.rect().center()).y()
            if y < centre:
                target = self._layout.indexOf(other)
                break

        current = self._layout.indexOf(self._dragged)
        if current != target:
            self._layout.removeWidget(self._dragged)
            # Изъятие сдвигает всё, что было ниже, на единицу — а место
            # считалось до него. Без поправки строка уезжает на позицию
            # дальше нужной, а в самом низу — за распорку.
            if current < target:
                target -= 1
            self._layout.insertWidget(target, self._dragged)

    def end_drag(self) -> None:
        if self._dragged is None:
            return
        self._mark(self._dragged, False)
        self._dragged = None
        order = self.order()
        # Порядок пишется в базу один раз, а не на каждое движение мыши.
        if order != self._before:
            self.reordered.emit(order)

    def _creep(self, y: int) -> None:
        """У краёв список подъезжает сам: иначе до дальнего конца длинного
        списка одним движением не добраться."""
        bar = self.area.view.verticalScrollBar()
        if y < EDGE_ZONE:
            bar.setValue(bar.value() - EDGE_SPEED)
        elif y > self.height() - EDGE_ZONE:
            bar.setValue(bar.value() + EDGE_SPEED)

    def _mark(self, row: Row, on: bool) -> None:
        row.setProperty("dragging", "true" if on else "false")
        row.style().unpolish(row)
        row.style().polish(row)
```

В `RowList.__init__` добавить `self._dragged = None` и `self._before = []`.

**Мышь слушает сама `RowList`, а не ручка.** При перестановке строка переезжает
в раскладке, и захват указателя на ручке срывается после первого же шага — то же
наблюдение записано в макете. Поэтому `mousePressEvent` ищет ручку под курсором
и зовёт `start_drag`, `mouseMoveEvent` — `drag_to`, `mouseReleaseEvent` —
`end_drag`. Три метода публичны нарочно: так порядок проверяется без мыши, а
через мышь проверяется только их связка.

Дописать в `client/theme/styles/modals.qss`:

```css
QWidget#tagRow[dragging="true"] {
    background: {row_dragged};
}
```

и в `tokens()` — `"row_dragged": "rgba(255, 255, 255, 0.04)"`.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_rowdrag.py tests/client/test_rowlist.py -v`
Ожидается: PASS, двадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/rowlist.py client/theme/styles/modals.qss \
        client/theme/qss.py tests/client/test_rowdrag.py
git commit -m "feat: перетаскивание строк списка"
```

---

### Задача 5: Модалки фильтров — жанры и теги

Два окна на общем каркасе. Отличие одно: **теги свои — их можно создавать,
удалять и переставлять; жанры приходят из внешней базы.**

**Фильтр вступает в силу сразу.** Кнопки «применить» нет: закрыл окно — уже
отфильтровано. Кнопка в шапке горит, пока фильтр задан, и повторное нажатие на
неё сбрасывает всё — это уже сделано в плане 5, задача 10.

**Набор показывается по текущему типу содержимого.** Теги у фильмов, сериалов и
игр независимы; жанров наборов два, кино и игры.

**Файлы:**
- Создать: `client/modals/filters.py`,
  `client/widgets/newrow.py`
- Создать: `tests/client/test_filters.py`

**Интерфейсы:**
- Потребляет: `Modal`, `RowList`, `BoxState`, `Filters`, `Kind`, `GenreKind`;
  `runtime.call`.
- Отдаёт: `NewRow(QWidget)` — строка «+ Новый тег» с сигналом `submitted(str)`;
  `FilterModal(Modal)` с `open_for(kind)`, `filters()`, `reset()`, полями
  `rows: RowList` и `new_row: NewRow | None`, и сигналом
  `filters_changed(object)`;
  фабрики `genres_modal(runtime, parent)` и `tags_modal(runtime, parent)`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_filters.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from backend.model import Filters, Genre, GenreKind, Kind
from client.modals.filters import genres_modal, tags_modal
from client.widgets.newrow import NewRow
from client.widgets.rowlist import BoxState
from tests.client.conftest import FakeRuntime, host

DRAMA = Genre(id=1, name="драма", kind=GenreKind.FILM)
HORROR = Genre(id=2, name="ужасы", kind=GenreKind.FILM)


def test_genres_are_asked_for_the_current_kind(qtbot, theme):
    """Наборов жанров два: кино и игры."""
    runtime = FakeRuntime({"genres.list_for_kind": [DRAMA, HORROR]})
    modal = genres_modal(runtime, host())

    modal.open_for(Kind.GAME)
    qtbot.wait(30)

    name, args, _ = runtime.asked[0]
    assert name == "genres.list_for_kind"
    assert args[0] is GenreKind.GAME


def test_films_and_series_share_one_set(qtbot, theme):
    """«Драма» у фильма и у сериала — одна строка, иначе фильтр по драме
    превратился бы в два разных фильтра."""
    runtime = FakeRuntime({"genres.list_for_kind": [DRAMA]})
    modal = genres_modal(runtime, host())

    modal.open_for(Kind.SERIES)
    qtbot.wait(30)

    _, args, _ = runtime.asked[0]
    assert args[0] is GenreKind.FILM


def test_a_chosen_genre_becomes_a_filter(qtbot, theme):
    runtime = FakeRuntime({"genres.list_for_kind": [DRAMA, HORROR]})
    modal = genres_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)
    heard = []
    modal.filters_changed.connect(heard.append)

    modal.rows.row(DRAMA.id).box.set_state(BoxState.ON)

    assert heard[-1] == Filters(genre_ids=(DRAMA.id,))


def test_an_excluded_genre_goes_to_the_other_field(qtbot, theme):
    """Исключённое вычитается последним и сильнее включённого."""
    runtime = FakeRuntime({"genres.list_for_kind": [DRAMA, HORROR]})
    modal = genres_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)

    modal.rows.row(DRAMA.id).box.set_state(BoxState.ON)
    modal.rows.row(HORROR.id).box.set_state(BoxState.EX)

    assert modal.filters() == Filters(genre_ids=(DRAMA.id,),
                                      excluded_genre_ids=(HORROR.id,))


def test_a_filter_takes_effect_at_once(qtbot, theme):
    """Кнопки «применить» нет: закрыл окно — уже отфильтровано."""
    runtime = FakeRuntime({"genres.list_for_kind": [DRAMA]})
    modal = genres_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)
    heard = []
    modal.filters_changed.connect(heard.append)

    qtbot.mouseClick(modal.rows.row(DRAMA.id).box, Qt.MouseButton.LeftButton)

    assert len(heard) == 1


def test_resetting_clears_everything(qtbot, theme):
    runtime = FakeRuntime({"genres.list_for_kind": [DRAMA, HORROR]})
    modal = genres_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)
    modal.rows.row(DRAMA.id).box.set_state(BoxState.ON)

    modal.reset()

    assert modal.filters() == Filters()


def test_genres_cannot_be_edited(qtbot, theme):
    """Приходят из внешней базы: ни создать, ни удалить."""
    runtime = FakeRuntime({"genres.list_for_kind": [DRAMA]})
    modal = genres_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)

    assert modal.rows.row(DRAMA.id).remove is None
    assert modal.new_row is None


def test_tags_can_be_created(qtbot, theme):
    runtime = FakeRuntime({"tags.list_for_kind": [(1, "пересмотреть")],
                           "tags.create": 7})
    modal = tags_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)

    modal.new_row.input.setText("с женой")
    modal.new_row.submit()
    qtbot.wait(30)

    name, args, _ = runtime.asked[-1]
    assert name == "tags.create"
    assert args == (Kind.MOVIE, "с женой")


def test_a_created_tag_appears_in_the_list(qtbot, theme):
    runtime = FakeRuntime({"tags.list_for_kind": [(1, "пересмотреть")],
                           "tags.create": 7})
    modal = tags_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)

    modal.new_row.input.setText("с женой")
    modal.new_row.submit()
    qtbot.wait(30)

    assert modal.rows.order() == [1, 7]


def test_an_empty_name_creates_nothing(qtbot, theme):
    runtime = FakeRuntime({"tags.list_for_kind": []})
    modal = tags_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)

    modal.new_row.input.setText("   ")
    modal.new_row.submit()

    assert not any(name == "tags.create" for name, _, _ in runtime.asked)


def test_removing_a_tag_reaches_the_base(qtbot, theme):
    runtime = FakeRuntime({"tags.list_for_kind": [(1, "пересмотреть")]})
    modal = tags_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)

    qtbot.mouseClick(modal.rows.row(1).remove, Qt.MouseButton.LeftButton)
    qtbot.wait(30)

    assert ("tags.delete", (1,), {}) in runtime.asked


def test_reordering_reaches_the_base(qtbot, theme):
    """Порядок ручной и должен пережить перезапуск."""
    runtime = FakeRuntime({"tags.list_for_kind": [(1, "первый"), (2, "второй")]})
    modal = tags_modal(runtime, host())
    modal.open_for(Kind.MOVIE)
    qtbot.wait(30)

    modal.rows.reordered.emit([2, 1])
    qtbot.wait(30)

    assert ("tags.reorder", (Kind.MOVIE, [2, 1]), {}) in runtime.asked


def test_the_new_row_shows_its_tick_only_when_filled(qtbot, theme):
    """Пустая кнопка подтверждения — мусор на экране."""
    row = NewRow()
    qtbot.addWidget(row)
    row.show()
    qtbot.waitExposed(row)

    assert row.ok.isHidden()

    row.input.setText("что-то")
    assert not row.ok.isHidden()

    row.input.setText("")
    assert row.ok.isHidden()
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_filters.py -v`
Ожидается: FAIL — `No module named 'client.modals'`: этот импорт в шапке
теста идёт раньше, а каталога модалок ещё нет.

- [ ] **Шаг 3: Строка нового тега**

Создать `client/widgets/newrow.py`:

```python
"""Строка «+ Новый тег». Без фона и рамки: в покое это просто серая надпись,
при фокусе под ней проступает акцентная полоса."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QToolButton, QWidget

from client.theme import GLYPHS, font, icon_font, typography


class NewRow(QWidget):
    submitted = Signal(str)

    def __init__(self, placeholder: str = "+ Новый тег", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("newRow")

        self.input = QLineEdit(self)
        self.input.setObjectName("newRowInput")
        self.input.setPlaceholderText(placeholder)
        self.input.setMaxLength(24)
        self.input.setFrame(False)
        self.input.setFont(font(typography.BODY_L))

        self.ok = QToolButton(self)
        self.ok.setObjectName("newRowOk")
        self.ok.setFixedSize(26, 26)
        self.ok.setFont(icon_font(18))
        self.ok.setText(GLYPHS["ok"])
        self.ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(8)
        layout.addWidget(self.input, 1)
        layout.addWidget(self.ok)

        self.input.textChanged.connect(self._sync)
        self.input.returnPressed.connect(self.submit)
        self.ok.clicked.connect(self.submit)

    def submit(self) -> None:
        name = self.input.text().strip()
        if not name:
            return
        self.submitted.emit(name)
        self.input.clear()
        self.input.setFocus()

    def _sync(self, text: str) -> None:
        # Появляется, только когда есть что подтверждать.
        self.ok.setVisible(bool(text.strip()))
```

- [ ] **Шаг 4: Модалки фильтров**

Создать `client/modals/filters.py`. Общий класс и две фабрики: жанры без
правки, теги с созданием, удалением и перетаскиванием. Строка списка у обоих —
`QLabel` с именем; ключ строки — идентификатор в базе, а не имя: имена у тегов
меняются, а фильтр держится за строку.

```python
class FilterModal(Modal):
    filters_changed = Signal(object)

    def __init__(self, parent, runtime=None, width: int = 560, *,
                 pack, editable: bool = False) -> None:
        """`runtime` необязателен: список оценок известен заранее, и модалка
        фильтра по оценке в базу не ходит вовсе. `pack` собирает выбранное в
        `Filters` — этим три модалки и отличаются."""

    def set_items(self, items) -> None:
        """Готовый список, минуя бэкенд. Для фильтра по оценке."""

    def open_for(self, kind: Kind) -> None:
        """Набор показывается по текущему типу содержимого: теги у трёх типов
        независимы, жанров наборов два.

        Строки перезагружаются только при смене типа: в макете состояние
        переключателей переживает закрытие окна, и галки должны остаться на
        месте, пока горит кнопка в шапке."""
        if kind is not self._kind:
            self._kind = kind
            self._load(kind)
        self.open()

    def _load(self, kind: Kind) -> None:
        """Без рантайма не делает ничего: у фильтра по оценке список задан
        заранее через set_items."""
        if self._runtime is None:
            return

    def filters(self) -> Filters:
        chosen, excluded = [], []
        for key, state in self.rows.states().items():
            (chosen if state is BoxState.ON else excluded).append(key)
        return self._pack(tuple(chosen), tuple(excluded))
```

`_pack` у жанров кладёт в `genre_ids`/`excluded_genre_ids`, у тегов — в
`tag_ids`/`excluded_tag_ids`. `_load` зовёт `genres.list_for_kind(GenreKind…)`
или `tags.list_for_kind(kind)` через `runtime.call`.

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_filters.py -v`
Ожидается: PASS, тринадцать тестов.

- [ ] **Шаг 6: Коммит**

```bash
git add client/widgets/newrow.py client/modals/filters.py \
        tests/client/test_filters.py
git commit -m "feat: модалки фильтров по жанрам и тегам"
```

---

### Задача 6: Фильтр по оценке

Тот же список, но строка — не имя, а десять звёзд и ярлык: «Шедевр»,
«Отлично», «Интересно». Цвет строки — из той же нотации, что у звёзд в карточке
и у столбцов гистограммы.

**Порядок сверху вниз: от десятки к единице.** В макете именно так, и это
разумно: высокие оценки нужнее.

**Файлы:**
- Изменить: `client/modals/filters.py`
- Создать: `tests/client/test_score_filter.py`

**Интерфейсы:**
- Потребляет: `RowList`, `VERDICTS`, `palette`.
- Отдаёт: `ScoreRow(QWidget)` — звёзды и ярлык одной оценки;
  `scores_modal(parent)` — модалка без похода в бэкенд: список известен
  заранее.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_score_filter.py`:

```python
from PySide6.QtWidgets import QWidget

from backend.model import Filters, Kind
from client.modals.filters import ScoreRow, scores_modal
from client.theme import palette
from client.widgets.rowlist import BoxState
from tests.client.conftest import host


def test_ten_rows_from_the_top(qtbot, theme):
    """Сверху десятка: высокие оценки нужнее."""
    modal = scores_modal(host())
    modal.open_for(Kind.MOVIE)

    assert modal.rows.order() == [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]


def test_a_row_carries_its_verdict(qtbot, theme):
    row = ScoreRow(7)
    qtbot.addWidget(row)

    assert row.label.text() == "Интересно"


def test_a_row_is_painted_by_the_shared_scale(qtbot, theme):
    """Тот же цвет, что у звёзд в карточке и у столбца статистики."""
    row = ScoreRow(3)
    qtbot.addWidget(row)

    assert palette.score_color(3) in row.styleSheet()


def test_the_stars_show_the_score(qtbot, theme):
    row = ScoreRow(4)
    qtbot.addWidget(row)

    lit = [star for star in row.stars if star.property("on") == "true"]
    assert len(lit) == 4


def test_a_chosen_score_becomes_a_filter(qtbot, theme):
    modal = scores_modal(host())
    modal.open_for(Kind.MOVIE)

    modal.rows.row(8).box.set_state(BoxState.ON)

    assert modal.filters() == Filters(scores=(8,))


def test_an_excluded_score_goes_to_the_other_field(qtbot, theme):
    modal = scores_modal(host())
    modal.open_for(Kind.MOVIE)

    modal.rows.row(1).box.set_state(BoxState.EX)

    assert modal.filters() == Filters(excluded_scores=(1,))


def test_several_scores_add_up(qtbot, theme):
    """Внутри признака «или»: показать восьмёрки и девятки."""
    modal = scores_modal(host())
    modal.open_for(Kind.MOVIE)

    modal.rows.row(9).box.set_state(BoxState.ON)
    modal.rows.row(8).box.set_state(BoxState.ON)

    assert set(modal.filters().scores) == {8, 9}


def test_the_score_list_does_not_ask_the_base(qtbot, theme):
    """Оценок всегда десять, и в базу за ними ходить незачем."""
    modal = scores_modal(host())

    assert not hasattr(modal, "_runtime") or modal._runtime is None
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_score_filter.py -v`
Ожидается: FAIL — `ImportError: cannot import name 'ScoreRow'`.

- [ ] **Шаг 3: Реализовать**

Дописать в `client/modals/filters.py`:

```python
class ScoreRow(QWidget):
    """Десять звёзд и ярлык. Строка красится в цвет своей оценки — той же
    нотацией, что звёзды в карточке и столбцы статистики."""

    def __init__(self, score: int, parent=None) -> None:
        super().__init__(parent)
        color = palette.score_color(score)
        self.setStyleSheet(f"color: {color};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.stars = []
        strip = QWidget(self)
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.setSpacing(1)
        for step in range(1, 11):
            star = QLabel(GLYPHS["score"], strip)
            on = step <= score
            star.setFont(icon_font(17, filled=on))
            star.setProperty("on", "true" if on else "false")
            star.setStyleSheet(
                f"color: {color};" if on
                else f"color: {palette.STAR_EMPTY_SMALL};"
            )
            strip_layout.addWidget(star)
            self.stars.append(star)
        layout.addWidget(strip)

        self.label = QLabel(VERDICTS[score], self)
        self.label.setFont(font(typography.TITLE_S))
        layout.addStretch(1)
        layout.addWidget(self.label)


def scores_modal(parent) -> FilterModal:
    """Список известен заранее — в базу за ним не ходим."""
    modal = FilterModal(parent, runtime=None, width=400,
                        pack=_pack_scores, editable=False)
    modal.set_items([(score, lambda s=score: ScoreRow(s))
                     for score in range(10, 0, -1)])
    return modal
```

`ScoreRow` берёт `palette.STAR_EMPTY_SMALL`. Сама константа, как и
`STAR_EMPTY`, `OVERLAY_DIM` и `ERROR_BOX`, заведена **задачей 1**: их читают
`Modal` и `tokens()` на уровне модуля, то есть при импорте. Объяви их здесь —
не собрался бы ни один тест каталога, а не только тесты этой задачи.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_score_filter.py -v`
Ожидается: PASS, восемь тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/modals/filters.py tests/client/test_score_filter.py
git commit -m "feat: фильтр по оценке со звёздами и ярлыками"
```

---

### Задача 7: Теги одной карточки

Тот же список, но переключатель на два состояния и в шапке кнопки нет. Окно
открывается кнопкой «± Тег» на карточке.

**Отличие от фильтра одно, и оно в цикле переключателя.** Исключать тег у
конкретной карточки нечего.

**Изменение уходит в базу сразу**, строка за строкой: поставил галку —
`assign`, снял — `unassign`. Кнопки «сохранить» нет, как и у фильтра.

**Файлы:**
- Создать: `client/modals/item_tags.py`
- Создать: `tests/client/test_item_tags.py`

**Интерфейсы:**
- Потребляет: `Modal`, `RowList`, `CYCLE_TOGGLE`, `NewRow`; `runtime.call`.
- Отдаёт: `ItemTagsModal(Modal)` с `open_for(item_id, kind)` и сигналом
  `tags_changed(int)` — карточку надо перерисовать.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_item_tags.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from backend.model import Kind
from client.modals.item_tags import ItemTagsModal
from client.widgets.rowlist import BoxState
from tests.client.conftest import FakeRuntime, host


def opened(qtbot, assigned=()) -> tuple:
    runtime = FakeRuntime({
        "tags.list_for_kind": [(1, "пересмотреть"), (2, "с женой")],
        "tags.tags_of": list(assigned),
        "tags.create": 9,
    })
    modal = ItemTagsModal(runtime, host())
    modal.open_for(item_id=42, kind=Kind.MOVIE)
    qtbot.wait(30)
    return modal, runtime


def test_the_whole_set_of_the_kind_is_shown(qtbot, theme):
    modal, _ = opened(qtbot)

    assert modal.rows.order() == [1, 2]


def test_what_is_already_on_the_card_is_ticked(qtbot, theme):
    modal, _ = opened(qtbot, assigned=[(1, "пересмотреть")])

    assert modal.rows.states() == {1: BoxState.ON}


def test_there_is_no_exclusion_here(qtbot, theme):
    """Исключать тег у конкретной карточки нечего."""
    modal, _ = opened(qtbot)

    box = modal.rows.row(1).box
    seen = [box.state]
    for _ in range(2):
        box._next()
        seen.append(box.state)

    assert BoxState.EX not in seen


def test_ticking_assigns_at_once(qtbot, theme):
    modal, runtime = opened(qtbot)

    qtbot.mouseClick(modal.rows.row(1).box, Qt.MouseButton.LeftButton)
    qtbot.wait(30)

    assert ("tags.assign", (42, 1), {}) in runtime.asked


def test_unticking_unassigns(qtbot, theme):
    modal, runtime = opened(qtbot, assigned=[(1, "пересмотреть")])

    qtbot.mouseClick(modal.rows.row(1).box, Qt.MouseButton.LeftButton)
    qtbot.wait(30)

    assert ("tags.unassign", (42, 1), {}) in runtime.asked


def test_the_card_is_told_to_redraw(qtbot, theme):
    modal, _ = opened(qtbot)
    heard = []
    modal.tags_changed.connect(heard.append)

    qtbot.mouseClick(modal.rows.row(1).box, Qt.MouseButton.LeftButton)
    qtbot.wait(30)

    assert heard == [42]


def test_a_new_tag_can_be_created_here_too(qtbot, theme):
    """Модалка тегов карточки правится так же, как общая: список один."""
    modal, runtime = opened(qtbot)

    modal.new_row.input.setText("шедевр")
    modal.new_row.submit()
    qtbot.wait(30)

    assert ("tags.create", (Kind.MOVIE, "шедевр"), {}) in runtime.asked
    assert modal.rows.order() == [1, 2, 9]


def test_a_freshly_created_tag_is_not_assigned_yet(qtbot, theme):
    """Завёл тег — не значит повесил его на карточку."""
    modal, runtime = opened(qtbot)

    modal.new_row.input.setText("шедевр")
    modal.new_row.submit()
    qtbot.wait(30)

    assert modal.rows.states() == {}
    assert not any(name == "tags.assign" for name, _, _ in runtime.asked)
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_item_tags.py -v`
Ожидается: FAIL — `No module named 'client.modals.item_tags'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/modals/item_tags.py`. Устройство то же, что у `FilterModal`:
`RowList` с `CYCLE_TOGGLE` и **`editable=True`** — теги свои, их и здесь можно
завести, удалить и переставить, как в макете; `NewRow` снизу; список берётся
`tags.list_for_kind(kind)`, отметки — `tags.tags_of(item_id)`. На смену
состояния строки уходит `assign` или `unassign` и испускается
`tags_changed(item_id)`.

**Начальная простановка отметок не должна писать в базу.** `StateBox.set_state`
испускает `changed` всегда, и при загрузке уже проставленных тегов это ушло бы
в `assign` по каждому — лишние записи при каждом открытии окна. Поэтому
отметки ставятся при заблокированных сигналах, а обработчик вешается после.

**Кнопки в шапке у этой модалки нет**, поэтому `FilterModal` для неё не
годится: та завязана на `filters_changed` и на подсветку кнопки. Общее у них —
`Modal`, `RowList` и `NewRow`, и этого достаточно; выносить третий класс ради
двух совпадающих строк не нужно.

**`RowList.changed` не говорит, какая строка изменилась.** Модалке тегов это
нужно: она пишет `assign` ровно по одной. Значит `Row` получает сигнал
`state_changed(object, str)` — ключ и новое состояние, — а `RowList`
пробрасывает его наружу под тем же именем. Сигнал без аргументов остаётся для
фильтров, которым нужен весь набор разом.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_item_tags.py -v`
Ожидается: PASS, восемь тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/modals/item_tags.py tests/client/test_item_tags.py
git commit -m "feat: модалка тегов одной карточки"
```

---

### Задача 8: Поле ввода и поле с подсказкой

**Поле — подчёркивание, а не рамка.** Одно на всё окно карточки и на строку
нового тега.

**Поле с подсказкой:** печатаешь — снизу совпадения, выбранное ложится справа.
**Enter контекстный:** ничего не подсвечено — заводит нового, подсвечена
строка — берёт существующего. Это и есть весь механизм различения тёзок, и
другого нет.

**В подсказке видно, чем один тёзка отличается от другого:** имя, маркер `•` и
название самого высоко оценённого тобой фильма с его участием.

**Файлы:**
- Создать: `client/widgets/field.py`, `client/widgets/picker.py`
- Создать: `tests/client/test_picker.py`

**Интерфейсы:**
- Потребляет: `Suggestion` из `backend.model`; `runtime.call`; `font`,
  `typography`, `palette`.
- Отдаёт: `Field(QWidget)` — подчёркнутое поле с полем `input`;
  `Picker(QWidget)` с `bind(chosen)`, `chosen()`, сигналами
  `picked(object)` и `created(str)`; константа `HITS_SHOWN` (8).

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_picker.py`:

```python
from PySide6.QtCore import Qt

from backend.model import Suggestion
from client.widgets.picker import HITS_SHOWN, Picker
from tests.client.conftest import FakeRuntime, host

NOLAN = Suggestion(entity_id=1, name="Кристофер Нолан",
                   hint="Интерстеллар", hint_item_id=10)
OTHER = Suggestion(entity_id=2, name="Кристофер Нолан",
                   hint="Наш выпускной", hint_item_id=11)


def picker(qtbot, answer=()) -> Picker:
    """Общий FakeRuntime из conftest: он выполняет задачу сразу и отдаёт ответ
    сигналом done — так же, как настоящий рантайм. Заглушка, отдающая
    результат возвратом, заставила бы писать реализацию, которая трогает
    виджеты в потоке бэкенда."""
    made = Picker(FakeRuntime({"people.suggest": list(answer)}),
                  placeholder="Актёры")
    qtbot.addWidget(made)
    made.resize(300, 200)
    made.show()
    qtbot.waitExposed(made)
    return made


def test_the_hint_list_is_hidden_until_there_is_something(qtbot, theme):
    made = picker(qtbot)

    assert made.hits.isHidden()


def test_typing_asks_for_matches(qtbot, theme):
    made = picker(qtbot, [NOLAN])

    made.input.setText("нолан")
    made.suggest()

    name, args, fields = made._runtime.asked[-1]
    assert name == "people.suggest"
    assert args[0] == "нолан"


def test_namesakes_are_told_apart_in_the_list(qtbot, theme):
    """Совпадение имени само по себе не значит того же человека. Узнают его
    по названию фильма, а не по метаданным."""
    made = picker(qtbot, [NOLAN, OTHER])

    made.input.setText("нолан")
    made.suggest()

    shown = [made.hits.item(place).text() for place in range(made.hits.count())]
    assert shown == ["Кристофер Нолан • Интерстеллар",
                     "Кристофер Нолан • Наш выпускной"]


def test_the_separator_is_a_bullet(qtbot, theme):
    """U+2022, а не точка: точка читается как конец предложения и слипается
    с названием."""
    made = picker(qtbot, [NOLAN])

    made.input.setText("нолан")
    made.suggest()

    assert "•" in made.hits.item(0).text()


def test_no_more_than_a_handful_is_shown(qtbot, theme):
    many = [Suggestion(entity_id=n, name=f"Имя {n}", hint="фильм",
                       hint_item_id=n) for n in range(30)]
    made = picker(qtbot, many)

    made.input.setText("имя")
    made.suggest()

    assert made.hits.count() == HITS_SHOWN


def test_enter_on_nothing_creates_a_new_one(qtbot, theme):
    """Ввёл имя, ничего не подсвечено, Enter — новый человек."""
    made = picker(qtbot, [NOLAN])
    created, picked = [], []
    made.created.connect(created.append)
    made.picked.connect(picked.append)

    made.input.setText("Василий Пупкин")
    made.suggest()
    qtbot.keyClick(made.input, Qt.Key.Key_Return)

    assert created == ["Василий Пупкин"]
    assert picked == []


def test_enter_on_a_highlighted_row_takes_the_existing_one(qtbot, theme):
    """Стрелкой вниз подсветил строку, Enter — выбран существующий."""
    made = picker(qtbot, [NOLAN, OTHER])
    created, picked = [], []
    made.created.connect(created.append)
    made.picked.connect(picked.append)

    made.input.setText("нолан")
    made.suggest()
    qtbot.keyClick(made.input, Qt.Key.Key_Down)
    qtbot.keyClick(made.input, Qt.Key.Key_Return)

    assert picked == [NOLAN]
    assert created == []


def test_the_second_namesake_is_reachable(qtbot, theme):
    """Ради этого подсказка и различает их до наведения."""
    made = picker(qtbot, [NOLAN, OTHER])
    picked = []
    made.picked.connect(picked.append)

    made.input.setText("нолан")
    made.suggest()
    qtbot.keyClick(made.input, Qt.Key.Key_Down)
    qtbot.keyClick(made.input, Qt.Key.Key_Down)
    qtbot.keyClick(made.input, Qt.Key.Key_Return)

    assert picked == [OTHER]


def test_a_click_takes_the_existing_one_too(qtbot, theme):
    made = picker(qtbot, [NOLAN])
    picked = []
    made.picked.connect(picked.append)

    made.input.setText("нолан")
    made.suggest()
    made.hits.setCurrentRow(0)
    made.take_highlighted()

    assert picked == [NOLAN]


def test_the_chosen_are_shown_and_can_be_taken_back(qtbot, theme):
    made = picker(qtbot)

    made.bind([("Мэттью Макконахи", 5), ("Энн Хэтэуэй", 6)])
    made.drop(5)

    assert [name for name, _ in made.chosen()] == ["Энн Хэтэуэй"]


def test_two_namesakes_are_both_kept(qtbot, theme):
    """Дедуп идёт по идентификатору, а не по имени: на том, что двух
    Кристоферов Ноланов можно добавить обоих, держится весь механизм."""
    made = picker(qtbot)

    made.add("Кристофер Нолан", 1)
    made.add("Кристофер Нолан", 2)

    assert [entity for _, entity in made.chosen()] == [1, 2]


def test_the_same_person_is_not_added_twice(qtbot, theme):
    made = picker(qtbot)

    made.bind([("Мэттью Макконахи", 5)])
    made.add("Мэттью Макконахи", 5)

    assert made.chosen() == [("Мэттью Макконахи", 5)]


def test_an_empty_enter_does_nothing(qtbot, theme):
    made = picker(qtbot)
    created = []
    made.created.connect(created.append)

    qtbot.keyClick(made.input, Qt.Key.Key_Return)

    assert created == []
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_picker.py -v`
Ожидается: FAIL — `No module named 'client.widgets.picker'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/field.py` — обёртка вокруг `QLineEdit` с нижней чертой,
меняющей цвет при фокусе (`QFrame` с `objectName="field"`, состояние через
`focusInEvent`/`focusOutEvent` на самом поле и свойство `focused` на обёртке:
`:focus-within` в Qt QSS нет).

Создать `client/widgets/picker.py`. Список совпадений — `QListWidget` без рамки,
поверх содержимого; строка собирается как `f"{s.name} • {s.hint}"`, а сама
`Suggestion` хранится в `Qt.ItemDataRole.UserRole`.

```python
HITS_SHOWN = 8
BULLET = "•"


def hint_line(suggestion) -> str:
    """Имя, маркер и название, по которому этого человека узнают.

    Маркер — U+2022, а не точка: точка читается как конец предложения и
    слипается с названием."""
    if not suggestion.hint:
        return suggestion.name
    return f"{suggestion.name} {BULLET} {suggestion.hint}"
```

Клавиши: `Down`/`Up` двигают подсветку в списке, `Return` смотрит на неё —
подсвечено что-то, значит выбран существующий, нет — заводится новый. `Escape`
прячет список.

- [ ] **Шаг 4: Стили полей, подсказки и выбранного**

Дописать в `client/theme/styles/modals.qss` — всё из макета, без единого цвета
по месту:

```css
QFrame#field {
    border-bottom: 2px solid {field_line};
}

QFrame#field[focused="true"],
QFrame#newRow[focused="true"] {
    border-bottom-color: {primary};
}

QLineEdit#fieldInput,
QLineEdit#newRowInput {
    border: none;
    background: transparent;
    color: {text_bright};
    selection-background-color: {primary_soft};
}

QFrame#newRow {
    border-bottom: 2px solid transparent;
}

QToolButton#newRowOk {
    border: none;
    border-radius: {r_full};
    background: transparent;
    color: {primary};
}

QToolButton#newRowOk:hover {
    background: {primary_soft};
}

QListWidget#pickerHits {
    border: 1px solid {panel_border};
    border-radius: 10px;
    background: {surface_pop};
    outline: none;
}

QListWidget#pickerHits::item {
    padding: 7px 10px;
    border-radius: 6px;
    color: {bright};
}

QListWidget#pickerHits::item:selected,
QListWidget#pickerHits::item:hover {
    background: {primary_soft};
    color: {primary};
}

QToolButton#pickedDrop {
    border: none;
    border-radius: {r_full};
    background: transparent;
    color: {faint};
}

QToolButton#pickedDrop:hover {
    color: {error};
}

QLabel#tagName {
    color: {text_bright};
}
```

и в `tokens()` — `"field_line": "rgba(255, 255, 255, 0.08)"`.

**`:focus-within` в Qt нет.** Поэтому у `Field` и `NewRow` есть свойство
`focused`: его ставит `focusInEvent`/`focusOutEvent` самого поля ввода, а
пересчитывает пара `unpolish`/`polish` — тем же приёмом, что у кнопок шапки в
плане 5.

**Длинное имя тега режется многоточием.** У `QLabel` своего многоточия нет,
поэтому текст обрезается руками через `QFontMetrics.elidedText` в
`resizeEvent`, а полное лежит в подсказке.

- [ ] **Шаг 5: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_picker.py tests/client/test_qss.py -v`
Ожидается: PASS — тринадцать тестов подсказки и семь тестов стилей.

- [ ] **Шаг 6: Коммит**

```bash
git add client/widgets/field.py client/widgets/picker.py \
        client/theme/styles/modals.qss client/theme/qss.py \
        tests/client/test_picker.py
git commit -m "feat: поле ввода и поле с подсказкой, различающей тёзок"
```

---

### Задача 9: Окно карточки — раскладка и поля

**Окно создания и правки — одно и то же:** пустое заводит, заполненное правит.

**Поля показываются по типу содержимого.** Тип берётся из переключателя в
шапке: он всегда на виду, и спрашивать его отдельно незачем.

| Тип | Свои поля |
|---|---|
| фильм | минуты, режиссёр |
| сериал | сезоны, серии, шоураннер |
| игра | разработчик, издатель |

Актёры показываются кино, жанры — всем.

**Ряд кнопок внизу — общий виджет, а не сборка по месту.** Он нужен и здесь, и
в подтверждении удаления, и обе кнопки в нём одинаковы: различает их только
цвет, приходящий под курсором. Значения из макета, все до одного:

| Что | Значение |
|---|---|
| ряд | прижат вправо, промежуток 14, отступ сверху — до низа окна |
| кнопка | не уже 150, отступы 12 сверху и снизу, 26 по бокам |
| скругление | `{r_full}` |
| шрифт | `LABEL_L` |
| цвет текста в покое | `{bright}` |
| подложка в покое | `{glass}` — у обеих кнопок она одинакова и блёкла |
| подложка «Отмена» под курсором | `{glass_error}` |
| подложка основной под курсором | `{glass_primary}` |
| длительность перехода цвета | 0.16 с |

Переход цвета в QSS не работает — `transition` Qt не понимает, — поэтому в
покое и под курсором просто два правила, без промежуточной анимации. Это
записано и в разделе «чего в плане нет».

Именно так пропадает последняя отсылка к `docs/design/`: раньше вид кнопки задавался
фразой «класс `neon` с `--neon: error`», то есть именем класса и именем
CSS-переменной из черновика, который будет удалён. Ни того ни другого в
чистовике нет — есть значения выше.

**Раскладка считается от постера.** Его ширина, высота строки и оба отступа —
переменные, а не числа по месту; высота колонки полей задана постером, иначе
каждое новое поле слева растягивало бы синопсис.

**Файлы:**
- Создать: `client/widgets/dialogbar.py`, `client/modals/card_window.py`
- Изменить: `client/theme/styles/modals.qss`
- Создать: `tests/client/test_card_window.py`

**Интерфейсы:**
- Потребляет: `Modal`, `Field`, `Picker`, `Kind`, `CardView`.
- Отдаёт: `DialogBar(QWidget)` — ряд из отменяющей и основной кнопки, с
  сигналами `accepted()` и `rejected()` и полями `go`, `cancel`.
- Отдаёт: `CardWindow(Modal)` с `open_new(kind)`, `open_edit(view)`,
  `values()`, полями `title`, `original`, `year`, `runtime`, `seasons`,
  `episodes`, `link`, `synopsis`, `director`, `showrunner`, `developer`,
  `publisher`, `actors`, `genres`, `poster`, сигналами `save_clicked()` и
  `cancel_clicked()`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_card_window.py`:

```python
from datetime import datetime

from PySide6.QtWidgets import QWidget

from backend.model import (
    CardView,
    Credit,
    Genre,
    GenreKind,
    Kind,
    PersonRole,
    Source,
)
from client.modals.card_window import CardWindow
from tests.client.conftest import host

WHEN = datetime(2026, 7, 27, 12, 0)


def window(qtbot, runtime=None) -> CardWindow:
    made = CardWindow(runtime, host())
    qtbot.addWidget(made)
    return made


def test_a_new_card_opens_empty(qtbot, theme):
    made = window(qtbot)

    made.open_new(Kind.MOVIE)

    assert made.title.input.text() == ""
    assert made.synopsis.toPlainText() == ""


def test_a_film_shows_minutes_and_a_director(qtbot, theme):
    made = window(qtbot)

    made.open_new(Kind.MOVIE)

    assert not made.runtime.isHidden()
    assert not made.director.isHidden()
    assert made.seasons.isHidden()
    assert made.developer.isHidden()


def test_a_series_shows_seasons_and_a_showrunner(qtbot, theme):
    made = window(qtbot)

    made.open_new(Kind.SERIES)

    assert not made.seasons.isHidden()
    assert not made.episodes.isHidden()
    assert not made.showrunner.isHidden()
    assert made.runtime.isHidden()
    assert made.director.isHidden()


def test_a_game_shows_a_developer_and_a_publisher(qtbot, theme):
    made = window(qtbot)

    made.open_new(Kind.GAME)

    assert not made.developer.isHidden()
    assert not made.publisher.isHidden()
    assert made.director.isHidden()
    assert made.actors.isHidden(), "состав игр приходить неоткуда"


def test_genres_are_shown_to_everyone(qtbot, theme):
    made = window(qtbot)

    for kind in (Kind.MOVIE, Kind.SERIES, Kind.GAME):
        made.open_new(kind)
        assert not made.genres.isHidden(), kind


def test_editing_fills_the_fields(qtbot, theme):
    """Окно одно: пустое заводит, заполненное правит."""
    made = window(qtbot)
    view = CardView(item_id=1, kind=Kind.MOVIE, source=Source.TMDB,
                    source_id="157336", title="Интерстеллар",
                    original_title="Interstellar", year=2014, runtime=169,
                    synopsis="про кукурузу", synced_at=WHEN)

    made.open_edit(view)

    assert made.title.input.text() == "Интерстеллар"
    assert made.original.input.text() == "Interstellar"
    assert made.year.input.text() == "2014"
    assert made.runtime.input.text() == "169"
    assert made.synopsis.toPlainText() == "про кукурузу"


def test_editing_fills_the_cast_and_the_genres_too(qtbot, theme):
    """Пустой Picker при сохранении означает не «оставить как было», а
    «стереть всё»: `save` делает `detach_all` и `set_for_item` до записи
    выбранного. Правка одного названия унесла бы весь состав и жанры."""
    made = window(qtbot)
    view = CardView(item_id=1, kind=Kind.MOVIE, source=Source.TMDB,
                    source_id="157336", title="Интерстеллар", synced_at=WHEN,
                    genres=(Genre(id=3, name="фантастика",
                                  kind=GenreKind.FILM),),
                    people=(Credit("Мэттью Макконахи", PersonRole.ACTOR),))

    made.open_edit(view)

    assert [c.name for c in made.actors.picked()] == ["Мэттью Макконахи"]
    assert [g.name for g in made.genres.picked()] == ["фантастика"]


def test_reopening_leaves_nothing_of_the_previous_card(qtbot, theme):
    """Окно одно на все карточки — половинчатая очистка даёт чужие данные."""
    made = window(qtbot)
    made.open_edit(CardView(item_id=1, kind=Kind.MOVIE, source=Source.TMDB,
                            source_id="1", title="Интерстеллар", year=2014,
                            synopsis="про кукурузу", synced_at=WHEN))

    made.open_new(Kind.MOVIE)

    assert made.title.input.text() == ""
    assert made.year.input.text() == ""
    assert made.synopsis.toPlainText() == ""


def test_the_switch_of_kind_is_remembered(qtbot, theme):
    made = window(qtbot)

    made.open_new(Kind.GAME)

    assert made.kind is Kind.GAME


def test_values_come_back_as_typed(qtbot, theme):
    made = window(qtbot)
    made.open_new(Kind.SERIES)

    made.title.input.setText("Андор")
    made.year.input.setText("2022")
    made.seasons.input.setText("2")
    made.episodes.input.setText("24")

    values = made.values()
    assert values["title"] == "Андор"
    assert values["year"] == 2022
    assert values["seasons_count"] == 2
    assert values["episodes_count"] == 24


def test_a_number_that_is_not_a_number_becomes_nothing(qtbot, theme):
    """Обязательно только название; остальное человек волен не заполнять и
    заполнить неверно."""
    made = window(qtbot)
    made.open_new(Kind.MOVIE)

    made.title.input.setText("Своё")
    made.year.input.setText("две тысячи")

    assert made.values()["year"] is None


def test_a_title_is_required(qtbot, theme):
    made = window(qtbot)
    made.open_new(Kind.MOVIE)

    assert made.values()["title"] == ""
    assert not made.can_save()

    made.title.input.setText("Своё")
    assert made.can_save()
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_card_window.py -v`
Ожидается: FAIL — `No module named 'client.modals.card_window'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/modals/card_window.py`. Раскладка по макету, и числа в ней
именно те:

| Что | Значение |
|---|---|
| ширина окна | `min(1080, доступная)` |
| ширина постера | 230, высота — полтора от неё |
| высота колонки полей | равна высоте постера |
| высота строки поля | 46 |
| промежуток между строками | 14 |
| промежуток между колонками | 36 |
| отступы окна | 34 сверху, 40 по бокам, 28 снизу |
| короткое поле (год, минуты, сезоны, серии) | 92 |
| промежуток внутри строки полей | 20 |
| промежуток между кнопками | 14 |

Высота колонки полей задана постером, а не содержимым: иначе каждое новое поле
слева растягивало бы синопсис и уводило режиссёра вниз. Под колонками — два
`Picker`, актёры и жанры; снизу две кнопки.

Поля с привязкой к типу держатся в словаре `self._for_kind`, и `open_new`
проходит по нему один раз:

```python
    _FOR_KIND = {
        "runtime": (Kind.MOVIE,),
        "director": (Kind.MOVIE,),
        "seasons": (Kind.SERIES,),
        "episodes": (Kind.SERIES,),
        "showrunner": (Kind.SERIES,),
        "developer": (Kind.GAME,),
        "publisher": (Kind.GAME,),
        "actors": (Kind.MOVIE, Kind.SERIES),
    }
```

`_clear()` обнуляет **все** поля и оба `Picker`, и зовётся из `open_new` и
`open_edit` первым делом: окно одно на все карточки, и половинчатая очистка —
это чужие данные в форме.

**`open_edit(view)` заполняет не только текстовые поля.** Оба `Picker` — актёры
из `view.people` с ролью актёра, жанры из `view.genres` — и поля ролей:
режиссёр, шоурраннер, разработчик, издатель из `view.people` и
`view.companies`. Причина не в удобстве: сохранение делает `detach_all` и
`set_for_item` **до** записи выбранного, то есть пустой `Picker` означает не
«оставить как было», а «стереть всё». Правка одного названия унесла бы с собой
весь состав и все жанры, а у игр состав заполняется только руками, и
восстановить его будет неоткуда.

Там же окно запоминает исходный `Item` в `self._item` — он нужен сохранению,
чтобы не потерять поля, которых в форме нет.

`values()` собирает словарь под `new_manual_item`: числа через безопасный
разбор — `int(text)` в `try`, иначе `None`. Обязательно только название, и это
проверяет `can_save()`.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_card_window.py -v`
Ожидается: PASS, одиннадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/dialogbar.py client/modals/card_window.py \n        client/theme/styles/modals.qss \
        tests/client/test_card_window.py
git commit -m "feat: окно карточки — раскладка и поля по типу содержимого"
```

---

### Задача 10: Окно карточки — ссылка, обложка, сохранение

**Привязка делается вставкой ссылки, а не поиском.** Если поиск находит вещь,
ручная карточка не появляется вовсе — её заводят как раз тогда, когда поиск
промахнулся.

**Галочка появляется, только когда ссылка разобрана** — она и есть единственный
признак, что адрес понят.

**Заполняется только пустое.** Чекбокс «перезаписать» виден всегда и меняет это
правило на обратное; что он значит — в подсказке.

**Обложку обрезает бэкенд.** Через границу она едет байтами: выбрал файл —
прочитал байты — отдал `posters.store_upload`, и Pillow обрежет по центру до
2:3 там же, где хранит.

**Файлы:**
- Изменить: `client/modals/card_window.py`
- Создать: `tests/client/test_card_saving.py`

**Интерфейсы:**
- Потребляет: `parse_link`, `Loader.card_for_link`, `Linker.link`,
  `new_manual_item`, `LibraryRepository.create`/`replace_fields`,
  `PosterService.store_upload`.
- Отдаёт: `CardWindow.link_state()`, `CardWindow.overwrite`,
  `CardWindow.pick_poster(path)`, сигнал `saved(int)`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_card_saving.py`:

```python
from PySide6.QtWidgets import QWidget

from backend.model import Kind, Source
from client.modals.card_window import CardWindow
from client.widgets.rowlist import BoxState
from tests.client.conftest import FakeRuntime, host


def window(qtbot, answers=None) -> tuple:
    runtime = FakeRuntime(answers or {})
    made = CardWindow(runtime, host())
    qtbot.addWidget(made)
    return made, runtime


def test_a_link_that_is_not_understood_shows_no_tick(qtbot, theme):
    made, _ = window(qtbot)
    made.open_new(Kind.MOVIE)

    made.link.input.setText("просто текст")

    assert made.tick.isHidden()


def test_an_understood_link_shows_the_tick(qtbot, theme):
    """Галочка — единственный признак, что адрес понят."""
    made, _ = window(qtbot)
    made.open_new(Kind.MOVIE)

    made.link.input.setText("https://www.themoviedb.org/movie/157336")

    assert not made.tick.isHidden()


def test_a_bare_number_works_for_films_only(qtbot, theme):
    """У игр Steam и GOG нумеруются независимо: по числу их не различить."""
    made, _ = window(qtbot)

    made.open_new(Kind.MOVIE)
    made.link.input.setText("157336")
    assert not made.tick.isHidden()

    made.open_new(Kind.GAME)
    made.link.input.setText("292030")
    assert made.tick.isHidden()


def test_clearing_the_link_hides_the_tick(qtbot, theme):
    made, _ = window(qtbot)
    made.open_new(Kind.MOVIE)
    made.link.input.setText("themoviedb.org/movie/1")

    made.link.input.setText("")

    assert made.tick.isHidden()


def test_the_overwrite_switch_has_only_two_states(qtbot, theme):
    """Это не фильтр: исключать тут нечего, и третье нажатие не должно уводить
    переключатель в «исключено»."""
    made, _ = window(qtbot)
    made.open_new(Kind.MOVIE)

    seen = [made.overwrite.state]
    for _ in range(2):
        made.overwrite.click()
        seen.append(made.overwrite.state)

    assert seen == [BoxState.OFF, BoxState.ON, BoxState.OFF]


def test_saving_a_new_card_writes_it(qtbot, theme):
    made, runtime = window(qtbot, {"library.create": 42})
    made.open_new(Kind.MOVIE)
    made.title.input.setText("Домашнее видео")

    made.save()
    qtbot.wait(30)

    assert any(name == "library.create" for name, _, _ in runtime.asked)


def test_saving_reports_the_identifier(qtbot, theme):
    made, _ = window(qtbot, {"library.create": 42})
    made.open_new(Kind.MOVIE)
    made.title.input.setText("Своё")
    heard = []
    made.saved.connect(heard.append)

    made.save()
    qtbot.wait(30)

    assert heard == [42]


def test_saving_without_a_title_writes_nothing(qtbot, theme):
    """Обязательно там только название.

    Проверяем отсутствие записи, а не молчание вообще: открытие окна законно
    спрашивает справочник жанров, и требовать пустого `asked` значило бы
    требовать, чтобы `open_new` за ним не ходил, — прямо против шага 3."""
    made, runtime = window(qtbot)
    made.open_new(Kind.MOVIE)

    made.save()

    written = {"library.create", "library.replace_fields", "posters.store_upload",
               "linker.link", "genres.set_for_item"}
    assert not [name for name, _, _ in runtime.asked if name in written]


def source_card() -> "SourceCard":
    from datetime import datetime

    from backend.model import Item, SourceCard

    return SourceCard(item=Item(
        id=0, kind=Kind.MOVIE, source=Source.TMDB, source_id="157336",
        title="Интерстеллар", synced_at=datetime(2026, 7, 27),
    ))


def test_a_link_turns_into_a_binding(qtbot, theme):
    """Привязка — это правка двух полей, а не смена идентичности: оценка,
    теги и закладка держатся за item.id."""
    made, runtime = window(qtbot, {"library.create": 42,
                                   "loader.card_for_link": source_card()})
    made.open_new(Kind.MOVIE)
    made.title.input.setText("Своё")
    made.link.input.setText("themoviedb.org/movie/157336")

    made.save()
    qtbot.wait(30)

    names = [name for name, _, _ in runtime.asked]
    assert "loader.card_for_link" in names
    assert "linker.link" in names


def test_a_source_that_did_not_answer_does_not_bind(qtbot, theme):
    """Иначе в Linker уехало бы None, и он упал бы на card.item.source."""
    made, runtime = window(qtbot, {"library.create": 42,
                                   "loader.card_for_link": None})
    made.open_new(Kind.MOVIE)
    made.title.input.setText("Своё")
    made.link.input.setText("themoviedb.org/movie/157336")
    heard = []
    made.trouble.connect(heard.append)

    made.save()
    qtbot.wait(30)

    assert not any(name == "linker.link" for name, _, _ in runtime.asked)
    assert heard, "человеку надо сказать, что привязка не вышла"


def test_saving_without_a_link_keeps_the_overwrite_off(qtbot, theme):
    """Что ты написал — остаётся твоим, приезжает только то, чего не было."""
    made, runtime = window(qtbot, {"library.create": 42,
                                   "loader.card_for_link": source_card()})
    made.open_new(Kind.MOVIE)
    made.title.input.setText("Своё")
    made.link.input.setText("themoviedb.org/movie/157336")

    made.save()
    qtbot.wait(30)

    call = next(c for c in runtime.asked if c[0] == "linker.link")
    assert call[2].get("overwrite") is False


def test_binding_passes_the_overwrite_choice(qtbot, theme):
    made, runtime = window(qtbot, {"library.create": 42,
                                   "loader.card_for_link": source_card()})
    made.open_new(Kind.MOVIE)
    made.title.input.setText("Своё")
    made.link.input.setText("themoviedb.org/movie/157336")
    made.overwrite.set_state(BoxState.ON)   # включили перезапись

    made.save()
    qtbot.wait(30)

    call = next(c for c in runtime.asked if c[0] == "linker.link")
    assert call[2].get("overwrite") is True


def test_a_chosen_poster_goes_to_the_backend_as_bytes(qtbot, theme, tmp_path):
    """Обрезает её бэкенд: работа с картинкой в главном потоке — ровно то, от
    чего окно замирает."""
    picture = tmp_path / "cover.png"
    picture.write_bytes(bytes.fromhex("89504e470d0a1a0a"))

    made, runtime = window(qtbot, {"library.create": 42})
    made.open_new(Kind.MOVIE)
    made.title.input.setText("Своё")
    made.pick_poster(str(picture))

    made.save()
    qtbot.wait(30)

    call = next(c for c in runtime.asked if c[0] == "posters.store_upload")
    assert isinstance(call[1][1], bytes)


def test_editing_replaces_instead_of_creating(qtbot, theme):
    from datetime import datetime

    from backend.model import CardView, Source

    made, runtime = window(qtbot)
    made.open_edit(CardView(item_id=7, kind=Kind.MOVIE, source=Source.MANUAL,
                            source_id="x", title="Своё",
                            synced_at=datetime(2026, 7, 27)))
    made.title.input.setText("Своё, но лучше")

    made.save()
    qtbot.wait(30)

    names = [name for name, _, _ in runtime.asked]
    assert "library.replace_fields" in names
    assert "library.create" not in names
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_card_saving.py -v`
Ожидается: FAIL — `AttributeError: 'CardWindow' object has no attribute 'tick'`.

- [ ] **Шаг 3: Реализовать**

Дописать в `client/modals/card_window.py`:

- `link.input.textChanged` → `parse_link(text, kind)`; результат непустой —
  показать `tick`, запомнить в `self._link`;
- `pick_poster(path)` читает байты в память и держит их в `self._poster`;
  выбор файла — `QFileDialog.getOpenFileName`, но сам путь приходит аргументом,
  чтобы тест обходился без диалога;
- `save()`:
  1. пустое название — выход;
  2. новая карточка — `library.create(new_manual_item(kind, **values))`;
     правка — `library.replace_fields(item_id, replace(self._item, **values))`,
     **поверх исходного `Item`, а не собранным заново**. `replace_fields` пишет
     все поля карточки, а в окне их не все: `released_at` и `poster_url` в
     форме не показываются вовсе. Собери `Item` из одних `values()` — полная
     дата выхода и адрес обложки обнулятся молча. Исходный `Item` окно берёт в
     `open_edit` и держит в `self._item`;
  3. **состав и жанры** — то, ради чего окно и заведено:
     `genres.set_for_item(item_id, genre_ids)`, и по каждому выбранному
     человеку и студии `people.ensure(credit)` → `people.attach(item_id,
     entity_id, role, position)`, то же через `companies`. Роль берётся из
     поля: режиссёр, шоураннер, актёр, разработчик, издатель. Перед записью —
     `detach_all(item_id)` у обоих репозиториев: правка заменяет состав, а не
     дописывает к нему;
  4. есть обложка — `posters.store_upload(item_id, data, now)`;
  5. разобрана ссылка — `loader.card_for_link(link)`, и **только если приехал
     `SourceCard`** — `linker.link(item_id, card, overwrite=…)`. Приехал
     `Missing` или `Refusal` — карточка уже сохранена, а про неудачу говорит
     плашка;
  6. `saved.emit(item_id)` и закрытие окна.

Каждый шаг — свой `runtime.call`; следующий запускается из обработчика
предыдущего. Цепочка длинная нарочно: между шагами приложение остаётся живым, а
любой из них может отказать, и тогда остальные просто не начинаются. У окна
есть сигнал `trouble(str)` — как у страницы ленты; `call.failed` каждого шага
идёт в него.

**Имя, введённое руками, — это `Credit` без идентичности.** `ensure` из плана 3
сам решит: нашёл тёзку без идентичности — возьмёт его, не нашёл — заведёт
нового. Выбранный из подсказки приходит с готовым идентификатором, и его
`attach` берёт напрямую, минуя `ensure`.

**Жанры подсказываются из справочника, а не из `people.suggest`.** У жанрового
`Picker` свой источник: `genres.list_for_kind(GenreKind…)` один раз при
открытии окна, дальше отбор идёт в памяти. Заводить жанр руками нельзя — он
приходит снаружи, — поэтому `created` у него отключён.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_card_saving.py -v`
Ожидается: PASS, двенадцать тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/modals/card_window.py tests/client/test_card_saving.py
git commit -m "feat: разбор ссылки, обложка и сохранение карточки"
```

---

### Задача 11: Удаление с подтверждением

**Удаление — единственное необратимое действие на карточке.**

**В подтверждении перечислено, что именно пропадёт:** оценка, теги, закладка.
Запрещающих ключей в схеме нет намеренно — иначе программа знала бы, чего
человек хочет, и всё равно заставляла бы доказывать серьёзность намерений.

**Файлы:**
- Создать: `client/widgets/confirm.py`
- Создать: `tests/client/test_confirm.py`

**Интерфейсы:**
- Потребляет: `Modal`; `LibraryRepository.deletion_summary(item_id)` и
  `LibraryRepository.delete(item_id, posters)` — **второй аргумент
  обязателен**: постер лежит во втором файле базы и каскадом не удаляется.
  Вызов целиком: `backend.library.delete(item_id, backend.posters.store)`.
- Отдаёт: `summary_text(summary: dict) -> str`;
  `ConfirmDelete(Modal)` с `ask(item_id, title)` и сигналом `confirmed(int)`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_confirm.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from client.widgets.confirm import ConfirmDelete, summary_text
from tests.client.conftest import FakeRuntime, host


def test_nothing_of_mine_is_a_short_sentence():
    assert summary_text({"has_rating": False, "tags": 0,
                         "in_wishlist": False}) == ""


def test_a_rating_is_named():
    assert "оценка" in summary_text({"has_rating": True, "tags": 0,
                                     "in_wishlist": False})


def test_tags_are_counted_and_declined():
    """1 тег, 2 тега, 5 тегов — иначе строка выглядит машинной."""
    assert "1 тег" in summary_text({"has_rating": False, "tags": 1,
                                    "in_wishlist": False})
    assert "2 тега" in summary_text({"has_rating": False, "tags": 2,
                                     "in_wishlist": False})
    assert "5 тегов" in summary_text({"has_rating": False, "tags": 5,
                                      "in_wishlist": False})


def test_everything_is_listed_together():
    text = summary_text({"has_rating": True, "tags": 3, "in_wishlist": True})

    assert "оценка" in text and "3 тега" in text and "закладка" in text


def test_the_question_names_the_card(qtbot, theme):
    runtime = FakeRuntime({"library.deletion_summary": {
        "has_rating": True, "tags": 2, "in_wishlist": False}})
    confirm = ConfirmDelete(runtime, host())

    confirm.ask(42, "Интерстеллар")
    qtbot.wait(30)

    assert "Интерстеллар" in confirm.question.text()
    assert "2 тега" in confirm.details.text()


def test_confirming_deletes_and_reports(qtbot, theme):
    runtime = FakeRuntime({"library.deletion_summary": {
        "has_rating": False, "tags": 0, "in_wishlist": False}})
    confirm = ConfirmDelete(runtime, host())
    heard = []
    confirm.confirmed.connect(heard.append)
    confirm.ask(42, "Своё")
    qtbot.wait(30)

    qtbot.mouseClick(confirm.yes, Qt.MouseButton.LeftButton)
    qtbot.wait(30)

    # Сверяем число аргументов, а не одно имя: постер лежит во втором файле
    # базы и каскадом не уходит, поэтому `delete` принимает второй аргумент.
    # Проверка имени зелена и при вызове с неверным их числом — то есть при
    # `TypeError` на живом бэкенде, где единственное необратимое действие
    # приложения просто не сработает.
    deletes = [args for name, args, _ in runtime.asked
               if name == "library.delete"]
    assert deletes and deletes[0][0] == 42
    assert len(deletes[0]) == 2, "постер вторым аргументом"
    assert heard == [42]


def test_cancelling_deletes_nothing(qtbot, theme):
    runtime = FakeRuntime({"library.deletion_summary": {
        "has_rating": False, "tags": 0, "in_wishlist": False}})
    confirm = ConfirmDelete(runtime, host())
    heard = []
    confirm.confirmed.connect(heard.append)
    confirm.ask(42, "Своё")
    qtbot.wait(30)

    qtbot.mouseClick(confirm.no, Qt.MouseButton.LeftButton)
    qtbot.wait(30)

    assert not any(name == "library.delete" for name, _, _ in runtime.asked)
    assert heard == []


def test_escape_is_the_same_as_cancel(qtbot, theme):
    """Необратимое действие не должно случаться от промаха по клавише."""
    runtime = FakeRuntime({"library.deletion_summary": {
        "has_rating": False, "tags": 0, "in_wishlist": False}})
    confirm = ConfirmDelete(runtime, host())
    confirm.ask(42, "Своё")
    qtbot.wait(30)

    qtbot.keyClick(confirm, Qt.Key.Key_Escape)

    assert not any(name == "library.delete" for name, _, _ in runtime.asked)
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_confirm.py -v`
Ожидается: FAIL — `No module named 'client.widgets.confirm'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/confirm.py`. `summary_text` собирает перечисление из
того, что вернул `deletion_summary`, склоняя число тегов той же `plural`, что
и в `facts.py`. Пустая сводка — пустая строка: перечислять нечего, и строку в
окне тогда не показываем вовсе.

Подтверждение зовёт `backend.library.delete(item_id, backend.posters.store)` —
**с постером вторым аргументом**. Без него на живом бэкенде `TypeError`, и
единственное необратимое действие приложения не работает вовсе.

Окно — `Modal` с вопросом, перечислением и двумя кнопками. Esc равен отмене —
это уже поведение `Modal`. Оформление кнопок — в `client/widgets/dialogbar.py`
(см. ниже): «Удалить» тоном `error`, «Отмена» обычная.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_confirm.py -v`
Ожидается: PASS, восемь тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/confirm.py tests/client/test_confirm.py
git commit -m "feat: подтверждение удаления с перечислением потерь"
```

---

### Задача 12: Кнопка «… ещё»

**Появляется, только когда содержимое не поместилось.** В макете она показана
всегда — и там же оговорено, что это для примера.

Два места: синопсис в карточке и длинный список актёров.

**Файлы:**
- Создать: `client/widgets/more.py`
- Изменить: `client/widgets/card.py`, `client/widgets/facts.py`
- Создать: `tests/client/test_more.py`

**Интерфейсы:**
- Потребляет: `font`, `typography`, `palette`.
- Отдаёт: `Expandable(QWidget)` — текст с обрезкой и кнопкой; поля `label`,
  `more`; методы `set_text(text)`, `expand()`; константа `SYNOPSIS_LINES` (3).

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_more.py`:

```python
from PySide6.QtCore import Qt

from client.widgets.more import SYNOPSIS_LINES, Expandable


def shown(qtbot, text: str, width: int = 400) -> Expandable:
    made = Expandable(lines=SYNOPSIS_LINES)
    qtbot.addWidget(made)
    made.setFixedWidth(width)
    made.set_text(text)
    made.show()
    qtbot.waitExposed(made)
    qtbot.wait(30)
    return made


def test_a_short_text_has_no_button(qtbot, theme):
    """Спрятанная кнопка — ловушка, лишняя — мусор."""
    made = shown(qtbot, "Коротко.")

    assert made.more.isHidden()


def test_a_long_text_gets_a_button(qtbot, theme):
    made = shown(qtbot, "Длинная строка синопсиса. " * 40)

    assert not made.more.isHidden()


def test_the_text_is_clipped_until_expanded(qtbot, theme):
    made = shown(qtbot, "Длинная строка синопсиса. " * 40)
    clipped = made.height()

    made.expand()
    qtbot.wait(30)

    assert made.height() > clipped


def test_expanding_hides_the_button(qtbot, theme):
    """Разворачивать второй раз нечего."""
    made = shown(qtbot, "Длинная строка синопсиса. " * 40)

    qtbot.mouseClick(made.more, Qt.MouseButton.LeftButton)
    qtbot.wait(30)

    assert made.more.isHidden()


def test_setting_a_new_text_folds_it_back(qtbot, theme):
    """Карточка переиспользуется: развёрнутый синопсис не должен достаться
    следующей."""
    made = shown(qtbot, "Длинная строка синопсиса. " * 40)
    made.expand()
    qtbot.wait(30)

    made.set_text("Длинная строка синопсиса. " * 40)
    qtbot.wait(30)

    assert not made.more.isHidden()


def test_a_narrower_widget_needs_the_button_sooner(qtbot, theme):
    """Текст перетекает — решение о кнопке зависит от ширины, а не от длины
    строки в символах."""
    text = "Строка синопсиса средней длины. " * 4

    wide = shown(qtbot, text, width=900)
    narrow = shown(qtbot, text, width=200)

    assert wide.more.isHidden()
    assert not narrow.more.isHidden()


def test_an_empty_text_shows_nothing(qtbot, theme):
    made = shown(qtbot, "")

    assert made.more.isHidden()
    assert made.label.text() == ""
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_more.py -v`
Ожидается: FAIL — `No module named 'client.widgets.more'`.

- [ ] **Шаг 3: Реализовать**

Создать `client/widgets/more.py`. `Expandable` держит полный текст, а показывает
`QLabel` с ограниченной высотой: `maximumHeight = lines × QFontMetrics.lineSpacing`.
Нужна ли кнопка — решает сравнение `label.heightForWidth(width)` с этой
границей; поэтому пересчёт идёт и в `resizeEvent`, а не только в `set_text`.

`set_text` всегда возвращает виджет в свёрнутое состояние: карточка
переиспользуется, и развёрнутый синопсис не должен достаться следующей.

В карточке `Expandable` заменяет `self.synopsis`; в `FactsBlock` — список
актёров, где вместо строк обрезается число показанных имён.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_more.py tests/client/test_card.py -v`
Ожидается: PASS — семь тестов кнопки и двадцать тестов карточки.

- [ ] **Шаг 5: Коммит**

```bash
git add client/widgets/more.py client/widgets/card.py \
        client/widgets/facts.py tests/client/test_more.py
git commit -m "feat: кнопка «… ещё» у синопсиса и списка актёров"
```

---

### Задача 13: Гистограмма

Десять столбцов и подвал под ними. Заглушка `StatsPage` из плана 5 наполняется.

**Цвет столбца — из той же шкалы, что у звёзд.**

**Столбцы вырастают из пола при каждом заходе на вкладку**, с задержкой 45 мс
на столбец. Растёт высота, а не масштаб: масштаб сплющил бы и число над
столбцом.

**Ширина равна содержимому шапки** — график живёт в той же колонке, что поиск,
переключатель и кнопки.

**Файлы:**
- Изменить: `client/pages/stats.py`
- Создать: `tests/client/test_stats.py`

**Интерфейсы:**
- Потребляет: `Histogram`, `Bucket`, `Filters`, `Kind`; `palette`, `font`.
- Отдаёт: `Bar(QWidget)` с `bind(bucket, peak)`; `StatsPage(QWidget)` с
  `show_for(kind, filters)`, `bind(histogram)`, `set_content_width(width)`,
  полями `bars`, `footer`; константа `BAR_DELAY` (45).

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_stats.py`:

```python
from backend.model import Bucket, Filters, Histogram, Kind
from client.pages.stats import BAR_DELAY, StatsPage
from tests.client.conftest import FakeRuntime, host


def histogram(counts, total=None, average=None) -> Histogram:
    buckets = tuple(Bucket(score=score, count=count)
                    for score, count in enumerate(counts, start=1))
    return Histogram(buckets=buckets,
                     total=total if total is not None else sum(counts),
                     average=average)


def page(qtbot) -> StatsPage:
    made = StatsPage(FakeRuntime())
    qtbot.addWidget(made)
    made.resize(900, 500)
    made.show()
    qtbot.waitExposed(made)
    return made


def test_there_are_always_ten_bars(qtbot, theme):
    made = page(qtbot)

    made.bind(histogram([0] * 10))

    assert len(made.bars) == 10


def test_the_tallest_bar_fills_the_plot(qtbot, theme):
    made = page(qtbot)

    made.bind(histogram([1, 2, 3, 4, 5, 6, 7, 8, 9, 100]))
    qtbot.wait(BAR_DELAY * 10 + 600)

    assert made.bars[9].fill.height() > made.bars[0].fill.height() * 5


def test_an_empty_column_is_still_visible(qtbot, theme):
    """Пустой столбец — это сведение, а не отсутствие данных."""
    made = page(qtbot)

    made.bind(histogram([0] * 10))
    qtbot.wait(BAR_DELAY * 10 + 600)

    assert all(bar.fill.height() > 0 for bar in made.bars)


def test_every_bar_carries_its_count_and_its_score(qtbot, theme):
    made = page(qtbot)

    # Числа свои, а не из макета: там они подставные, и ссылаться на них
    # нельзя ни в чём. Один заметный пик и один ноль — этого хватает.
    made.bind(histogram([2, 0, 4, 9, 15, 31, 62, 48, 21, 6]))

    assert made.bars[6].count.text() == "62"
    assert made.bars[6].value.text() == "7"


def test_the_footer_shows_the_average_and_the_total(qtbot, theme):
    made = page(qtbot)

    made.bind(histogram([0] * 9 + [4], total=4, average=9.75))

    assert "9.75" in made.footer.text()
    assert "4" in made.footer.text()


def test_the_footer_names_the_kind(qtbot, theme):
    made = page(qtbot)
    made.set_kind(Kind.GAME)

    made.bind(histogram([1] * 10, average=5.5))

    assert "игр" in made.footer.text()


def test_an_empty_library_says_so_without_an_average(qtbot, theme):
    """Считать нечего — и выдумывать ноль незачем: ноль это оценка."""
    made = page(qtbot)

    made.bind(histogram([0] * 10, total=0, average=None))

    # Проверяем отсутствие самой рубрики, а не наличие нуля: «Средняя
    # оценка: 0.00» содержит «0» — то есть тест проходил бы ровно на той
    # выдумке, от которой сторожит.
    assert "Средняя" not in made.footer.text()
    assert "None" not in made.footer.text()


def test_the_bars_grow_one_after_another(qtbot, theme):
    """Задержка 45 мс на столбец — это уже внутри страницы, а не переход."""
    made = page(qtbot)

    made.bind(histogram([10] * 10))
    qtbot.wait(BAR_DELAY * 2 + 20)

    # Замеряем поведение, а не поле, которое реализация себе присвоила:
    # столбцы должны расти по очереди, а не все разом.
    assert made.bars[0].fill.height() > 0
    assert made.bars[9].fill.height() == 0


def test_reopening_grows_them_again(qtbot, theme):
    """Столбцы вырастают при каждом заходе на вкладку."""
    made = page(qtbot)
    made.bind(histogram([10] * 10))
    qtbot.wait(BAR_DELAY * 10 + 600)

    made.replay()

    assert made.bars[0].fill.height() < made.bars[0].target


def test_the_width_follows_the_top_bar(qtbot, theme):
    """График живёт в той же колонке, что поиск, переключатель и кнопки."""
    made = page(qtbot)

    made.set_content_width(700)

    assert made.chart.maximumWidth() == 700
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_stats.py -v`
Ожидается: FAIL — `ImportError: cannot import name 'BAR_DELAY'`.

- [ ] **Шаг 3: Реализовать**

Переписать `client/pages/stats.py`. `Bar` — колонка из подписи-числа сверху,
заливки и подписи оценки снизу. Минимум высоты — 6 пикселей, как в макете:
пустой столбец должен быть виден.

**Высота заливки анимируется своим свойством, а не `maximumHeight`.** У заливки
в колонке с распоркой сверху `minimumHeight` равен нулю, и менеджер раскладки
даёт ей ровно ноль, сколько бы ни был максимум: столбцов на экране не будет
вовсе. Поэтому у `Bar` объявляется `Property(int)`, чей сеттер зовёт
`setFixedHeight`, и `QPropertyAnimation` идёт по нему — с задержкой
`BAR_DELAY × индекс`.

**У отложенного запуска должен быть владелец:** `QTimer.singleShot(delay, self,
…)` либо `QTimer` полем столбца. Без владельца таймер переживёт виджет и
выстрелит в удалённый объект — в прогоне это выглядит как тесты, зелёные
поодиночке и красные в пачке.

`show_for(kind, filters)` идёт в `feed.histogram(kind, filters)` через
`runtime.call` и отдаёт результат в `bind`. `replay()` перезапускает анимацию —
её зовёт окно при каждом заходе на страницу.

Подвал: «Средняя оценка: 7.31 • Всего фильмов: 248». Подпись типа берётся из
словаря; разделитель — тот же маркер `•`, что и в подсказке к тёзкам. Пустая
библиотека рубрику про среднюю не показывает вовсе: средней у неё нет, а ноль
на её месте — выдумка.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_stats.py -v`
Ожидается: PASS, десять тестов.

- [ ] **Шаг 5: Коммит**

```bash
git add client/pages/stats.py tests/client/test_stats.py
git commit -m "feat: гистограмма со столбцами и подвалом"
```

---

### Задача 14: Сборка и полный прогон

Последняя задача. Модалки связываются с окном, карточка получает свои действия,
и приложение впервые работает целиком.

**Файлы:**
- Изменить: `client/window.py`, `client/pages/feed.py`
- Создать: `tests/client/test_wiring.py`

**Интерфейсы:**
- Потребляет: всё, что построено задачами 1–13 и планом 5.
- Отдаёт: `MainWindow` со всеми модалками и связями.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/client/test_wiring.py`:

```python
from backend.model import Filters, Kind
from client.widgets.toolbar import View
from client.window import MainWindow
from tests.client.conftest import FakeRuntime, host


def views(count: int):
    from datetime import datetime

    from backend.model import CardView, Source

    return [CardView(item_id=100 + n, kind=Kind.MOVIE, source=Source.TMDB,
                     source_id=str(n), title=f"Фильм {n}",
                     synced_at=datetime(2026, 7, 27))
            for n in range(count)]


def game_views(count: int):
    from datetime import datetime

    from backend.model import CardView, Source

    return [CardView(item_id=200 + n, kind=Kind.GAME, source=Source.STEAM,
                     source_id=str(n), title=f"Игра {n}",
                     synced_at=datetime(2026, 7, 27))
            for n in range(count)]


def window(qtbot, runtime=None):
    """Рантайм обязателен: модалки ходят в бэкенд при открытии, и окно с None
    падало бы на первом же нажатии кнопки фильтра."""
    made = MainWindow(runtime=runtime or FakeRuntime())
    qtbot.addWidget(made)
    made.resize(1200, 800)
    made.show()
    qtbot.waitExposed(made)
    return made


def test_a_filter_button_opens_its_modal(qtbot, theme):
    made = window(qtbot)

    made.topbar.tools.filter_clicked.emit("genres")
    qtbot.wait(30)

    assert not made.modals["genres"].isHidden()


def test_a_lit_filter_button_resets_instead(qtbot, theme):
    made = window(qtbot)
    made.filters = Filters(genre_ids=(1,))

    made.topbar.tools.filter_reset.emit("genres")
    qtbot.wait(30)

    assert made.filters == Filters()
    assert made.modals["genres"].isHidden()


def test_a_changed_filter_reaches_the_feed(qtbot, theme):
    made = window(qtbot)
    heard = []
    made._pages["list"].show_section = lambda *args: heard.append(args)

    made.on_filters_changed(Filters(tag_ids=(3,)))

    assert heard and heard[-1][2] == Filters(tag_ids=(3,))


def test_the_filter_button_lights_while_the_filter_is_set(qtbot, theme):
    made = window(qtbot)

    made.on_filters_changed(Filters(genre_ids=(1,)))

    assert made.topbar.tools.filter_button("genres").property("on") == "true"


def test_switching_the_kind_clears_the_modals_too(qtbot, theme):
    """Наборы тегов у трёх типов независимы: показанный список устарел."""
    made = window(qtbot)
    made.filters = Filters(tag_ids=(1,))

    made.on_kind_changed(Kind.GAME)

    assert made.filters == Filters()
    for name in ("genres", "tags", "scores"):
        assert made.topbar.tools.filter_button(name).property("on") == "false"


def test_the_plus_opens_an_empty_card_window(qtbot, theme):
    made = window(qtbot)

    made.topbar.tools.add_clicked.emit()
    qtbot.wait(30)

    assert not made.card_window.isHidden()
    assert made.card_window.title.input.text() == ""


def test_the_card_window_opens_for_the_current_kind(qtbot, theme):
    """Тип берётся из переключателя: он всегда на виду."""
    made = window(qtbot)
    made.on_kind_changed(Kind.SERIES)

    made.topbar.tools.add_clicked.emit()
    qtbot.wait(30)

    assert made.card_window.kind is Kind.SERIES


def test_the_tag_chip_opens_the_card_tags(qtbot, theme):
    made = window(qtbot)

    made._pages["list"].tags_wanted.emit(42)
    qtbot.wait(30)

    assert not made.item_tags.isHidden()


def test_deleting_asks_first(qtbot, theme):
    """Единственное необратимое действие на карточке."""
    made = window(qtbot)

    made._pages["list"].delete_wanted.emit(42, "Интерстеллар")
    qtbot.wait(30)

    assert not made.confirm.isHidden()


def test_the_statistics_asks_for_its_numbers(qtbot, theme):
    made = window(qtbot)
    heard = []
    made._pages["stats"].show_for = lambda kind, filters: heard.append(kind)

    made.on_view_changed(View.STATS)

    assert heard == [made._kind]


def test_the_statistics_obeys_the_filters(qtbot, theme):
    """Гистограмма строится по тому же отфильтрованному набору."""
    made = window(qtbot)
    heard = []
    made._pages["stats"].show_for = lambda kind, filters: heard.append(filters)
    made.filters = Filters(tag_ids=(2,))

    made.on_view_changed(View.STATS)

    assert heard == [Filters(tag_ids=(2,))]


def test_a_score_of_a_film_is_written(qtbot, theme):
    """Главная задача приложения, и до сих пор она не проверялась ничем.
    У кино шкала одна, её номер -1."""
    runtime = FakeRuntime()
    made = window(qtbot, runtime)
    page = made._pages["list"]
    page.feed.set_rows(views(3))
    qtbot.wait(30)

    page.feed.score_picked.emit(1, -1, 8)
    qtbot.wait(30)

    call = next(c for c in runtime.asked if c[0] == "ratings.set_score")
    assert call[1][0] == page.feed.rows[1].view.item_id
    assert call[1][1] == 8


def test_a_score_of_a_game_goes_to_the_three_scales(qtbot, theme):
    """У игры оценка — среднее трёх шкал, и пишутся они вместе."""
    runtime = FakeRuntime()
    made = window(qtbot, runtime)
    page = made._pages["list"]
    page.feed.set_rows(game_views(1))
    qtbot.wait(30)

    page.feed.score_picked.emit(0, 1, 9)

    qtbot.wait(30)
    names = [name for name, _, _ in runtime.asked]
    assert "ratings.set_aspects" in names
    assert "ratings.set_score" not in names


def test_a_bookmark_goes_both_ways(qtbot, theme):
    runtime = FakeRuntime()
    made = window(qtbot, runtime)
    page = made._pages["list"]
    page.feed.set_rows(views(2))
    qtbot.wait(30)

    page.feed.wish_toggled.emit(0, True)
    page.feed.wish_toggled.emit(0, False)
    qtbot.wait(30)

    names = [name for name, _, _ in runtime.asked]
    assert "wishlist.add" in names
    assert "wishlist.remove" in names


def test_the_row_is_redrawn_after_a_write(qtbot, theme):
    """Иначе вердикт и средняя останутся старыми до перезахода в раздел."""
    runtime = FakeRuntime()
    made = window(qtbot, runtime)
    page = made._pages["list"]
    page.feed.set_rows(views(2))
    qtbot.wait(30)

    page.feed.score_picked.emit(0, -1, 7)
    qtbot.wait(30)

    assert any(name == "views.views_for" for name, _, _ in runtime.asked)


def test_a_card_action_reaches_the_page_through_the_feed(qtbot, theme):
    """Между карточкой и страницей стоит лента: если она сигнал не
    пробрасывает, нажатие на карточке не делает ничего, а тест, эмитящий
    сигнал страницы руками, этого не заметит."""
    made = window(qtbot, FakeRuntime())
    page = made._pages["list"]
    page.feed.set_rows(views(3))
    qtbot.wait(30)

    row = next(r for r in page.feed.rows if r.card is not None)
    heard = []
    page.feed.tags_wanted.connect(heard.append)

    row.card.add_tag_clicked.emit()

    assert heard == [row.card.property("row")]
```

- [ ] **Шаг 2: Убедиться, что тест падает**

Запустить: `pipenv run pytest tests/client/test_wiring.py -v`
Ожидается: FAIL — `AttributeError: 'MainWindow' object has no attribute 'modals'`.

- [ ] **Шаг 3: Связать**

Дописать в `MainWindow`: словарь `self.modals` с тремя фильтрами,
`self.item_tags`, `self.card_window`, `self.confirm`. Связи:

| Откуда | Куда |
|---|---|
| `tools.filter_clicked` | `modals[name].open_for(kind)` |
| `tools.filter_reset` | `modals[name].reset()` и обновление ленты |
| `modal.filters_changed` | `on_filters_changed` — свести три фильтра в один `Filters`, зажечь кнопки, перерисовать ленту и статистику |
| `tools.add_clicked` | `card_window.open_new(kind)` |
| страница `card_edit_wanted` | `card_window.open_edit(view)` |
| страница `tags_wanted` | `item_tags.open_for(item_id, kind)` |
| страница `delete_wanted` | `confirm.ask(item_id, title)` |
| `confirm.confirmed` | убрать строку из ленты |
| `card_window.saved` | перерисовать ленту |
| `item_tags.tags_changed` | перерисовать одну карточку через `backend.views` |

**Между карточкой и страницей стоит лента, и она эти сигналы не пробрасывает.**
`FeedView._wire` из плана 5 связывает только `toggled` и `score_picked`;
`edit_clicked`, `delete_clicked`, `add_tag_clicked` и `wish_toggled` не идут
никуда. Значит правится и `client/widgets/feed.py` — `_wire` дополняется:

```python
        # Остальные действия карточка только просит — решает страница.
        for signal, out in ((card.edit_clicked, self.edit_wanted),
                            (card.delete_clicked, self.delete_wanted),
                            (card.add_tag_clicked, self.tags_wanted)):
            signal.connect(
                lambda _=False, c=card, out=out: out.emit(c.property("row"))
            )
        card.wish_toggled.connect(
            lambda on, c=card: self.wish_toggled.emit(c.property("row"), on)
        )
```

и у `FeedView` появляются сигналы `edit_wanted(int)`, `delete_wanted(int)`,
`tags_wanted(int)`, `wish_toggled(int, bool)` — все с номером строки.

Дописать в `FeedPage` сигналы `card_edit_wanted(object)`, `tags_wanted(int)`,
`delete_wanted(int, str)`, `wish_toggled(int, bool)`: страница переводит номер
строки в идентификатор и название, и она же пишет в базу.

Оценка: у кино `ratings.set_score(item_id, score, now)`, у игры
`ratings.set_aspects(item_id, visual, narrative, gameplay, now)` — номер шкалы
приходит первым аргументом `score_picked`, `-1` означает единственную. Закладка:
`wishlist.add(item_id, now)` или `wishlist.remove(item_id)`. После каждой записи
строка перерисовывается через `views.views_for([item_id])` — иначе вердикт и
средняя останутся старыми.

- [ ] **Шаг 4: Убедиться, что тесты проходят**

Запустить: `pipenv run pytest tests/client/test_wiring.py -v`
Ожидается: PASS, одиннадцать тестов.

- [ ] **Шаг 5: Прогнать всё целиком**

Запустить: `pipenv run pytest -v`
Ожидается: PASS, весь набор планов 1–6.

- [ ] **Шаг 6: Посмотреть глазами**

Запустить: `pipenv run python main.py`

Пройти сценарии:

1. поиск по названию — своё сразу, внешнее следом;
2. оценка ставится, снимается повторным кликом, переживает перезапуск;
3. фильтры по жанру, тегу и оценке, включая исключение;
4. теги: завести, переставить, повесить на карточку, удалить;
5. карточка заводится руками, правится, привязывается по ссылке;
6. удаление с подтверждением;
7. статистика: столбцы отрастают, подвал считает;
8. без сети: своё показывается, плашка сообщает.

**Это единственная проверка внешнего вида.** Всё, что тестами не покрыто —
цвета, отступы, стекло модалки без размытия, гало кромки градиентом, — смотрится
здесь и правится в `client/theme/`.

- [ ] **Шаг 7: Коммит**

```bash
git add client tests/client/test_wiring.py
git commit -m "feat: связать модалки с окном — приложение работает целиком"
```

---

## Что этот план сознательно не делает

| Что | Куда |
|---|---|
| Рекомендации | отложено спекой модели данных: сначала профиль вкуса |
| Отдельные шкалы у игр в фильтре и гистограмме | отложено спекой разделов: схема готова, работа в запросах и интерфейсе |
| Пагинация внешнего поиска | не делаем: контракт клиентов плана 2 без номера страницы |
| Переименование тега | не делаем: `TagsRepository.rename` есть с плана 1, но в макете этого жеста нет |
| Слияние двух людей | не делаем: см. `docs/specs/2026-07-27-people.md` |
| Размытие под модалкой | не делаем: в Qt нет `backdrop-filter`, а снимок окна с размытием на каждое открытие стоит дороже, чем даёт |

## Числа и правила, взятые не из спек

| Что | Значение | Почему так |
|---|---|---|
| Стекло модалки без размытия | так | `backdrop-filter` в Qt нет; панель остаётся тёмной полупрозрачной. Первое, на что смотреть глазами |
| `MIN_THUMB` | 28 | из макета |
| `HIDE_AFTER` | 700 мс | из макета |
| `EDGE_ZONE`, `EDGE_SPEED` | 48 и 13 | из макета |
| Ключ строки списка | идентификатор, а не имя | имена тегов меняются, фильтр держится за строку |
| Порядок в фильтре по оценке | сверху десятка | из макета; высокие оценки нужнее |
| Пустая сводка удаления — пустая строка | так | перечислять нечего, и строку тогда не показываем вовсе |
| Перетаскивание разложено на три метода | `start_drag`, `drag_to`, `end_drag` | так порядок проверяется без мыши |
| `SYNOPSIS_LINES` | 3 | в макете обрезка показана, но число не названо |

## Что осталось описанным прозой

Половина задач даёт тесты и правила, но не код. Тесты в них точны настолько,
чтобы задать API, — но не настолько, чтобы по ним нельзя было написать
неверную реализацию. Места, где исполнителю придётся решать самому:

| Где | Чего не хватает |
|---|---|
| задача 5, `FilterModal._load` и `_pack` | тела; подпись и правило про пустой рантайм записаны |
| задача 7, `ItemTagsModal` | тела целиком |
| задача 9, `CardWindow` | сборка раскладки; числа и состав полей записаны |
| задача 10, `save()` | тела шести шагов; порядок и правила записаны |
| задача 11, `ConfirmDelete` | тела; `summary_text` покрыт тестами полностью |
| задача 12, `Expandable` | тела; в `expand()` и `set_text` обязателен `adjustSize`, иначе виджет не вырастет |
| задача 13, `Bar` и `StatsPage` | тела; числа анимации записаны неполно |
| задача 14, связывание | тела обработчиков; таблица связей полная |

## Чего в плане нет, а в макете есть

Записано **значениями, а не ссылками на `docs/design/`.** Папка объявлена черновиком
и будет удалена; строка вида «см. `index.html:868`» после этого перестаёт что-то
означать, а до этого подталкивает взять готовое оттуда вместо переноса. Всё
нужное перенесено сюда числами — доделывать это можно уже без макета.

Записано честно, чтобы не выглядело сделанным:

| Что | Где в макете |
|---|---|
| Кромка модалки с восемью точками градиента и гало **над** панелью | Нить высотой 1 идёт от левого края +24 до правого −24; доли акцента по длине: 0, 18, 55, 88, 100, 88, 55, 18, 0 %. Гало — отдельный слой высотой 24, поднятый на 11 над панелью, доли 0, 4, 15, 15, 4, 0 %, размытие 12. `NeonEdge` плана 5 гасит нить двумя точками и льёт гало вниз |
| Тень панели | `0 30px 90px rgba(0, 0, 0, 0.6)` плюс две внутренние: `inset 0 1px 0` белым 14 % и `inset 0 -1px 0` чёрным 25 %. В QSS теней нет, нужен `QGraphicsDropShadowEffect`. Сейчас панель отделена от фона только рамкой — вместе с отказом от размытия это главное, на что смотреть глазами |
| Ручка перетаскивания: шесть квадратов 4×4 с шагом 4 | Два столбца по три, белые, прозрачность 0.28, под курсором 0.7, курсор `grab`. В плане это пустая кнопка 12×16 |
| Своя полоса прокрутки у синопсиса | `ScrollArea` обёрнута вокруг `QScrollArea` и к `QTextEdit` не прикладывается — нужна вторая реализация или общий источник диапазона |
| Кнопка «… ещё» стоит **в строке** текста | В плане это отдельный виджет под абзацем |
| Числа гистограммы | Столбец: скругление верхушки 5, минимальная высота 6, промежуток между столбцами 14, между заливкой и подписью 7, запас сверху под число 34 и 16 снизу. Число над столбцом — отступ 5, вес 700, цветом столбца; подпись оценки — вес 700, белая. Подвал: отступ сверху 14, черта над ним белым 7 %, текст белым 45 %, выделенное белым 80 % и весом 600. Рост: 0.5 с, кривая `cubic-bezier(.2, .8, .2, 1)`, задержка 45 мс на столбец. Из перечисленного в задаче 13 записаны только задержка и минимальная высота |
| Наведение на строку подсказки с постером | `docs/specs/2026-07-27-people.md:75–84`; `Suggestion.hint_item_id` заведён под это и не используется |
| Предупреждение о совпадении названия | `docs/specs/2026-07-27-manual-cards.md:117–128` |
| `ItemExists` при привязке к занятой идентичности | `docs/specs/2026-07-27-manual-cards.md:78–80` |
| Обложка перетаскиванием и из буфера | `docs/specs/2026-07-27-manual-cards.md:109–110`; сделан только диалог выбора файла |

## Открытые вопросы

**Как выглядит окно подтверждения удаления.** В макете его нет: там пять
накладок, и подтверждения среди них нет ни одной. Состав, порядок и оформление
придуманы здесь — вопрос, помечать, что окно ещё не нарисовано.

**Как выглядит модалка без размытия.** В макете под ней размывается фон, в Qt
этого нет. Панель остаётся тёмным стеклом; смотреть глазами на шаге 6 задачи 14
и решать, хватает ли отделения от фона.

**Что показывает окно карточки, пока едет ответ на привязку.** Ссылка разобрана,
`card_for_link` ушёл в сеть, галочка уже горит — а данные ещё не приехали. Ни
спека, ни макет про этот промежуток не говорят.

**Переименование тега.** `TagsRepository.rename` написан планом 1 и не зовётся
ниоткуда. В макете строка тега не редактируется; если жест нужен, он и рисуется,
и делается отдельно.

**Ширина списка совпадений при длинных именах.** В макете список равен ширине
поля, а поле — ширине постера. Длинное имя с длинным названием фильма туда не
поместится; обрезка многоточием или перенос — решается глазами.

