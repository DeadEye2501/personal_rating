/* Таска указателем: захват, движение, отпускание. */

/** Ведёт таску от нажатия до потери захвата.
 *
 *  Захват вешается на переданный узел, а не на тот, за который схватили: строка
 *  списка при перестановке переезжает в DOM, и захват на ней сорвался бы после
 *  первой же. Конец считаем по потере захвата, а не по `pointerup`: кнопку
 *  могут отпустить за окном приложения, и `pointerup` тогда не придёт вовсе, а
 *  `lostpointercapture` приходит и на узел, убранный из документа. */
export function dragging(node, event, onmove, onstop = null) {
  event.preventDefault()
  node.setPointerCapture(event.pointerId)

  // Чужие указатели в счёт не идут: второй палец или вторая мышь заставили бы
  // строку прыгать между двумя следами.
  const moved = (moving) => { if (moving.pointerId === event.pointerId) onmove(moving) }

  node.addEventListener('pointermove', moved)
  node.addEventListener('lostpointercapture', () => {
    node.removeEventListener('pointermove', moved)
    onstop?.()
  }, { once: true })
}
