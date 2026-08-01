/* Запись своей оценки: балл у кино и сериала, три шкалы у игры. */

import { call } from '$api/bridge.js'

const ASPECT_KEYS = ['visual', 'narrative', 'gameplay']

/** Отдаёт поля для строки, а не меняет её сам: у ленты строка ищется по номеру,
 *  у выдачи поиска — по паре «источник плюс идентификатор», и владеют этим
 *  разделы. Общего у них ровно то, что здесь: какой вызов и что после него
 *  показывать. */
export async function scored(view, value) {
  await call('marks.score', view.item_id, value)
  return { rating: { ...view.rating, score: value } }
}

/** Три шкалы уезжают вместе, потому что средний балл считает база: у игры
 *  оценка — среднее выставленных шкал, и вторым объявлением на странице оно
 *  разошлось бы с первым молча. */
export async function aspected(view, key, value) {
  const next = { ...blank(), ...view.rating, [key]: value }
  next.score = await call('marks.aspects', view.item_id,
                          ...ASPECT_KEYS.map((one) => next[one]))
  return { rating: next }
}

/** Свежезаведённая карточка приезжает без оценки вовсе, и первая же звезда по
 *  ней — обычный ход: пустые шкалы обязаны доехать пустыми, а не пропасть. */
const blank = () => Object.fromEntries(ASPECT_KEYS.map((one) => [one, null]))
