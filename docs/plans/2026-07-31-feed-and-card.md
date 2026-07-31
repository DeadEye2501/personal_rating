# План 7. Лента и карточка

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** приложение начинает работать по главному сценарию. Поиск находит и
своё, и чужое, найденное заводится в библиотеку, карточка показывает всё, что о
ней известно, оценка ставится звёздами, разделы «Оценённые» и «Хочу посмотреть»
отдают ленту с фильтрами и сортировкой. После этого плана остаются только модалки
и окно карточки.

**Архитектура:** карточка — самый крупный блок макета, около 400 строк стилей и
четырнадцать правил на одно свёрнутое состояние. Разбирается она на компоненты по
ответственности, а не по числу потребителей: постер, метки, факты, звёзды, оценки
агрегаторов, ряд действий. Всё, что можно посчитать без разметки — нотация оценок
и строки фактов, — уезжает в `state/` и проверяется Vitest.

**Лента держится браузером, а не библиотекой.** Карточка за краем экрана не
рисуется, место под неё остаётся по последней измеренной высоте — это
`content-visibility` с `contain-intrinsic-size`, средство самого движка.

**Стек:** тот же, что в плане 6. Ни одной новой зависимости.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от планов 5 и 6.** Мост отвечает на всё, обёртка `$api/bridge.js`
  нумерует и отменяет, состояние приложения считает фильтры и сортировку, шапка
  переключает тип и раздел.
- **Значения макета переносятся точь-в-точь**, и ничего оформительского не
  придумывается: нет значения в макете — это вопрос к пользователю.
- **`<style>` внутри компонента не бывает вовсе**, цвет — только в палитре,
  компонент получает всё входными параметрами и сам никуда не ходит.
- **Данные в макете — рыба, и на них не ссылаемся ни в чём.** Оттуда берутся
  только имена классов и значения стилей.
- **Состояние принадлежит данным, а не элементу.** Свёрнута карточка или
  развёрнута, какая оценка выставлена — свойство элемента ленты; компонент
  показывает то, что ему передали.
- **Компоненты не проверяются**, проверяется `state/`. Лента остаётся на
  запуске: её поломка видна глазами сразу.
- **Пустая выдача — не событие.** Плашка появляется, только когда база **не
  ответила**. Неприехавшая оценка агрегатора не сообщает ничего.
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ client/
│  ├─ styles/
│  │  ├─ feed.css                лента: полоса, отступы, промежутки
│  │  ├─ film.css                карточка: рама, сворачивание, постер, тело
│  │  ├─ chips.css               метки жанров и тегов
│  │  ├─ facts.css               строки фактов и имена
│  │  ├─ stars.css               ряд звёзд, дробная звезда, вердикт
│  │  ├─ aggr.css                оценки агрегаторов и кружок ожидания
│  │  └─ acts.css                ряд действий карточки
│  ├─ components/
│  │  ├─ Film.svelte             карточка целиком
│  │  ├─ Poster.svelte           обложка с заглушкой
│  │  ├─ Chips.svelte            жанры, теги и кнопка «± Тег»
│  │  ├─ Facts.svelte            длительность, сезоны, состав
│  │  ├─ Synopsis.svelte         обрезанный текст с раскрытием
│  │  ├─ Stars.svelte            ряд из десяти звёзд
│  │  ├─ Aggregates.svelte       оценки агрегаторов
│  │  ├─ Acts.svelte             правка, удаление, закладка
│  │  └─ Feed.svelte             список карточек с догрузкой
│  ├─ state/
│  │  ├─ scores.js               нотация оценок: ярлык, ступень, среднее, шкалы источников
│  │  └─ facts.js                строки фактов: длительность, сезоны, состав
│  └─ app/
│     ├─ section.js              запрос раздела из состояния
│     ├─ visible.js              что делать с карточкой в поле зрения
│     ├─ SearchScreen.svelte     поиск: своё, чужое, заведение
│     └─ LibraryScreen.svelte    оценённые и хочу посмотреть
└─ tests/web/
   ├─ scores.test.js
   └─ facts.test.js
```

Правятся и чужие файлы: `client/app/App.svelte` (запрос от шапки к разделу,
плашка снизу вверх), `client/main.js` (новые файлы оформления).

**`app/visible.js` и `app/section.js` лежат в сборке, а не в состоянии.** Первый
зовёт мост, второй собирает запрос из фильтров и сортировки — оба знают про
границу, а `state/` о ней не знает вовсе.

---

### Задача 1: Нотация оценок и строки фактов

Два модуля чистых функций и все проверки плана. Дальше в плане тестов не будет:
остальное — разметка, а она по решению не проверяется.

**Шкала одна на всё приложение.** Цвет закреплён за значением и одинаков везде —
в фильтре, на карточках, в статистике. Любая внешняя шкала приводится к
десятибалльной, чтобы цвет агрегатора брался из той же нотации, что и своя
оценка.

**Дробные оценки округляются вниз** — правило общее для всего показа: у игр
оценка это среднее трёх шкал, 7.33 показывается семёркой и красится седьмой
ступенью.

**Файлы:**
- Создать: `client/state/scores.js`, `client/state/facts.js`
- Создать: `tests/web/scores.test.js`, `tests/web/facts.test.js`

**Интерфейсы:**
- Потребляет: ничего.
- Отдаёт: `LABELS`, `stepOf(value, max)`, `stepOfSource(value, source)`,
  `nameOf(source)`, `colorOf(step)`, `verdictOf(score)`, `average(values)`,
  `partOf(score)`; `runtimeOf(minutes)`, `seriesOf(seasons, episodes)`,
  `castOf(credits, role, limit)`.

- [ ] **Шаг 1: Написать падающие тесты**

Создать `tests/web/scores.test.js`:

```js
import { describe, expect, it } from 'vitest'

import { LABELS, average, colorOf, nameOf, partOf, stepOf, stepOfSource,
  verdictOf } from '$state/scores.js'

describe('нотация оценок', () => {
  it('десять ступеней, и ни одна не повторяется', () => {
    const colours = Array.from({ length: 10 }, (_, index) => colorOf(index + 1))
    expect(new Set(colours).size).toBe(10)
  })

  it('приводит чужую шкалу к десяти', () => {
    // У агрегаторов шкалы разные: 0–10 у IMDb, 0–100 у Metacritic. Цвет обязан
    // браться из той же нотации, что и своя оценка.
    expect(stepOf(8.7, 10)).toBe(9)
    expect(stepOf(87, 100)).toBe(9)
  })

  it('знает шкалу каждого источника', () => {
    // Проверка не таблицы, а следствия: у GOG шкала 0–50, и `46` это девятая
    // ступень, а не десятая. С пятёркой десятой была бы каждая игра из GOG.
    expect(stepOfSource(46, 'gog')).toBe(stepOf(46, 50))
    expect(stepOfSource(87, 'metacritic')).toBe(stepOf(87, 100))
    // Незнакомый источник — десятибалльный: молчать тут нельзя, а гадать не о
    // чем, шкала 0–10 у трёх из семи.
    expect(stepOfSource(8.7, 'кто-то новый')).toBe(stepOf(8.7, 10))
  })

  it('зажимает выход за границы шкалы', () => {
    // Чужой ответ бывает и нулём, и больше максимума: ступень 0 или 11 дала бы
    // `var(--score-0)`, то есть отсутствие цвета и невидимую цифру.
    expect(stepOf(0, 10)).toBe(1)
    expect(stepOf(-3, 10)).toBe(1)
    expect(stepOf(140, 100)).toBe(10)
  })

  it('ярлык следует оценке', () => {
    expect(verdictOf(10)).toBe(LABELS[10])
    expect(verdictOf(1)).toBe(LABELS[1])
  })

  it('дробная оценка берёт ярлык по целой части', () => {
    // У игры оценка — среднее трёх шкал: 7.33 это «Интересно», а не пустота.
    expect(verdictOf(7.33)).toBe(LABELS[7])
  })

  it('снятая оценка не имеет ярлыка', () => {
    // Карточка остаётся, а вердикт исчезает: сказать о ней нечего.
    expect(verdictOf(null)).toBe('')
    expect(verdictOf(0)).toBe('')
  })

  it('среднее считается по выставленным шкалам, а не по трём всегда', () => {
    // Инвариант держит приложение: у игры может быть заполнена одна шкала из
    // трёх, и делить на три значило бы занизить втрое.
    expect(average([8, 7, 7])).toBeCloseTo(7.333, 3)
    expect(average([9, null, null])).toBe(9)
    expect(average([null, null, null])).toBe(null)
  })

  it('доля дробной звезды — остаток, а не сама оценка', () => {
    // Закрашенная часть лежит поверх контурной и обрезается по ширине: ошибка
    // здесь красит целую звезду вместо трети.
    expect(partOf(7.33)).toBeCloseTo(0.33, 2)
    expect(partOf(7)).toBe(0)
  })
})
```

Создать `tests/web/facts.test.js`:

```js
import { describe, expect, it } from 'vitest'

