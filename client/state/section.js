/* Запрос раздела: то, что уезжает мостом в `feed.page`. */

/* Строится только для двух разделов, которые спрашивают базу, — «Оценённых» и
 * «Хочу посмотреть». За поиск и статистику он падает, и падает намеренно: у них
 * нет ни своего порядка, ни страницы, а тихий запасной набор выдал бы им чужой
 * круг сортировки. */

import { chosen } from '$state/filters.js'
import { orderFor } from '$state/sorting.js'

export function requestOf(session) {
  return {
    section: session.section,
    kind: session.kind,
    filters: chosen(session.filters),
    // Что означает нетронутый переключатель и какой у раздела набор состояний —
    // знает `orderFor`, а не эта сборка.
    order: orderFor(session.section, session.sort),
  }
}
