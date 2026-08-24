/* Три состояния строки фильтра: не выбран, включён, исключён. */

import { ASPECTS, stepOfScore } from '$state/scores.js'

// Признаки, у которых значение у карточки одно: «семь и восемь разом» не бывает
// ни у чего, поэтому внутри такого признака выбранное складывается по «или».
// Шкалы берутся теми же ключами, что и на карточке, а не переписываются
// списком: разъехавшись, они дали бы отбор по колонке, которой в базе нет.
const SINGLE = ['scores', ...ASPECTS.map((one) => one.key)]

// Имена полей — контракт с мостом: он раскладывает их прямо в `Filters`.
const FIELDS = ['tags', 'genres', ...SINGLE]

// Признаки за одной кнопкой шапки: у каждого своя, а у оценки одна на четыре
// колонки. Окно фильтра по оценке у игр показывает общую и три шкалы, а кнопка
// над ним одна — гореть и гаснуть они обязаны вместе, иначе выставленное в
// колонке шкалы нечем ни увидеть, ни снять.
const GROUPS = { ...Object.fromEntries(FIELDS.map((field) => [field, [field]])),
                 scores: SINGLE }

const sets = () => Object.fromEntries(FIELDS.map((field) => [field, []]))

export const EMPTY = { on: sets(), ex: sets() }

/** Новая пара наборов: у названного признака оба списка заменены, чужие
 *  признаки не тронуты. Форма одна на все три перехода, и списанная порознь она
 *  теряла бы половину молча — подмену второй половины проходит любой тест,
 *  который зовёт только одну из функций. */
const replaced = (filters, field, on, ex) => ({
  on: { ...filters.on, [field]: on },
  ex: { ...filters.ex, [field]: ex },
})

/** Следующее состояние строки: пусто → включено → исключено → пусто. */
export function cycled(filters, field, id) {
  const on = filters.on[field].includes(id)
  const ex = filters.ex[field].includes(id)

  // Включённое и исключённое разом дало бы «покажи драмы» вместе с «ни одной
  // драмы», то есть пустоту всегда.
  return replaced(filters, field,
                  on ? without(filters.on[field], id)
                     : ex ? filters.on[field]
                          : [...filters.on[field], id],
                  on ? [...filters.ex[field], id]
                     : without(filters.ex[field], id))
}

/** Состояние строки в списке. Читающая половина `cycled`: списанная по месту,
 *  она уехала бы в разметку, которую не проверяет ничто, — а перебор и его
 *  чтение обязаны понимать три состояния одинаково. */
export function stateOf(filters, field, id) {
  if (filters.on[field].includes(id)) return 'on'
  return filters.ex[field].includes(id) ? 'ex' : 'off'
}

/** То, что уезжает мосту: двенадцать кортежей, как их ждёт `Filters`. */
export function chosen(filters) {
  return {
    tag_ids: filters.on.tags,
    genre_ids: filters.on.genres,
    scores: filters.on.scores,
    visual: filters.on.visual,
    narrative: filters.on.narrative,
    gameplay: filters.on.gameplay,
    excluded_tag_ids: filters.ex.tags,
    excluded_genre_ids: filters.ex.genres,
    excluded_scores: filters.ex.scores,
    excluded_visual: filters.ex.visual,
    excluded_narrative: filters.ex.narrative,
    excluded_gameplay: filters.ex.gameplay,
  }
}

/** Метка на карточке: два состояния вместо трёх. Включён и не активен —
 *  исключить с карточки нечем.
 *
 *  Отдельно от `cycled` не по прихоти: пройди метка тем же перебором, второе
 *  нажатие означало бы «ни одного такого», то есть скрывало бы ту самую
 *  карточку, с которой нажали. */
export function marked(filters, field, id) {
  const on = filters.on[field].includes(id)
  // Включённой метка становится из любого состояния: иначе исключённый в
  // модалке жанр с карточки было бы не включить.
  return replaced(filters, field,
                  on ? without(filters.on[field], id)
                     : [...filters.on[field], id],
                  without(filters.ex[field], id))
}

