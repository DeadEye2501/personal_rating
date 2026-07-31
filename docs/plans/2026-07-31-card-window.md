# План 9. Окно карточки

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** библиотеку можно наполнять без интернета. Карточка заводится руками,
правится, привязывается к внешней базе вставкой ссылки, отвязывается и
удаляется. После этого плана приложение умеет всё, что записано в спеках; дальше
только поставка.

**Архитектура:** одно окно на создание и на правку — пустое заводит, заполненное
правит, а «Сохранить» сам решает, вставка это или обновление. Поля показываются
своему типу содержимого: у фильма длительность, у сериала сезоны и серии, у игры
разработчик и издатель.

**Состав пишется страницей, а не сервисом.** Порядок записи — карточка, жанры,
люди, студии, постер — принадлежит ей: решение проекта «клиент зовёт репозитории
напрямую, сервисный слой поверх не заводится».

**Стек:** тот же. Ни одной новой зависимости.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от планов 5–8.** Мост отвечает на всё, оболочка модалки и своя
  полоса прокрутки написаны, лента зовёт правку и удаление пустыми
  обработчиками.
- **Обязательно только название.** Всё остальное дозаполняется когда угодно:
  требовать год у короткометражки, которую помнишь смутно, значит мешать.
- **Совпадение названия — предупреждение, а не запрет.** Сравнение по названию и
  по оригинальному названию, и только внутри того же типа содержимого.
- **Внешнее заполняет только пустое.** Непустое считается занятым целиком,
  включая состав и жанры. Галочка «перезаписать данные» — на случай, когда
  карточка заводилась на скорую руку.
- **Значения макета переносятся точь-в-точь**, ничего оформительского не
  придумывается, `<style>` внутри компонента не бывает, цвет — только в палитре.
- **Компоненты не проверяются**, проверяется `state/`.
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ client/
│  ├─ styles/
│  │  ├─ field.css               поле ввода: подчёркивание, подсказка
│  │  ├─ cardform.css            раскладка окна карточки
│  │  ├─ picker.css              поле с подсказкой и выбранным
│  │  └─ btn.css                 кнопки подвала окна
│  ├─ components/
│  │  ├─ Field.svelte            строка ввода
│  │  ├─ Picker.svelte           поле с подсказкой имён
│  │  ├─ PosterPick.svelte       постер: файл, перетаскивание, Ctrl+V
│  │  └─ Button.svelte           кнопка подвала
│  ├─ state/
│  │  └─ card.js                 форма карточки: поля по типу, что заполнено
│  └─ app/
│     ├─ CardModal.svelte        окно создания и правки
│     ├─ LinkField.svelte        вставка ссылки и привязка
│     └─ Confirm.svelte          подтверждение и предупреждение
└─ tests/web/
   └─ card.test.js               поля по типу, пустое и занятое
```

Правятся и чужие файлы: `client/styles/newtag.css` (пять правил поля ввода
уезжают в `field.css` — это было записано в плане 8), `client/app/App.svelte`
(окно, подтверждение, «+» в шапке), `client/main.js`.

---

### Задача 1: Поле ввода и оболочка окна

Раскладка окна и все его поля, кроме двух с подсказкой. Здесь же — общее поле
ввода, которое план 8 объявил у себя временно.

**Раскладка считается от постера.** Его ширина, высота строки и оба отступа —
переменные, а не числа по месту: высота колонки полей задана постером, иначе
каждое новое поле слева растягивало бы синопсис и уводило режиссёра вниз.

**Черта проступает только под фокусом.** В покое поле обозначает себя
подсказкой: десяток линий разом превращает окно в бланк.

**Файлы:**
- Создать: `client/styles/field.css`, `cardform.css`, `btn.css`
- Создать: `client/components/Field.svelte`, `Button.svelte`
- Создать: `client/state/card.js`, `tests/web/card.test.js`
- Создать: `client/app/CardModal.svelte`
- Изменить: `client/styles/newtag.css`, `client/main.js`

**Интерфейсы:**
- Потребляет: `Modal`, `Scrollarea` из плана 8.
- Отдаёт: `FIELDS`, `emptyCard(kind)`, `shownFor(kind)`, `filled(card)`;
  `Field` с входными `value`, `placeholder`, `variant`; `CardModal` с
  `view`, `kind`, `onsave`, `onclose`.

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/web/card.test.js`:

```js
import { describe, expect, it } from 'vitest'

import { emptyCard, filled, shownFor } from '$state/card.js'

describe('форма карточки', () => {
  it('у фильма длительность, а сезонов нет', () => {
    const shown = shownFor('movie')
    expect(shown).toContain('runtime')
    expect(shown).not.toContain('seasons_count')
  })

  it('у сериала сезоны и серии вместо длительности', () => {
    const shown = shownFor('series')
    expect(shown).toContain('seasons_count')
    expect(shown).toContain('episodes_count')
    expect(shown).not.toContain('runtime')
  })

  it('у игры ни того, ни другого', () => {
    // Сезонов у неё нет, а поля времени прохождения убраны из модели: их не
    // отдавал ни один источник, а вбивать такое руками никто не станет.
    const shown = shownFor('game')
    expect(shown).not.toContain('runtime')
    expect(shown).not.toContain('seasons_count')
  })

  it('роли состава разные у трёх типов', () => {
    // Режиссёр у фильма, шоураннер у сериала, разработчик с издателем у игры.
    expect(shownFor('movie')).toContain('director')
    expect(shownFor('series')).toContain('showrunner')
    expect(shownFor('game')).toContain('developer')
    expect(shownFor('movie')).not.toContain('developer')
  })

  it('пустая форма знает свой тип и больше ничего', () => {
    const card = emptyCard('game')
    expect(card.kind).toBe('game')
    expect(card.title).toBe('')
    expect(card.genres).toEqual([])
  })

  it('заполненным считается непустое, а не тронутое', () => {
    // Внешнее доливает только пустое, и «пустое» здесь и определяется. Пробел
    // — это пусто: иначе случайный Space занял бы поле навсегда.
    expect(filled({ title: 'Одиссея' }, 'title')).toBe(true)
    expect(filled({ title: '   ' }, 'title')).toBe(false)
    expect(filled({ year: 0 }, 'year')).toBe(false)
    expect(filled({ year: 1997 }, 'year')).toBe(true)
  })

  it('непустое — значит занятое целиком, в том числе у полей, которых много', () => {
    // Вписал одного разработчика — состав не дополняется. Выбрал один жанр —
    // то же самое.
    expect(filled({ companies: [{ name: 'CD Projekt' }] }, 'companies')).toBe(true)
    expect(filled({ companies: [] }, 'companies')).toBe(false)
  })
})
```

