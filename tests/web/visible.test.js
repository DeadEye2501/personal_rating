import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме этой проверки.
import { onCardShown, stale } from '../../client/app/visible.js'

const DAY = 24 * 60 * 60 * 1000

/** Поддельный мост: записывает путь и доводы, отвечает тем, что положили. */
function fake(answers = {}) {
  const asked = []
  const reply = (path) => (...args) => {
    asked.push([path, args])
    const answer = answers[path] ?? { ok: [] }
    return typeof answer === 'function' ? answer(...args) : answer
  }
  globalThis.window = {
    pywebview: {
      api: { world: { enrich: reply('world.enrich'),
                      refresh_series: reply('world.refresh_series') } },
    },
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
  it('спрашивает оценки агрегаторов той ручкой и теми доводами', async () => {
    // Числа вызовов мало: переставленные доводы и подменённое имя ручки его не
    // меняют, а мост ответил бы не о той карточке.
    const asked = fake()
    const one = card({ kind: 'series' })

    await onCardShown(one, [])

    expect(asked).toHaveLength(1)
    const [path, args] = asked[0]
    expect(path).toBe('world.enrich')
    expect(args.slice(1)).toEqual([one.item_id, 'series'])
  })

  it('отдаёт приехавшие оценки наверх', async () => {
    // Возврат обязателен: без него приехавшее некуда положить, и кружок на
    // месте оценки крутится до перезахода в раздел.
    fake({ 'world.enrich': { ok: [{ source: 'imdb', value: 8.7 }] } })

    expect(await onCardShown(card(), []))
      .toEqual([{ source: 'imdb', value: 8.7 }])
  })

  it('отказ агрегатора не роняет показ и не приносит оценок', async () => {
    // Штатный путь: источник отказал, на месте оценки просто ничего — без
    // плашки и без следа на карточке.
    fake({ 'world.enrich': { fail: 'refused', detail: 'квота' } })

    expect(await onCardShown(card(), [])).toBe(null)
  })

  it('просроченный сериал сперва перезапрашивает сезоны', async () => {
    // Перезапрос идёт своей ручкой и до обогащения: выключенный целиком, он
    // числа вызовов не менял бы, если смотреть только на длину.
    const asked = fake()
    const old = new Date(Date.now() - 60 * DAY).toISOString()

    await onCardShown(card({ kind: 'series', synced_at: old }), [])

    expect(asked.map(([path]) => path))
      .toEqual(['world.refresh_series', 'world.enrich'])
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

  it('две видимые карточки не гасят друг друга', async () => {
    // Канал наружу не уезжает, и сверять номера бесполезно — они и так растут.
    // Наблюдается следствие: обе спрошенные разом карточки получают свой
    // ответ. С общим каналом выжила бы последняя, а первая ушла бы родом
    // `stale`, который молчит.
    let first = true
    fake({
      'world.enrich': () => {
        if (!first) return { ok: [{ source: 'imdb', value: 2 }] }
        first = false
        return new Promise((resolve) =>
          setTimeout(() => resolve({ ok: [{ source: 'imdb', value: 1 }] }), 20))
      },
    })

    const slow = onCardShown(card(), [])
    const quick = onCardShown(card(), [])

    expect(await quick).toEqual([{ source: 'imdb', value: 2 }])
    expect(await slow).toEqual([{ source: 'imdb', value: 1 }])
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
