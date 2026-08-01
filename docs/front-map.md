# Карта фронта

Собрана из кода. Число в скобках — строк в файле.

## api — 1 файлов

### api/bridge.js (105)
- Единственное место страницы, которое знает про `window.pywebview`.
- отдаёт: Failed, call, cancel, lastOp, numbered, ready

## app — 1 файлов

### app/App.svelte (12)
- Корень страницы: показывает, дождалась ли она моста.

## state — 3 файлов

### state/filters.js (103)
- Три состояния строки фильтра: не выбран, включён, исключён.
- отдаёт: EMPTY, chosen, cleared, cycled, isEmpty, marked, passes

### state/session.js (31)
- Выбранное в приложении вместе с переходами между выборами.
- отдаёт: newSession, withCollapsed, withKind, withSection

### state/sorting.js (65)
- Все состояния переключателя сортировки. Набор у раздела свой: в «Оценённых» восемь, в отложенном четыре, и выбирает его `cycleOf`.
- отдаёт: ADDED_AT, SORT_STATES, cycleOf, nextSort, orderFor, stateAt

## styles — 3 файлов

### styles/base.css (110)
- Правила, действующие на всю страницу сразу, а не на её блок.
- селекторы (14): *, *::before, *::after, [hidden], html, body, #root, body, :focus-visible, ::selection, .material-symbols-outlined, .is-active > .material-symbols-outlined,
.is-on > .material-symbols-outlined, .app, .app::before,
.app::after, .app::before, .app::after, .app__main, @media (prefers-reduced-motion: reduce)
- берёт: --bg, --body-m, --fill-primary-hover, --primary, --text, --text-bright

### styles/neon.css (49)
- Общий приём: полоса по верхней кромке, гаснущая к краям, гало под ней и свечение текста. Цвет из --neon, высоту гало из --halo-h ставит тот, кто применяет класс.
- селекторы (3): .neon, .neon::before, .neon::after
- объявляет: --halo-h
- берёт: --halo-h, --neon, --opaque

### styles/palette.css (103)
- Единственное место, где есть цвет. По месту пишется только var().
- селекторы (2): @property --primary, :root
- объявляет: --accent-game, --accent-movie, --accent-series, --bg, --body-l, --body-m, --error, --fill-primary-hover, --font, --glass, --glass-error, --label-l, --label-m, --opaque, --r-card, --r-full, --score-1, --score-10, --score-2, --score-3, --score-4, --score-5, --score-6, --score-7, --score-8, --score-9, --shade-25, --shade-32, --shade-55, --shade-60, --surface-pop, --text, --text-bright, --text-dim, --tint-02, --tint-035, --tint-05, --tint-06, --tint-07, --tint-09, --tint-10, --tint-14, --tint-16, --tint-18, --tint-22, --tint-25, --tint-28, --tint-30, --tint-34, --tint-35, --tint-40, --tint-45, --tint-55, --tint-75, --tint-80, --tint-85, --title-l, --title-s
- берёт: --font, --primary
