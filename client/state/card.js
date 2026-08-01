/* Форма карточки: из каких полей она состоит у каждого типа содержимого. */

// Общие для всех трёх типов. Обложки тут нет намеренно: поля формы — это поля
// карточки, а обложка лежит вторым файлом базы и записывается отдельно.
const COMMON = ['title', 'original_title', 'year', 'synopsis', 'genres']

// Своё у каждого типа: длительность у фильма, сезоны и серии у сериала, у игры
// ни того, ни другого — поля времени прохождения убраны из модели. Актёров у
// игры нет тоже: состав ей заменяют разработчик с издателем.
const OWN = {
  movie: ['runtime', 'director', 'actor'],
  series: ['seasons_count', 'episodes_count', 'showrunner', 'actor'],
  game: ['developer', 'publisher'],
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
})
