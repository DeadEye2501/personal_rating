# Карта фронта

Собрана из кода. Число в скобках — строк в файле.

## api — 2 файлов

### api/bridge.js (119)
- Единственное место страницы, которое знает про `window.pywebview`.
- отдаёт: Failed, call, cancel, lastOp, numbered, ready

### api/owned.svelte.js (18)
- Что раздел запустил, то он и гасит при уходе.
- отдаёт: owned

## app — 12 файлов

### app/App.svelte (217)
- Корень страницы: шапка, стопка разделов и плашка сообщений.
- берёт: ./CardModal.svelte, ./CardTagsModal.svelte, ./FiltersModal.svelte, ./LibraryScreen.svelte, ./SearchScreen.svelte, ./StatsScreen.svelte, ./Topbar.svelte, ./trouble.js

### app/CardModal.svelte (53)
- Окно создания и правки карточки: поля показываются своему типу.
- принимает: kind, onsave, onclose

### app/CardTagsModal.svelte (82)
- Теги одной карточки: тот же список, но два состояния вместо трёх — исключать тег у конкретной карточки нечего.
- принимает: view, onview, onclose, ontrouble
- берёт: ./tags.js, ./trouble.js

### app/FiltersModal.svelte (158)
- Три фильтра одной сборкой: жанры, теги и оценки. Списки разные, поведение строки общее; правку набора имеет только теговый.
- принимает: field, kind, title, filters, onfilters, onforget, onclose, ontrouble
- берёт: ./tags.js, ./tagset.js, ./trouble.js

### app/LibraryScreen.svelte (133)
- Обе половины библиотеки: «Оценённые» и «Хочу посмотреть». Различает их `session.section`, он же уезжает в запрос; второй файл был бы дословной копией, которую планы 8 и 9 правили бы дважды.
- принимает: session, expected, root, tagged, forgotten, ontrouble, onmark, onperson, onopen, ontag
- берёт: ./trouble.js, ./visible.js

### app/SearchScreen.svelte (118)
- Раздел «Поиск»: сначала своя выдача, потом внешняя.
- принимает: session, query, expected, root, ontrouble, onmark, onperson, onopen, ontag
- берёт: ./trouble.js, ./visible.js

### app/StatsScreen.svelte (59)
- Раздел «Статистика»: гистограмма своих оценок по тому же отфильтрованному набору, что и разделы с карточками.
- принимает: session, ontrouble
- берёт: ./trouble.js

### app/Topbar.svelte (146)
- Сборка шапки: три зоны и всё, что в них нажимается.
- принимает: session, onsession, onsearch, onadd, onfilter

### app/tags.js (33)
- Заведение тега с общим отказом.
- отдаёт: created

### app/tagset.js (30)
- Правка самого набора тегов: удалить и переставить.
- отдаёт: dropped, ordered, wearers

### app/trouble.js (15)
- Единственный способ поступить с отказом операции.
- отдаёт: reported

### app/visible.js (61)
- Что делать с карточкой, попавшей в поле зрения.
- отдаёт: onCardShown, stale

## components — 26 файлов

### components/Acts.svelte (21)
- Ряд действий карточки: правка, удаление, закладка.
- принимает: wished, onedit, ondelete, onwish

### components/Aggregates.svelte (57)
- Оценки агрегаторов: цифра, кружок ожидания или пустое место.
- принимает: external, expected, ids, onopen

### components/Bar.svelte (16)
- Столбец гистограммы: заливка, число над верхушкой и подпись оценки.
- принимает: score, count, share, index

### components/Button.svelte (6)
- Кнопка ответного ряда внизу окна.
- принимает: variant, onclick, children

### components/Chips.svelte (29)
- Метки карточки: жанры, теги и кнопка добавления тега.
- принимает: genres, tags, on, onmark, ontag

### components/Confirm.svelte (22)
- Вопрос и две кнопки. Спрашивают им и то, что пропадёт навсегда, и то, что просто выглядит подозрительно, — цвет и слово согласия приходят снаружи.
- принимает: label, text, ok, danger, onyes, onclose

### components/Facts.svelte (45)
- Строки фактов карточки: длительность или сезоны, кто сделал, кто играл.
- принимает: view, onperson

### components/Feed.svelte (84)
- Список карточек, который растёт порциями и не знает своей полной длины.
- принимает: views, collapsed, expected, root, onmore, onshown, ...card

### components/Field.svelte (25)
- Строка ввода окна карточки: однострочная или абзацем.
- принимает: value, placeholder, variant, area

### components/Film.svelte (84)
- Карточка ленты целиком.
- принимает: view, collapsed, expected, on, oncollapse, onmark, onperson, onopen, ontag, onscore, onaspect, onedit, ondelete, onwish

