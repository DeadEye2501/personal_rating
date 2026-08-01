import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { rowTurns } from '../../client/app/inturn.js'

const film = { source: 'tmdb', source_id: '27205' }
const twin = { source: 'steam', source_id: '27205' }

/** Обещание, которое разрешают снаружи: без него очерёдность не наблюдается —
 *  всё успевает закончиться раньше, чем начнётся следующее. */
function held() {
  let release
  const promise = new Promise((resolve) => { release = resolve })
  return { promise, release }
}

describe('одно заведение на строку', () => {
  it('второй проситель ждёт того же ответа, а не заводит второй раз', async () => {
    // Показ строки и нажатие звезды по ней случаются одновременно, а два
    // заведения подряд — это два ответа, и второй возвращает строку такой,
    // какой она была до первого.
    const turns = rowTurns()
    const gate = held()
    let starts = 0

    const first = turns.once(film, () => { starts += 1; return gate.promise })
    const second = turns.once(film, () => { starts += 1; return gate.promise })
    gate.release('карточка')

    expect(await first).toBe('карточка')
    expect(await second).toBe('карточка')
    expect(starts).toBe(1)
  })

  it('строки различаются парой, а не идентификатором', async () => {
    // `27205` есть и у TMDB, и у Steam, и это разные вещи.
    const turns = rowTurns()
    let starts = 0

    await Promise.all([turns.once(film, () => { starts += 1 }),
                       turns.once(twin, () => { starts += 1 })])

    expect(starts).toBe(2)
  })

  it('доведённое до конца забывается: следующий жест заводит заново', async () => {
    // Память держит начатое, а не сделанное: иначе строка, заведение которой
    // сорвалось, второго шанса не получила бы.
    const turns = rowTurns()
    let starts = 0

    await turns.once(film, () => { starts += 1 })
    await turns.once(film, () => { starts += 1 })

    expect(starts).toBe(2)
  })

  it('сорвавшееся тоже забывается', async () => {
    const turns = rowTurns()

    await expect(turns.once(film, () => Promise.reject(new Error('сеть'))))
      .rejects.toThrow('сеть')
    await expect(turns.once(film, () => 'вторая попытка'))
      .resolves.toBe('вторая попытка')
  })

  it('забвение начатого не задевает соседнюю строку', async () => {
    const turns = rowTurns()
    const gate = held()
    let starts = 0

    const waiting = turns.once(film, () => gate.promise)
    await turns.once(twin, () => { starts += 1 })
    gate.release(null)
    await waiting

    expect(starts).toBe(1)
  })
})

describe('записи по строке идут по очереди', () => {
  it('вторая запись видит то, что сделала первая', async () => {
    // Три шкалы игры, нажатые подряд, считаются от общего состояния: пущенные
    // вперегонки, они затирают друг друга, и в базе остаётся последняя.
    const turns = rowTurns()
    const done = []
    const gate = held()

    const first = turns.inTurn(film, async () => {
      await gate.promise
      done.push('первая')
    })
    const second = turns.inTurn(film, () => { done.push('вторая') })

    expect(done).toEqual([])
    gate.release()
    await Promise.all([first, second])

    expect(done).toEqual(['первая', 'вторая'])
  })

  it('сорвавшаяся запись не запирает очередь', async () => {
    // Отказ сети на одной шкале не должен сделать карточку неоценимой до конца
    // сеанса.
    const turns = rowTurns()

    const failed = turns.inTurn(film, () => Promise.reject(new Error('сеть')))
    const after = turns.inTurn(film, () => 'следующая')

    await expect(failed).rejects.toThrow('сеть')
    expect(await after).toBe('следующая')
  })

  it('очередь у каждой строки своя', async () => {
    // Медленная запись по одной карточке не держит нажатие по соседней.
    const turns = rowTurns()
    const gate = held()
    let neighbour = false

    const slow = turns.inTurn(film, () => gate.promise)
    await turns.inTurn(twin, () => { neighbour = true })

    expect(neighbour).toBe(true)
    gate.release()
    await slow
  })
})
