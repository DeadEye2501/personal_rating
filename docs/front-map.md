# Карта фронта

Собрана из кода. Число в скобках — строк в файле.

## api — 1 файлов

### api/bridge.js (105)
- Единственное место страницы, которое знает про `window.pywebview`.
- отдаёт: Failed, call, cancel, lastOp, numbered, ready

## app — 5 файлов

### app/App.svelte (50)
- Корень страницы: шапка, стопка разделов и плашка сообщений.
- берёт: ./LibraryScreen.svelte, ./SearchScreen.svelte, ./StatsScreen.svelte, ./Topbar.svelte

### app/LibraryScreen.svelte (3)
- Обе половины библиотеки: «Оценённые» и «Хочу посмотреть». Различает их `session.section`, он же уезжает в запрос. Пока пуст.

### app/SearchScreen.svelte (2)
- Раздел «Поиск»: сначала своя выдача, потом внешняя. Пока пуст.

### app/StatsScreen.svelte (2)
- Раздел «Статистика»: гистограмма своих оценок. Пока пуст.

### app/Topbar.svelte (147)
- Сборка шапки: три зоны и всё, что в них нажимается.
- принимает: session, onsession, onsearch, onadd, onfilter

## components — 5 файлов

### components/Icon.svelte (6)
- Глиф Material Symbols.
- принимает: name, extra

### components/SearchField.svelte (30)
- Поле поиска с кнопкой очистки.
- принимает: onsearch

### components/Segmented.svelte (17)
- Капсульный переключатель: один выбранный из нескольких.
- принимает: items, chosen, onchoose

### components/Snack.svelte (41)
- Плашка сообщений: одна на всё приложение.
- принимает: message

### components/ToolButton.svelte (17)
- Круглая кнопка ряда в шапке.
- принимает: icon, dir, label, active, pressed, onclick, children

## state — 4 файлов

### state/filters.js (103)
- Три состояния строки фильтра: не выбран, включён, исключён.
- отдаёт: EMPTY, chosen, cleared, cycled, isEmpty, marked, passes

### state/redraw.js (20)
- Перезапуск анимации: снять признак, заставить браузер пересчитать стили и * вернуть признак обратно. * * Пересчёт посреди — не украшение, а весь смысл. Браузер сличает состояние на * конец задачи, и снятый в той же задаче класс для него не снимался вовсе. * Отложить возврат кадром не помогает: колбэк `requestAnimationFrame` * выполняется **до** пересчёта стилей того же кадра. Чтение `offsetWidth` * пересчёт вызывает принудительно — приём, которым это сделано и в макете. * * Вынесено сразу, потому что второй потребитель известен и близок: тем же * приёмом отрастает гистограмма в плане 8. * * Это способ для узла, который обязан пережить перезапуск, — кнопки, столбика. * Там, где узел можно пересоздать целиком, анимация заводится сама, и * пересоздание дешевле: так сделан переход между разделами.
- отдаёт: redrawn

### state/session.js (43)
- Выбранное в приложении вместе с переходами между выборами.
- отдаёт: newSession, withCollapsed, withKind, withNextSort, withSection, withToggledSection

### state/sorting.js (70)
- Все состояния переключателя сортировки. Набор у раздела свой: в «Оценённых» восемь, в отложенном четыре, и выбирает его `cycleOf`.
- отдаёт: ADDED_AT, SORT_STATES, cycleOf, hasSort, nextSort, orderFor, stateAt

## styles — 9 файлов

### styles/base.css (118)
- Правила, действующие на всю страницу сразу, а не на её блок.
- селекторы (15): *, *::before, *::after, [hidden], html, body, #root, body, :focus-visible, ::selection, .material-symbols-outlined, .is-active > .material-symbols-outlined,
.is-on > .material-symbols-outlined, .app, .app::before,
.app::after, .app::before, .app::after, .app__main, .content, @media (prefers-reduced-motion: reduce)
- берёт: --bg, --body-m, --fill-primary-hover, --primary, --text, --text-bright