import { castOf, runtimeOf, seriesOf } from '$state/facts.js'

describe('строки фактов', () => {
  it('длительность показывается часами и минутами', () => {
    expect(runtimeOf(158)).toBe('2 ч 38 мин')
    expect(runtimeOf(47)).toBe('47 мин')
  })

  it('ровный час не тянет за собой нулевые минуты', () => {
    expect(runtimeOf(120)).toBe('2 ч')
  })

  it('неизвестной длительности нет вовсе', () => {
    // У кандидата поиска строка пустует, пока не приехал круг деталей.
    expect(runtimeOf(null)).toBe('')
  })

  it('сериал склоняет оба числительных', () => {
    // «2 сезона, 24 серии» — оба числа приходят одним ответом.
    expect(seriesOf(2, 24)).toBe('2 сезона, 24 серии')
    expect(seriesOf(1, 8)).toBe('1 сезон, 8 серий')
    expect(seriesOf(5, 101)).toBe('5 сезонов, 101 серия')
  })

  it('склонение не путается на подвохах русского счёта', () => {
    // 11–14 идут по правилу «много», а не по последней цифре.
    expect(seriesOf(11, 12)).toBe('11 сезонов, 12 серий')
    expect(seriesOf(21, 22)).toBe('21 сезон, 22 серии')
  })

  it('без числа серий показывает только сезоны', () => {
    expect(seriesOf(3, null)).toBe('3 сезона')
    expect(seriesOf(null, null)).toBe('')
  })

  it('состав берёт своих по роли, а не всех подряд', () => {
    // Роли лежат в одном списке, и путаница ролью показала бы режиссёра в
    // строке «В ролях».
    const credits = [
      { name: 'Дэвид Финчер', role: 'director', position: null },
      { name: 'Руни Мара', role: 'actor', position: 0 },
      { name: 'Дэниел Крейг', role: 'actor', position: 1 },
    ]

    expect(castOf(credits, 'director')).toEqual(['Дэвид Финчер'])
    expect(castOf(credits, 'actor')).toEqual(['Руни Мара', 'Дэниел Крейг'])
  })

  it('актёры идут по позиции в титрах, а не по тому, как легли в ответе', () => {
    // Топ-5 — это первые пять по `position`, и сортировка тут и есть смысл.
    const credits = [
      { name: 'Третий', role: 'actor', position: 2 },
      { name: 'Первый', role: 'actor', position: 0 },
      { name: 'Второй', role: 'actor', position: 1 },
    ]

    expect(castOf(credits, 'actor')).toEqual(['Первый', 'Второй', 'Третий'])
  })

  it('показывает только первых, а не весь состав', () => {
    // У сериала состав приезжает из aggregate_credits — у «Andor» это 302
    // человека, и вся лента превратилась бы в список имён.
    const many = Array.from({ length: 20 }, (_, index) =>
      ({ name: `Актёр ${index}`, role: 'actor', position: index }))

    expect(castOf(many, 'actor', 5)).toHaveLength(5)
  })
})
```

- [ ] **Шаг 2: Прогнать и увидеть красное**

```bash
cd client && npm test
```

Ожидание: FAIL, `Cannot find module '$state/scores.js'`.

- [ ] **Шаг 3: Написать нотацию**

Создать `client/state/scores.js`:

```js
/** Нотация оценок: ярлык словом, ступень шкалы, среднее трёх шкал. */

// Цвета лежат в палитре (--score-1…10), ярлыки — здесь. Значения из макета.
export const LABELS = {
  10: 'Шедевр', 9: 'Отлично', 8: 'Хорошо', 7: 'Интересно', 6: 'Неплохо',
  5: 'Средне', 4: 'Посредственно', 3: 'Уныло', 2: 'Плохо', 1: 'Отвратительно',
}

const STEPS = 10

/** Любая внешняя шкала приводится к десятибалльной: цвет агрегатора берётся из
 *  той же нотации, что и своя оценка. Зажим обязателен — чужой ответ бывает и
 *  нулём, и больше максимума, а `--score-0` это отсутствие цвета. */
export function stepOf(value, max) {
  return Math.min(STEPS, Math.max(1, Math.ceil((value / max) * STEPS)))
}

export const colorOf = (step) => `var(--score-${step})`

/** Шкала каждого источника — часть нотации, а не знание карточки: показывает
 *  цифру одно место, а красит её эта таблица.
 *
 *  У GOG шкала 0–50, а не 0–5: доля положительных отзывов кладётся в базу как
 *  есть (`reviewsRating` в ответе каталога), и в записанных ответах там 46, 39,
 *  41. С пятёркой каждая игра из GOG получала бы десятую ступень. */
const MAX = { imdb: 10, kinopoisk: 10, tmdb: 10, gog: 50,
              rotten: 100, metacritic: 100, steam: 100 }

const NAMES = { imdb: 'IMDb', kinopoisk: 'Кинопоиск', tmdb: 'TMDB',
                rotten: 'Rotten Tomatoes', metacritic: 'Metacritic',
                steam: 'Steam', gog: 'GOG' }

export const stepOfSource = (value, source) => stepOf(value, MAX[source] ?? 10)

export const nameOf = (source) => NAMES[source] ?? source

/** Дробные оценки округляются вниз — правило общее для всего показа. */
export function verdictOf(score) {
  return LABELS[Math.floor(score ?? 0)] ?? ''
}

/** Среднее по выставленным шкалам, а не по трём всегда: у игры может быть
 *  заполнена одна, и деление на три занизило бы втрое. */
export function average(values) {
  const given = values.filter((value) => value !== null && value !== undefined)
  if (!given.length) return null
  return given.reduce((sum, value) => sum + value, 0) / given.length
}

/** Остаток для дробной звезды: закрашенная часть лежит поверх контурной и
 *  обрезается по ширине. */
export const partOf = (score) => score - Math.floor(score)
```

- [ ] **Шаг 4: Написать строки фактов**

Создать `client/state/facts.js`:

```js
/** Строки фактов карточки: длительность, сезоны и серии, состав. */

// Сколько актёров показывает карточка. У сериала состав приезжает из
// aggregate_credits — у «Andor» это 302 человека.
const TOP = 5

const SEASON = ['сезон', 'сезона', 'сезонов']
const EPISODE = ['серия', 'серии', 'серий']

export function runtimeOf(minutes) {
  if (!minutes) return ''
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (!hours) return `${rest} мин`
  return rest ? `${hours} ч ${rest} мин` : `${hours} ч`
}

export function seriesOf(seasons, episodes) {
  const parts = []
  if (seasons) parts.push(`${seasons} ${plural(seasons, SEASON)}`)
  if (episodes) parts.push(`${episodes} ${plural(episodes, EPISODE)}`)
  return parts.join(', ')
}

/** Свои по роли, по позиции в титрах и только первые. Роли лежат в одном
 *  списке, и путаница ролью показала бы режиссёра в строке «В ролях». */
export function castOf(credits, role, limit = TOP) {
  return credits
    .filter((credit) => credit.role === role)
    .toSorted((one, other) => (one.position ?? 0) - (other.position ?? 0))
    .slice(0, limit)
    .map((credit) => credit.name)
}