- [ ] **Шаг 2: Прогнать и увидеть красное**

```bash
cd client && npm test
```

Ожидание: FAIL, `Cannot find module '$state/card.js'`.

- [ ] **Шаг 3: Написать форму**

Создать `client/state/card.js`:

```js
/** Форма карточки: какие поля показывать типу и что считать заполненным. */

// Общие для всех трёх типов.
const COMMON = ['title', 'original_title', 'year', 'synopsis', 'poster',
                'genres', 'link']

// Своё у каждого типа: длительность у фильма, сезоны и серии у сериала, у игры
// ни того, ни другого — поля времени прохождения убраны из модели.
const OWN = {
  movie: ['runtime', 'director', 'actors'],
  series: ['seasons_count', 'episodes_count', 'showrunner', 'actors'],
  game: ['developer', 'publisher'],
}

export const FIELDS = COMMON

export const shownFor = (kind) => [...COMMON, ...OWN[kind]]

export const emptyCard = (kind) => ({
  kind,
  title: '',
  original_title: '',
  year: null,
  synopsis: '',
  runtime: null,
  seasons_count: null,
  episodes_count: null,
  genres: [],
  people: [],
  companies: [],
})

/** Заполненным считается непустое, а не тронутое: внешнее доливает только
 *  пустое, и граница проходит здесь. Пробел — это пусто, иначе случайный
 *  Space занял бы поле навсегда. */
export function filled(card, field) {
  const value = card[field]
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'string') return value.trim().length > 0
  return Boolean(value)
}
```

- [ ] **Шаг 4: Перенести поле ввода**

Создать `client/styles/field.css` — перенос `docs/design/index.html:996-1054`.
Правила `.newtag__input` из плана 8 **удаляются из `newtag.css`** и переезжают
сюда: в макете строка ввода одна на всё окно и на форму нового тега, отличаются
только обёртки.

```css
.field {
  display: flex;
  align-items: center;
  /* Без этого поле не сожмётся ниже собственной ширины input, и заданная ширина
     короткого поля не сработает. */
  min-width: 0;
  min-height: var(--field-h, 46px);
  padding: 0 2px;
  /* Черта проступает только под фокусом: в покое поле обозначает себя
     подсказкой, а десяток линий разом превращает окно в бланк. */
  border-bottom: 2px solid transparent;
  transition: border-color .18s;
}
.field:focus-within { border-bottom-color: var(--primary) }

.field__input,
.newtag__input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-bright);
  font: var(--body-l);
  caret-color: var(--primary);
  user-select: text;         /* body запрещает выделение, полю оно нужно */
}
.field__input::placeholder,
.newtag__input::placeholder {
  color: var(--text-dim);
  transition: color .16s;
}
.field:hover .field__input::placeholder,
.newtag__input:hover::placeholder { color: var(--text-bright) }

.field__input:focus::placeholder,
.newtag__input:focus::placeholder { color: transparent }

/* Название — главное поле карточки, поэтому крупнее остальных. */
.field--title .field__input { font: var(--title-l) }

/* Синопсис. Подчёркивания нет намеренно: под абзацем оно читается как черта, а
   не как поле. Рамки и фона тоже нет — только подсказка, которая уступает
   место курсору. */
.field--area {
  flex: 1;
  align-items: stretch;
  padding-top: 12px;
  border-bottom: none;
}
/* Системная полоса убрана: вместо неё своя, та же, что в списках тегов. Отступ
   справа — место под неё. */
.field--area .field__input {
  resize: none;
  line-height: 22px;
  padding-right: 14px;
  scrollbar-width: none;
}
.field--area .field__input::-webkit-scrollbar { display: none }
```

- [ ] **Шаг 5: Перенести раскладку окна и кнопки**

Создать `client/styles/cardform.css` — перенос `index.html:914-990`:

```css
/* Окно создания и правки — одно и то же: пустое заводит, заполненное правит.
   Раскладка считается от постера, поэтому его ширина, высота строки и оба
   отступа — переменные, а не числа по месту. */
.modal--card {
  --poster-w: 230px;
  --field-h: 46px;
  --row-gap: 14px;
  --col-gap: 36px;

  width: min(1080px, 100%);
  max-height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--row-gap);
  padding: 34px 40px 28px;
}

/* Постер слева, поля справа от него. */
.cardform__top {
  display: flex;
  align-items: flex-start;
  gap: var(--col-gap);
}

/* Высота задана постером, а не соседней колонкой: иначе каждое новое поле слева
   растягивало бы синопсис и уводило режиссёра вниз. */
.cardform__fields {
  flex: 1;
  min-width: 0;
  height: calc(var(--poster-w) * 1.5);
  display: flex;
  flex-direction: column;
  gap: var(--row-gap);
}

/* Строка из нескольких полей: длинное тянется, короткое стоит по своей ширине. */
.cardform__row {
  display: flex;
  gap: 20px;
}
.cardform__row .field { flex: 1 }
.cardform__row .field--short { flex: 0 0 92px }

/* Галочка появляется, только когда ссылка разобрана, — она и есть единственный
   признак, что адрес понят. */
.cardform__valid {
  flex: 0 0 auto;
  align-self: center;
  font-size: 22px;
  color: var(--primary);
}

/* Чекбокс «перезаписать» виден всегда; что он значит — в подсказке. */
.cardform__check {
  flex: 0 0 auto;
  align-self: center;
}

/* Пропорция та же, что у обложки в ленте: постер обрезается под 2:3. */
.cardform__poster {
  flex: 0 0 var(--poster-w);
  align-self: flex-start;
  aspect-ratio: 2 / 3;
  display: grid;
  place-items: center;
  border: 1px solid var(--tint-18);
  border-radius: 8px;
  color: var(--tint-22);
  cursor: pointer;
  overflow: hidden;
  transition: border-color .16s, color .16s;
}
.cardform__poster .material-symbols-outlined { font-size: 56px }
.cardform__poster img { width: 100%; height: 100%; object-fit: cover }

.cardform__poster:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.cardform__foot {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  gap: 14px;
}
```

