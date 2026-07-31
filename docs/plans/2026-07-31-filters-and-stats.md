# План 8. Модалки-списки, фильтры и статистика

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** фильтры начинают работать. Три модалки с трёхпозиционными строками
сужают ленту, модалка тегов карточки вешает свои метки, а раздел «Статистика»
показывает гистограмму по тому же отфильтрованному набору. После этого плана
остаётся только окно карточки и поставка.

**Архитектура:** четыре модалки макета — это одна оболочка и один вид строки с
двумя поведениями. Различаются они списком и тем, что строка умеет: у фильтров
три состояния, у тегов карточки два. Спека говорит про это буквально: «Список тот
же, поведение разное — и это единственное, чем две модалки тегов отличаются».

**Своя полоса прокрутки, а не системная.** Причина записана в макете: Chromium не
анимирует переходы на `::-webkit-scrollbar`, он её только мгновенно
перерисовывает.

**Стек:** тот же. Ни одной новой зависимости.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от планов 5–7.** Мост отвечает на всё, состояние считает фильтры,
  шапка зовёт `onfilter`, лента показывает карточки.
- **Значения макета переносятся точь-в-точь**, и ничего оформительского не
  придумывается.
- **`<style>` внутри компонента не бывает вовсе**, цвет — только в палитре,
  компонент получает всё входными параметрами и сам никуда не ходит.
- **Компоненты не проверяются**, проверяется `state/`.
- **Фильтры действуют везде, включая поиск**, и разделами не сбрасываются — это
  уже написано в `state/filters.js` и `state/session.js`, здесь только
  используется.
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ client/
│  ├─ styles/
│  │  ├─ modal.css               оболочка: затемнение, стекло, кромка
│  │  ├─ scrollarea.css          своя полоса прокрутки
│  │  ├─ taglist.css             список, строка, ручка, переключатель
│  │  ├─ scorerow.css            строка оценки со звёздами
│  │  ├─ newtag.css              форма нового тега
│  │  └─ chart.css               гистограмма и сноска
│  ├─ state/
│  │  ├─ scroll.js               арифметика своей полосы прокрутки
│  │  ├─ tags.js                 заведение тега с общим отказом
│  │  └─ histogram.js            доли столбцов гистограммы
│  ├─ components/
│  │  ├─ Modal.svelte            оболочка любого наложения
│  │  ├─ Scrollarea.svelte       область со своей полосой
│  │  ├─ TagBox.svelte           переключатель строки: два или три состояния
│  │  ├─ TagRow.svelte           строка списка: ручка, имя, переключатель
│  │  ├─ ScoreRow.svelte         строка оценки: звёзды и ярлык
│  │  ├─ NewTag.svelte           форма заведения тега
│  │  └─ Bar.svelte              столбец гистограммы
│  └─ app/
│     ├─ FiltersModal.svelte     три фильтра одной сборкой
│     ├─ CardTagsModal.svelte    теги конкретной карточки
│     └─ StatsScreen.svelte      гистограмма со сноской
└─ tests/web/
   └─ histogram.test.js          высоты столбцов и подвал
```

Правятся и чужие файлы: `client/styles/palette.css` (красный исключения),
`client/app/App.svelte` (наложения и их открытие), `client/main.js`.

---

### Задача 1: Оболочка модалки и своя полоса прокрутки

Общее у всех четырёх наложений плюс приём, который дальше понадобится и окну
карточки: список тегов, синопсис и список совпадений прокручиваются своей
полосой.

**Красный крестика исключения переезжает в палитру.** В макете он написан по
месту — `#ef4444`, и это **не** `--error` (`#ff4a45`), которым красятся плашка и
корзина. Два близких, но разных красных: у беды свой, у исключения свой. Цвет по
месту хук отклоняет, поэтому второй заводится токеном — не потому, что выбран
новый цвет, а потому, что старый обязан лежать там же, где остальные.

**Файлы:**
- Создать: `client/styles/modal.css`, `scrollarea.css`
- Создать: `client/components/Modal.svelte`, `Scrollarea.svelte`
- Изменить: `client/styles/palette.css`, `client/main.js`

**Интерфейсы:**
- Потребляет: ничего.
- Отдаёт: `thumbOf(visible, total, passed)`, `scaleOf(visible, total)`;
  `Modal` с входными `narrow`, `ask`, `danger`, `label`, `onclose`,
  `children`;
  `Scrollarea` с входным `children`.

- [ ] **Шаг 1: Завести цвет исключения**

Дописать в `client/styles/palette.css`, рядом с `--error`:

```css
  /* Красный крестика «ни одного такого». Отличается от --error намеренно: у
     беды свой красный, у исключения свой — так в макете. */
  --exclude:            #ef4444;
```

- [ ] **Шаг 2: Перенести оболочку**

Создать `client/styles/modal.css` — перенос `docs/design/index.html:831-907`:

```css
.overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--shade-32);
  animation: overlay-in .18s ease-out;
}

.modal {
  position: relative;
  width: min(560px, 100%);
  min-height: 200px;
  padding: 22px 24px 18px;
  border: 1px solid var(--tint-09);
  border-radius: var(--r-card);

  /* Тёмное стекло: заливка чёрная и полупрозрачная, поэтому окно остаётся
     тёмным и при этом размывает то, что под ним. */
  background: var(--glass);
  backdrop-filter: blur(8px) saturate(140%);

  box-shadow:
    inset 0 1px 0 var(--tint-14),
    inset 0 -1px 0 var(--shade-25),
    0 30px 90px var(--shade-60);

  animation: modal-in .22s cubic-bezier(.2,.8,.2,1);
}

/* Содержимое фиксированной ширины — тянуть окно не за чем. */
.modal--narrow { width: min(400px, 100%) }

/* Неоновая кромка — та же, что по верху окна приложения. Промежуточные точки:
   переход от цвета к прозрачности по прямой даёт заметный обрыв, ступени его
   сглаживают. */
.modal::before {
  content: '';
  position: absolute;
  top: 0;
  left: 24px;
  right: 24px;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    color-mix(in srgb, var(--primary) 18%, transparent) 14%,
    color-mix(in srgb, var(--primary) 55%, transparent) 26%,
    color-mix(in srgb, var(--primary) 88%, transparent) 38%,
    var(--primary) 50%,
    color-mix(in srgb, var(--primary) 88%, transparent) 62%,
    color-mix(in srgb, var(--primary) 55%, transparent) 74%,
    color-mix(in srgb, var(--primary) 18%, transparent) 86%,
    transparent 100%);
}

/* Свечение отдельным слоем, а не тенью: тень легла бы ровной полосой во всю
   ширину и торцы бы срезались. Здесь оно гаснет вместе с нитью. */
.modal::after {
  content: '';
  position: absolute;
  top: -11px;
  left: 24px;
  right: 24px;
  height: 24px;
  background: linear-gradient(90deg,
    transparent 0%,
    color-mix(in srgb, var(--primary) 4%,  transparent) 18%,
    color-mix(in srgb, var(--primary) 15%, transparent) 40%,
    color-mix(in srgb, var(--primary) 15%, transparent) 60%,
    color-mix(in srgb, var(--primary) 4%,  transparent) 82%,
    transparent 100%);
  filter: blur(12px);
  pointer-events: none;
}

@keyframes overlay-in {
  from { opacity: 0 }
  to   { opacity: 1 }
}
@keyframes modal-in {
  from { opacity: 0; transform: scale(.94) translateY(8px) }
  to   { opacity: 1; transform: none }
}
```

Префикс `-webkit-backdrop-filter` из макета не переносится: рисует нас
Chromium 150, и там свойство давно без префикса. Это единственное расхождение с
макетом в этом файле.

- [ ] **Шаг 3: Перенести полосу прокрутки**

Создать `client/styles/scrollarea.css` — перенос `index.html:1188-1234`:

```css
/* Полоса своя, а не системная: Chromium не анимирует переходы на
   ::-webkit-scrollbar, он её только мгновенно перерисовывает. */
.scrollarea { position: relative }

.scrollarea__box {
  overflow-y: auto;
  scrollbar-width: none;
}
.scrollarea__box::-webkit-scrollbar { display: none }

.scrollbar {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 8px;
  opacity: 0;
  pointer-events: none;
  transition: opacity .25s ease;
}
.scrollbar.is-shown {
  opacity: 1;
  pointer-events: auto;
}

.scrollbar__thumb {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  border-radius: 4px;
  background: var(--tint-16);
  cursor: grab;
  transition: background .18s;
}
.scrollbar__thumb:hover  { background: var(--tint-28) }
.scrollbar__thumb:active { cursor: grabbing; background: var(--tint-34) }
```

В макете скрытие системной полосы висит на `.taglist`, здесь оно уехало на
`.scrollarea__box`: областей с этим приёмом четыре — список, синопсис, список
совпадений и снова список, — и привязывать общий приём к имени одного из них
значило бы писать его четырежды.

- [ ] **Шаг 4: Написать счёт ползунка**

Создать `tests/web/scroll.test.js`:

```js
import { describe, expect, it } from 'vitest'

import { scaleOf, thumbOf } from '$state/scroll.js'

describe('своя полоса прокрутки', () => {
  it('на коротком содержимом полосы нет вовсе', () => {
    expect(thumbOf(400, 300, 0)).toBe(null)
    expect(thumbOf(400, 400, 0)).toBe(null)
  })

  it('высота ползунка — доля видимого от всего', () => {
    // Видно четверть — ползунок в четверть области.
    expect(thumbOf(400, 1600, 0).height).toBe(100)
  })

  it('короткий ползунок не даёт себя ухватить, и потому у него есть предел', () => {
    // Доля дала бы четыре пикселя: на списке в сто строк это не мишень.
    expect(thumbOf(400, 40000, 0).height).toBe(28)
  })

  it('внизу списка ползунок стоит внизу области, а не за её краем', () => {
    const found = thumbOf(400, 1600, 1200)

    expect(found.offset).toBe(400 - found.height)
  })

  it('пиксель курсора стоит больше пикселя содержимого', () => {
    // Иначе ползунок отставал бы от мыши тем сильнее, чем длиннее список.
    expect(scaleOf(400, 1600)).toBe(4)
  })
})
```

Создать `client/state/scroll.js`:

```js
/** Арифметика своей полосы прокрутки. */

// Минимальная высота ползунка: на длинном списке доля содержимого делает его
// неухватываемым.
const MIN_THUMB = 28

/** Высота и смещение ползунка, либо `null` — прокручивать нечего. */
export function thumbOf(visible, total, passed) {
  if (total <= visible) return null

  const height = Math.max(MIN_THUMB, visible * (visible / total))
  const room = visible - height
  return { height, offset: room * (passed / (total - visible)) }
}

/** Во сколько раз пиксель курсора длиннее пикселя содержимого. */
export const scaleOf = (visible, total) => total / visible
```

- [ ] **Шаг 5: Написать оболочку**

`client/components/Modal.svelte`:

```svelte
<script module>
  // Счётчик общий на все окна: он про стопку, а не про одно из них.
  let opened = 0
</script>

<script>
  let { narrow = false, ask = false, danger = false, label, onclose, children }
    = $props()

  // Клик мимо окна закрывает, внутри — нет. Проверяем цель, а не всплытие:
  // остановка всплытия внутри сломала бы всё, что на нём стоит.
  const outside = (event) => { if (event.target === event.currentTarget) onclose() }

  // Окна встают стопкой: подтверждение удаления открывается поверх списка
  // тегов, предупреждение о совпадении — поверх окна карточки. Escape обязан
  // убрать **верхнее**, иначе одно нажатие сложило бы оба.
  let mine = $state(0)

  $effect(() => {
    mine = ++opened
    return () => { opened -= 1 }
  })

  const escaped = (event) => {
    if (event.key === 'Escape' && mine === opened) onclose()
  }
</script>

<svelte:window onkeydown={escaped} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- Затемнение — не кнопка: клавиатуре тут делать нечего, окно закрывает
     Escape. Предупреждения сняты адресно, а не настройкой на весь проект. -->
<div class="overlay" onclick={outside}>
  <div class="modal" class:modal--narrow={narrow} class:modal--ask={ask}
       class:modal--danger={danger} role="dialog" aria-modal="true"
       aria-label={label}>
    {@render children()}
  </div>
</div>
```