/** Русский счёт: 11–14 идут по правилу «много», а не по последней цифре. */
function plural(count, forms) {
  const tail = count % 100
  if (tail >= 11 && tail <= 14) return forms[2]
  const last = count % 10
  if (last === 1) return forms[0]
  if (last >= 2 && last <= 4) return forms[1]
  return forms[2]
}
```

`castOf` берёт `TOP` по умолчанию, а не `Infinity`: у режиссёра и студий их
всё равно единицы, а забытый довод у актёров вывалил бы в ленту весь состав.

- [ ] **Шаг 5: Прогнать и увидеть зелёное**

```bash
cd client && npm test
```

Ожидание: PASS, 60 тестов — семнадцать новых и сорок три из плана 6.

- [ ] **Шаг 6: Коммит**

```bash
git add client/state/scores.js client/state/facts.js \
        tests/web/scores.test.js tests/web/facts.test.js
git commit -m "feat: нотация оценок и строки фактов карточки"
```

---

### Задача 2: Карточка

Самый крупный блок макета. Здесь она собирается целиком, кроме оценок и ряда
действий — они в задаче 3.

**Свёрнутая карточка — одна строка: название и оценка.** Четырнадцать правил
макета убирают постер, метки, факты, синопсис, агрегаторы и вердикт, а тело
разворачивают в ряд. Разворачивание мгновенное; анимируется только поворот
стрелки.

**Обложка едет своей ручкой, а не мостом.** `<img src="/poster?item=12">` —
браузер берёт её сам, кеширует по `ETag` и обрывает запрос, когда карточка ушла
из разметки. Заглушка появляется по `onerror`.

**Файлы:**
- Создать: `client/styles/feed.css`, `film.css`, `chips.css`, `facts.css`
- Создать: `client/components/Film.svelte`, `Poster.svelte`, `Chips.svelte`,
  `Facts.svelte`, `Synopsis.svelte`
- Изменить: `client/main.js`, `client/app/LibraryScreen.svelte`

**Интерфейсы:**
- Потребляет: `runtimeOf`, `seriesOf`, `castOf` из `$state/facts.js`.
- Отдаёт: `Film` с входными `view`, `collapsed`, `on`, `oncollapse`,
  `onmark`, `onperson`, `ontag`; место под оценки и действия из задачи 3.

- [ ] **Шаг 1: Перенести оформление ленты и рамы**

Создать `client/styles/feed.css`:

```css
/* Те же границы, что у гистограммы и у содержимого шапки. */
.feed {
  width: 100%;
  max-width: var(--content-w, 1146px);
  margin: 0 auto;
  padding: 18px 0 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
```

Создать `client/styles/film.css` — перенос `docs/design/index.html:340-446`
точь-в-точь, плюс два правила, которых в макете нет и которых там быть не могло:

```css
.film {
  /* Колонка под угловые иконки: шеврон сверху, закладка снизу. */
  --gutter: 52px;
  --icon-inset: 14px;

  position: relative;
  display: flex;
  gap: 20px;
  padding: 18px var(--gutter) 18px 18px;
  border: 1px solid var(--tint-07);
  border-radius: 14px;
  background: var(--tint-035);

  /* Карточка за краем экрана не рисуется, а место под неё держится по
     последней измеренной высоте. Запасное число выведено из макета: постер
     158 × 1.5 плюс отступы 18 сверху и снизу. Оно нужно ровно до первого
     показа, дальше браузер помнит настоящее. */
  content-visibility: auto;
  contain-intrinsic-size: auto 273px;
}

.film__toggle {
  position: absolute;
  top: 10px;
  right: var(--icon-inset);
  display: block;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: var(--r-full);
  background: transparent;
  color: var(--tint-30);
  cursor: pointer;
  transition: background .16s, color .16s;
}
.film__toggle .material-symbols-outlined {
  display: block;
  width: 28px;
  font-size: 22px;
  line-height: 28px;
  text-align: center;
  transition: transform .22s cubic-bezier(.2,.8,.2,1);
}
.film__toggle:hover { color: var(--text-bright) }

.film.is-collapsed .film__toggle .material-symbols-outlined {
  transform: rotate(180deg);
}

/* Свёрнутая карточка — одна строка: название и оценка. */
.film.is-collapsed .film__acts,
.film.is-collapsed .film__poster,
.film.is-collapsed .film__chips,
.film.is-collapsed .film__facts,
.film.is-collapsed .film__synopsis,
.film.is-collapsed .film__aggr,
.film.is-collapsed .film__verdict { display: none }

.film.is-collapsed { padding: 12px var(--gutter) 12px 18px }

.film.is-collapsed .film__body {
  flex-direction: row;
  align-items: center;
  gap: 16px;
}
.film.is-collapsed .film__title { font: var(--body-l) }
.film.is-collapsed .film__scores { margin-left: auto }

.film__poster {
  flex: 0 0 auto;
  /* Без этого флекс растянул бы постер на всю высоту карточки и соотношение
     сторон не сработало бы. */
  align-self: flex-start;
  width: 158px;             /* 158 × 1.5 = 237 — высота текстовой колонки */
  aspect-ratio: 2 / 3;      /* пропорция афиши */
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: linear-gradient(160deg, var(--tint-09), var(--tint-02));
  color: var(--tint-16);
  overflow: hidden;
}
.film__poster .material-symbols-outlined { font-size: 38px }

/* Картинка ложится поверх подложки-заглушки. В макете этих двух правил нет,
   потому что там нет ни одного <img>: постеры нарисованы пустыми блоками. */
.film__poster img { width: 100%; height: 100%; object-fit: cover }

.film__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  /* Остаток высоты раскладывается по промежуткам, поэтому последняя строка
     встаёт вровень с нижним краем постера. */
  justify-content: space-between;
  gap: 6px;
}

.film__title {
  margin: 0;
  font: var(--title-l);
  font-weight: 600;
  letter-spacing: -.2px;
  color: var(--text-bright);
}

.film__synopsis {
  margin: 0;
  font: var(--body-m);
  line-height: 1.55;
  color: var(--tint-55);
}

/* Раскрывает обрезанный текст. Появляется только когда содержимое не
   поместилось. */
.more {
  margin-left: 5px;
  padding: 0;
  border: none;
  background: transparent;
  font: inherit;
  color: var(--tint-40);
  cursor: pointer;
  transition: color .16s ease;
}
.more:hover { color: var(--primary) }
```

- [ ] **Шаг 2: Перенести метки и факты**

Создать `client/styles/chips.css` — перенос `index.html:449-504`:

```css
.film__chips {
  display: flex;
  flex-wrap: wrap;
  /* Оправа вылезает на 10px в каждую сторону, ещё 4 — воздух между соседними
     пилюлями. */
  gap: 8px 24px;
  /* Сдвиг вправо на вылет оправы: иначе она торчит за левый край колонки, где
     все остальные строки начинаются вровень. */
  margin: 2px 0 0 7px;
}

/* Внешняя база отдаёт жанры строчными — поднимаем первую букву стилями, чтобы
   не зависеть от источника. */
.chip::first-letter { text-transform: uppercase }

.chip {
  position: relative;
  font: var(--label-m);
  color: var(--tint-55);
  cursor: pointer;
}

/* Свои теги отличаются от жанров из внешней базы. */
.chip--tag { color: var(--text-bright) }

/* Оправа рисуется псевдоэлементом с отрицательными отступами: она выходит за
   границы слова, не занимая места, поэтому соседи при наведении не
   разъезжаются. */
.chip::before {
  content: '';
  position: absolute;
  inset: -3px -10px;
  border: 1px solid var(--tint-09);
  border-radius: var(--r-full);
  background: transparent;
  pointer-events: none;
  transition: border-color .18s ease, background .18s ease;
}
/* Наведение — белым, включённый фильтр — акцентом. Разводит их цвет, а не
   форма: акцент означает «этот жанр сейчас выбран», а белый — «сюда можно
   нажать». В макете у метки было только наведение, и оно было акцентным;
   акцент уехал состоянию, наведению остался белый. */
.chip:hover { color: var(--text-bright) }
.chip:hover::before {
  border-color: var(--tint-55);
  background: var(--tint-06);
}

/* Метки кликабельны, поэтому они кнопки, а не надписи: своей подложки и рамки
   у кнопки быть не должно — оправу рисует ::before. */
.chip,
.chip--add {
  padding: 0;
  border: none;
  background: transparent;
  font: var(--label-m);
}

/* Видна всегда и приглушённой: спрятанная кнопка — ловушка, про которую надо
   догадаться. */