Правила `img` и `overflow` в макете нет по той же причине, что и в ленте: там
нет ни одного `<img>`.

Создать `client/styles/btn.css` — перенос `index.html:1162-1184`:

```css
/* Ни подложки, ни рамки в покое — кнопка это надпись, и обе одинаково блёклы.
   Под курсором проступает рамка и светлеет текст; разводит их только цвет:
   отмена белым, сохранение акцентом. */
.btn {
  min-width: 150px;
  padding: 12px 26px;
  /* Рамка стоит всегда и только красится: заводить её под курсором значило бы
     двигать соседей в момент наведения. */
  border: 1px solid transparent;
  border-radius: var(--r-full);
  background: transparent;
  font: var(--label-l);
  color: var(--text-dim);
  cursor: pointer;
  transition: color .16s, border-color .16s;
}

.btn--cancel:hover {
  border-color: var(--text-bright);
  color: var(--text-bright);
}

.btn--go:hover {
  border-color: var(--primary);
  color: var(--primary);
}
```

- [ ] **Шаг 6: Написать поле и кнопку**

`client/components/Field.svelte`:

```svelte
<script>
  let { value = $bindable(''), placeholder, variant = '', area = false,
        label = placeholder } = $props()
</script>

<label class="field {variant}">
  {#if area}
    <textarea class="field__input" {placeholder} aria-label={label}
              spellcheck="false" bind:value></textarea>
  {:else}
    <input class="field__input" type="text" {placeholder} aria-label={label}
           spellcheck="false" autocomplete="off" bind:value>
  {/if}
</label>
```

`client/components/Button.svelte`:

```svelte
<script>
  let { variant, onclick, children } = $props()
</script>

<button type="button" class="btn {variant}" {onclick}>{@render children()}</button>
```

- [ ] **Шаг 7: Собрать окно**

`client/app/CardModal.svelte` — поля по типу, постер и подсказки встанут в
задачах 2 и 3:

```svelte
<script>
  import Button from '$components/Button.svelte'
  import Field from '$components/Field.svelte'
  import Modal from '$components/Modal.svelte'
  import Scrollarea from '$components/Scrollarea.svelte'
  import { emptyCard, shownFor } from '$state/card.js'

  let { view = null, kind, onsave, onclose } = $props()

  // Одно окно на создание и на правку: пустое заводит, заполненное правит.
  // Тип берётся из тумблера шапки и отдельно не спрашивается.
  let card = $state(view ? { ...view } : emptyCard(kind))

  const shown = $derived(new Set(shownFor(card.kind)))
</script>

<Modal label="Карточка" {onclose}>
  {#snippet children()}
    <div class="cardform__top">
      <div class="cardform__poster"></div>

      <div class="cardform__fields">
        <Field bind:value={card.title} placeholder="Название" variant="field--title" />

        <div class="cardform__row">
          <Field bind:value={card.original_title} placeholder="Оригинальное название" />
          <Field bind:value={card.year} placeholder="Год" variant="field--short" />
          {#if shown.has('runtime')}
            <Field bind:value={card.runtime} placeholder="Минуты" variant="field--short" />
          {/if}
          {#if shown.has('seasons_count')}
            <Field bind:value={card.seasons_count} placeholder="Сезоны" variant="field--short" />
            <Field bind:value={card.episodes_count} placeholder="Серии" variant="field--short" />
          {/if}
        </div>

        <Scrollarea>
          {#snippet children()}
            <Field bind:value={card.synopsis} placeholder="Синопсис"
                   variant="field--area" area />
          {/snippet}
        </Scrollarea>
      </div>
    </div>

    <div class="cardform__foot">
      <Button variant="btn--cancel" onclick={onclose}>
        {#snippet children()}Отмена{/snippet}
      </Button>
      <Button variant="btn--go" onclick={() => onsave(card)}>
        {#snippet children()}Сохранить{/snippet}
      </Button>
    </div>
  {/snippet}
</Modal>
```

**Кнопки «удалить» внутри окна нет.** Удаление живёт на карточке, и второго
входа ему не нужно.

- [ ] **Шаг 8: Подключить, прогнать, посмотреть**

Дописать в `client/main.js`:

```js
import '$styles/field.css'
import '$styles/cardform.css'
import '$styles/btn.css'
```

Открыть окно кнопкой «+» шапки (`onadd` в `App.svelte`).

```bash
cd client && npm test && npm run build
cd .. && pipenv run python main.py
```

Ожидание: PASS, 70 тестов. В окне: постер слева, поля справа, подчёркивание
только под фокусом, у фильма «Минуты», у сериала «Сезоны» и «Серии», у игры ни
того ни другого.

- [ ] **Шаг 9: Коммит**

