/* Форма карточки: из каких полей она состоит у каждого типа содержимого. */

// Общие для всех трёх типов.
const COMMON = ['title', 'original_title', 'year', 'synopsis']

// Своё у каждого типа: длительность у фильма, сезоны и серии у сериала, у игры
// ни того, ни другого — поля времени прохождения убраны из модели.
const OWN = {
  movie: ['runtime'],
  series: ['seasons_count', 'episodes_count'],
  game: [],
}

export const shownFor = (kind) => [...COMMON, ...OWN[kind]]

/* Ключи перечислены сами, а не выведены из `shownFor`: выведенные, они
   совпадали бы с ним всегда — а расхождение и есть то, что нужно ловить.
   Показанное поле без своего ключа Svelte не свяжет: `bind:value` на
   `undefined` молча ничего не делает, и набранное уходило бы в никуда. */
export const emptyCard = (kind) => ({
  kind,
  title: '',
  original_title: '',
  year: null,
  synopsis: '',
  runtime: null,
  seasons_count: null,
  episodes_count: null,
})