- [ ] **Шаг 6: Написать область со своей полосой**

`client/components/Scrollarea.svelte`:

```svelte
<script>
  import { scaleOf, thumbOf } from '$state/scroll.js'

  let { children } = $props()

  let box = $state()
  let thumb = $state()
  let shown = $state(false)

  // Считает `state/scroll.js`, здесь остаётся привязка к DOM: арифметику
  // ползунка иначе не сторожит ничто — компоненты по решению не проверяются.
  function measure() {
    if (!box || !thumb) return
    const found = thumbOf(box.clientHeight, box.scrollHeight, box.scrollTop)
    shown = found !== null
    if (!shown) return

    thumb.style.height = `${found.height}px`
    thumb.style.transform = `translateY(${found.offset}px)`
  }

  // Пересчёт нужен и при вводе текста, и при смене содержимого: список
  // фильтруется, а высота ползунка от этого меняется.
  $effect(() => {
    measure()
    const watcher = new ResizeObserver(measure)
    watcher.observe(box)
    return () => watcher.disconnect()
  })

  function drag(event) {
    event.preventDefault()
    const start = event.clientY
    const from = box.scrollTop
    const scale = scaleOf(box.clientHeight, box.scrollHeight)

    const move = (moved) => {
      box.scrollTop = from + (moved.clientY - start) * scale
    }
    const stop = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', stop)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', stop)
  }
</script>

<div class="scrollarea">
  <div class="scrollarea__box" bind:this={box} onscroll={measure}>
    {@render children()}
  </div>
  <div class="scrollbar" class:is-shown={shown}>
    <div class="scrollbar__thumb" bind:this={thumb} onpointerdown={drag}></div>
  </div>
</div>
```

- [ ] **Шаг 7: Подключить и посмотреть**

Дописать в `client/main.js`:

```js
import '$styles/modal.css'
import '$styles/scrollarea.css'
```

Смотреть пока не на чем — списка нет. Проверка оболочки идёт в задаче 3, вместе
с первой настоящей модалкой.

- [ ] **Шаг 8: Коммит**

```bash
git add client/styles/ client/components/ client/main.js
git commit -m "feat: оболочка модалки и своя полоса прокрутки"
```

---

### Задача 2: Строка списка

Один вид строки на четыре модалки. Отличий два: переключатель умеет два
состояния или три, и у строки бывает ручка перетаскивания с крестиком удаления.

**Три состояния: не выбран, включён, исключён.** Третье отмечено красным
крестиком и означает «ни одного такого». Работает у тегов, жанров и оценок.

**У тегов самого фильма исключения нет.** Там два состояния, есть и нет:
исключать тег у конкретной карточки нечего.

**Файлы:**
- Создать: `client/styles/taglist.css`, `scorerow.css`, `newtag.css`
- Создать: `client/components/TagBox.svelte`, `TagRow.svelte`,
  `ScoreRow.svelte`, `NewTag.svelte`
- Изменить: `client/main.js`

**Интерфейсы:**
- Потребляет: `colorOf`, `LABELS` из `$state/scores.js`.
- Отдаёт: `TagBox` с входными `state`, `onclick`; `TagRow` с `name`, `state`,
  `ontoggle`, `ondelete`, `ongrab`; `ScoreRow` с `score`, `state`, `ontoggle`;
  `NewTag` с `oncreate`.

- [ ] **Шаг 1: Перенести оформление списка**

Создать `client/styles/taglist.css` — перенос `index.html:1191-1370`:

```css
.taglist {
  margin: 0;
  padding: 0 14px 0 0;      /* обнуляет и браузерный отступ списка слева */
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  /* Тянемся по высоте окна, но не во всю: у списка есть свой потолок, дальше
     он прокручивается. */
  max-height: min(calc(100vh - 140px), 640px);
}

.tagrow {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.tagrow__name {
  flex: 1;
  min-width: 0;
  color: var(--text-bright);
  font: var(--body-l);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Ручка перетаскивания: сетка 2×3 из квадратиков. Размер и шаг кратны четырём:
   при масштабе 125% и 150% это целые физические пиксели, иначе квадраты
   размывает по-разному. */
.taggrip {
  flex: 0 0 auto;
  align-self: center;
  display: grid;
  grid-template-columns: repeat(2, 4px);
  gap: 4px;
  opacity: .28;
  cursor: grab;
  touch-action: none;
  transition: opacity .16s;
}
.taggrip:hover { opacity: .7 }
.taggrip i {
  display: block;
  width: 4px;
  height: 4px;
  background: var(--text-bright);
}

/* Класс вешает перетаскивание — то самое, что двигает строку: ставит его
   обработчик `ongrab`, а не входной параметр компонента. */
.tagrow.is-dragging { opacity: .55 }
.tagrow.is-dragging .taggrip { cursor: grabbing }

/* Три состояния: пусто, галочка, крестик. */
.tagbox {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 2px solid var(--tint-25);
  border-radius: var(--r-full);
  background: transparent;
  color: transparent;
  cursor: pointer;
  transition: border-color .16s, background .16s, color .16s;
}
.tagbox .material-symbols-outlined {
  font-size: 15px;
  font-variation-settings: 'wght' 600;
}

/* Реагирует только невыбранный: у включённого рамка уже цветная, и белая
   поверх неё сказала бы не то. Состояние в селекторе, а не порядок правил
   ниже, — иначе перестановка блоков молча сломала бы это. */
.tagbox[data-state="off"]:hover { border-color: var(--tint-55) }

.tagbox[data-state="on"] {
  border-color: var(--primary);
  background: var(--primary);
  color: var(--bg);
}
.tagbox[data-state="ex"] {
  border-color: var(--exclude);
  background: var(--exclude);
  color: var(--bg);
}

.tagrow__del {
  flex: 0 0 auto;
  display: block;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  /* Подложки нет, но скругление держим: по нему идёт рамка фокуса. */
  border-radius: var(--r-full);
  background: transparent;
  color: var(--tint-30);
  cursor: pointer;
  transition: color .16s;
}
.tagrow__del .material-symbols-outlined {
  display: block;
  width: 28px;
  font-size: 18px;
  line-height: 28px;
  text-align: center;
}
.tagrow__del:hover { color: var(--error) }
```