```bash
git add client/state/card.js client/styles/ client/components/ client/app/ \
        client/main.js tests/web/card.test.js
git commit -m "feat: окно карточки — поля по типу содержимого"
```

---

### Задача 2: Поле с подсказкой

Актёры, режиссёр, студии и жанры. Здесь же — жест, которым различаются полные
тёзки.

**Enter контекстный.** Ввёл имя, ничего в списке не подсвечено, Enter — **новый
человек**. Подсветил стрелкой или выбрал мышью — **существующий**. Совпадение
имени само по себе не решает ничего: завести второго Василия Пупкина можно.

**Выбор мышью идёт на `mousedown`, а не на `click`:** поле теряет фокус раньше,
чем клик состоится, и список успевает закрыться.

**Строка подсказки несёт название самой высоко оценённой связанной карточки** —
по нему человека и узнают. Различие видно до наведения: иначе, чтобы найти
нужного из четырёх однофамильцев, пришлось бы наводить на каждого по очереди.

**Файлы:**
- Создать: `client/styles/picker.css`, `client/components/Picker.svelte`
- Изменить: `client/app/CardModal.svelte`

**Интерфейсы:**
- Потребляет: `call` из `$api/bridge.js`; `Field`.
- Отдаёт: `Picker` с входными `label`, `hits`, `chosen`, `ontype`, `onchosen`,
  `oncreate`. За мостом ходит сборка: у компонента своего источника данных не
  бывает, и `api/` ему закрыт машинной проверкой границы слоёв.

- [ ] **Шаг 1: Перенести оформление**

Создать `client/styles/picker.css` — перенос `index.html:1060-1148`:

```css
/* Актёры и жанры: поле стоит под постером, той же ширины, а выбранное ложится
   справа — в место, которое иначе пустует. */
.cardform__pick {
  display: flex;
  align-items: flex-start;
  gap: var(--col-gap);
}

.cardform__pick .picker {
  position: relative;
  flex: 0 0 var(--poster-w);
}

/* Список совпадений висит над содержимым и ничего не сдвигает. */
.picker__hits {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 5;
  margin: 4px 0 0;
  padding: 4px;
  max-height: 216px;
  overflow-y: auto;
  list-style: none;
  border: 1px solid var(--tint-09);
  border-radius: 10px;
  background: var(--surface-pop);
  box-shadow: 0 18px 40px var(--shade-55);
  scrollbar-width: none;
}
.picker__hits::-webkit-scrollbar { display: none }

.picker__hit {
  display: block;
  width: 100%;
  padding: 7px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--tint-75);
  font: var(--body-m);
  text-align: left;
  cursor: pointer;
}
.picker__hit:hover,
.picker__hit.is-marked {
  background: var(--fill-primary-hover);
  color: var(--primary);
}

/* Выбранное — не «таблетки», а имена подряд, у каждого крестик. */
.picker__chosen {
  flex: 1;
  min-width: 0;
  min-height: var(--field-h);
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0 18px;
}

.picked {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--tint-80);
  font: var(--body-m);
}
.picked__del {
  display: block;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  border-radius: var(--r-full);
  background: transparent;
  color: var(--tint-30);
  cursor: pointer;
  transition: color .16s;
}
.picked__del .material-symbols-outlined {
  display: block;
  width: 20px;
  font-size: 15px;
  line-height: 20px;
  text-align: center;
}
.picked__del:hover { color: var(--error) }
```

Правило `.picker__hit.is-marked` в макете отсутствует: там подсветка стрелками
не сделана вовсе, а без видимой подсветки жест различения тёзок не работает —
однозначность держится ровно на том, что подсветку видно. Значения взяты у
`:hover`, чтобы состояние выглядело одинаково независимо от того, мышью его
навели или стрелкой.

- [ ] **Шаг 2: Написать поле с подсказкой**

`client/components/Picker.svelte`:

```svelte
<script>
  import Field from '$components/Field.svelte'
  import Icon from '$components/Icon.svelte'

  // Разделитель строки подсказки: `U+2022 BULLET`. Обычная точка не годится —
  // она читается как конец предложения и слипается с названием.
  const DOT = '•'

  // Совпадения приходят параметром, а за мостом ходит сборка: компонент,
  // у которого есть свой источник данных, перестаёт быть показом переданного.
  // Отсюда же и закрытый список жанров — он просто не передаёт `oncreate`.
  let { label, hits = [], chosen = [], ontype, onchosen, oncreate } = $props()

  let text = $state('')
  let marked = $state(-1)

  $effect(() => {
    const typed = text.trim()
    // Подсветки нет, пока её не поставили стрелкой: пока в списке ничего не
    // подсвечено, Enter заводит нового.
    marked = -1
    ontype(typed)
  })

  function keydown(event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      marked = Math.min(marked + 1, hits.length - 1)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      marked = Math.max(marked - 1, -1)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      marked >= 0 ? take(hits[marked]) : create()
    }
  }

  const take = (hit) => { add({ entity_id: hit.entity_id, name: hit.name }) }

  // Enter при неподсвеченном списке заводит нового — и человека, и студию.
  // Совпадение имени само по себе не решает ничего: полные тёзки существуют.
  // У закрытого списка (жанры) заводить нечего, и `oncreate` там не передан —
  // отсутствие обработчика и есть закрытость.
  function create() {
    const name = text.trim()
    if (!name || !oncreate) return
    oncreate({ entity_id: null, name })
    clear()
  }

  function add(one) {
    if (!one.name) return
    onchosen([...chosen, one])
    clear()
  }

  function clear() {
    text = ''
    marked = -1
  }

  const drop = (index) => onchosen(chosen.filter((_, at) => at !== index))
</script>

<div class="cardform__pick">
  <div class="picker">
    <Field bind:value={text} placeholder={label} />
    <svelte:element this="ul" class="picker__hits" hidden={!hits.length}>
      {#each hits as hit, index (hit.entity_id)}
        <li>
          <!-- На mousedown, а не на click: поле теряет фокус раньше, чем клик
               состоится, и список успевает закрыться. -->
          <button type="button" class="picker__hit" class:is-marked={index === marked}
                  onmousedown={() => take(hit)}>
            {hit.name}{#if hit.hint} {DOT} {hit.hint}{/if}
          </button>
        </li>
      {/each}
    </svelte:element>
  </div>

  <ul class="picker__chosen">
    {#each chosen as one, index (one.name + index)}
      <li class="picked">
        {one.name}
        <button type="button" class="picked__del" aria-label="Убрать"
                onclick={() => drop(index)}>
          <Icon name="close" />
        </button>
      </li>
    {/each}
  </ul>
</div>
```

