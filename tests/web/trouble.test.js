import { afterEach, describe, expect, it, vi } from 'vitest'

import { Failed } from '$api/bridge.js'
// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { reported } from '../../client/app/trouble.js'

const written = () => vi.spyOn(console, 'warn').mockImplementation(() => {})

afterEach(() => { vi.restoreAllMocks() })

describe('отказ операции наружу', () => {
  it('молчаливый не оставляет следа нигде', () => {
    // Отменённое и устаревшее — это уход со страницы и вытеснение канала:
    // штатный ход, о котором нечего сказать ни человеку, ни журналу. Скажи —
    // и лента при каждой смене фильтра писала бы в журнал и показывала плашку.
    const log = written()
    const said = []

    reported(new Failed('cancelled'), 'лента', () => said.push('сказано'))
    reported(new Failed('stale'), 'лента', () => said.push('сказано'))

    expect(log).not.toHaveBeenCalled()
    expect(said).toEqual([])
  })

  it('обычный пишется в журнал и говорится наружу', () => {
    const log = written()
    const said = []

    reported(new Failed('broken', 'мост лёг'), 'теги', () => said.push('сказано'))

    expect(log).toHaveBeenCalledTimes(1)
    expect(said).toEqual(['сказано'])
  })

  it('журнал называет место, а не только сам отказ', () => {
    // Иначе в журнале десяток одинаковых «broken» без единого признака того,
    // кто именно сорвался.
    const log = written()
    const error = new Failed('broken')

    reported(error, 'гистограмма')

    expect(log).toHaveBeenCalledWith('гистограмма', error)
  })

  it('без плашки отказ всё равно записывается', () => {
    // Сорвавшемуся агрегатору на карточке отведено пустое место, и плашка про
    // него была бы шумом, — но след обязан остаться: ни один вызов моста не
    // уходит бесследно.
    const log = written()

    expect(() => reported(new Failed('refused'), 'агрегатор')).not.toThrow()
    expect(log).toHaveBeenCalledTimes(1)
  })
})
