import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { aspected, scored } from '../../client/app/rating.js'
import { fake } from './fake.js'

const film = { item_id: 7, rating: { score: 5 } }
const game = { item_id: 9, rating: { visual: 8, narrative: null, gameplay: 6 } }

describe('своя оценка', () => {
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

  it('отказ записи доходит до просителя, а не глотается', async () => {
    // Молчание тут запрещено правилом отказов: не дошло до базы — человек
    // обязан узнать, а журнал получить след. Обещание отклоняется, и ловит его
    // тот, кто просил.
    fake({ 'marks.score': { fail: 'timeout' } })

    await expect(scored(film, 8)).rejects.toMatchObject({ kind: 'timeout' })
  })

  it('отказ записи шкал доходит так же', async () => {
    fake({ 'marks.aspects': { fail: 'broken' } })

    await expect(aspected(game, 'visual', 3)).rejects.toMatchObject({ kind: 'broken' })
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