**При наведении на строку всплывает постер — и только он.** Решено 31.07.2026.
Название показывать незачем: оно уже стоит в самой строке, после маркера.

Всплывает обычной картинкой рядом со строкой, `/poster?item=` от
`Suggestion.hint_item_id`. **Подсказка не ждёт диска синхронно:** она живёт и
пока постер едет, и если он не приехал вовсе, — то есть отсутствие картинки не
двигает и не гасит строку.

Дописать в `Picker.svelte`:

```svelte
  let hovered = $state(null)
</script>
```

и в строке списка:

```svelte
          <button type="button" class="picker__hit" class:is-marked={index === marked}
                  onmouseenter={() => { hovered = hit }}
                  onmouseleave={() => { hovered = null }}
                  onmousedown={() => take(hit)}>
            {hit.name}{#if hit.hint} {DOT} {hit.hint}{/if}
          </button>
          {#if hovered === hit && hit.hint_item_id}
            <img class="picker__poster" src={`/poster?item=${hit.hint_item_id}`} alt="">
          {/if}
```

плюс правило в `picker.css`. В макете такой всплывашки нет вовсе, поэтому
значения берутся у ближайшего родственника — списка совпадений
(`.picker__hits`): та же подложка, та же рамка, та же тень, та же пропорция
постера 2:3, что и везде.

```css
/* Всплывает сбоку от списка, а не над ним: список и так висит над содержимым,
   и вторая всплывашка поверх первой перекрыла бы соседние строки. */
.picker__poster {
  position: absolute;
  left: 100%;
  margin-left: 8px;
  width: 120px;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  z-index: 6;
  border: 1px solid var(--tint-09);
  border-radius: 10px;
  background: var(--surface-pop);
  box-shadow: 0 18px 40px var(--shade-55);
  pointer-events: none;
}
```

Ширина 120px названа здесь впервые — в макете её нет, потому что нет и самой
всплывашки. Взята от ширины списка совпадений: он равен ширине постера окна
(`--poster-w`, 230px), и половина этого рядом со строкой читается, не заслоняя
список.

- [ ] **Шаг 3: Встроить в окно**

Дописать в `CardModal.svelte` после `.cardform__top` — роли по типу содержимого:

```svelte
<script>
  // За мостом ходит сборка, а не поле: у компонента своего источника данных не
  // бывает. Роль здесь — ключ, потому что полей на экране до четырёх, и у
  // каждого свой список совпадений.
  let suggested = $state({})

  async function suggest(role, domain, text) {
    if (!text) { suggested = { ...suggested, [role]: [] }; return }
    const found = await call('refs.suggest', domain, text)
    suggested = { ...suggested, [role]: found }
  }

  const ROLES = [
    { role: 'director',   label: 'Режиссёр',    domain: 'people' },
    { role: 'showrunner', label: 'Шоураннер',   domain: 'people' },
    { role: 'developer',  label: 'Разработчик', domain: 'companies' },
    { role: 'publisher',  label: 'Издатель',    domain: 'companies' },
    { role: 'actor',      label: 'Актёры',      domain: 'people' },
  ]
</script>

    {#each ROLES as one (one.role)}
      {#if shown.has(one.role)}
        <Picker label={one.label} hits={suggested[one.role] ?? []}
                ontype={(text) => suggest(one.role, one.domain, text)}
                oncreate={(made) => setRole(one.role, [...roles[one.role], made])}
                chosen={roles[one.role]}
                onchosen={(list) => setRole(one.role, list)} />
      {/if}
    {/each}
```

Пять полей одним перебором, а не пятью почти одинаковыми блоками: различаются
они подписью, доменом и ключом роли — то есть данными, а не разметкой. `actors`
в наборе полей называется `actor` в ролях состава; таблица и держит это
соответствие в одном месте.

**Жанры выбираются тем же полем, и второго поведения у него от этого не
появляется.** `Picker` не знает, откуда берутся совпадения: он получает `hits`
и сообщает набранное через `ontype`. У людей и студий сборка отвечает на это
`refs.suggest`, у жанров — отбором из уже прочитанного `refs.genres`.

Заводить новое умеет тот, кому передали `oncreate`. Жанрам его не передают —
набор зашит в миграцию, своего жанра не бывает, — и Enter при неподсвеченном
списке там не делает ничего. Это не параметр «а теперь ты не поле», а отсутствие
обработчика: ровно тот довод, по которому план 8 отказался сводить `Stars` и
`ScoreRow`.

- [ ] **Шаг 4: Посмотреть**

- ввод имени показывает список с названием после маркера;
- стрелка вниз подсвечивает, Enter берёт подсвеченного;
- Enter без подсветки заводит нового — в списке появляются два одинаковых имени;
- выбор мышью срабатывает, а не теряется на потере фокуса;
- крестик убирает выбранного;
- у жанров Enter без подсветки не заводит ничего.

- [ ] **Шаг 5: Коммит**

```bash
git add client/styles/picker.css client/components/Picker.svelte client/app/
git commit -m "feat: поле с подсказкой и жест различения тёзок"
```

