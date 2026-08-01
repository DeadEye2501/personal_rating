/* Свои отметки на карточке: оценка и закладка. */

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

/** Закладка ставится и снимается одним жестом: у карточки в списке дел кнопка
 *  горит, и она же её и гасит. Какой из двух путей звать, решает нынешнее
 *  состояние карточки. */
export async function wished(view) {
  // Два вызова литералами, а не один с выбором пути строкой: сторож границы
  // «страница → мост» читает путь прямо из вызова и составленного не видит —
  // опечатка в нём осталась бы зелёной на обоих наборах.
  await (view.in_wishlist
    ? call('marks.unwish', view.item_id)
    : call('marks.wish', view.item_id))
  return { in_wishlist: !view.in_wishlist }
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
