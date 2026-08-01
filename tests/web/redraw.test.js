import { describe, expect, it } from 'vitest'

import { redrawn } from '$state/redraw.js'

/** Двойник узла, записывающий порядок: именно порядок здесь и есть предмет. */
function node(name = 'is-drawing') {
  const steps = []
  return {
    steps,
    classList: {
      remove: (one) => steps.push(`снят ${one}`),
      add: (one) => steps.push(`возвращён ${one}`),
    },
    get offsetWidth() { steps.push('пересчёт'); return 0 },
    name,
  }
}

describe('перезапуск анимации', () => {
  it('заставляет браузер пересчитать стили между снятием и возвратом', () => {
    // Без пересчёта браузер смены не увидит вовсе: он сличает состояние на
    // конец задачи, и снятый в той же задаче класс для него не снимался.
    // Отложить возврат кадром не помогает — колбэк `requestAnimationFrame`
    // выполняется до пересчёта стилей того же кадра. Замерено в Chromium:
    // столбики отрастают ровно один раз за сеанс, а первое нажатие это
    // маскирует, потому что класса до него не было.
    const element = node()

    redrawn(element, 'is-drawing')

    expect(element.steps).toEqual(['снят is-drawing', 'пересчёт',
                                   'возвращён is-drawing'])
  })

  it('возвращает тот же признак, что и снял', () => {
    const element = node()

    redrawn(element, 'is-growing')

    expect(element.steps.at(0)).toBe('снят is-growing')
    expect(element.steps.at(-1)).toBe('возвращён is-growing')
  })
})