---

### Задача 3: Постер

Три способа вставки и обрезка на бэкенде.

**Обрезается по центру до 2:3, без вопросов.** Рамку кадрирования с
перетаскиванием и масштабированием не делаем: это отдельный виджет, а выигрывает
он в редком случае, когда картинка сильно не той формы.

**Обрезку делает бэкенд**, там же, где картинка и хранится: `PIL` в клиент не
пускает граница слоёв, а в потоке интерфейса ей делать нечего.

**Файлы:**
- Создать: `client/components/PosterPick.svelte`
- Изменить: `client/app/CardModal.svelte`

**Интерфейсы:**
- Потребляет: `call` из `$api/bridge.js`.
- Отдаёт: `PosterPick` с входными `item_id`, `onpicked`.

- [ ] **Шаг 1: Написать выбор постера**

`client/components/PosterPick.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'

  let { item_id = null, onpicked } = $props()

  // Что показывать: уже сохранённое или только что выбранное.
  let preview = $state(null)

  const shown = $derived(preview ?? (item_id ? `/poster?item=${item_id}` : null))

  async function take(file) {
    if (!file || !file.type.startsWith('image/')) return
    // Внутрь картинка идёт base64: аргументы уезжают postMessage-ом, и этот
    // канал бинарным тоже не бывает.
    const bytes = new Uint8Array(await file.arrayBuffer())
    let binary = ''
    for (const byte of bytes) binary += String.fromCharCode(byte)
    preview = URL.createObjectURL(file)
    onpicked(btoa(binary))
  }
</script>

<svelte:window onpaste={(event) => take(event.clipboardData?.files?.[0])} />

<label class="cardform__poster"
       ondragover={(event) => event.preventDefault()}
       ondrop={(event) => { event.preventDefault(); take(event.dataTransfer.files[0]) }}>
  {#if shown}
    <img src={shown} alt="">
  {:else}
    <Icon name="photo_camera" />
  {/if}
  <input type="file" accept="image/*" hidden
         onchange={(event) => take(event.currentTarget.files[0])}>
</label>
```

**Ctrl+V ловится на окне, а не на постере:** буфер вставляется туда, где фокус, а
фокуса у картинки не бывает. Пока открыто окно карточки, вставка изображения
означает обложку — других мест для картинки в нём нет.

- [ ] **Шаг 2: Встроить и отложить запись**

Постер записывается **после** карточки, а не вместе с ней: у новой карточки ещё
нет `item_id`, а хранилище обложек ключуется по нему. В `CardModal.svelte`
выбранное складывается в поле формы, а `covers.store_upload` зовёт сохранение —
задача 4.

- [ ] **Шаг 3: Посмотреть**

- щелчок по постеру открывает диалог файла;
- перетаскивание картинки в окно ставит её же;
- Ctrl+V из буфера — то же самое;
- не картинка не делает ничего;
- после сохранения обложка обрезана по центру до 2:3.

- [ ] **Шаг 4: Коммит**

```bash
git add client/components/PosterPick.svelte client/app/
git commit -m "feat: постер тремя способами вставки"
```

---

### Задача 4: Сохранение

Кнопка «Сохранить» сама решает, вставка это или обновление.

**Порядок записи принадлежит странице.** Сначала карточка, потом жанры, состав и
обложка: у первой записи появляется `item_id`, без которого остальным писать
некуда.

**Совпадение названия — предупреждение, а не запрет.** Проверяется по названию и
по оригинальному названию, внутри того же типа содержимого. Запрещать нельзя:
фильмов с одинаковыми названиями много. Молчать тоже нельзя: так плодятся дубли.

**Файлы:**
- Создать: `client/app/Confirm.svelte`
- Изменить: `client/app/CardModal.svelte`, `client/app/App.svelte`

**Интерфейсы:**
- Потребляет: `call` из `$api/bridge.js`; `Modal`, `Button`.
- Отдаёт: `Confirm` с входными `label`, `text`, `ok`, `onyes`, `onclose`.

- [ ] **Шаг 1: Написать подтверждение**

`client/app/Confirm.svelte` — одна оболочка на предупреждение о совпадении и на
подтверждение удаления: спрашивают они разное, а устроены одинаково.

```svelte
<script>
  import Button from '$components/Button.svelte'
  import Modal from '$components/Modal.svelte'

  let { label, text, ok = 'Продолжить', onyes, onclose } = $props()
</script>

<Modal narrow {label} {onclose}>
  {#snippet children()}
    <p>{text}</p>
    <div class="cardform__foot">
      <Button variant="btn--cancel" onclick={onclose}>
        {#snippet children()}Отмена{/snippet}
      </Button>
      <Button variant="btn--go" onclick={onyes}>
        {#snippet children()}{ok}{/snippet}
      </Button>
    </div>
  {/snippet}
</Modal>
```

**Вида этих двух окон в макете нет.** Пять наложений там — теги фильма, оценки,
жанры, теги и карточка; ни подтверждения удаления, ни предупреждения о совпадении
не нарисовано, хотя спека ручных карточек требует оба. Здесь они собраны из уже
готовых частей — узкая модалка и два подвальных кнопочных места, — и это
**заглушка до решения пользователя**, а не выбор оформления.

- [ ] **Шаг 2: Написать сохранение**

Дописать в `CardModal.svelte`:

