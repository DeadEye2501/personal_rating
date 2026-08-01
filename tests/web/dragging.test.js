import { describe, expect, it } from 'vitest'

import { dragging } from '$state/dragging.js'

/** Двойник узла: помнит, чей указатель захвачен и кто на что подписан. */
function node() {
  const listeners = {}
  return {
    captured: null,
    setPointerCapture(id) { this.captured = id },
    addEventListener(name, run) { (listeners[name] ??= []).push(run) },
    removeEventListener(name, run) {
      listeners[name] = (listeners[name] ?? []).filter((one) => one !== run)
    },
    fire(name, event = {}) {
      [...(listeners[name] ?? [])].forEach((run) => run(event))
    },
    count(name) { return (listeners[name] ?? []).length },
  }
}

const press = (pointerId = 1) => {
  let prevented = false
  return {
    pointerId,
    get prevented() { return prevented },
    preventDefault() { prevented = true },
  }
}

describe('таска указателем', () => {
  it('захватывает переданный узел, а не тот, за который схватили', () => {
    // Строка списка при перестановке переезжает в DOM, и захват на ней
    // сорвался бы после первой же: держит его список целиком.
    const list = node()
    const grip = node()

    dragging(list, press(7), () => {})

    expect(list.captured).toBe(7)
    expect(grip.captured).toBe(null)
  })

  it('гасит действие браузера по умолчанию', () => {
    // Иначе нажатие начинает выделение текста, и таска идёт поверх него.
    const event = press()

    dragging(node(), event, () => {})

    expect(event.prevented).toBe(true)
  })

  it('везёт движения своего указателя', () => {
    const list = node()
    const seen = []

    dragging(list, press(1), (moved) => seen.push(moved.clientY))
    list.fire('pointermove', { pointerId: 1, clientY: 40 })
    list.fire('pointermove', { pointerId: 1, clientY: 90 })

    expect(seen).toEqual([40, 90])
  })

  it('чужой указатель в счёт не идёт', () => {
    // Второй палец или вторая мышь заставили бы строку прыгать между двумя
    // следами.
    const list = node()
    const seen = []

    dragging(list, press(1), (moved) => seen.push(moved.clientY))
    list.fire('pointermove', { pointerId: 2, clientY: 40 })

    expect(seen).toEqual([])
  })

  it('на потере захвата снимает подписку и говорит, что кончилось', () => {
    // Конец считаем по потере захвата, а не по `pointerup`: кнопку могут
    // отпустить за окном приложения, и `pointerup` тогда не придёт вовсе.
    const list = node()
    const seen = []
    let stopped = 0

    dragging(list, press(1), (moved) => seen.push(moved.clientY),
             () => { stopped += 1 })
    list.fire('lostpointercapture')
    list.fire('pointermove', { pointerId: 1, clientY: 40 })

    expect(stopped).toBe(1)
    expect(seen).toEqual([])
    expect(list.count('pointermove')).toBe(0)
  })

  it('без обработчика конца не падает', () => {
    // Ползунку прокрутки сообщать об окончании нечего: он ничего не сохраняет.
    const list = node()

    dragging(list, press(1), () => {})

    expect(() => list.fire('lostpointercapture')).not.toThrow()
  })
})