Два расхождения с макетом, и оба вынужденные: `#0a0a0a` у заливки переключателя
заменён на `var(--bg)` — это то же значение, и цвет по месту хук отклоняет;
скрытие системной полосы уехало в `scrollarea.css` задачей 1.

Создать `client/styles/scorerow.css` — перенос `index.html:1257-1284`:

```css
/* Цвет берётся из --score, который строка получает инлайн; сами значения лежат
   в палитре одним блоком. */
.scorerow {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.scorerow__stars {
  display: flex;
  gap: 1px;
  color: var(--score);
}
.scorerow__stars .material-symbols-outlined {
  font-size: 17px;
  font-variation-settings: 'FILL' 1;
}
.scorerow__stars .is-empty {
  color: var(--tint-14);
  font-variation-settings: 'FILL' 0;
}

.scorerow__label {
  margin-left: auto;          /* прижата к правому краю строки */
  color: var(--score);
  font: var(--title-s);
  white-space: nowrap;
}
```

Создать `client/styles/newtag.css` — перенос `index.html:1376-1421`:

```css
/* Без фона и рамки: в покое это просто серая надпись, при фокусе под ней
   проступает акцентная полоса. */
.newtag {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  margin-top: 10px;
  padding: 0 2px;
  border-bottom: 2px solid transparent;
  transition: border-color .18s;
}
.newtag:focus-within { border-bottom-color: var(--primary) }

.newtag__input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text);
  font: var(--body-l);
  caret-color: var(--primary);
  user-select: text;
}
.newtag__input::placeholder { color: var(--text-dim) }

/* Появляется, только когда есть что подтверждать. */
.newtag__ok {
  flex: 0 0 auto;
  display: block;
  width: 26px;
  height: 26px;
  padding: 0;
  border: none;
  border-radius: var(--r-full);
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  opacity: 0;
  transform: scale(.7);
  pointer-events: none;
  transition: opacity .16s, transform .16s, background .15s;
}
.newtag__ok .material-symbols-outlined {
  display: block;
  width: 26px;
  font-size: 18px;
  line-height: 26px;
  text-align: center;
}
.newtag__ok:hover { background: color-mix(in srgb, var(--primary) 14%, transparent) }

.newtag.is-filled .newtag__ok {
  opacity: 1;
  transform: none;
  pointer-events: auto;
}
```

Правил `.newtag__input` в макете нет: там строка ввода общая с полями окна
карточки, а окна карточки в этом плане ещё не будет. Значения взяты у
`.search__input` — единственного поля ввода, которое к этому моменту в проекте
есть, и совпадают они с ним не случайно: в макете оба ссылаются на одну и ту же
типографику. **Когда план 9 заведёт общее поле, эти пять правил обязаны уехать
туда** — иначе поле ввода окажется объявлено дважды.

- [ ] **Шаг 2: Написать переключатель и строку**

`client/components/TagBox.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'

  // Состояний три у фильтров и два у тегов карточки; сам переключатель одинаков,
  // а что за чем следует — решает тот, кто его поставил.
  let { state = 'off', onclick } = $props()

  const GLYPH = { off: 'check', on: 'check', ex: 'close' }
  const TITLE = { off: 'Не выбрано', on: 'Включено', ex: 'Исключено' }
</script>

<button type="button" class="tagbox" data-state={state} {onclick}
        aria-label={TITLE[state]} title={TITLE[state]}>
  <Icon name={GLYPH[state]} />
</button>
```

`client/components/TagRow.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'
  import TagBox from '$components/TagBox.svelte'

  let { name, state = 'off', ontoggle, ondelete = null, ongrab = null }
    = $props()
</script>

<li class="tagrow">
  {#if ongrab}
    <!-- Порядок хранит база: `tags.reorder` пишет `position`, и он переживает
         перезапуск. -->
    <span class="taggrip" onpointerdown={ongrab} aria-hidden="true">
      <i></i><i></i><i></i><i></i><i></i><i></i>
    </span>
  {/if}

  <span class="tagrow__name">{name}</span>

  {#if ondelete}
    <button type="button" class="tagrow__del" aria-label="Удалить" onclick={ondelete}>
      <Icon name="close" />
    </button>
  {/if}

  <TagBox {state} onclick={ontoggle} />
</li>
```

`client/components/ScoreRow.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'
  import TagBox from '$components/TagBox.svelte'
  import { LABELS, colorOf } from '$state/scores.js'

  let { score, state = 'off', ontoggle } = $props()

  const TEN = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
</script>

<li class="tagrow" style:--score={colorOf(score)}>
  <span class="scorerow">
    <span class="scorerow__stars">
      {#each TEN as step (step)}
        <span class:is-empty={step > score}><Icon name="star" /></span>
      {/each}
    </span>
    <span class="scorerow__label">{LABELS[score]}</span>
  </span>

  <TagBox {state} onclick={ontoggle} />
</li>
```

Звёзды здесь свои, а не `Stars.svelte` из плана 7, и это не дубль: у той десять
кнопок с дробной звездой и выставлением оценки, у этой — неподвижная строка из
десяти глифов, где закрашенность и есть само значение. Общее у них только слово
«звёзды»; сведение их в один компонент дало бы параметр «а теперь ты не
кнопка», то есть два поведения в одном месте.

- [ ] **Шаг 3: Написать форму нового тега**