```svelte
  async function save() {
    const same = await call('library.same_title', card.kind, card.title.trim())
    // Предупреждение, а не запрет; и не при правке самой себя.
    const others = same.filter((one) => one.id !== card.item_id)
    if (others.length && !confirmed) {
      warning = others[0]
      return
    }
    await write()
  }

  async function write() {
    const fields = {
      kind: card.kind, title: card.title.trim(),
      original_title: card.original_title.trim(),
      year: number(card.year), synopsis: card.synopsis.trim(),
      runtime: number(card.runtime),
      seasons_count: number(card.seasons_count),
      episodes_count: number(card.episodes_count),
    }

    // Порядок принадлежит странице: у новой карточки `item_id` появляется
    // только после первой записи, а жанрам и составу без него писать некуда.
    const id = card.item_id
      ? (await call('library.replace', card.item_id, fields), card.item_id)
      : await call('library.create', fields)

    await call('refs.set_genres', id, card.genres.map((one) => one.id))
    await writeCredits(id)
    if (picture) await call('covers.store_upload', id, picture)

    onsave(id)
  }

  const number = (value) => (value === '' || value === null ? null : Number(value))
```

**`refs.set_genres` и запись состава — новые операции моста.** План 5 их не
завёл намеренно: там не было сегодняшнего потребителя. Заводятся они здесь,
вместе с ним, в `bridge/refs.py`:

```python
    def set_genres(self, item_id: int, genre_ids: list) -> dict:
        """Жанры приходят снаружи, но у ручной карточки их ставит человек —
        выбором из зашитого набора, а не заведением своих."""
        return self._reply(
            lambda back: back.genres.set_for_item(item_id, genre_ids))

    def set_credits(self, domain: str, item_id: int, credits: list) -> dict:
        """Состав пишется целиком: у страницы он и правится целиком, а сличать
        построчно значило бы решать за неё, что именно человек поменял."""
        return self._reply(lambda back: _rewritten(back, domain, item_id, credits))


async def _rewritten(back, domain, item_id, credits):
    repository = _of(back, domain)
    await repository.detach_all(item_id)
    for position, one in enumerate(credits):
        entity_id = one["entity_id"] or await repository.create_manual(one["name"])
        await repository.attach(item_id, entity_id, one["role"], position)
```

и дописываются в сторож поверхности — он собирает имена разбором исходников, так
что править его не нужно, но прогнать обязательно.

- [ ] **Шаг 3: Открыть окно с карточки и из шапки**

В `App.svelte`: «+» открывает пустое, карандаш — заполненное.

```svelte
  let editing = $state(undefined)   // undefined — закрыто, null — новое

  <Topbar ... onadd={() => { editing = null }} />
  <Screen ... onedit={(view) => { editing = view }} />

  {#if editing !== undefined}
    <CardModal view={editing} kind={session.kind}
               onsave={() => { editing = undefined; /* перечитать карточку */ }}
               onclose={() => { editing = undefined }} />
  {/if}
```

- [ ] **Шаг 4: Посмотреть**

- «+» заводит карточку того типа, что в тумблере;
- обязательно только название; пустой год не мешает сохранить;
- карандаш открывает то же окно заполненным, «Сохранить» обновляет;
- название, уже занятое в этом типе, поднимает предупреждение, но не запрещает;
- то же название у другого типа не поднимает ничего;
- жанры, состав и обложка сохраняются и видны в ленте.

- [ ] **Шаг 5: Коммит**

```bash
git add bridge/refs.py client/app/
git commit -m "feat: сохранение карточки с предупреждением о совпадении"
```

---

### Задача 5: Привязка и отвязка

Ручная карточка связывается с внешней базой вставкой ссылки.

**Поиском — незачем.** Если поиск находит вещь, ручная карточка не появляется
вовсе: её заводят как раз тогда, когда поиск промахнулся, а страница найдена в
браузере.

**Разбор идёт на каждое нажатие клавиши и не ходит в сеть.** Галочка появляется,
когда адрес похож на разобранный, — она и есть единственный признак, что адрес
понят.

**Привязка не выполняется, если ссылка ведёт на карточку, которая уже есть.**
Говорим, что такое уже есть, и дубль завести не даём.

**Файлы:**
- Создать: `client/app/LinkField.svelte`
- Изменить: `client/app/CardModal.svelte`

**Интерфейсы:**
- Потребляет: `call`, `numbered` из `$api/bridge.js`; `Field`, `TagBox`.
- Отдаёт: `LinkField` с входными `item_id`, `kind`, `onlinked`, `ontrouble`.

- [ ] **Шаг 1: Написать поле ссылки**

`client/app/LinkField.svelte`:

```svelte
<script>
  import Field from '$components/Field.svelte'
  import Icon from '$components/Icon.svelte'
  import TagBox from '$components/TagBox.svelte'
  import { call, lastOp, numbered } from '$api/bridge.js'

  let { item_id, kind, onlinked, ontrouble } = $props()

  let raw = $state('')
  let parsed = $state(null)
  let overwrite = $state(false)

  // Разбор без сети и без диска: чистая функция на стороне питона. Вторую
  // регулярку на тот же адрес заводить нельзя — разойдутся молча.
  $effect(() => {
    if (!raw.trim()) { parsed = null; return }
    call('world.parse', raw.trim(), kind).then((link) => { parsed = link })
  })

  export async function link() {
    if (!parsed) return
    const outcome = await numbered('world.card_for_link', raw.trim(), kind,
                                   { channel: 'link' })
    if (outcome.outcome !== 'found') {
      ontrouble(outcome.outcome === 'missing'
        ? 'Источник не знает такой карточки'
        : 'Внешняя база недоступна')
      return
    }
    try {
      // Тем же номером, что и разбор: карточку мост помнит под ним, и с новым
      // номером сюда всегда приходило бы «устарело».
      await numbered('world.link', item_id, overwrite,
                     { channel: 'link', op: lastOp('link') })
      onlinked()
    } catch (error) {
      ontrouble(error.kind === 'item-exists'
        ? 'Такая карточка в библиотеке уже есть'
        : 'Не удалось привязать')
    }
  }
</script>

<div class="cardform__row">
  <Field bind:value={raw} placeholder="Ссылка на внешнюю базу" />

  {#if parsed}
    <span class="cardform__valid material-symbols-outlined" role="img"
          aria-label="Ссылка разобрана">check</span>
  {/if}

  <span class="cardform__check">
    <TagBox state={overwrite ? 'on' : 'off'}
            onclick={() => { overwrite = !overwrite }} />
  </span>
</div>
```

