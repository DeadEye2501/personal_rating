/* Выбранное в приложении вместе с переходами между выборами. */

import { EMPTY, cleared, forgotten, marked } from '$state/filters.js'
import { nextSort } from '$state/sorting.js'

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

/** Повторный щелчок по разделу возвращает простой список: раздел — это подмена
 *  содержимого, а не переключатель с залипанием, и отдельной кнопки «обратно»
 *  под него нет. */
export const withToggledSection = (session, section) =>
  withSection(session, section === session.section ? 'search' : section)

/** Следующее состояние переключателя. Круг у раздела свой, и позиция считается
 *  по нему; нетронутый переключатель двигается с первого состояния. */
export const withNextSort = (session) =>
  ({ ...session, sort: nextSort(session.section, session.sort) })

/** Клик по метке на карточке включает фильтр по ней, повторный выключает.
 *  Переход живёт здесь, а не в разметке: остальные пять его собратьев тоже
 *  здесь, и проверяются они тестами, а разметка — ничем. */
export const withMark = (session, field, id) =>
  ({ ...session, filters: marked(session.filters, field, id) })

/** Повторное нажатие по горящей кнопке фильтра гасит **свой** признак. */
export const withClearedFilter = (session, field) =>
  ({ ...session, filters: cleared(session.filters, field) })

/** Перебор строки в списке уже сложил новые наборы — сеанс их принимает. */
export const withFilters = (session, filters) => ({ ...session, filters })

/** Тег удалили из набора — сеанс обязан его забыть. */
export const withForgotten = (session, field, id) =>
  ({ ...session, filters: forgotten(session.filters, field, id) })

/** Тумблер всего приложения, а не настройка раздела. */
export const withCollapsed = (session, collapsed) => ({ ...session, collapsed })

/** Свёрнута ли карточка. Свёрнутость приходит с двух сторон: тумблер шапки —
 *  состояние всего приложения, шеврон карточки — свойство её самой. Своё
 *  сильнее общего, и правило это одно на обе стороны — лента им рисует,
 *  раздел им переключает. */
export const collapsedOf = (view, collapsed) => view.collapsed ?? collapsed