`client/components/NewTag.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'

  // Ограничение из макета.
  const LIMIT = 24

  let { oncreate } = $props()

  let name = $state('')

  function submit(event) {
    event.preventDefault()
    const clean = name.trim()
    if (!clean) return
    oncreate(clean)
    name = ''
  }
</script>

<form class="newtag" class:is-filled={name.trim()} onsubmit={submit}>
  <input class="newtag__input" type="text" maxlength={LIMIT} spellcheck="false"
         autocomplete="off" placeholder="+ Новый тег"
         aria-label="Название нового тега" bind:value={name}>
  <button type="submit" class="newtag__ok" aria-label="Добавить тег">
    <Icon name="check" />
  </button>
</form>
```

- [ ] **Шаг 4: Подключить**

Дописать в `client/main.js`:

```js
import '$styles/taglist.css'
import '$styles/scorerow.css'
import '$styles/newtag.css'
```

- [ ] **Шаг 5: Коммит**

```bash
git add client/styles/ client/components/ client/main.js
git commit -m "feat: строка списка с тремя состояниями и форма нового тега"
```

---

### Задача 3: Три модалки фильтров

Жанры, теги и оценки. Списки разные, поведение одно, поэтому и сборка одна.

**Включённые внутри признака складываются по «или», между признаками — по «и»,
исключённые вычитаются последними.** Само сложение делает база; здесь только
перебор состояний, и он уже написан в `state/filters.js`.

**Кнопка в шапке горит, пока фильтр применён**, и повторное нажатие по горящей
сбрасывает фильтр целиком, а не открывает модалку.

**Файлы:**
- Создать: `client/app/FiltersModal.svelte`
- Изменить: `client/app/App.svelte`, `client/app/Topbar.svelte`

**Интерфейсы:**
- Потребляет: `cycled`, `isEmpty`, `cleared` из `$state/filters.js`; `plural`
  из `$state/facts.js`; `created` из `$state/tags.js`; `Confirm` из плана 9;
  `Modal`,
  `Scrollarea`, `TagRow`, `ScoreRow`; `call` из `$api/bridge.js`.
- Отдаёт: `FiltersModal` с входными `field`, `kind`, `filters`, `onfilters`,
  `onclose`.

- [ ] **Шаг 1: Написать сборку фильтров**

`client/app/FiltersModal.svelte`:

```svelte
<script>
  import Modal from '$components/Modal.svelte'
  import ScoreRow from '$components/ScoreRow.svelte'
  import Scrollarea from '$components/Scrollarea.svelte'
  import TagRow from '$components/TagRow.svelte'
  import { call } from '$api/bridge.js'
  import { cycled } from '$state/filters.js'

  let { field, kind, filters, onfilters, onclose } = $props()

  const TITLE = { genres: 'Жанры', tags: 'Теги', scores: 'Фильтр по оценке' }
  const TEN = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

  let rows = $state([])

  // Наборов жанров два: кино (фильмы и сериалы делят один) и игры. Наборов
  // тегов три — по одному на тип содержимого.
  const genreKind = $derived(kind === 'game' ? 'game' : 'film')

  $effect(() => {
    if (field === 'scores') return
    const ask = field === 'genres'
      ? call('refs.genres', genreKind)
      : call('marks.tags', kind)
    ask.then((list) => { rows = list })
  })

  const stateOf = (id) =>
    filters.on[field].includes(id) ? 'on'
      : filters.ex[field].includes(id) ? 'ex' : 'off'

  const toggle = (id) => onfilters(cycled(filters, field, id))
</script>

<Modal narrow={field === 'scores'} label={TITLE[field]} {onclose}>
  {#snippet children()}
    <Scrollarea>
      {#snippet children()}
        <ul class="taglist">
          {#if field === 'scores'}
            <!-- Список открывается на высоких оценках: их ищут чаще. -->
            {#each TEN as score (score)}
              <ScoreRow {score} state={stateOf(score)}
                        ontoggle={() => toggle(score)} />
            {/each}
          {:else}
            {#each rows as row (row.id)}
              <TagRow name={row.name} state={stateOf(row.id)}
                      ontoggle={() => toggle(row.id)} />
            {/each}
          {/if}
        </ul>
      {/snippet}
    </Scrollarea>
  {/snippet}
</Modal>
```

**Ни создания, ни удаления, ни перетаскивания здесь нет.** Модалка фильтра по
жанрам и по оценке их не имеет вовсе — набор зашит; у фильтра по тегам они есть,
и заводит их задача 4, вместе с модалкой тегов карточки: правка набора тегов
одна на обе.

- [ ] **Шаг 2: Открывать и закрывать**

В `client/app/App.svelte` — какое наложение открыто, знает сборка:

```svelte
  let modal = $state(null)   // null | 'genres' | 'tags' | 'scores'

  // Повторное нажатие по горящей кнопке сбрасывает **свой** признак, а не
  // открывает модалку: так в макете, где у каждого из трёх фильтров свой
  // `isActive()` и свой `reset()`.
  //
  // По признаку, а не одним махом на три: сбрасывая всё, кнопка «Жанры» стирала
  // бы теговый фильтр и не открывала ничего, а сочетание «выбрал драму,
  // исключил ужасы» стало бы недостижимым — при том что спека требует «между
  // признаками — по „и“».
  function filter(field) {
    if (!isEmpty(session.filters, field)) {
      session = { ...session, filters: cleared(session.filters, field) }
      return
    }
    modal = field
  }

  <Topbar ... onfilter={filter} />

  {#if modal}
    <FiltersModal field={modal} kind={session.kind} filters={session.filters}
                  onfilters={(next) => { session = { ...session, filters: next } }}
                  onclose={() => { modal = null }} />
  {/if}
```

- [ ] **Шаг 3: Посмотреть**

Сверить с макетом рядом:

- затемнение проявляется, окно приезжает из уменьшенного и смещённого;
- по верхней кромке окна неоновая нить, гаснущая к краям;
- строка перебирает три состояния: пусто → галочка → крестик;
- крестик красный, галочка акцентная и перекрашивается вместе с типом
  содержимого;
