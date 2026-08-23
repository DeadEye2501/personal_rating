import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме этой проверки.
import { forgetCard, onCardShown, stale } from '../../client/app/visible.js'
import { fake, slow } from './fake.js'

const DAY = 24 * 60 * 60 * 1000

/** Обе ручки объявлены всегда: обогащение зовут парой, и отсутствие метода в
 *  подделке читалось бы как «мост сломан», а не «источник ответил пусто». */
const world = (answers = {}) =>
  fake({ 'world.enrich': { ok: [] }, 'world.refresh_series': { ok: [] },
         'feed.synopsis': { ok: 'про восстание' }, ...answers })

/** Собранные правки карточки: круг кладёт их по мере приезда, и число правок —
 *  такое же свойство, как их содержимое. */
const shown = async (view, ops = []) => {
  const put = []
  await onCardShown(view, ops, (fields) => put.push(fields))
  return put
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
    const asked = world()
    const one = card({ kind: 'series' })

    await shown(one)

    const [, args] = asked.find(([path]) => path === 'world.enrich')
    expect(args.slice(1)).toEqual([one.item_id, 'series'])
  })

  it('кладёт приехавшие оценки правкой карточки', async () => {
    // Без этого приехавшее некуда положить, и кружок на месте оценки крутится
    // до перезахода в раздел.
    world({ 'world.enrich': { ok: [{ source: 'imdb', value: 8.7 }] } })

    expect(await shown(card())).toContainEqual({
      external: [{ source: 'imdb', value: 8.7 }],
      enriched: true,
    })
  })

  it('спрашивает синопсис своей ручкой и по номеру карточки', async () => {
    // Лента его не возит вовсе: показ синопсиса на пятидесяти карточках порции
    // стоит 150 мс из 186, а на экран их попадает четыре.
    const asked = world()
    const one = card()

    await shown(one)

    const [, args] = asked.find(([path]) => path === 'feed.synopsis')
    expect(args.slice(1)).toEqual([one.item_id])
  })

  it('приехавший синопсис кладёт своей правкой, не дожидаясь оценок', async () => {
    // Своей, а не общей с оценками: текст читается с диска за миллисекунды, а
    // оценки идут в сеть до двадцати секунд. Снимок строки, собранный до сети,
    // затирал бы всё, что случилось с ней за эти секунды, — правку синопсиса в
    // том числе.
    world({ 'world.enrich': slow({ ok: [] }) })

    expect(await shown(card()))
      .toEqual([{ synopsis: 'про восстание' }, { external: [], enriched: true }])
  })

  it('молчание синопсиса не стирает показанный', async () => {
    // Пустое в правку не кладётся: карточка, которой синопсис уже доехал,
    // осталась бы без него от любого повторного круга.
    world({ 'feed.synopsis': { ok: '' } })

    expect(await shown(card()).then((put) => put.some((one) => 'synopsis' in one)))
      .toBe(false)
  })

  it('отказ агрегатора не роняет показ и не приносит оценок', async () => {
    // Штатный путь: источник отказал, на месте оценки просто ничего — без
    // плашки и без следа на карточке.
    world({ 'world.enrich': { fail: 'refused', detail: 'квота' } })

    expect(await shown(card())).toContainEqual({ enriched: true })
  })

  it('просроченный сериал сперва перезапрашивает сезоны', async () => {
    // Перезапрос идёт своей ручкой и до обогащения: выключенный целиком, он
    // числа вызовов не менял бы, если смотреть только на длину.
    const asked = world()
    const old = new Date(Date.now() - 60 * DAY).toISOString()

    await shown(card({ kind: 'series', synced_at: old }))

    // Порядок сверяется у двух вызовов наружу: синопсис к ним не относится и
    // уходит первым, потому что ждать сеть ему незачем.
    expect(asked.map(([path]) => path).filter((path) => path.startsWith('world.')))
      .toEqual(['world.refresh_series', 'world.enrich'])
  })

  it('о кандидате поиска не спрашивает вовсе', async () => {
    // У него нет номера строки: он ещё не в базе, и спрашивать о нём нечем.
    const asked = world()

    expect(await shown(card({ item_id: null }))).toEqual([{ enriched: true }])
    expect(asked).toHaveLength(0)
  })

  it('оценки о той же карточке второй раз не спрашивает', async () => {
    // Прокрутка вверх-вниз иначе гоняла бы круги загрузки по кругу, тратя
    // квоты агрегаторов.
    const asked = world()
    const one = card()

    await shown(one)
    await shown(one)

    expect(asked.filter(([path]) => path === 'world.enrich')).toHaveLength(1)
  })

  it('а синопсис — спрашивает, и на каждый показ', async () => {
    // Память сделала бы текст одноразовым: смена вкладки перечитывает ленту, а
    // в приехавших из базы строках синопсиса нет вовсе — пропал бы на первом же
    // переключении и не вернулся никогда.
    const asked = world()
    const one = card()

    await shown(one)
    const again = await shown(one)

    expect(asked.filter(([path]) => path === 'feed.synopsis')).toHaveLength(2)
    expect(again).toContainEqual({ synopsis: 'про восстание' })
  })

  it('забытую карточку спрашивает заново', async () => {
    // Номер `item` SQLite выдаёт повторно: заведённая заново карточка получает
    // номер удалённой. Не забыв покойницу, память приняла бы новую за уже
    // спрошенную — кольца на месте оценок крутились бы до конца сеанса.
    const asked = world()
    const one = card()

    await shown(one)
    forgetCard(one.item_id)
    await shown(one)

    expect(asked.filter(([path]) => path === 'world.enrich')).toHaveLength(2)
  })

  it('забвение чужого номера памяти не трогает', async () => {
    // Иначе удаление одной карточки открывало бы круг всем соседям разом.
    const asked = world()
    const one = card()

    await shown(one)
    forgetCard(one.item_id + 1)
    await shown(one)

    expect(asked.filter(([path]) => path === 'world.enrich')).toHaveLength(1)
  })

  it('кладёт номер операции в список отменяемых', async () => {
    // Иначе гасить при уходе с раздела нечего, и `cancel` зовётся с пустотой.
    world()
    const ops = []

    await shown(card(), ops)

    // Один номер, а не два: гасят тут поход в сеть за оценками. Чтение текста в
    // отменяемые не кладётся нарочно — оно спрашивается на каждое появление
    // карточки, и список рос бы прокруткой, а гасить в нём нечего.
    expect(ops).toHaveLength(1)
  })

  it('две видимые карточки не гасят друг друга', async () => {
    // Канал наружу не уезжает, и сверять номера бесполезно — они и так растут.
    // Наблюдается следствие: обе спрошенные разом карточки получают свой
    // ответ. С общим каналом выжила бы последняя, а первая ушла бы родом
    // `stale`, который молчит.
    world({
      'world.enrich': slow({ ok: [{ source: 'imdb', value: 1 }] },
                           { ok: [{ source: 'imdb', value: 2 }] }),
    })

    const late = shown(card())
    const quick = shown(card())

    expect(await quick).toContainEqual({ external: [{ source: 'imdb', value: 2 }],
                                        enriched: true })
    expect(await late).toContainEqual({ external: [{ source: 'imdb', value: 1 }],
                                       enriched: true })
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
