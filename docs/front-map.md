# Карта фронта

Собрана из кода. Число в скобках — строк в файле.

## api — 1 файлов

### api/bridge.js (119)
- Единственное место страницы, которое знает про `window.pywebview`.
- отдаёт: Failed, call, cancel, lastOp, numbered, ready

## app — 5 файлов

### app/App.svelte (64)
- Корень страницы: шапка, стопка разделов и плашка сообщений.
- берёт: ./LibraryScreen.svelte, ./SearchScreen.svelte, ./StatsScreen.svelte, ./Topbar.svelte

### app/LibraryScreen.svelte (33)
- Обе половины библиотеки: «Оценённые» и «Хочу посмотреть». Черновик: спрашивает одно и то же и ничем не управляет — настоящий раздел собирает задача 6.

### app/SearchScreen.svelte (2)
- Раздел «Поиск»: сначала своя выдача, потом внешняя. Пока пуст.

### app/StatsScreen.svelte (2)
- Раздел «Статистика»: гистограмма своих оценок. Пока пуст.

### app/Topbar.svelte (146)
- Сборка шапки: три зоны и всё, что в них нажимается.
- принимает: session, onsession, onsearch, onadd, onfilter

## components — 13 файлов

### components/Acts.svelte (21)
- Ряд действий карточки: правка, удаление, закладка.
- принимает: wished, onedit, ondelete, onwish

### components/Aggregates.svelte (57)
- Оценки агрегаторов: цифра, кружок ожидания или пустое место.
- принимает: external, expected, ids, onopen

### components/Chips.svelte (26)
- Метки карточки: жанры, теги и кнопка добавления тега.
- принимает: genres, tags, on, onmark, ontag

### components/Facts.svelte (45)
- Строки фактов карточки: длительность или сезоны, кто сделал, кто играл.
- принимает: view, onperson

### components/Film.svelte (81)
- Карточка ленты целиком.
- принимает: view, collapsed, expected, on, oncollapse, onmark, onperson, onopen, ontag, onscore, onaspect, onedit, ondelete, onwish

### components/Icon.svelte (6)
- Глиф Material Symbols.
- принимает: name, extra

### components/Poster.svelte (28)
- Обложка карточки с заглушкой.
- принимает: item_id, source, poster_url

### components/SearchField.svelte (30)
- Поле поиска с кнопкой очистки.
- принимает: onsearch

### components/Segmented.svelte (17)
- Капсульный переключатель: один выбранный из нескольких.
- принимает: items, chosen, onchoose

### components/Snack.svelte (41)
- Плашка сообщений: одна на всё приложение.
- принимает: message

### components/Stars.svelte (39)
- Ряд из десяти звёзд: кликабельный или неподвижный с дробной.
- принимает: score, onpick

### components/Synopsis.svelte (28)
- Описание карточки, обрезанное до трёх строк, с раскрытием.
- принимает: text

### components/ToolButton.svelte (17)
- Круглая кнопка ряда в шапке.
- принимает: icon, dir, label, active, pressed, onclick, children

## state — 7 файлов

### state/facts.js (50)
- Строки фактов карточки: длительность, сезоны и серии, состав.
- отдаёт: castOf, plural, runtimeOf, seriesOf

### state/filters.js (103)
- Три состояния строки фильтра: не выбран, включён, исключён.
- отдаёт: EMPTY, chosen, cleared, cycled, isEmpty, marked, passes

### state/redraw.js (20)
- Перезапуск анимации на узле, который обязан его пережить.
- отдаёт: redrawn

### state/scores.js (67)
- Нотация оценки: ярлык словом, ступень шкалы, среднее, доля звезды.
- отдаёт: ASPECTS, LABELS, average, colorOf, meanOf, partOf, stepOf, toneOf, verdictOf

### state/session.js (43)
- Выбранное в приложении вместе с переходами между выборами.
- отдаёт: newSession, withCollapsed, withKind, withNextSort, withSection, withToggledSection

### state/sorting.js (70)
- Все состояния переключателя сортировки. Набор у раздела свой: в «Оценённых» восемь, в отложенном четыре, и выбирает его `cycleOf`.
- отдаёт: ADDED_AT, SORT_STATES, cycleOf, hasSort, nextSort, orderFor, stateAt

### state/sources.js (52)
- Всё, что страница знает о чужом источнике: имя, шкала, адрес страницы.
- отдаёт: nameOf, pagesOf, stepOfSource

## styles — 18 файлов

### styles/acts.css (41)
- Ряд действий карточки: правка, удаление, закладка.
- селекторы (8): .film__acts, .film__wish,
.film__act, .film__wish .material-symbols-outlined,
.film__act  .material-symbols-outlined, .film__wish:hover,
.film__act:hover, .film__wish.is-on, .film__act[data-act="delete"]:hover, .film__act, .film:hover .film__act
- берёт: --error, --gutter, --icon-inset, --primary, --tint-30

### styles/aggr.css (51)
- Оценки агрегаторов и кружок на месте неприехавшей.
- селекторы (9): .film__aggr, .film__aggr span, .aggr, .aggr:hover, .aggr--flat, .aggr--flat:hover, .film__aggr b, .aggr-wait, @keyframes aggr-spin
- объявляет: --flat
- берёт: --body-m, --primary, --score, --tint-16, --tint-35, --tint-55

### styles/app.css (59)
- Оболочка окна: неоновая кромка сверху и место под содержимое.
- селекторы (6): .app, .app::before,
.app::after, .app::before, .app::after, .app__main, .content
- берёт: --primary

