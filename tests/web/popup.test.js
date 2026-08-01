/** Место всплывающей картинки рядом с указателем. */

import { describe, expect, it } from 'vitest'

import { beside } from '$state/popup.js'

const SIZE = { width: 120, height: 180 }
const VIEW = { width: 1000, height: 800 }

describe('картинка у указателя', () => {
  it('ложится рядом с указателем, справа снизу', () => {
    // Точкой, а не «больше чем»: односторонняя проверка переживает и отрыв на
    // пол-экрана, а «рядом» — это ровно небольшой отступ. Вплотную картинка
    // накрыла бы строку, на которую показывают, и подпись стала бы не видна
    // ровно в тот момент, когда её читают.
    expect(beside({ x: 300, y: 400 }, SIZE, VIEW)).toEqual({ left: 316,
                                                             top: 416 })
  })

  it('у правого края уходит влево, а не за экран', () => {
    // Тем же отступом от края, что и от курсора: прижатая вплотную, она
    // выглядит вылезшей, даже когда влезла целиком.
    const at = beside({ x: 960, y: 400 }, SIZE, VIEW)

    expect(at.left).toBe(VIEW.width - SIZE.width - 16)
  })

  it('у нижнего края поднимается, а не обрезается', () => {
    const at = beside({ x: 300, y: 780 }, SIZE, VIEW)

    expect(at.top).toBe(VIEW.height - SIZE.height - 16)
  })

  it('в тесном окне остаётся видимой хотя бы углом', () => {
    // Окно уже картинки — крайний случай, но уводить её в отрицательные
    // координаты нельзя: там её не видно вовсе.
    const at = beside({ x: 10, y: 10 }, SIZE, { width: 100, height: 100 })

    expect(at.left).toBeGreaterThanOrEqual(0)
    expect(at.top).toBeGreaterThanOrEqual(0)
  })
})
