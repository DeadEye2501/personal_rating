/* Выбранное в приложении вместе с переходами между выборами. */

import { EMPTY } from '$state/filters.js'

/** При запуске карточек нет: приложение открывается на поиске. */
export const newSession = () => ({
  kind: 'movie',
  section: 'search',
  filters: EMPTY,
  // `null` значит «переключатель не тронут», и тогда действует порядок по
  // умолчанию раздела. Нулём это не записать: ноль — законное состояние.
  sort: null,
  collapsed: false,
})

/** Смена типа сбрасывает все фильтры: наборы тегов у трёх типов независимы, а
 *  жанров наборов два, и фильтр после переключения указывал бы в пустоту. */
export function withKind(session, kind) {
  if (kind === session.kind) return session
  return { ...session, kind, filters: EMPTY }
}

/** Разделы фильтры не трогают: иначе отфильтрованную гистограмму не увидеть
 *  никогда. А вот сортировка живёт ровно сеанс раздела. */
export function withSection(session, section) {
  if (section === session.section) return session
  return { ...session, section, sort: null }
}

/** Тумблер всего приложения, а не настройка раздела. */
export const withCollapsed = (session, collapsed) => ({ ...session, collapsed })