### styles/base.css (75)
- Правила, у которых нет своего блока.
- селекторы (10): *, *::before, *::after, [hidden], html, body, #root, body, button, :focus-visible, ::selection, .material-symbols-outlined, .is-active > .material-symbols-outlined,
.is-on > .material-symbols-outlined, @media (prefers-reduced-motion: reduce)
- берёт: --bg, --body-m, --fill-primary-hover, --primary, --text, --text-bright

### styles/chips.css (78)
- Метки карточки: жанры, теги и кнопка «± Тег».
- селекторы (14): .film__chips, .chip::first-letter, .chip, .chip--tag, .chip::before, .chip:hover, .chip:hover::before, .chip--add:hover, .chip--add:hover::before, .chip.is-on, .chip.is-on::before, .chip.is-on:hover, .chip.is-on:hover::before, .chip--add
- объявляет: --add
- берёт: --label-m, --primary, --r-full, --text-bright, --tint-06, --tint-09, --tint-30, --tint-55

### styles/facts.css (29)
- Строки фактов карточки и имена в них.
- селекторы (6): .film__facts, .film__facts dt, .film__facts dd, .film__role, .person, .person:hover
- берёт: --body-m, --primary, --tint-35, --tint-85

### styles/feed.css (12)
- Лента: полоса по ширине шапки и промежутки между карточками.
- селекторы (1): .feed
- берёт: --content-w

### styles/film.css (125)
- Карточка ленты: рама, сворачивание, постер, текстовая колонка.
- селекторы (19): .film, .film__toggle, .film__toggle .material-symbols-outlined, .film__toggle:hover, .film.is-collapsed .film__toggle .material-symbols-outlined, .film.is-collapsed .film__acts,
.film.is-collapsed .film__poster,
.film.is-collapsed .film__chips,
.film.is-collapsed .film__facts,
.film.is-collapsed .film__synopsis,
.film.is-collapsed .film__aggr,
.film.is-collapsed .film__verdict, .film.is-collapsed, .film.is-collapsed .film__body, .film.is-collapsed .film__title, .film.is-collapsed .film__scores, .film__poster, .film__poster .material-symbols-outlined, .film__poster img, .film__body, .film__title, .film__synopsis, .film__synopsis.is-cut, .more, .more:hover
- объявляет: --gutter, --icon-inset
- берёт: --body-l, --body-m, --gutter, --icon-inset, --primary, --text-bright, --tint-02, --tint-035, --tint-07, --tint-09, --tint-16, --tint-30, --tint-40, --tint-55, --title-l

### styles/iconbutton.css (20)
- Круглая кнопка с одним глифом: шеврон карточки, закладка, крестик поиска.
- селекторы (2): .icon-btn, .icon-btn .material-symbols-outlined
- объявляет: --icon-btn
- берёт: --icon-btn, --r-full

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

### styles/search.css (63)
- Поле поиска в левой зоне шапки.
- селекторы (11): .search, .search:hover, .search:focus-within, .search__icon, .search:focus-within .search__icon, .search__input, .search__input::placeholder, .search__input::-webkit-search-cancel-button,
.search__input::-webkit-search-decoration, .search__clear, .search__clear .material-symbols-outlined, .search__clear:hover
- объявляет: --icon-btn
- берёт: --body-l, --fill-primary-14, --primary, --r-full, --side-w, --text, --tint-035, --tint-05, --tint-06, --tint-10, --tint-28, --tint-35

### styles/seg.css (43)
- Капсула переключателя типа содержимого.
- селекторы (6): .seg, .seg__btn, .seg__btn .material-symbols-outlined, .seg__btn:hover, .seg__btn.is-active, .seg__btn.is-active:hover
- берёт: --fill-primary-14, --primary, --r-full, --tint-035, --tint-05, --tint-06, --tint-45, --tint-75, --title-s

### styles/snack.css (25)
- Единственное место, где приложение что-то сообщает: и отказ источника, и непредвиденный сбой. Уехавшая вниз плашка пустая — отсутствие сообщений само себя ничем не обозначает.
- селекторы (2): .snack, .snack.is-shown
- объявляет: --halo-h, --neon
- берёт: --body-m, --error, --glass-error, --r-full

### styles/stars.css (70)
- Своя оценка: ряд звёзд, дробная звезда и ярлык словом.
- селекторы (14): .film__scores, .film__aspect, .stars, .stars button,
.stars > span, .stars .star--part, .stars .star--part i, .stars .star--part i .material-symbols-outlined, .stars .material-symbols-outlined, .stars .is-on, .stars .is-on .material-symbols-outlined, .film__verdict, .film__scores.film__scores--avg, .film.is-collapsed .film__scores--avg, .film.is-collapsed .film__scores--aspect
- берёт: --body-m, --fill, --score, --tint-16, --tint-35, --title-s

### styles/tools.css (80)
- Ряд круглых кнопок в правой зоне шапки.
- селекторы (13): .tools, .tools__btn, .tools__btn .material-symbols-outlined, .tools__btn:hover, .tools__btn.is-active, .tools__btn:has(.tools__dir) .material-symbols-outlined, .tools__dir, .tools__chart, .tools__chart rect, .is-drawing .tools__chart rect, .is-drawing .tools__chart rect:nth-child(2), .is-drawing .tools__chart rect:nth-child(3), @keyframes bar-grow
- берёт: --fill-primary-14, --primary, --r-full, --side-w, --tint-035, --tint-05, --tint-06, --tint-45, --tint-75

### styles/topbar.css (28)
- Раскладка шапки: три зоны, из ширины которых выведен минимум окна.
- селекторы (2): .topbar, .topbar__seg
- объявляет: --corner, --side-w
- берёт: --corner

### styles/view.css (17)
- Стопка разделов: виден один, переход между ними — проявление.
- селекторы (3): .view, .view.is-shown, @keyframes screen-in