/** Метка забыта целиком: её больше нет в наборе, и номер, оставшийся в
 *  фильтре, отбирал бы ленту по мертвецу — а выключить его было бы нечем,
 *  строки в списке уже нет. Из обеих половин, потому что удалить можно и
 *  включённый тег, и исключённый. */
export const forgotten = (filters, field, id) =>
  replaced(filters, field, without(filters.on[field], id),
           without(filters.ex[field], id))

/** Признак сброшен, остальные на месте: кнопка фильтра гасит свой, а не все.
 *  Второе нажатие по горящей кнопке — это «убрать этот отбор», и убирать вместе
 *  с ним чужой значило бы отменять то, чего человек не трогал. */
export const cleared = (filters, field) =>
  GROUPS[field].reduce((next, one) => replaced(next, one, [], []), filters)

/** По этому горит кнопка фильтра в шапке.
 *
 *  Признак необязателен: без него — «нет ни одного фильтра вовсе», с ним — «нет
 *  фильтра по этому признаку». Кнопок в шапке три, и каждая обязана гореть за
 *  себя: спека требует сочетаний («между признаками — по „и“»), а одна общая
 *  проверка делала бы «выбрал драму, исключил ужасы» недостижимым с экрана. */
export function isEmpty(filters, field = null) {
  const fields = field ? GROUPS[field] : FIELDS
  return fields.every((one) => !filters.on[one].length
                            && !filters.ex[one].length)
}

/** Проходит ли карточка фильтр. Нужно поиску: спросить источник с фильтром
 *  нечем — у TMDB и магазинов нет ни наших тегов, ни наших оценок, — поэтому
 *  ответ приходит целиком, а отсев идёт здесь.
 *
 *  В разделах библиотеки этим не пользуются: там то же самое делает база, и
 *  делает лучше — она не тащит через границу то, что всё равно скроют. Правило
 *  при этом одно на обе стороны, и разъехаться им нельзя: две выбранные метки
 *  давали бы в поиске один список, а в библиотеке другой.
 *
 *  Включённые складываются по «и» — решение пользователя 02.08.2026. Оценка и
 *  три шкалы игры — исключение, и не по решению, а по устройству: каждая из них
 *  у карточки одна, и «семь и восемь разом» не бывает ни у чего. Внутри такого
 *  признака выбранное складывается по «или», а между признаками остаётся «и».
 *  Исключённые вычитаются последними и означают «ни одного из этих», а не «не
 *  все сразу». */
export function passes(view, filters) {
  return FIELDS.every((field) => {
    const has = ownedBy(view, field)
    if (filters.ex[field].some((id) => has.includes(id))) return false
    if (!filters.on[field].length) return true
    const together = SINGLE.includes(field) ? 'some' : 'every'
    return filters.on[field][together]((id) => has.includes(id))
  })
}

/** Чем карточка отвечает на каждый признак. У кандидата поиска есть только
 *  жанры: теги, оценка и шкалы держатся за `item_id`, а его у него нет.
 *
 *  Оценка названа веткой, а шкалы оставлены остатком, а не наоборот: остаток
 *  здесь — это чтение колонки `rating` по имени признака, и незнакомый признак
 *  ответит пустотой. Назови остатком оценку — и он молча отобрал бы по ней. */
function ownedBy(view, field) {
  if (field === 'genres') return view.genres.map((one) => one.id)
  if (field === 'tags') return view.tags.map((one) => one.id)
  if (field === 'scores') {
    // Столбец у общей оценки тот же, что ступень на карточке, и считает его
    // общий `stepOfScore`: свой счёт здесь означал бы, что в поиске отбирается
    // не то, что подписано.
    const score = view.rating?.score
    return score ? [stepOfScore(score)] : []
  }
  // Шкалы игры целые — их заводит ряд звёзд, и считать у них нечего.
  // Невыставленная не отвечает ни на одну ступень: она никакая, а не низшая.
  const step = view.rating?.[field]
  return step ? [step] : []
}

const without = (ids, id) => ids.filter((each) => each !== id)