Подсказку «перезаписать данные» повесить на обёртку `title`: макет держит её на
самом переключателе.

- [ ] **Шаг 2: Отвязать**

Отвязка — источник снимается, карточка становится ручной, данные остаются: они
уже твои. Вход у неё в том же поле: когда карточка привязана, вместо ссылки
показывается имя источника и крестик.

```svelte
  async function unlink() {
    await call('library.unlink', item_id)
    onlinked()
  }
```

- [ ] **Шаг 3: Посмотреть**

- вставка `themoviedb.org/movie/157336` зажигает галочку;
- голый идентификатор принимается тоже;
- хвост `-interstellar` и `?…` не мешают;
- сохранение с разобранной ссылкой доливает пустое и не трогает написанное;
- галочка «перезаписать» берёт всё из источника;
- ссылка на карточку, которая уже в библиотеке, поднимает плашку и ничего не
  меняет;
- отвязка снимает источник, данные остаются.

- [ ] **Шаг 4: Коммит**

```bash
git add client/app/
git commit -m "feat: привязка карточки вставкой ссылки и отвязка"
```

---

### Задача 6: Удаление и «всё с этим человеком»

Два последних жеста ленты, у которых до сих пор были пустые обработчики.

**Удалить можно любую карточку**, не только ручную. Библиотека своя, «убери это
отсюда» одинаково законно для обеих.

**Оценка, теги и закладка уходят вместе с карточкой** — по подтверждению, в
котором перечислено, что именно пропадёт.

**Файлы:**
- Изменить: `client/app/App.svelte`, `client/app/LibraryScreen.svelte`,
  `SearchScreen.svelte`

**Интерфейсы:**
- Потребляет: `Confirm`; `call` из `$api/bridge.js`.
- Отдаёт: ничего нового.

- [ ] **Шаг 1: Написать удаление**

В `App.svelte`:

```svelte
  let removing = $state(null)

  async function askRemoval(view) {
    // Сводка приходит от базы: сколько тегов, есть ли оценка и закладка.
    const summary = await call('library.deletion_summary', view.item_id)
    removing = { view, summary }
  }

  async function remove() {
    // Порядок двух файлов базы знает бэкенд: обложка уходит первой.
    await call('library.delete', removing.view.item_id)
    removing = null
    // Перечитать раздел: карточки в нём больше нет.
  }
```

и разметка с перечислением из сводки:

```svelte
  {#if removing}
    <Confirm label="Удалить карточку" ok="Удалить"
             text={lost(removing.view, removing.summary)}
             onyes={remove} onclose={() => { removing = null }} />
  {/if}
```

где `lost` собирает фразу из непустых полей сводки — оценка, число тегов,
закладка. **Слова этой фразы в макете не нарисованы**, как и само окно: это тот
же открытый вопрос, что и в задаче 4.

- [ ] **Шаг 2: «Всё с этим человеком» делает не этот план**

Жест забрал план 11 (`docs/plans/2026-07-31-people-search.md`, задача 5), и
здесь его быть не должно. Три причины, каждая из которых сама по себе решает:

- **Место названо.** Решено 31.07.2026: щелчок по человеку — это обычная выдача
  поиска, раздел переключается на «Поиск», сначала своё и потом чужое. Прежняя
  запись «куда это показывается — вопрос к пользователю» устарела.
- **Внешняя половина обязательна.** Одной своей базой жест не отвечает: снаружи
  фильмография по идентичности, а без неё — поиск по имени.
- **Зовётся другое.** `Search.by_person(op, domain, entity_id, kind)` отдаёт обе
  половины уже собранными; `refs.items_of` под это не нужен и в план 5 не
  заводится вовсе.

Что остаётся этому плану: `Facts.svelte` обязан отдавать наверх **`entity_id`, а
не имя** — имя тёзку не различает, и по нему `by_person` звать нельзя. Правка в
плане 7, задача 2.

- [ ] **Шаг 3: Посмотреть**

- корзина спрашивает подтверждение и перечисляет, что пропадёт;
- отказ ничего не меняет;
- согласие убирает карточку из ленты и из базы; обложка уходит тоже;
- поиск той же вещи находит её заново во внешней базе.

- [ ] **Шаг 4: Коммит**

```bash
git add client/app/
git commit -m "feat: удаление карточки с подтверждением"
```

---

## Самопроверка плана

**Покрытие.** `manual-cards.md` — задачи 1, 3, 4, 5, 6 целиком: одно окно на
создание и правку, обязательно только название, предупреждение о совпадении,
постер тремя способами, привязка вставкой ссылки, отвязка, удаление с
перечислением. `people.md` — задача 2: Enter контекстный, маркер в строке
подсказки, склейка приехавших из источника по идентичности, а не по имени.

**Что этот план сознательно не делает.** Ничего: после него закрыты все спеки,
кроме поставки. Но три места ждут пользователя, и это не забывчивость — макет о
них молчит:

1. **Подтверждение удаления** — вида в макете нет ни одного из пяти наложений.
2. **Предупреждение о совпадении названия** — то же самое.
3. **Куда показывается «всё с этим человеком».** Жест и смысл в спеке есть,
   места нет.

Первое и второе собраны из готовых частей — узкая модалка и подвал с двумя
кнопками — как заглушка до решения; третье оставлено пустым обработчиком.

**Чем измеряется готовность.** `npm test` зелёный, 67 тестов. Карточку можно
завести, оценить, привязать и удалить **без интернета** — то есть выполнена
главная граница проекта: без сети нельзя найти готовое, всё остальное работает.