.chip--add {
  color: var(--tint-30);
  transition: color .18s ease;
}

/* Метка, по которой включён фильтр. Акцентная — те самые значения, что в макете
   стояли у наведения. */
.chip.is-on { color: var(--primary) }
.chip.is-on::before {
  border-color: color-mix(in srgb, var(--primary) 55%, transparent);
  background: color-mix(in srgb, var(--primary) 10%, transparent);
}
```

**Акцент и белый поменялись местами по сравнению с макетом**, и это решение
пользователя от 31.07.2026: акцентная метка теперь означает включённый фильтр, а
наведение подсвечивает белым. В макете включённого состояния у метки не было
вовсе — там был только акцентный `:hover`.

Значения белого наведения названы здесь впервые: `var(--tint-55)` у
оправы — то же, что у единственного белого наведения в макете
(`.tagbox[data-state="off"]:hover`), и `var(--tint-06)` у подложки —
вдвое слабее акцентной, чтобы белая заливка не читалась ярче цветной.

Создать `client/styles/facts.css` — перенос `index.html:508-541`:

```css
.film__facts {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 12px;
  font: var(--body-m);
}
.film__facts dt {
  color: var(--tint-35);
  white-space: nowrap;
}
.film__facts dd {
  margin: 0;
  color: var(--tint-85);
}

/* Подпись роли внутри строки — выглядит как заголовок в левой колонке. */
.film__role {
  margin: 0 8px 0 20px;
  color: var(--tint-35);
}

/* Каждое имя — отдельная цель: по нему можно найти остальное с его участием. */
.person {
  padding: 0;
  border: none;
  background: transparent;
  font: inherit;
  color: inherit;
  cursor: pointer;
  transition: color .16s ease;
}
.person:hover { color: var(--primary) }
```

- [ ] **Шаг 3: Написать части карточки**

`client/components/Poster.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'

  let { item_id = null, source = '', poster_url = '' } = $props()

  // У кандидата номера нет — он ещё не в базе, и обложку тогда не сохраняют.
  // Ручка одна, различаются только доводы.
  const address = $derived(item_id
    ? `/poster?item=${item_id}`
    : poster_url && `/poster?source=${source}&url=${encodeURIComponent(poster_url)}`)

  let broken = $state(false)
</script>