- список длиннее окна прокручивается своей полосой, ползунок хватается мышью;
- щелчок мимо окна закрывает, внутри — нет; Escape закрывает **верхнее** окно, а
  не все разом;
- лента сужается сразу, а кнопка в шапке загорается;
- повторное нажатие по горящей кнопке сбрасывает фильтр.

- [ ] **Шаг 4: Коммит**

```bash
git add client/app/
git commit -m "feat: три модалки фильтров с трёхпозиционными строками"
```

---

### Задача 4: Теги карточки и правка набора

Вторая модалка тегов и всё, что делается с самим набором: завести, удалить,
переставить.

**Список тот же, поведение разное — и это единственное, чем две модалки тегов
отличаются.** Здесь два состояния: есть и нет. Исключать тег у конкретной
карточки нечего.

**Ручной порядок обязан пережить перезапуск.** Его пишет `marks.reorder_tags` в
`position`, и перетаскивание — это перестановка списка плюс один вызов.

**Файлы:**
- Создать: `client/app/CardTagsModal.svelte`
- Изменить: `client/app/FiltersModal.svelte`, `client/app/App.svelte`

**Интерфейсы:**
- Потребляет: `Modal`, `Scrollarea`, `TagRow`, `NewTag`; `call` из
  `$api/bridge.js`.
- Отдаёт: `created(kind, name, ontrouble)` из `$state/tags.js`; `CardTagsModal`
  с входными `view`, `onview`, `onclose`, `ontrouble` — без последнего он падает
  на занятом имени тега.

- [ ] **Шаг 1: Написать модалку тегов карточки**

`client/app/CardTagsModal.svelte`:

```svelte
<script>
  import Modal from '$components/Modal.svelte'
  import NewTag from '$components/NewTag.svelte'
  import Scrollarea from '$components/Scrollarea.svelte'
  import TagRow from '$components/TagRow.svelte'
  import { call } from '$api/bridge.js'

  let { view, onview, onclose, ontrouble } = $props()

  let rows = $state([])
  let mine = $state(new Set(view.tags.map((tag) => tag.id)))

  $effect(() => { call('marks.tags', view.kind).then((list) => { rows = list }) })

  async function toggle(tag) {
    const on = mine.has(tag.id)
    await call(on ? 'marks.unassign' : 'marks.assign', view.item_id, tag.id)

    const next = new Set(mine)
    on ? next.delete(tag.id) : next.add(tag.id)
    mine = next
    // Карточка в ленте обязана показать метку сразу: перечитывать её целиком
    // ради одной строки незачем.
    onview({ tags: rows.filter((row) => next.has(row.id)) })
  }

  const create = (name) =>
    created(view.kind, name, ontrouble).then((row) => {
      if (row) rows = [...rows, row]
    })
</script>

<Modal label="Теги фильма" {onclose}>
  {#snippet children()}
    <Scrollarea>
      {#snippet children()}
        <ul class="taglist">
          {#each rows as row (row.id)}
            <TagRow name={row.name} state={mine.has(row.id) ? 'on' : 'off'}
                    ontoggle={() => toggle(row)} />
          {/each}
        </ul>
      {/snippet}
    </Scrollarea>
    <NewTag oncreate={create} />
  {/snippet}
</Modal>
```

**Заведение тега — одно на обе модалки.** Вынесено в `client/state/tags.js`:

```js
import { call } from '$api/bridge.js'

/** Новый тег или `null`, если завести не вышло.
 *
 *  Отказ обрабатывается здесь, а не у каждого вызывающего: занятое имя — это
 *  нормальный ход событий, и сказать про него надо одинаково в обоих местах. */
export async function created(kind, name, ontrouble) {
  try {
    const id = await call('marks.create_tag', kind, name)
    return { id, name }
  } catch (error) {
    ontrouble(error.kind === 'tag-exists' ? 'Такой тег уже есть'
                                          : 'Не удалось завести тег')
    return null
  }
}
```

Слой `state/` тут не нарушается: это не разметка и не сборка, а обычная функция
над обычными данными — та же, что `passes` или `lost`.

- [ ] **Шаг 2: Дописать правку набора в модалку фильтра по тегам**

В `FiltersModal.svelte` у поля `tags` появляются крестик, форма и ручка —
остальные два фильтра их не получают: набор жанров зашит в миграцию, набор
оценок это десять чисел.

```svelte
  const editable = $derived(field === 'tags')

  // Удаление тега бьёт по всей библиотеке и не отменяется, поэтому у тега с
  // носителями оно спрашивает и называет их число. Ничей уходит молча: терять
  // нечего, и спрашивать не о чем.
  async function remove(row) {
    const worn = await call('marks.tag_usage', row.id)
    if (!worn) return drop(row)
    asking = { row, worn }
  }

  async function drop(row) {
    await call('marks.delete_tag', row.id)
    rows = rows.filter((each) => each !== row)
    asking = null
  }

  // Тот же `created`, что и у модалки тегов карточки: заведение одно на обе, и
  // отказ у него один — занятое имя это нормальный ход событий.
  const create = (name) =>
    created(kind, name, ontrouble).then((row) => { if (row) rows = [...rows, row] })

  // Порядок хранит база: без вызова перестановка живёт до перезапуска.
  async function reorder(from, to) {
    const next = [...rows]
    next.splice(to, 0, ...next.splice(from, 1))
    rows = next
    await call('marks.reorder_tags', kind, next.map((row) => row.id))
  }
```

и в разметке строки — `ondelete={() => remove(row)}` с `ongrab` при `editable`,
плюс `<NewTag oncreate={create} />` после списка и подтверждение поверх:

```svelte
  {#if asking}
    <Confirm label="Удалить тег" ok="Удалить" danger
             text={`Удалить тег «${asking.row.name}»? ${asking.worn} `
                   + `${plural(asking.worn, NOUNS[kind])} `
                   + `${plural(asking.worn, WEARS)} этот тег.`}
             onyes={() => drop(asking.row)}
             onclose={() => { asking = null }} />
  {/if}
```

