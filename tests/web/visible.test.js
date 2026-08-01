import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме этой проверки.
import { onCardShown, stale } from '../../client/app/visible.js'

const DAY = 24 * 60 * 60 * 1000

/** Поддельный мост: записывает, о чём спросили, и отвечает пустым. */
function fake() {
  const asked = []
  const answer = (...args) => { asked.push(args); return { ok: [] } }
  globalThis.window = {
    pywebview: { api: { world: { enrich: answer, refresh_series: answer } } },
    addEventListener: () => {},
  }
  return asked
}

/** Номер у каждой карточки свой: память спрошенных общая на весь сеанс, и
 *  повтор номера между тестами читался бы как «уже спрашивали». */
let next = 1000
const card = (fields = {}) => ({ item_id: next += 1, kind: 'movie',
                                 source: 'tmdb', synced_at: null, ...fields })

describe('карточка попала в поле зрения', () => {
  it('спрашивает оценки агрегаторов', async () => {
    const asked = fake()

    await onCardShown(card(), [])

    expect(asked).toHaveLength(1)
  })

  it('о кандидате поиска не спрашивает вовсе', async () => {
    // У него нет номера строки: он ещё не в базе, и спрашивать о нём нечем.
    const asked = fake()

    expect(await onCardShown(card({ item_id: null }), [])).toBe(null)
    expect(asked).toHaveLength(0)
  })

  it('о той же карточке второй раз не спрашивает', async () => {
    // Прокрутка вверх-вниз иначе гоняла бы круги загрузки по кругу, тратя
    // квоты агрегаторов.
    const asked = fake()
    const one = card()

    await onCardShown(one, [])
    await onCardShown(one, [])

    expect(asked).toHaveLength(1)
  })

  it('кладёт номер операции в список отменяемых', async () => {
    // Иначе гасить при уходе с раздела нечего, и `cancel` зовётся с пустотой.
    fake()
    const ops = []

    await onCardShown(card(), ops)

    expect(ops).toHaveLength(1)
  })

  it('у каждой карточки свой канал', async () => {
    // Общий по имени вызова означал бы, что десяток видимых карточек гасят
    // друг друга: выжила бы последняя, а остальные ушли бы родом `stale`,
    // который молчит.
    const asked = fake()

    await onCardShown(card(), [])
    await onCardShown(card(), [])

    expect(asked[0][0]).not.toBe(asked[1][0])
  })
})

describe('просрочка карточки', () => {
  const long = new Date(Date.now() - 60 * DAY).toISOString()
  const recent = new Date(Date.now() - 3 * DAY).toISOString()

  it('сериал старше месяца перезапрашивается', () => {
    expect(stale({ kind: 'series', source: 'tmdb', synced_at: long })).toBe(true)
  })

  it('свежий сериал — нет', () => {
    expect(stale({ kind: 'series', source: 'tmdb', synced_at: recent }))
      .toBe(false)
  })

  it('фильм не перезапрашивается никогда, как бы стар ни был', () => {
    // Обновляются только сезоны и серии: у фильма их нет.
    expect(stale({ kind: 'movie', source: 'tmdb', synced_at: long })).toBe(false)
  })

  it('сериал не из TMDB — тоже нет', () => {
    // Сезоны умеет перезапрашивать один источник.
    expect(stale({ kind: 'series', source: 'manual', synced_at: long }))
      .toBe(false)
  })

  it('никогда не синхронизированное просроченным не считается', () => {
    expect(stale({ kind: 'series', source: 'tmdb', synced_at: null }))
      .toBe(false)
  })
})