### components/Icon.svelte (6)
- Глиф Material Symbols.
- принимает: name, extra

### components/ListModal.svelte (19)
- Окно со списком строк: прокручиваемый список и, если есть, форма под ним.
- принимает: label, narrow, onclose, items, footer

### components/Modal.svelte (54)
- Оболочка любого наложения: затемнение, окно и два способа его закрыть.
- принимает: narrow, ask, danger, card, label, onclose, children

### components/NewTag.svelte (36)
- Форма заведения тега.
- принимает: oncreate

### components/Poster.svelte (28)
- Обложка карточки с заглушкой.
- принимает: item_id, source, poster_url

### components/ScoreRow.svelte (24)
- Строка оценки в списке: неподвижные звёзды и ярлык словом.
- принимает: score, state, ontoggle

### components/Scrollarea.svelte (16)
- Область, которая прокручивается вместо страницы.
- принимает: children

### components/Scrollbar.svelte (89)
- Своя полоса прокрутки для того, что прокручивается.
- принимает: box, area

### components/SearchField.svelte (30)
- Поле поиска с кнопкой очистки.
- принимает: onsearch

### components/Segmented.svelte (17)
- Капсульный переключатель: один выбранный из нескольких.
- принимает: items, chosen, onchoose

### components/Snack.svelte (41)
- Плашка сообщений: одна на всё приложение.
- принимает: message

### components/Stars.svelte (37)
- Ряд из десяти звёзд: кликабельный или неподвижный с дробной.
- принимает: score, onpick

### components/Synopsis.svelte (28)
- Описание карточки, обрезанное до трёх строк, с раскрытием.
- принимает: text

### components/TagBox.svelte (18)
- Переключатель строки списка: не выбран, включён, исключён.
- принимает: state, label, onclick

### components/TagRow.svelte (29)
- Строка списка: ручка, переключатель, имя, удаление.
- принимает: name, state, moving, ontoggle, ondelete, ongrab

### components/ToolButton.svelte (17)
- Круглая кнопка ряда в шапке.
- принимает: icon, dir, label, active, pressed, onclick, children

## state — 14 файлов

### state/card.js (29)
- Форма карточки: из каких полей она состоит у каждого типа содержимого.
- отдаёт: emptyCard, shownFor

### state/dragging.js (23)
- Таска указателем: захват, движение, отпускание.
- отдаёт: dragging

### state/facts.js (50)
- Строки фактов карточки: длительность, сезоны и серии, состав.
- отдаёт: castOf, plural, runtimeOf, seriesOf

### state/filters.js (119)
- Три состояния строки фильтра: не выбран, включён, исключён.
- отдаёт: EMPTY, chosen, cleared, cycled, forgotten, isEmpty, marked, passes, stateOf

### state/histogram.js (9)
- Доля каждого столбца от самого высокого.
- отдаёт: heightsOf

### state/kinds.js (13)
- Как тип содержимого называется человеку.
- отдаёт: NOUNS

### state/redraw.js (21)
- Перезапуск анимации на узле, который обязан его пережить.
- отдаёт: redrawn

### state/reorder.js (23)
- Куда встаёт строка, которую тащат указателем.
- отдаёт: dragged

### state/scores.js (74)
- Нотация оценки: ярлык словом, ступень шкалы, среднее, доля звезды.
- отдаёт: ASPECTS, LABELS, SCALE, average, colorOf, meanOf, partOf, stepOf, toneOf, verdictOf

### state/scroll.js (23)
- Арифметика своей полосы прокрутки.
- отдаёт: thumbOf

### state/section.js (20)
- Запрос раздела: то, что уезжает мостом в `feed.page`.
- отдаёт: requestOf

### state/session.js (66)
- Выбранное в приложении вместе с переходами между выборами.
- отдаёт: collapsedOf, newSession, withClearedFilter, withCollapsed, withFilters, withForgotten, withKind, withMark, withNextSort, withSection, withToggledSection

### state/sorting.js (70)
- Все состояния переключателя сортировки. Набор у раздела свой: в «Оценённых» восемь, в отложенном четыре, и выбирает его `cycleOf`.
- отдаёт: ADDED_AT, SORT_STATES, cycleOf, hasSort, nextSort, orderFor, stateAt

### state/sources.js (52)
- Всё, что страница знает о чужом источнике: имя, шкала, адрес страницы.
- отдаёт: nameOf, pagesOf, stepOfSource

## styles — 28 файлов

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

