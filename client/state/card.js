/* Форма карточки: из каких полей она состоит у каждого типа содержимого. */

import { ROLES } from '$state/credits.js'

// Общие для всех типов. Обложки тут нет намеренно: поля формы — это поля
// карточки, а обложка лежит вторым файлом базы и записывается отдельно.
const COMMON = ['title', 'original_title', 'year', 'synopsis', 'genres']

// Своё у каждого типа: длительность у фильма, сезоны и серии у сериала, у игры
// ни того, ни другого — поля времени прохождения убраны из модели. Актёров у
// игры нет тоже: состав ей заменяют разработчик с издателем.
//
// У книги и альбома нет ни длительности, ни сезонов: своих полей им не
// заводилось вовсе, решение 22.08.2026. Состав у них в одну строку — автор и
// исполнитель; треки альбома придут своим списком, а не ролью человека.
const OWN = {
  movie: ['runtime', 'director', 'actor'],
  series: ['seasons_count', 'episodes_count', 'showrunner', 'actor'],
  game: ['developer', 'publisher'],
  book: ['author'],
  music: ['performer'],
}

export const shownFor = (kind) => [...COMMON, ...OWN[kind]]

/* Ключи перечислены сами, а не выведены из `shownFor`: выведенные, они
   совпадали бы с ним всегда — а расхождение и есть то, что нужно ловить.
   Показанное поле без своего ключа Svelte не свяжет: `bind:value` на
   `undefined` молча ничего не делает, и набранное уходило бы в никуда.

   Выбранное лежит по роли, а не двумя списками людей и студий: поле знает
   ровно свою роль, а раскладывать по домену нужно один раз — при записи. */
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
  director: [],
  showrunner: [],
  actor: [],
  developer: [],
  publisher: [],
  author: [],
  performer: [],
})

// Поля, которые база держит числами. Форма всегда отдаёт строку — поле ввода
// другого не умеет.
const NUMBERS = ['year', 'runtime', 'seasons_count', 'episodes_count']

/** Незаполненное поле — это «не знаю», а не «пусто»: мост отбрасывает `null` и
 *  оставляет полю умолчание, а пустую строку доносит до базы как есть. */
const said = (value) => {
  const clean = String(value ?? '').trim()
  return clean === '' ? null : clean
}

/** Поля формы в поля карточки. Состава и жанров тут нет: они пишутся своими
 *  вызовами и после самой карточки — уехав сюда, они стали бы лишними доводами
 *  сборщика и уронили бы запись. */
export function fieldsOf(form) {
  const number = (name) => {
    const clean = said(form[name])
    return clean === null ? null : Number(clean)
  }

  return {
    kind: form.kind,
    title: said(form.title),
    original_title: said(form.original_title),
    synopsis: said(form.synopsis),
    ...Object.fromEntries(NUMBERS.map((name) => [name, number(name)])),
  }
}

/** Числовые поля, в которых написано не число. Молча они превращаются в `NaN`,
 *  уезжают пустотой и просто пропадают — человек узнаёт об этом, когда откроет
 *  карточку снова. */
export const wrongNumbers = (form) => NUMBERS.filter((name) => {
  const clean = said(form[name])
  return clean !== null && !Number.isFinite(Number(clean))
})

/** Карточка, открытую на правку, в форму. Номер едет с ней: он и отличает
 *  правку от заведения, а состав раскладывается по ролям — поле показывает
 *  ровно свою.
 *
 *  Пара «номер и имя» у выбранного одна на людей, студии и жанры: поле с
 *  подсказкой не знает, кого показывает, а запись по номеру узнаёт, что этот
 *  уже есть. Потеряй форма номер — на каждом сохранении заводился бы тёзка. */
export function formOf(view) {
  const picked = (list, role) => list
    .filter((one) => one.role === role)
    .map((one) => ({ id: one.entity_id, name: one.name }))

  return {
    ...emptyCard(view.kind),
    item_id: view.item_id,
    title: view.title,
    original_title: view.original_title,
    year: view.year,
    synopsis: view.synopsis,
    runtime: view.runtime,
    seasons_count: view.seasons_count,
    episodes_count: view.episodes_count,
    genres: view.genres.map((one) => ({ id: one.id, name: one.name })),
    ...Object.fromEntries(ROLES.map(({ role, domain }) =>
      [role, picked(view[domain] ?? [], role)])),
  }
}
