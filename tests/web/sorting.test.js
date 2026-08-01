import { describe, expect, it } from 'vitest'

import { ADDED_AT, SORT_STATES, cycleOf, hasSort, nextSort, orderFor, stateAt }
  from '$state/sorting.js'

/** Круг раздела так, как его проходит человек: от нетронутого переключателя
 *  нажатиями до возврата в начало. Длина набора отсюда — следствие, а не
 *  прочитанное объявление. */
const walk = (section) => {
  const seen = []
  let at = 0
  do {
    seen.push(orderFor(section, at))
    at = nextSort(section, at)
  } while (at !== 0)
  return seen
}

const keysOf = (section) => walk(section).map((order) => order.key)

describe('переключатель сортировки', () => {
  it('в оценённых восемь состояний, в отложенном четыре', () => {
    expect(walk('rated')).toHaveLength(8)
    expect(walk('wishlist')).toHaveLength(4)
  })

  it('в отложенном осмысленны только два критерия', () => {
    // Своей оценки у неоценённого не бывает, времени оценки тем более, а дата
    // выхода в списке дел ни о чём не говорит.
    expect(new Set(keysOf('wishlist'))).toEqual(new Set([ADDED_AT, 'title']))
  })

  it('дату добавления в оценённых не встретить', () => {
    // Девятое состояние понадобилось бы ровно одному разделу.
    expect(keysOf('rated')).not.toContain(ADDED_AT)
  })

  it('соседи — две стороны одного критерия, и это верно в обоих разделах', () => {
    // Перебор обязан сначала перевернуть направление и лишь потом сменить
    // критерий: иначе он читается как случайный список.
    for (const section of ['rated', 'wishlist']) {
      const cycle = cycleOf(section)
      for (let at = 0; at < cycle.length; at += 2) {
        const first = orderFor(section, at)
        const second = orderFor(section, at + 1)

        expect(second.key).toBe(first.key)
        expect(second.descending).toBe(!first.descending)
      }
    }
  })

  it('нетронутый переключатель даёт первое состояние своего набора', () => {
    expect(orderFor('rated', null)).toEqual({ key: 'score', descending: true })
    expect(orderFor('wishlist', null)).toEqual({ key: ADDED_AT, descending: true })
  })

  it('замыкается по своему набору, а не по общей таблице', () => {
    // В отложенном круг вчетверо короче: перебор по восьми увёл бы его в
    // состояния, которых у раздела нет.
    let at = 0
    for (let step = 0; step < 4; step += 1) at = nextSort('wishlist', at)
    expect(at).toBe(0)

    at = 0
    for (let step = 0; step < 8; step += 1) at = nextSort('rated', at)
    expect(at).toBe(0)
  })

  it('не повторяет ни одного состояния внутри набора', () => {
    for (const section of ['rated', 'wishlist']) {
      const seen = walk(section).map(({ key, descending }) => `${key}:${descending}`)
      expect(new Set(seen).size).toBe(seen.length)
    }
  })
})

describe('где переключатель вообще есть', () => {
  it('в обеих половинах библиотеки — да, в поиске и статистике — нет', () => {
    // У поиска порядок задан склейкой своего и чужого, у статистики сортировать
    // нечего. Кнопка, которая перебирает восемь состояний и не меняет ничего,
    // обманывает.
    expect(hasSort('rated')).toBe(true)
    expect(hasSort('wishlist')).toBe(true)
    expect(hasSort('search')).toBe(false)
    expect(hasSort('stats')).toBe(false)
  })

  it('отвечает по тому же набору, из которого берёт состояния', () => {
    // Вторым списком это разошлось бы молча: раздел получил бы круг состояний,
    // но не получил бы кнопку — или наоборот, кнопку без круга.
    for (const section of ['rated', 'wishlist', 'search', 'stats']) {
      expect(hasSort(section)).toBe(cycleOf(section) !== undefined)
    }
  })
})

describe('вид кнопки переключателя', () => {
  it('берёт состояние своего раздела', () => {
    // Позиция 0 в двух разделах — разные состояния, и глиф обязан различаться.
    expect(stateAt('wishlist', 0).icon).toBe('bookmark_added')
    expect(stateAt('rated', 0).icon).toBe('star')
  })

  it('нетронутый переключатель рисуется первым состоянием своего набора', () => {
    // `sort: null` — стартовое значение в каждом разделе, то есть основной
    // путь, а не крайний случай: до первого щелчка кнопку рисовать нечем.
    expect(stateAt('rated', null)).toBe(SORT_STATES[0])
    expect(stateAt('wishlist', null).key).toBe(ADDED_AT)
  })

  it('в паре меняются подпись и стрелка, а глиф остаётся', () => {
    // Критерий показан глифом, сторона — стрелкой в углу. Разъедься они —
    // кнопка сообщала бы одно, а список приходил бы другим.
    for (const section of ['rated', 'wishlist']) {
      const cycle = cycleOf(section)
      for (let at = 0; at < cycle.length; at += 2) {
        const first = stateAt(section, at)
        const second = stateAt(section, at + 1)

        expect(first.dir).toBe('arrow_downward')
        expect(second.dir).toBe('arrow_upward')
        expect(second.icon).toBe(first.icon)
        expect(second.label).not.toBe(first.label)
      }
    }
  })

  it('«А → Я» — это возрастание, а не убывание', () => {
    // У чисел и дат «сначала большие» совпадает с убыванием, и стрелка вниз
    // читается заодно и как сторона. У текста не совпадает: А → Я это
    // возрастание. Разъехавшись, кнопка обещала бы А → Я, а база отдала бы
    // Я → А — и наоборот, молча, потому что оба ответа выглядят законными.
    const forward = SORT_STATES.find((state) => state.label.endsWith('А → Я'))
    const backward = SORT_STATES.find((state) => state.label.endsWith('Я → А'))

    expect(forward.down).toBe(false)
    expect(backward.down).toBe(true)
  })
})