### styles/neon.css (49)
- Общий приём: полоса по верхней кромке, гаснущая к краям, гало под ней и свечение текста. Цвет из --neon, высоту гало из --halo-h ставит тот, кто применяет класс.
- селекторы (3): .neon, .neon::before, .neon::after
- объявляет: --halo-h
- берёт: --halo-h, --neon, --opaque

### styles/palette.css (107)
- Единственное место, где есть цвет. По месту пишется только var().
- селекторы (2): @property --primary, :root
- объявляет: --accent-game, --accent-movie, --accent-series, --bg, --body-l, --body-m, --error, --fill-primary-14, --fill-primary-hover, --font, --glass, --glass-error, --label-l, --label-m, --opaque, --r-card, --r-full, --score-1, --score-10, --score-2, --score-3, --score-4, --score-5, --score-6, --score-7, --score-8, --score-9, --shade-25, --shade-32, --shade-55, --shade-60, --surface-pop, --text, --text-bright, --text-dim, --tint-02, --tint-035, --tint-05, --tint-06, --tint-07, --tint-09, --tint-10, --tint-14, --tint-16, --tint-18, --tint-22, --tint-25, --tint-28, --tint-30, --tint-34, --tint-35, --tint-40, --tint-45, --tint-55, --tint-75, --tint-80, --tint-85, --title-l, --title-s
- берёт: --font, --primary

### styles/search.css (78)
- Поле поиска в левой зоне шапки.
- селекторы (11): .search, .search:hover, .search:focus-within, .search__icon, .search:focus-within .search__icon, .search__input, .search__input::placeholder, .search__input::-webkit-search-cancel-button,
.search__input::-webkit-search-decoration, .search__clear, .search__clear .material-symbols-outlined, .search__clear:hover
- берёт: --body-l, --fill-primary-14, --primary, --r-full, --side-w, --text, --tint-035, --tint-05, --tint-06, --tint-10, --tint-28, --tint-35

### styles/seg.css (46)
- Капсула переключателя типа содержимого.
- селекторы (6): .seg, .seg__btn, .seg__btn .material-symbols-outlined, .seg__btn:hover, .seg__btn.is-active, .seg__btn.is-active:hover
- берёт: --fill-primary-14, --primary, --r-full, --tint-035, --tint-05, --tint-06, --tint-45, --tint-75, --title-s

### styles/snack.css (25)
- Единственное место, где приложение что-то сообщает: и отказ источника, и непредвиденный сбой. Уехавшая вниз плашка пустая — отсутствие сообщений само себя ничем не обозначает.
- селекторы (2): .snack, .snack.is-shown
- объявляет: --halo-h, --neon
- берёт: --body-m, --error, --glass-error, --r-full

### styles/tools.css (83)
- Ряд круглых кнопок в правой зоне шапки.
- селекторы (13): .tools, .tools__btn, .tools__btn .material-symbols-outlined, .tools__btn:hover, .tools__btn.is-active, .tools__btn:has(.tools__dir) .material-symbols-outlined, .tools__dir, .tools__chart, .tools__chart rect, .is-drawing .tools__chart rect, .is-drawing .tools__chart rect:nth-child(2), .is-drawing .tools__chart rect:nth-child(3), @keyframes bar-grow
- берёт: --fill-primary-14, --primary, --r-full, --side-w, --tint-035, --tint-05, --tint-06, --tint-45, --tint-75

### styles/topbar.css (27)
- Раскладка шапки: три зоны, из ширины которых выведен минимум окна.
- селекторы (2): .topbar, .topbar__seg
- объявляет: --corner, --side-w
- берёт: --corner

### styles/view.css (17)
- Стопка разделов: виден один, переход между ними — проявление.
- селекторы (3): .view, .view.is-shown, @keyframes screen-in
