import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { aspected, reviewed, scored, wished } from '../../client/app/marks.js'
import { fake } from './fake.js'

const film = { item_id: 7, rating: { score: 5 } }
const game = { item_id: 9, rating: { visual: 8, narrative: null, gameplay: 6 } }

describe('свои отметки на карточке', () => {
  it('пишет балл и отдаёт поля для строки', async () => {
    // Строку обновляет тот, кто ею владеет: у ленты она ищется по номеру, у
    // выдачи поиска — по паре «источник плюс идентификатор». Здесь только то,
    // что записалось.
    const asked = fake({ 'marks.score': { ok: null } })

    const fields = await scored(film, 8)

    expect(asked).toEqual([['marks.score', [7, 8]]])
    expect(fields).toEqual({ rating: { score: 8 } })
  })

  it('снятая оценка доезжает пустотой, а не нулём', async () => {
    // Ноль — законная оценка ниже некуда, а снятая это её отсутствие. Слипшись,
    // они превратили бы «снять» в «поставить единицу».
    const asked = fake({ 'marks.score': { ok: null } })

    const fields = await scored(film, null)

    expect(asked).toEqual([['marks.score', [7, null]]])
    expect(fields.rating.score).toBe(null)
  })

  it('у игры записывает три шкалы разом и берёт средний балл от базы', async () => {
    // Среднее считает база: у игры это среднее выставленных шкал, и второе его
    // объявление на странице разошлось бы с первым молча.
    const asked = fake({ 'marks.aspects': { ok: 7.5 } })

    const fields = await aspected(game, 'narrative', 9)

    expect(asked).toEqual([['marks.aspects', [9, 8, 9, 6]]])
    expect(fields).toEqual({
      rating: { visual: 8, narrative: 9, gameplay: 6, score: 7.5 },
    })
  })

  it('шкалу снимают тем же путём, соседние не трогая', async () => {
    const asked = fake({ 'marks.aspects': { ok: 6 } })

    const fields = await aspected(game, 'visual', null)

    expect(asked).toEqual([['marks.aspects', [9, null, null, 6]]])
    expect(fields.rating.visual).toBe(null)
    expect(fields.rating.gameplay).toBe(6)
  })

  it('закладка ставится и снимается тем же жестом', async () => {
    // Один жест на два действия: у карточки в списке дел кнопка горит, и она же
    // её и гасит. Какой из двух путей моста звать, решает нынешнее состояние.
    const put = fake({ 'marks.wish': { ok: null } })
    expect(await wished({ item_id: 7, in_wishlist: false }))
      .toEqual({ in_wishlist: true })
    expect(put).toEqual([['marks.wish', [7]]])

    const off = fake({ 'marks.unwish': { ok: null } })
    expect(await wished({ item_id: 7, in_wishlist: true }))
      .toEqual({ in_wishlist: false })
    expect(off).toEqual([['marks.unwish', [7]]])
  })

  it('рецензия пишется к своей карточке и не трогает оценку', async () => {
    // Оценка и рецензия живут в одной строке базы, и запись одной не смеет
    // стереть другую: у карточки с баллом рецензия доливается к нему.
    const asked = fake({ 'marks.review': { ok: null } })

    const fields = await reviewed(film, 'смотрел трижды')

    expect(asked).toEqual([['marks.review', [7, 'смотрел трижды']]])
    expect(fields).toEqual({ rating: { score: 5, review: 'смотрел трижды' } })
  })

  it('пустой текст — это «рецензии нет», и он доезжает пустым', async () => {
    // Отдельного «удалить рецензию» нет: гасит кнопку сохранённая пустота.
    const asked = fake({ 'marks.review': { ok: null } })

    const fields = await reviewed({ item_id: 7, rating: { review: 'было' } }, '')

    expect(asked).toEqual([['marks.review', [7, '']]])
    expect(fields.rating.review).toBe('')
  })

  it('рецензия у карточки без оценок вовсе не падает', async () => {
    // Свежезаведённая карточка приезжает без `rating`: первая рецензия по ней —
    // обычный ход, и заводит она ту же строку, что и первая звезда.
    fake({ 'marks.review': { ok: null } })

    const fields = await reviewed({ item_id: 3, rating: null }, 'коротко')

    expect(fields.rating).toEqual({ review: 'коротко' })
  })

  it('отказ записи доходит до просителя, а не глотается', async () => {
    // Молчание тут запрещено правилом отказов: не дошло до базы — человек
    // обязан узнать, а журнал получить след. Обещание отклоняется, и ловит его
    // тот, кто просил.
    fake({ 'marks.score': { fail: 'timeout' } })

    await expect(scored(film, 8)).rejects.toMatchObject({ kind: 'timeout' })
  })

  it('отказ закладки доходит так же', async () => {
    fake({ 'marks.wish': { fail: 'timeout' } })

    await expect(wished({ item_id: 7, in_wishlist: false }))
      .rejects.toMatchObject({ kind: 'timeout' })
  })

  it('отказ записи шкал доходит так же', async () => {
    fake({ 'marks.aspects': { fail: 'broken' } })

    await expect(aspected(game, 'visual', 3)).rejects.toMatchObject({ kind: 'broken' })
  })

  it('отказ записи рецензии доходит так же', async () => {
    // Окно на этом остаётся открытым, чтобы набранное не пропало, — но узнать
    // об отказе оно может только отклонённым обещанием.
    fake({ 'marks.review': { fail: 'timeout' } })

    await expect(reviewed(film, 'текст')).rejects.toMatchObject({ kind: 'timeout' })
  })

  it('оценка первой шкалы у карточки без оценок вовсе не падает', async () => {
    // Свежезаведённая карточка приезжает без `rating`, и первая же звезда по
    // ней — обычный ход.
    const asked = fake({ 'marks.aspects': { ok: 9 } })

    const fields = await aspected({ item_id: 3, rating: null }, 'gameplay', 9)

    expect(asked).toEqual([['marks.aspects', [3, null, null, 9]]])
    expect(fields.rating).toEqual({ visual: null, narrative: null,
                                    gameplay: 9, score: 9 })
  })
})