**Существительное — по открытой вкладке**, как в макете: «3 фильма», «3 сериала»,
«3 игры». Склонение берётся общим `plural` из `$state/facts.js` — тем же, что
считает серии и сезоны, второго его объявления быть не должно.

```js
  const NOUNS = { movie: ['фильм', 'фильма', 'фильмов'],
                  series: ['сериал', 'сериала', 'сериалов'],
                  game: ['игра', 'игры', 'игр'] }

  const WEARS = ['имеет', 'имеют', 'имеют']
```

**Окно подтверждения заводит план 9**, а зовут его отсюда и оттуда: спрашивают им
удаление карточки, удаление тега с носителями и совпадение названия. Значит либо
`Confirm` переезжает в план 8 вместе с первым потребителем, либо эта половина
задачи 4 уезжает в план 9 — **выбирает исполнитель на месте**, и довод
записывает; на порядок задач это не влияет, планы соседние.

**Перетаскивание указателем:** строка переставляется, как только курсор перешёл
середину соседней. Порядок при этом держит массив `rows`, а не DOM: в макете его
хранил сам DOM, но там не было ни ленты, ни перерисовки по данным.

- [ ] **Шаг 3: Открыть модалку с карточки**

В `App.svelte` кнопка «± Тег» ленты открывает вторую модалку:

```svelte
  let tagging = $state(null)

  <Screen ... ontag={(view) => { tagging = view }} />

  {#if tagging}
    <CardTagsModal view={tagging}
                   onview={(fields) => { /* пробросить в ленту */ }}
                   ontrouble={(text) => { trouble = text }}
                   onclose={() => { tagging = null }} />
  {/if}
```

- [ ] **Шаг 4: Посмотреть**

- «± Тег» на карточке открывает список с двумя состояниями, без крестиков;
- отметил тег — метка появляется на карточке сразу, белой, отдельно от жанров;
- фильтр по тегам открывает тот же список, но с тремя состояниями, крестиками
  удаления, ручками и формой;
- завёл тег — он появляется в обоих списках;
- переставил строки, перезапустил приложение — порядок на месте;
- завёл тег с занятым именем — снизу выехала плашка, тег не задвоился.

- [ ] **Шаг 5: Коммит**

```bash
git add client/app/
git commit -m "feat: теги карточки и правка набора тегов"
```

---

### Задача 5: Статистика

Гистограмма распределения оценок по тому же отфильтрованному набору, что и
разделы с карточками.

**Столбцов десять, дробные оценки округляются вниз.** У игр оценка это среднее
трёх шкал, 7.33 попадает в столбец 7.

**Средняя — настоящая, а не собранная из столбцов.** Столбец знает округлённое
вниз значение, и у игр сумма по столбцам занижала бы результат почти на полбалла.
Считает её база.

**Столбцы отрастают при каждом заходе на раздел**, а не один раз: класс вешается
на вход, а не держится состоянием.

**Файлы:**
- Создать: `client/styles/chart.css`, `client/components/Bar.svelte`
- Создать: `tests/web/histogram.test.js`
- Изменить: `client/app/StatsScreen.svelte`, `client/main.js`

**Интерфейсы:**
- Потребляет: `colorOf` из `$state/scores.js`; `requestOf` из `./section.js`.
- Отдаёт: `heightsOf(buckets)` — доля каждого столбца от пика; `Bar` с
  входными `score`, `count`, `share`, `index`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/web/histogram.test.js`:

```js
import { describe, expect, it } from 'vitest'

import { heightsOf } from '$state/histogram.js'

describe('высоты столбцов', () => {
  it('считаются от пика, а не от суммы', () => {
    // От суммы самый высокий столбец занял бы долю процентов, и гистограмма
    // выглядела бы плоской.
    const shares = heightsOf([{ score: 1, count: 5 }, { score: 2, count: 10 }])
    expect(shares).toEqual([0.5, 1])
  })

  it('пустой столбец имеет нулевую долю, а не отсутствует', () => {
    // Десять столбцов стоят всегда: пропущенный сдвинул бы шкалу, и седьмая
    // оценка оказалась бы под шестой подписью.
    const shares = heightsOf([{ score: 1, count: 0 }, { score: 2, count: 4 }])
    expect(shares).toEqual([0, 1])
  })

  it('на пустой библиотеке не делит на ноль', () => {
    const shares = heightsOf([{ score: 1, count: 0 }, { score: 2, count: 0 }])
    expect(shares).toEqual([0, 0])
  })
})
```

- [ ] **Шаг 2: Прогнать и увидеть красное**

```bash
cd client && npm test
```

Ожидание: FAIL, `Cannot find module '$state/histogram.js'`.

- [ ] **Шаг 3: Написать доли**

Создать `client/state/histogram.js`:

```js
/** Доля каждого столбца от самого высокого. */

export function heightsOf(buckets) {
  const peak = Math.max(...buckets.map((one) => one.count), 0)
  // От суммы самый высокий занял бы доли процента: гистограмма показывает
  // соотношение, а не вклад в целое.
  return buckets.map((one) => (peak ? one.count / peak : 0))
}
```

- [ ] **Шаг 4: Перенести оформление**

Создать `client/styles/chart.css` — перенос `index.html:730-816`:

```css
/* Ширина равна содержимому шапки: график живёт в той же колонке, что поиск,
   переключатель и кнопки. */
.chart {
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: var(--content-w, 1146px);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  /* Сверху запас под число над самым высоким столбцом. */
  padding: 34px 0 16px;
}

.chart__bars {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: stretch;
  gap: 14px;
}

.bar {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-rows: 1fr auto;
  justify-items: center;
  gap: 7px;
}

.bar__plot {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: flex-end;
}

.bar__fill {
  position: relative;
  width: 100%;
  height: max(var(--h), 6px);
  border-radius: 5px 5px 0 0;
  background: var(--score);
}

/* Число привязано к верхушке своего столбца, а не к общей строке. */
.bar__count {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  margin-bottom: 5px;
  text-align: center;
  font: var(--label-l);
  font-weight: 700;
  color: var(--score);
}