<div class="film__poster">
  {#if address && !broken}
    <!-- Загрузку обрывает сам браузер, когда карточка уходит из разметки: своей
         отмены тут не нужно ни строки. -->
    <img src={address} alt="" loading="lazy" onerror={() => { broken = true }}>
  {:else}
    <Icon name="theaters" />
  {/if}
</div>
```

`client/components/Chips.svelte`:

```svelte
<script>
  let { genres = [], tags = [], on = { genres: [], tags: [] }, onmark, ontag }
    = $props()
</script>

<div class="film__chips">
  <!-- Клик по метке включает фильтр по ней, повторный выключает. Не поиск:
       «найти во внешней базе все боевики» — не тот вопрос, который задают, а
       фильтр по своей библиотеке отвечает мгновенно и работает без сети. -->
  {#each genres as genre (genre.id)}
    <button type="button" class="chip" class:is-on={on.genres.includes(genre.id)}
            aria-pressed={on.genres.includes(genre.id)}
            onclick={() => onmark('genres', genre.id)}>{genre.name}</button>
  {/each}
  {#each tags as tag (tag.id)}
    <button type="button" class="chip chip--tag" class:is-on={on.tags.includes(tag.id)}
            aria-pressed={on.tags.includes(tag.id)}
            onclick={() => onmark('tags', tag.id)}>{tag.name}</button>
  {/each}
  <!-- Кнопка всегда последняя и всегда видна. -->
  <button type="button" class="chip chip--add" onclick={ontag}>± Тег</button>
</div>
```

**У метки на карточке два состояния, а не три:** включён и не активен. Исключить
с карточки нечем — третье состояние живёт только в модалке фильтра.

**Переключение делает сборка, а не компонент.** `onmark` уходит наверх, там
меняется `session.filters`, и оттуда же обратно приезжает `on`: компонент только
показывает переданное и сам в общее состояние не лезет.

В макете жанры и теги — `<span>`, а не кнопки: обработчика у них там не было
вовсе. Здесь они кликабельны, и элемент обязан быть кнопкой — иначе жест
недоступен ни с клавиатуры, ни озвучке экрана. Оформление от этого не меняется:
`.chip` уже задаёт шрифт, цвет и курсор, а сброс рамки с подложкой, который есть
у `.chip--add`, придётся распространить на `.chip` целиком.

`client/components/Facts.svelte`:

```svelte
<script>
  import { castOf, runtimeOf, seriesOf } from '$state/facts.js'

  let { view, onperson } = $props()

  // Кто сделал — раньше, чем кто играл: у фильма режиссёр, у сериала
  // шоураннер, у игры разработчик и издатель.
  const ROWS = [
    { label: 'Режиссёр', from: 'people', role: 'director' },
    { label: 'Шоураннер', from: 'people', role: 'showrunner' },
    { label: 'Разработчик', from: 'companies', role: 'developer' },
    { label: 'Издатель', from: 'companies', role: 'publisher' },
    { label: 'В ролях', from: 'people', role: 'actor' },
  ]

  const length = $derived(view.kind === 'series'
    ? seriesOf(view.seasons_count, view.episodes_count)
    : runtimeOf(view.runtime))

  const rows = $derived(ROWS
    .map((row) => ({ ...row, names: castOf(view[row.from], row.role) }))
    .filter((row) => row.names.length))
</script>

<dl class="film__facts">
  {#if length}
    <dt>{view.kind === 'series' ? 'Сезоны' : 'Длительность'}</dt>
    <dd>{length}</dd>
  {/if}

  {#each rows as row (row.label)}
    <dt>{row.label}</dt>
    <dd>
      {#each row.names as name, index (name)}
        {#if index}, {/if}
        <button type="button" class="person" onclick={() => onperson(row.from, name)}
        >{name}</button>
      {/each}
    </dd>
  {/each}
</dl>
```

`client/components/Synopsis.svelte`:

```svelte
<script>
  import { onMount } from 'svelte'

  // Сколько строк показывать до раскрытия. Значение из макета.
  const LINES = 3

  let { text = '' } = $props()

  let full = $state(false)
  let paragraph = $state()
  let cut = $state(false)

  // Кнопка появляется, только когда есть что раскрывать: обрезанный текст
  // отличается от целого высотой прокрутки. Замер идёт после отрисовки —
  // до неё обе высоты нулевые.
  onMount(() => {
    cut = paragraph.scrollHeight > paragraph.clientHeight
  })
</script>

{#if text}
  <p class="film__synopsis" class:is-cut={!full} bind:this={paragraph}>
    {text}{#if cut && !full}<button type="button" class="more"
      onclick={() => { full = true }}>ещё</button>{/if}
  </p>
{/if}
```

и правило обрезки — в `client/styles/film.css`, потому что стиль блока живёт
своим файлом, а не в компоненте:

```css
.film__synopsis.is-cut {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
```

- [ ] **Шаг 4: Собрать карточку**

`client/components/Film.svelte`:

```svelte
<script>
  import Chips from '$components/Chips.svelte'
  import Facts from '$components/Facts.svelte'
  import Icon from '$components/Icon.svelte'
  import Poster from '$components/Poster.svelte'
  import Synopsis from '$components/Synopsis.svelte'

  let { view, collapsed = false, on, oncollapse, onmark, onperson, ontag }
    = $props()
</script>

<article class="film" class:is-collapsed={collapsed}>
  <button type="button" class="film__toggle" aria-expanded={!collapsed}
          aria-label={collapsed ? 'Развернуть' : 'Свернуть'}
          onclick={() => oncollapse(view)}>
    <Icon name="expand_less" />
  </button>

  <Poster item_id={view.item_id} source={view.source} poster_url={view.poster_url} />

  <div class="film__body">
    <h2 class="film__title">{view.title}{#if view.year} ({view.year}){/if}</h2>

    <Chips genres={view.genres} tags={view.tags} {on} {onmark}
           ontag={() => ontag(view)} />
    <Facts {view} onperson={(domain, name) => onperson(domain, name, view)} />
    <Synopsis text={view.synopsis} />
  </div>
</article>
```

Оценки, агрегаторы и ряд действий встанут сюда в задаче 3.

- [ ] **Шаг 5: Подключить оформление и показать одну карточку**

Дописать в `client/main.js`:

```js
import '$styles/feed.css'
import '$styles/film.css'
import '$styles/chips.css'
import '$styles/facts.css'
```

Чтобы карточку было на чём посмотреть до того, как появится раздел, — черновик
в `client/app/LibraryScreen.svelte`:

```svelte
<script>
  import Film from '$components/Film.svelte'
  import { numbered } from '$api/bridge.js'

  let views = $state([])

  $effect(() => {
    numbered('feed.page', { section: 'rated', kind: 'movie', filters: {},
                            order: { key: 'score', descending: true } }, 0, 50,
             { channel: 'feed' })
      .then((page) => { views = page })
  })
</script>

<div class="feed">
  {#each views as view (view.source + ' ' + view.source_id)}
    <Film {view} onperson={() => {}} ontag={() => {}} oncollapse={() => {}} />
  {/each}
</div>
```

Черновик заменяется настоящим разделом в задаче 6 и до тех пор не трогается.

- [ ] **Шаг 6: Собрать и сверить с макетом**

```bash
cd client && npm run build
cd .. && pipenv run python main.py
```

**База должна быть непустой.** Поиск появится только в задаче 5, поэтому карточку
заводят одним вызовом моста из инспектора (`PR_DEBUG=1`):

```js
await window.pywebview.api.world.parse('themoviedb.org/movie/157336', null)
```

и дальше `world.card_for_link` с `world.link` — либо берут базу, наполненную
раньше.

Сверить с макетом рядом: постер 2:3 слева, название крупно, метки в оправе с
поднятой первой буквой, факты в две колонки, синопсис в три строки с кнопкой
«ещё». Шеврон в правом верхнем углу, при сворачивании поворачивается и оставляет
одну строку.

- [ ] **Шаг 7: Коммит**

```bash
git add client/styles/ client/components/ client/app/ client/main.js
git commit -m "feat: карточка ленты — постер, метки, факты, синопсис"
```

---

### Задача 3: Оценки, агрегаторы и действия

Правая половина карточки: своя оценка звёздами, оценки агрегаторов с кружками
ожидания и ряд действий, всплывающий под курсором.

**У игры три шкалы, у кино одна.** Свёрнутой игре три строки не нужны: они
сводятся в одну усреднённую с дробной звездой.

**Кружок на месте неприехавшей оценки, а не пустота.** Сколько их рисовать,
известно до ответа сети: `world.expected(op, kind)` — чистая операция без диска
и сети.

**Три состояния оценки агрегатора различаются на экране так же, как в базе.**
Строки нет — крутится кружок; строка с пустым значением — на месте оценки просто
ничего, без следа и без сообщения; строка со значением — цифра.

**Файлы:**
- Создать: `client/styles/stars.css`, `aggr.css`, `acts.css`
- Создать: `client/components/Stars.svelte`, `Aggregates.svelte`, `Acts.svelte`
- Изменить: `client/components/Film.svelte`, `client/main.js`

**Интерфейсы:**
- Потребляет: `average`, `colorOf`, `partOf`, `stepOf`, `verdictOf` из
  `$state/scores.js`.
- Отдаёт: `Film` дополняется входными `expected`, `onscore`, `onaspect`,
  `onedit`, `ondelete`, `onwish`.

- [ ] **Шаг 1: Перенести оформление оценок**

Создать `client/styles/stars.css` — перенос `index.html:398-402, 612-670`:

```css
/* Порядок в строке: звёзды, ярлык, оценки агрегаторов. */
.film__scores {
  position: relative;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 0;
}

/* Подпись стороны оценки у игр. Ширина общая, чтобы звёзды в трёх строках
   стояли по одной вертикали. */
.film__aspect {
  flex: 0 0 auto;
  width: 86px;
  font: var(--body-m);
  color: var(--tint-35);
}

.stars { display: flex; gap: 2px }

.stars button,
.stars > span {
  display: grid;
  place-items: center;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--tint-16);
}
.stars button { cursor: pointer }

/* Дробная часть: поверх контурной звезды лежит закрашенная, обрезанная по
   ширине. */
.stars .star--part { position: relative }
.stars .star--part i {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--fill);
  overflow: hidden;
  color: var(--score);
}
.stars .star--part i .material-symbols-outlined {
  font-variation-settings: 'FILL' 1;
}
.stars .material-symbols-outlined {
  font-size: 21px;
  font-variation-settings: 'FILL' 0;
  transition: color .12s, font-variation-settings .12s;
}
.stars .is-on { color: var(--score) }
.stars .is-on .material-symbols-outlined { font-variation-settings: 'FILL' 1 }

.film__verdict {
  margin-left: 8px;
  font: var(--title-s);
  color: var(--score);
}

/* У игры три шкалы сворачиваются в одну усреднённую. Селектор двойной: иначе
   общее правило .film__scores перебьёт скрытие. */
.film__scores.film__scores--avg { display: none }
.film.is-collapsed .film__scores--avg { display: flex }
.film.is-collapsed .film__scores--aspect { display: none }
```

Создать `client/styles/aggr.css` — перенос `index.html:568-607`:

```css
/* Значения красятся по той же шкале, что и свои оценки: 0–10 и 0–100
   приводятся к десятибалльной. */
.film__aggr {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font: var(--body-m);
}
.film__aggr span { color: var(--tint-35) }

/* Название источника ведёт на страницу карточки у него. */
.aggr {
  color: inherit;
  text-decoration: none;
  cursor: pointer;
  transition: color .16s ease;
}
.aggr:hover { color: var(--primary) }
.film__aggr b {
  margin-left: 5px;
  font-weight: 600;
  color: var(--score);
}

/* Оценка ещё едет. Имя источника остаётся на месте, число заменено кольцом —
   так строка не прыгает, когда цифра приедет. */
.aggr-wait {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-left: 6px;
  vertical-align: -1px;
  border: 2px solid var(--tint-16);
  border-top-color: var(--tint-55);
  border-radius: 50%;
  animation: aggr-spin .8s linear infinite;
}

@keyframes aggr-spin {
  to { transform: rotate(360deg) }
}
```

Создать `client/styles/acts.css` — перенос `index.html:676-723`:

```css
/* Ряд вынесен из потока: он выше строки со звёздами и иначе растягивал бы её,
   разводя строки оценки на разное расстояние. Закладка встаёт в ту же колонку,
   что и шеврон, а правка с удалением уходят левее, внутрь карточки. */
.film__acts {
  position: absolute;
  top: 50%;
  right: calc(var(--icon-inset) - var(--gutter));
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 2px;
}

.film__wish,
.film__act {
  display: block;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: var(--r-full);
  background: transparent;
  color: var(--tint-30);
  cursor: pointer;
  transition: color .16s, opacity .16s;
}
.film__wish .material-symbols-outlined,
.film__act  .material-symbols-outlined {
  display: block;
  width: 28px;
  font-size: 20px;
  line-height: 28px;
  text-align: center;
}
.film__wish:hover,
.film__act:hover { color: var(--primary) }
.film__wish.is-on { color: var(--primary) }

/* Удаление — единственное необратимое действие на карточке. */
.film__act[data-act="delete"]:hover { color: var(--error) }

/* Правка и удаление показываются только под курсором: в покое карточка
   остаётся чистой. */
.film__act {
  opacity: 0;
  pointer-events: none;
}
.film:hover .film__act {
  opacity: 1;
  pointer-events: auto;
}
```

- [ ] **Шаг 2: Написать звёзды**

`client/components/Stars.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'
  import { colorOf, partOf } from '$state/scores.js'

  // Кликабельный ряд — своя оценка; неподвижный с дробной звездой —
  // усреднённая у свёрнутой игры. Двух компонентов тут не нужно: отличие в
  // одном свойстве, а строение и оформление общие.
  let { score = null, onpick = null } = $props()

  const TEN = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

  const whole = $derived(Math.floor(score ?? 0))
  const part = $derived(score ? partOf(score) : 0)
  const colour = $derived(colorOf(Math.max(1, whole)))
</script>

<div class="stars">
  {#each TEN as step (step)}
    {#if onpick}
      <!-- Повторное нажатие по той же звезде снимает оценку: карточка при этом
           остаётся. -->
      <button type="button" class:is-on={step <= whole} style:--score={colour}
              aria-label={`Оценка ${step}`}
              onclick={() => onpick(step === score ? null : step)}>
        <Icon name="star" />
      </button>
    {:else if step <= whole}
      <span class="is-on" style:--score={colour}><Icon name="star" /></span>
    {:else if step === whole + 1 && part > 0}
      <span class="star--part" style:--score={colour}
            style:--fill={`${Math.round(part * 100)}%`}>
        <Icon name="star" /><i><Icon name="star" /></i>
      </span>
    {:else}
      <span><Icon name="star" /></span>
    {/if}
  {/each}
</div>
```

- [ ] **Шаг 3: Написать оценки агрегаторов**

`client/components/Aggregates.svelte`:

```svelte
<script>
  import { colorOf, nameOf, stepOfSource } from '$state/scores.js'

  let { external = [], expected = [] } = $props()

  const arrived = $derived(new Map(external.map((one) => [one.source, one])))

  // Приехавшее и ожидаемое идут одной строкой: имя источника стоит на месте с
  // самого начала, и строка не прыгает, когда цифра приедет.
  const shown = $derived(expected.map((source) => ({
    source,
    value: arrived.get(source)?.value ?? null,
    asked: arrived.has(source),
  })))
</script>

<div class="film__aggr">
  {#each shown as one (one.source)}
    <span>
      <a class="aggr">{nameOf(one.source)}</a>
      {#if one.value !== null}
        <b style:--score={colorOf(stepOfSource(one.value, one.source))}
        >{one.value}</b>
      {:else if !one.asked}
        <i class="aggr-wait" aria-hidden="true"></i>
      {/if}
    </span>
  {/each}
</div>
```

**Ссылка на страницу источника пока никуда не ведёт.** Собирается она из
`view.external_ids`, и делает это окно карточки в плане 9 — там же, где эти
идентификаторы правят. Заводить адрес здесь значило бы собирать его дважды.

- [ ] **Шаг 4: Написать ряд действий**

`client/components/Acts.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'

  let { wished = false, onedit, ondelete, onwish } = $props()
</script>

<div class="film__acts">
  <button type="button" class="film__act" data-act="edit" aria-label="Править"
          onclick={onedit}>
    <Icon name="edit" />
  </button>
  <button type="button" class="film__act" data-act="delete" aria-label="Удалить"
          onclick={ondelete}>
    <Icon name="delete" />
  </button>
  <button type="button" class="film__wish" class:is-on={wished}
          aria-pressed={wished} aria-label="Хочу посмотреть" onclick={onwish}>
    <Icon name="bookmark" />
  </button>
</div>
```

- [ ] **Шаг 5: Встроить в карточку**

Дописать в `client/components/Film.svelte`:

```svelte
<script>
  import Acts from '$components/Acts.svelte'
  import Aggregates from '$components/Aggregates.svelte'
  import Stars from '$components/Stars.svelte'
  import { average, colorOf, verdictOf } from '$state/scores.js'

  let { view, collapsed = false, expected = [], oncollapse, onperson, ontag,
        onscore, onaspect, onedit, ondelete, onwish } = $props()

  const ASPECTS = [
    { key: 'visual', label: 'Визуал' },
    { key: 'narrative', label: 'Нарратив' },
    { key: 'gameplay', label: 'Геймплей' },
  ]

  const rating = $derived(view.rating)
  const mean = $derived(view.kind === 'game'
    ? average(ASPECTS.map((one) => rating?.[one.key] ?? null))
    : rating?.score ?? null)
  const tone = $derived(colorOf(Math.max(1, Math.floor(mean ?? 1))))
</script>
```

и разметка после `Synopsis`:

```svelte
    <Aggregates external={view.external} {expected} />

    {#if view.kind === 'game'}
      {#each ASPECTS as aspect (aspect.key)}
        <div class="film__scores film__scores--aspect">
          <span class="film__aspect">{aspect.label}</span>
          <Stars score={rating?.[aspect.key] ?? null}
                 onpick={(value) => onaspect(view, aspect.key, value)} />
        </div>
      {/each}
      <div class="film__scores film__scores--avg">
        <Stars score={mean} />
        <span class="film__verdict" style:--score={tone}>{verdictOf(mean)}</span>
      </div>
    {:else}
      <div class="film__scores">
        <Stars score={mean} onpick={(value) => onscore(view, value)} />
        <span class="film__verdict" style:--score={tone}>{verdictOf(mean)}</span>
      </div>
    {/if}
  </div>

  <Acts wished={view.in_wishlist} onedit={() => onedit(view)}
        ondelete={() => ondelete(view)} onwish={() => onwish(view)} />
</article>
```

- [ ] **Шаг 6: Подключить оформление и посмотреть**

Дописать в `client/main.js`:

```js
import '$styles/stars.css'
import '$styles/aggr.css'
import '$styles/acts.css'
```

```bash
cd client && npm run build
cd .. && pipenv run python main.py
```

Сверить: десять звёзд, закрашенные до выставленной оценки и того же цвета; ярлык
словом справа; у игры три подписанные строки, у кино одна; в свёрнутом виде у
игры одна усреднённая строка с дробной звездой; правка и удаление появляются под
курсором, удаление краснеет; закладка горит закрашенной иконкой.

- [ ] **Шаг 7: Коммит**

```bash
git add client/styles/ client/components/ client/main.js
git commit -m "feat: оценки звёздами, агрегаторы и ряд действий карточки"
```

---

### Задача 4: Лента

Список карточек, который растёт порциями и не знает своей полной длины.

**Полосу прокрутки держит загруженное, а не предсказанное.** Прыжка в середину
библиотеки нет.

**Высоту непоказанной карточки предсказывать не нужно никогда.** Известны только
реально измеренные — это `content-visibility` из задачи 2, и своего кода тут не
нужно ни строки.

**Свёрнутость на загрузку не влияет.** Карточка грузится целиком независимо от
того, свёрнута она или нет: цена страницы считается по числу видимых карточек, а
не по тому, что из них сейчас показано.

**Файлы:**
- Создать: `client/components/Feed.svelte`, `client/app/visible.js`

**Интерфейсы:**
- Потребляет: `Film`; `numbered` из `$api/bridge.js`.
- Отдаёт: `Feed` с входными `views`, `collapsed`, `expected`, `onmore`,
  `onshown` и всеми обработчиками карточки; `onCardShown(view, ops)`.

- [ ] **Шаг 1: Написать ленту**

`client/components/Feed.svelte`:

```svelte
<script>
  import Film from '$components/Film.svelte'

  // Насколько заранее просить следующую порцию. Экран с запасом: догрузка
  // обязана начаться до того, как человек упрётся в дно.
  const AHEAD = 600

  let { views = [], collapsed = false, expected = [], onmore, onshown,
        ...card } = $props()

  let box = $state()
  let asking = $state(false)
  const told = new Set()

  // Просим ещё, только когда близко дно, и не просим повторно, пока предыдущая
  // порция не приехала.
  function scrolled() {
    if (asking || !box) return
    if (box.scrollHeight - box.scrollTop - box.clientHeight > AHEAD) return
    asking = true
    Promise.resolve(onmore()).finally(() => { asking = false })
  }

  // О показе карточки сообщаем один раз: прокрутка вверх-вниз иначе гоняла бы
  // круги загрузки по кругу, тратя квоты агрегаторов.
  function shown(view) {
    const key = `${view.source} ${view.source_id}`
    if (told.has(key)) return
    told.add(key)
    onshown(view)
  }
</script>

<div class="feed" bind:this={box} onscroll={scrolled}>
  {#each views as view (view.source + ' ' + view.source_id)}
    <div onintroend={() => shown(view)}>
      <Film {view} {collapsed} {expected} {...card} />
    </div>
  {/each}
</div>
```

**Ключ `{#each}` — пара «источник + идентификатор», а не номер строки.** По
номеру Svelte переиспользовал бы элемент под другую карточку, и постер уехал бы к
чужим данным. Пул карточек в вебе не заводится — эта пара и есть то, что вместо
него держит соответствие.

**Что считать «попала в поле зрения», решает исполнитель** и записывает довод в
код: у `content-visibility` есть событие `contentvisibilityautostatechange`,
которое срабатывает ровно на смене «рисуется / не рисуется», а есть
`IntersectionObserver`, который работает независимо от него. Первое короче и не
заводит наблюдателя на каждую карточку, второе понятнее и не зависит от свойства
оформления. Оба годятся; `onintroend` выше — заглушка, которую надо заменить
одним из двух.

- [ ] **Шаг 2: Написать три круга по требованию**

Создать `client/app/visible.js`:

```js
/** Что делать с карточкой, попавшей в поле зрения.

Обложку берёт сам браузер — она едет ручкой, а не мостом. Здесь остаются два
обращения, и оба только для того, что уже в базе: у кандидата поиска нет
`imdb_id`, и спросить агрегаторов о нём нечем. */

import { numbered } from '$api/bridge.js'

// Через сколько дней карточка считается просроченной. Число из правила
// перезапроса по сроку: обновляются только сезоны, серии и оценки.
const FRESH_DAYS = 30
const DAY = 24 * 60 * 60 * 1000

export async function onCardShown(view, ops) {
  if (!view.item_id) return

  // Номера ложатся в `ops`: карточка ушла за край экрана, человек ушёл с
  // раздела — начатое ею гасится, и квота агрегаторов не тратится на ответ,
  // которого никто не ждёт.
  if (stale(view)) await quietly('world.refresh_series', view.item_id, { ops })
  await quietly('world.enrich', view.item_id, view.kind, { ops })
}

/** Просрочку считает и бэкенд — `SeriesRefresh` тихо ничего не делает в трёх
 *  случаях. Второй раз она считается здесь не по забывчивости: вызов, который в
 *  подавляющем большинстве случаев не сделает ничего, стоит потока на стороне
 *  питона и пересечения границы на каждой карточке прокрутки. */
function stale(view) {
  if (view.kind !== 'series' || view.source !== 'tmdb') return false
  if (!view.synced_at) return false
  return Date.now() - Date.parse(view.synced_at) > FRESH_DAYS * DAY
}

async function quietly(path, ...args) {
  // Отказ агрегатора ничему не мешает и ничего не сообщает: на месте оценки
  // просто ничего, без следа и без плашки. Но и молча не глотаем: в лог.
  try {
    await numbered(path, ...args)
  } catch (error) {
    if (!error.silent) console.warn(path, error)
  }
}
```

- [ ] **Шаг 3: Посмотреть**

```bash
cd client && npm run build
cd .. && pipenv run python main.py
```

Сверить: лента прокручивается плавно; при подходе к дну приезжает следующая
порция; карточки за краем экрана не рисуются — видно в инспекторе по
`content-visibility`; тумблер «Свернуть всё» сворачивает все разом; прокрутка
вверх и обратно не повторяет запросов.

- [ ] **Шаг 4: Коммит**

```bash
git add client/components/Feed.svelte client/app/visible.js
git commit -m "feat: лента порциями и три круга по требованию видимой карточки"
```

---

### Задача 5: Поиск

Раздел, на котором приложение открывается. Своё показывается сразу, внешнее
доливается по готовности, найденное заводится в библиотеку одним нажатием.

**Сначала своя половина целиком, потом чужая.** Внутри половин порядок не
трогается: своя приходит упорядоченной по названию, у чужой его задаёт источник —
у него есть данные о популярности и совпадении с запросом, которых у нас нет.
Складывает это `merge_results` на мосту, и правило одно на всю выдачу поиска.

**Вкладка — первичный фильтр.** Тип содержимого уезжает доводом в каждый запрос,
и во вкладке фильмов сериалов не бывает нигде — ни в своей половине, ни в чужой.

**Отказ внешней базы — плашка, пустая выдача — нет.** Разница осмысленная: без
внешней базы человек не получит того, что искал, и должен понимать причину.

**Файлы:**
- Изменить: `client/app/SearchScreen.svelte`, `client/app/App.svelte`

**Интерфейсы:**
- Потребляет: `numbered`, `cancel` из `$api/bridge.js`; `Feed`; `onCardShown`.
- Отдаёт: `SearchScreen` с входными `session`, `query`, `ontrouble`.

- [ ] **Шаг 1: Написать раздел**

`client/app/SearchScreen.svelte`:

```svelte
<script>
  import Feed from '$components/Feed.svelte'
  import { cancel, lastOp, numbered } from '$api/bridge.js'
  import { passes } from '$state/filters.js'
  import { onCardShown } from './visible.js'

  let { session, query = '', ontrouble } = $props()

  let views = $state([])
  let expected = $state([])
  const ops = []

  // Фильтры работают и в поиске. Спросить источник с фильтром нечем — у TMDB и
  // магазинов нет ни наших тегов, ни наших оценок, — поэтому ответ приходит
  // целиком, а отсев идёт здесь, тем же правилом, что и в ленте.
  const shown = $derived(views.filter((view) => passes(view, session.filters)))

  // Страница владеет тем, что запустила, и отменяет это при уходе.
  $effect(() => () => { cancel(ops.splice(0)) })

  $effect(() => {
    numbered('world.expected', session.kind, { channel: 'expected', ops })
      .then((sources) => { expected = sources })
      .catch(lost)
  })

  $effect(() => {
    if (!query) { views = []; return }
    look(query, session.kind).catch(lost)
  })

  // Ни один вызов моста не остаётся без обработчика: невыполненное обещание в
  // JS не даёт ни плашки, ни записи — то есть ровно то молчание, которое
  // правило отказов запрещает.
  const lost = (error) => {
    if (!error.silent) ontrouble('Не удалось выполнить операцию')
  }

  async function look(text, kind) {
    // Своё показывается сразу: локальная база отвечает за миллисекунды.
    views = await numbered('search.local', kind, text, { channel: 'search', ops })

    // Внешнее доливается по готовности и складывается со своим на стороне
    // моста: `merge_results` живёт в модели ровно потому, что складывать
    // приходится клиенту, и второго его объявления быть не должно.
    //
    // Тем же номером, что и первый шаг: мостовая память узнаёт выдачу по нему,
    // и с новым номером сюда всегда приходило бы «устарело».
    try {
      const outer = await numbered('search.external',
                                   { channel: 'search', op: lastOp('search') })
      views = outer.views
      // Отказ источника — поле в ответе, а не исключение. Пустая выдача при
      // этом молчит: пустая лента и есть ответ.
      if (outer.refusals.length) ontrouble('Внешняя база недоступна')
    } catch (error) {
      if (!error.silent) ontrouble('Внешняя база недоступна')
    }
  }

  async function add(view) {
    // Тот же номер: кандидата мост берёт из выдачи, которую помнит под ним.
    const outcome = await numbered('search.ensure', view.source, view.source_id,
                                   { channel: 'search', op: lastOp('search') })
    if (outcome.outcome === 'refusal') {
      ontrouble('Внешняя база недоступна')
      return
    }
    if (outcome.outcome === 'missing') {
      ontrouble('Источник больше не знает такой карточки')
      return
    }
    // Карточка записана целиком: перечитываем её одну, чтобы в ленте появились
    // жанры, состав и длительность, которых у кандидата не было.
    const [fresh] = await numbered('feed.views_of', [outcome.value],
                                   { channel: 'views', ops })
    views = views.map((each) => each === view ? fresh : each)
  }
</script>

<Feed views={shown} collapsed={session.collapsed} {expected}
      onmore={() => {}}
      onshown={(view) => onCardShown(view, ops)}
      onscore={add} onaspect={add} oncollapse={() => {}}
      onedit={() => {}} ondelete={() => {}} onwish={() => {}}
      onperson={() => {}} ontag={() => {}} />
```

**Порции в поиске не догружаются**, и `onmore` пуст намеренно: у TMDB одна
страница выдачи это ровно 20 кандидатов и один запрос, у игр два магазина по 20.
Вторая страница в спеке не описана, и придумывать её здесь нечего.

**Оценка кандидата сначала заводит карточку.** У кандидата нет `item_id`, и
`marks.score` звать не с чем; поэтому и `onscore`, и `onaspect` ведут в `add`.
Оценка вторым действием появится тогда же, когда появится окно карточки, — план
9.

- [ ] **Шаг 2: Провести запрос от шапки к разделу**

В `client/app/App.svelte` строка поиска отдаёт запрос вниз, а плашка поднимается
вверх:

```svelte
  let query = $state('')

  <Topbar ... onsearch={(text) => { query = text }} />

  <Screen {session} {query} ontrouble={(text) => { trouble = text }} />
```

- [ ] **Шаг 3: Посмотреть**

Проверить живьём:

- ввод и Enter — своё появляется сразу, внешнее доливается;
- выключить сеть — выдача остаётся локальной, снизу выезжает плашка;
- запрос, на который ничего не нашлось, — пустая лента и **никакой плашки**;
- набрать новый запрос, пока летит старый, — старые результаты не затирают
  новые;
- нажать по кандидату — карточка заводится и достраивается на месте: появляются
  жанры, состав и длительность.

- [ ] **Шаг 4: Коммит**

```bash
git add client/app/
git commit -m "feat: поиск — своё сразу, внешнее по готовности, заведение найденного"
```

---

### Задача 6: Оценённые и Хочу посмотреть

Два раздела на одной ленте, отличающиеся только тем, что спрашивают у бэкенда.

**Фильтры и сортировка действуют здесь, а в поиске нет.** Фильтр по своему тегу
оставил бы только то, что уже в библиотеке, то есть выключил бы внешний поиск.

**Порция — 50.** Лента читается с диска и стоит дёшево.

**Файлы:**
- Создать: `client/app/section.js`
- Изменить: `client/app/LibraryScreen.svelte`

**Интерфейсы:**
- Потребляет: `chosen` из `$state/filters.js`; `orderFor` из
  `$state/sorting.js`.
- Отдаёт: `requestOf(session)` — то, что уезжает в `feed.page` и
  `feed.histogram`.

- [ ] **Шаг 1: Собрать запрос из состояния**

Создать `client/app/section.js`:

```js
/** Запрос раздела: то, что уезжает мостом в `feed.page` и `feed.histogram`. */

import { chosen } from '$state/filters.js'
import { orderFor } from '$state/sorting.js'

export function requestOf(session) {
  return {
    section: session.section,
    kind: session.kind,
    filters: chosen(session.filters),
    // Что означает нетронутый переключатель и где он не действует вовсе —
    // знает `orderFor`, а не эта сборка.
    order: orderFor(session.section, session.sort),
  }
}
```

- [ ] **Шаг 2: Написать раздел**

`client/app/LibraryScreen.svelte` — **один экран на оба раздела библиотеки.**
Различает их `session.section`, и он же уезжает в запрос через `requestOf`;
второй файл был бы дословной копией, которую планы 8 и 9 правили бы дважды, а
машинная проверка дублей `.svelte` не разбирает вовсе:

```svelte
<script>
  import Feed from '$components/Feed.svelte'
  import { call, cancel, numbered } from '$api/bridge.js'
  import { requestOf } from './section.js'
  import { onCardShown } from './visible.js'

  // Порция ленты. Число из спеки: читается с диска и стоит дёшево.
  const PAGE = 50

  let { session, ontrouble } = $props()

  let views = $state([])
  let expected = $state([])
  const ops = []

  $effect(() => () => { cancel(ops.splice(0)) })

  $effect(() => {
    numbered('world.expected', session.kind, { channel: 'expected', ops })
      .then((sources) => { expected = sources })
      .catch((error) => {
        if (!error.silent) ontrouble('Не удалось прочитать библиотеку')
      })
  })

  // Смена фильтра, сортировки или типа содержимого перезапрашивает раздел с
  // начала: догружать поверх старого набора нечего.
  $effect(() => {
    numbered('feed.page', requestOf(session), 0, PAGE, { channel: 'feed', ops })
      .then((page) => { views = page })
      .catch((error) => {
        if (!error.silent) ontrouble('Не удалось прочитать библиотеку')
      })
  })

  async function more() {
    const next = await numbered('feed.page', requestOf(session), views.length,
                                PAGE, { channel: 'feed', ops })
    views = [...views, ...next]
  }

  // Записи идут без номера: отменять запись нельзя. Отказ у них показывается
  // плашкой, а не гасится — человек должен знать, что оценка не сохранилась.
  async function score(view, value) {
    await call('marks.score', view.item_id, value)
    patch(view, { rating: { ...view.rating, score: value } })
  }

  async function aspect(view, key, value) {
    const next = { ...view.rating, [key]: value }
    // Ответ — выведенный балл: у игр оценка это среднее выставленных шкал, и
    // считает его база.
    next.score = await call('marks.aspects', view.item_id, next.visual,
                            next.narrative, next.gameplay)
    patch(view, { rating: next })
  }

  async function wish(view) {
    await call(view.in_wishlist ? 'marks.unwish' : 'marks.wish', view.item_id)
    patch(view, { in_wishlist: !view.in_wishlist })
  }

  // Свёрнутость принадлежит элементу ленты, а не виджету.
  const collapse = (view) => patch(view, { collapsed: !view.collapsed })

  const patch = (view, fields) => {
    views = views.map((each) => each === view ? { ...each, ...fields } : each)
  }
</script>

<Feed {views} collapsed={session.collapsed} {expected} onmore={more}
      onshown={(view) => onCardShown(view, ops)}
      onscore={score} onaspect={aspect} onwish={wish} oncollapse={collapse}
      onedit={() => {}} ondelete={() => {}} onperson={() => {}}
      ontag={() => {}} />
```

**Свёрнутость приходит с двух сторон, и это не путаница.** Тумблер шапки —
состояние всего приложения, `session.collapsed`; шеврон карточки — свойство её
самой, `view.collapsed`. Компонент карточки получает одно значение, и в задаче 3
это `collapsed` из ленты; сведение двух в одно — работа этого шага, и делается
оно там, где оба видны: `collapsed={view.collapsed ?? session.collapsed}` в
`Feed.svelte`.

- [ ] **Шаг 3: Посмотреть**

- открыть «Оценённые» — лента приезжает, прокрутка догружает по 50;
- сменить сортировку — раздел перезапрашивается с начала;
- сменить тип содержимого — фильтры слетают, лента другая;
- поставить оценку — звёзды красятся сразу, ярлык меняется;
- снять оценку повторным нажатием — карточка остаётся;
- у игры выставить одну шкалу — усреднённая в свёрнутом виде следует ей;
- закладка переносит карточку в «Хочу посмотреть»;
- «Свернуть всё» сворачивает ленту, шеврон одной карточки разворачивает её
  обратно, не трогая остальные.

- [ ] **Шаг 4: Коммит**

```bash
git add client/app/
git commit -m "feat: разделы «Оценённые» и «Хочу посмотреть» на общей ленте"
```

---

## Самопроверка плана

**Покрытие.** Спека разделов — задачи 5 и 6: первые три раздела одна лента,
фильтры в поиске не действуют, порядок по умолчанию у отложенного свой.
`search-and-loading.md` — задачи 4 и 5: своё сразу, внешнее по готовности, порции
20 и 50, свёрнутость на загрузку не влияет, кандидат ещё не карточка. Спека
клиента, «Лента» — задачи 2 и 4. `errors.md` — задача 5: плашка только когда база
не ответила.

**Что этот план сознательно не делает.** Модалок нет: кнопка «± Тег», правка,
удаление и «показать всё с этим человеком» получают пустые обработчики — их
наполняют планы 8 и 9. Гистограммы нет. Ссылка на страницу источника у оценок
агрегаторов не собирается: адрес строится из `external_ids`, и делает это окно
карточки в плане 9. Вторая страница выдачи поиска не догружается: в спеке её нет.

**Одно место оставлено исполнителю с двумя годными вариантами** — чем считать
«карточка попала в поле зрения»: событием `content-visibility` или
`IntersectionObserver`. Оба удовлетворяют требованию; выбор записывается доводом
в код.

**Чем измеряется готовность.** `npm test` зелёный, 57 тестов. Найденное в
интернете заводится в библиотеку, оценивается звёздами и остаётся в разделах
после перезапуска.
