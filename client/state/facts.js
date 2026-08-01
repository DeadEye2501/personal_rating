/* Строки фактов карточки: длительность, сезоны и серии, состав. */

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
 *  списке, и путаница ролью показала бы режиссёра в строке «В ролях».
 *
 *  Предел стоит по умолчанию, а не бесконечностью: у режиссёра и студий их
 *  всё равно единицы, а забытый довод у актёров вывалил бы в ленту весь
 *  состав. Отдаются титры целиком, а не имена: клик по имени зовёт поиск по
 *  номеру строки человека, и без него звать было бы нечего — имя тёзку не
 *  различает. */
export function castOf(credits, role, limit = TOP) {
  return credits
    .filter((credit) => credit.role === role)
    .toSorted((one, other) => (one.position ?? 0) - (other.position ?? 0))
    .slice(0, limit)
}

/** Русский счёт: 11–14 идут по правилу «много», а не по последней цифре.
 *  Открыт наружу со второго потребителя: тем же считает план 8 носителей тега
 *  («3 фильма имеют этот тег»), и второго такого правила быть не должно. */
export function plural(count, forms) {
  const tail = count % 100
  if (tail >= 11 && tail <= 14) return forms[2]
  const last = count % 10
  if (last === 1) return forms[0]
  if (last >= 2 && last <= 4) return forms[1]
  return forms[2]
}