.bar__value {
  font: var(--title-s);
  font-weight: 700;
  color: var(--text-bright);
}

.chart__foot {
  margin: 14px 0 0;
  padding-top: 14px;
  border-top: 1px solid var(--tint-07);
  text-align: center;
  font: var(--body-m);
  color: var(--tint-45);
}
.chart__foot b {
  color: var(--tint-80);
  font-weight: 600;
}

/* Столбцы вырастают из пола при каждом заходе на раздел. Растёт высота, а не
   масштаб: масштаб сплющил бы и число над столбцом. */
.view.is-drawing .bar__fill {
  animation: bar-rise .5s cubic-bezier(.2,.8,.2,1) both;
  animation-delay: calc(var(--i) * 45ms);
}

@keyframes bar-rise {
  from { height: 0 }
  to   { height: max(var(--h), 6px) }
}
```

`var(--text-bright)` у `.bar__value` заменён на `var(--text-bright)` — то же значение, и цвет
по месту хук отклоняет.

- [ ] **Шаг 5: Написать столбец и раздел**

`client/components/Bar.svelte`:

```svelte
<script>
  import { colorOf } from '$state/scores.js'

  let { score, count, share, index } = $props()
</script>

<div class="bar" style:--score={colorOf(score)} style:--i={index}
     style:--h={`${Math.round(share * 100)}%`}>
  <div class="bar__plot">
    <div class="bar__fill">
      <span class="bar__count">{count}</span>
    </div>
  </div>
  <span class="bar__value">{score}</span>
</div>
```

`client/app/StatsScreen.svelte`:

```svelte
<script>
  import Bar from '$components/Bar.svelte'
  import { cancel, numbered } from '$api/bridge.js'
  import { heightsOf } from '$state/histogram.js'
  import { requestOf } from '$state/section.js'

  let { session, ontrouble } = $props()

  let histogram = $state({ buckets: [], total: 0, average: null })
  const ops = []

  $effect(() => () => { cancel(ops.splice(0)) })

  // Гистограмма строится по тому же отфильтрованному набору, что и разделы с
  // карточками, — иначе отфильтрованную её не увидеть никогда.
  $effect(() => {
    const { kind, filters } = requestOf(session)
    numbered('feed.histogram', kind, filters, { channel: 'feed', ops })
      .then((answer) => { histogram = answer })
      .catch((error) => {
        if (!error.silent) ontrouble('Не удалось построить гистограмму')
      })
  })

  const shares = $derived(heightsOf(histogram.buckets))
</script>

<div class="chart">
  <div class="chart__bars">
    {#each histogram.buckets as bucket, index (bucket.score)}
      <Bar score={bucket.score} count={bucket.count} share={shares[index]}
           {index} />
    {/each}
  </div>

  <!-- Оба числа считает база по неокруглённым значениям: сумма по столбцам у
       игр занижала бы среднюю почти на полбалла. -->
  <p class="chart__foot">
    Средняя оценка <b>{histogram.average?.toFixed(2) ?? '—'}</b>,
    всего <b>{histogram.total}</b>
  </p>
</div>
```

**Подпись подвала — «Средняя оценка … , всего …».** Согласовано 31.07.2026:
слова те, а числа в макете были заглушкой.

- [ ] **Шаг 6: Завести отрастание при каждом заходе**

Класс отрастания вешается на каждый заход и снимается после анимации: держать
его состоянием нельзя — тогда столбцы вырастут один раз за всё время работы.

**Приём тот же, что у столбиков иконки статистики в шапке**, и второй раз он не
переписывается: `redrawn` из `$state/redraw.js` заведён планом 6 у своего первого
потребителя.

Класс на `.view` вешает `App.svelte`, там же, где выбирается экран:

```svelte
  let drawing = $state(false)

  $effect(() => {
    if (session.section !== 'stats') return
    redrawn((on) => { drawing = on })
  })

  <section class="view is-shown" class:is-drawing={drawing}>
```

**Имя класса общее с шапкой, и это не столкновение.** `.is-drawing` там стоит на
`.tools`, здесь на `.view`, и оба правила отбирают по родителю: `.is-drawing
.tools__chart rect` против `.view.is-drawing .bar__fill`.

- [ ] **Шаг 7: Прогнать и посмотреть**

```bash
cd client && npm test && npm run build
cd .. && pipenv run python main.py
```

Ожидание: PASS, 72 теста. В окне: десять столбцов, цвет по шкале, число над
верхушкой своего столбца, подпись оценки под ним; при заходе на раздел столбцы
отрастают из пола с задержкой; фильтр сужает и гистограмму тоже; уход и возврат
проигрывают анимацию заново.

- [ ] **Шаг 8: Коммит**

```bash
git add client/state/histogram.js client/styles/chart.css \
        client/components/Bar.svelte client/app/ client/main.js \
        tests/web/histogram.test.js
git commit -m "feat: гистограмма оценок по отфильтрованному набору"
```

---

## Самопроверка плана

**Покрытие.** Спека разделов: «Фильтр умеет исключать» — задачи 2 и 3; «У тегов
самого фильма исключения нет» — задача 4; «Что в подвале статистики» и «Столбцов
десять» — задача 5; «Фильтр по тегам показывает набор текущего типа контента» —
задача 3. Опись макета: пять наложений, из них четыре здесь, пятое (окно
карточки) — план 9.

**Что этот план сознательно не делает.** Окна карточки нет: правка, удаление,
привязка и подсказки имён — план 9. Ссылка на страницу источника у агрегаторов
по-прежнему не собирается. Поле ввода объявлено локально в `newtag.css` и
переезжает в общее, когда план 9 заведёт `field.css`, — это записано прямо там.

**Открытых вопросов не осталось:** слова в подвале статистики согласованы
31.07.2026.

**Чем измеряется готовность.** `npm test` зелёный, 72 теста. Фильтры сужают и
ленту, и гистограмму; теги вешаются на карточку и переживают перезапуск вместе
со своим порядком.