### styles/base.css (82)
- Правила, у которых нет своего блока.
- селекторы (11): *, *::before, *::after, [hidden], html, body, #root, body, button, :focus-visible, ::selection, .material-symbols-outlined, .is-active > .material-symbols-outlined,
.is-on > .material-symbols-outlined, @keyframes fade-in, @media (prefers-reduced-motion: reduce)
- берёт: --bg, --body-m, --fill-primary-hover, --primary, --text, --text-bright

### styles/cardform.css (58)
- Раскладка окна создания и правки карточки.
- селекторы (7): .modal--card, .cardform__top, .cardform__fields, .cardform__row, .cardform__row .field, .cardform__row .field--short, .cardform__poster
- объявляет: --col-gap, --field-h, --poster-w, --row-gap
- берёт: --col-gap, --poster-w, --row-gap, --tint-18, --tint-22

### styles/chart.css (92)
- Гистограмма оценок и её подвал.
- селекторы (11): .chart, .chart__bars, .bar, .bar__plot, .bar__fill, .bar__count, .bar__value, .chart__foot, .chart__foot b, .view.is-drawing .bar__fill, @keyframes bar-rise
- берёт: --body-m, --content-w, --ease, --h, --i, --label-l, --score, --text-bright, --tint-07, --tint-45, --tint-80, --title-s

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

### styles/field.css (74)
- Строка ввода: общее у поиска в шапке, формы нового тега и полей карточки.
- селекторы (12): .field,
.newtag, .field:focus-within,
.newtag:focus-within, .field, .field__input, .field .field__input,
.newtag__input, .field .field__input::placeholder,
.newtag__input::placeholder, .field:hover .field__input::placeholder,
.newtag__input:hover::placeholder, .field .field__input:focus::placeholder,
.newtag__input:focus::placeholder, .field--title .field__input, .field--area, .field--area .field__input, .field--area .field__input::-webkit-scrollbar
- берёт: --body-l, --field-h, --primary, --text-bright, --text-dim, --title-l

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
- берёт: --body-l, --body-m, --ease, --gutter, --icon-inset, --primary, --text-bright, --tint-02, --tint-035, --tint-07, --tint-09, --tint-16, --tint-30, --tint-40, --tint-55, --title-l

### styles/iconbutton.css (31)
- Круглая кнопка с одним глифом: шеврон карточки, закладка, крестик поиска.
- селекторы (5): .icon-btn, .icon-btn .material-symbols-outlined, .icon-btn--accent, .icon-btn--accent .material-symbols-outlined, .icon-btn--accent:hover
- объявляет: --accent, --icon-btn
- берёт: --fill-primary-14, --icon-btn, --primary, --r-full

### styles/modal.css (106)
- Оболочка любого наложения: затемнение, тёмное стекло, неоновая кромка.
- селекторы (9): .overlay, .modal, .modal--narrow, .modal--ask, .modal--danger, .ask__text, .modal::before, .modal::after, @keyframes modal-in
- объявляет: --neon
- берёт: --body-l, --ease, --error, --glass, --neon, --primary, --r-card, --shade-25, --shade-32, --shade-60, --text, --tint-09, --tint-14

### styles/modalfoot.css (42)
- Ряд ответных кнопок внизу окна.
- селекторы (5): .modalfoot, .btn, .btn--cancel:hover, .btn--go:hover, .btn--danger:hover
- объявляет: --cancel, --danger, --go
- берёт: --error, --label-l, --primary, --r-full, --text-bright, --text-dim

### styles/neon.css (49)
- Общий приём: полоса по верхней кромке, гаснущая к краям, гало под ней и свечение текста. Цвет из --neon, высоту гало из --halo-h ставит тот, кто применяет класс.
- селекторы (3): .neon, .neon::before, .neon::after
- объявляет: --halo-h
- берёт: --halo-h, --neon, --opaque

### styles/newtag.css (25)
- Форма заведения тега под списком.
- селекторы (3): .newtag, .newtag__ok, .newtag.is-filled .newtag__ok

### styles/palette.css (119)
- Единственное место, где есть цвет. По месту пишется только var().
- селекторы (2): @property --primary, :root
- объявляет: --accent-game, --accent-movie, --accent-series, --bg, --body-l, --body-m, --content-w, --ease, --error, --exclude, --fill-primary-14, --fill-primary-hover, --font, --glass, --glass-error, --label-l, --label-m, --opaque, --r-card, --r-full, --score-1, --score-10, --score-2, --score-3, --score-4, --score-5, --score-6, --score-7, --score-8, --score-9, --shade-25, --shade-32, --shade-55, --shade-60, --surface-pop, --text, --text-bright, --text-dim, --tint-02, --tint-035, --tint-05, --tint-06, --tint-07, --tint-09, --tint-10, --tint-14, --tint-16, --tint-18, --tint-22, --tint-25, --tint-28, --tint-30, --tint-34, --tint-35, --tint-40, --tint-45, --tint-55, --tint-75, --tint-80, --tint-85, --title-l, --title-s
- берёт: --font, --primary

### styles/scorerow.css (34)
- Строка оценки в списке: десять звёзд и ярлык словом.
- селекторы (5): .scorerow, .scorerow__stars, .scorerow__stars .material-symbols-outlined, .scorerow__stars .is-empty, .scorerow__label
- берёт: --score, --tint-14, --title-s

### styles/scrollarea.css (45)
- Область со своей полосой прокрутки вместо системной.
- селекторы (8): .scrollarea, .scrollarea__box, .scrollarea__box::-webkit-scrollbar, .scrollbar, .scrollbar.is-shown, .scrollbar__thumb, .scrollbar__thumb:hover, .scrollbar__thumb:active
- берёт: --tint-16, --tint-28, --tint-34

### styles/search.css (46)
- Поле поиска в левой зоне шапки.
- селекторы (9): .search, .search:hover, .search:focus-within, .search__icon, .search:focus-within .search__icon, .search__input, .search__input::placeholder, .search__input::-webkit-search-cancel-button,
.search__input::-webkit-search-decoration, .search__clear
- берёт: --primary, --side-w, --text, --tint-05, --tint-10, --tint-28, --tint-35

### styles/seg.css (40)
- Капсула переключателя типа содержимого.
- селекторы (6): .seg, .seg__btn, .seg__btn .material-symbols-outlined, .seg__btn:hover, .seg__btn.is-active, .seg__btn.is-active:hover
- берёт: --fill-primary-14, --primary, --r-full, --tint-05, --tint-45, --tint-75, --title-s

### styles/snack.css (27)
- Единственное место, где приложение что-то сообщает: и отказ источника, и непредвиденный сбой. Уехавшая вниз плашка пустая — отсутствие сообщений само себя ничем не обозначает.
- селекторы (2): .snack, .snack.is-shown
- объявляет: --halo-h, --neon
- берёт: --body-m, --ease, --error, --glass-error, --r-full

### styles/stars.css (70)
- Своя оценка: ряд звёзд, дробная звезда и ярлык словом.
- селекторы (14): .film__scores, .film__aspect, .stars, .stars button,
.stars > span, .stars .star--part, .stars .star--part i, .stars .star--part i .material-symbols-outlined, .stars .material-symbols-outlined, .stars .is-on, .stars .is-on .material-symbols-outlined, .film__verdict, .film__scores.film__scores--avg, .film.is-collapsed .film__scores--avg, .film.is-collapsed .film__scores--aspect
- берёт: --body-m, --fill, --score, --tint-16, --tint-35, --title-s

### styles/taglist.css (104)
- Список наложения: строка, ручка перетаскивания и трёхпозиционный переключатель.
- селекторы (16): .taglist, .tagrow, .tagrow__name, .taggrip, .taggrip:hover, .taggrip i, .tagrow.is-dragging, .tagrow.is-dragging .taggrip, .tagbox, .tagbox .material-symbols-outlined, .tagbox[data-state="off"]:hover, .tagbox[data-state="on"], .tagbox[data-state="ex"], .tagrow__del, .tagrow__del .material-symbols-outlined, .tagrow__del:hover
- берёт: --bg, --body-l, --error, --exclude, --primary, --r-full, --text-bright, --tint-25, --tint-30, --tint-55

### styles/tools.css (77)
- Ряд круглых кнопок в правой зоне шапки.
- селекторы (13): .tools, .tools__btn, .tools__btn .material-symbols-outlined, .tools__btn:hover, .tools__btn.is-active, .tools__btn:has(.tools__dir) .material-symbols-outlined, .tools__dir, .tools__chart, .tools__chart rect, .is-drawing .tools__chart rect, .is-drawing .tools__chart rect:nth-child(2), .is-drawing .tools__chart rect:nth-child(3), @keyframes bar-grow
- берёт: --ease, --fill-primary-14, --primary, --r-full, --side-w, --tint-05, --tint-45, --tint-75

### styles/topbar.css (32)
- Раскладка шапки: три зоны, из ширины которых выведен минимум окна.
- селекторы (2): .topbar, .topbar__seg
- объявляет: --corner, --side-w
- берёт: --corner

### styles/view.css (12)
- Стопка разделов: виден один, переход между ними — проявление.
- селекторы (2): .view, .view.is-shown

### styles/zone.css (11)
- Подложка зоны шапки: капсула с тонкой рамкой.
- селекторы (1): .zone
- берёт: --r-full, --tint-035, --tint-06
