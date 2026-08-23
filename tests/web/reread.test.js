import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { onCardShown } from '../../client/app/visible.js'
import { again, without, withoutText } from '../../client/app/reread.js'
import { fake, slow } from './fake.js'

const own = { item_id: 5, source: 'tmdb', source_id: '157336' }
const twin = { item_id: null, source: 'steam', source_id: '157336' }
// Второй недогруженный кандидат: он обязан уцелеть. Без него весь отсев
// сходится к «убрать всё, у чего нет номера», и ветка про пару не наблюдается
// вовсе — а в приложении такая поломка вычищает из выдачи разом всё, что ещё не
// успело догрузиться.
const waiting = { item_id: null, source: 'gog', source_id: '1207658930' }
const other = { item_id: 7, source: 'tmdb', source_id: '27205' }

describe('удалённая строка уходит из списка', () => {
  it('своя — по номеру', () => {
    expect(without([own, other], { item_id: 5 })).toEqual([other])
  })

  it('кандидат без номера — по паре «источник плюс идентификатор»', () => {
    const gone = { item_id: null, source: 'steam', source_id: '157336' }

    expect(without([own, twin, waiting, other], gone))
      .toEqual([own, waiting, other])
  })

  it('одинаковый идентификатор у другого источника не задевается', () => {
    // Половина ключа не сторожила бы вторую: `157336` есть и у TMDB, и у Steam,
    // и это разные вещи.
    const gone = { item_id: null, source: 'steam', source_id: '157336' }

    expect(without([own, twin], gone)).toEqual([own])
  })

  it('удаление по номеру не задевает недогруженных соседей', () => {
    // У них номера нет вовсе, и сравнение с ним не должно их касаться.
    expect(without([own, twin, waiting], { item_id: 5 })).toEqual([twin, waiting])
  })
})

// Строка из базы **всегда** несёт синопсис — `CardView` объявляет его полем без
// умолчания, — и в подделке он пустой ровно поэтому: с рядом, у которого поля
// нет вовсе, снятие `withoutText` не наблюдалось бы ничем.

describe('строка из базы кладётся без пустого синопсиса', () => {
  it('поле снимается, остальные остаются', () => {
    // Лента синопсис не возит вовсе, и положенное доливом пустое поле стёрло бы
    // показанный текст: у кандидата выдачи он от источника, у своей карточки от
    // второго круга.
    const fresh = { item_id: 5, title: 'Своё', synopsis: '' }

    expect(withoutText(fresh)).toEqual({ item_id: 5, title: 'Своё' })
  })
})

/** Перечитывание строки, которая в списке есть: сам вызов у четырёх проверок
 *  один и тот же, а различаются они ответами подделки. */
const refreshedRow = (put, at = 1) =>
  again([{ item_id: 5 }], { item_id: 5, at }, [], (view) => put.push(view))

describe('перечитывают только то, что ещё в списке', () => {
  it('строку списка перечитывает', async () => {
    const asked = fake({
      'feed.views_of': { ok: [{ item_id: 5, title: 'Своё', synopsis: '' }] },
      'feed.synopsis': { ok: 'про восстание' },
    })
    const put = []

    await again([{ item_id: 5 }], { item_id: 5, at: 1 }, [],
                (view) => put.push(view))

    expect(asked.map(([path]) => path)).toEqual(['feed.views_of', 'feed.synopsis'])
    expect(put).toHaveLength(1)
  })

  it('о пропавшей не спрашивает никого', async () => {
    // Раздел мог смениться, пока запись доезжала до базы: спрашивать базу о
    // строке, которой на экране нет, значит платить походом за ответ, который
    // некуда положить. Свидетель — счётчик спрошенного: без него «перечитали
    // впустую» неотличимо от «не перечитывали».
    const asked = fake({ 'feed.views_of': { ok: [] }, 'feed.synopsis': { ok: '' } })

    const answer = again([{ item_id: 7 }], { item_id: 5, at: 1 }, [], () => {})

    expect(answer).toBe(null)
    expect(asked).toEqual([])
  })
})

describe('перечитывание одной правленой карточки', () => {
  it('просит именно эту строку и кладёт приехавшую с меткой момента', async () => {
    // Метка едет в `cover`: адрес ручки обложки от содержимого не зависит, а
    // отдаёт она сутки кеша — без метки перезалитая картинка осталась бы
    // прежней и в ленте, и в окне правки.
    const asked = fake({
      'feed.views_of': { ok: [{ item_id: 5, title: 'Своё', synopsis: '' }] },
      'feed.synopsis': { ok: 'про восстание' },
    })
    const put = []

    await again([{ item_id: 5 }], { item_id: 5, at: 1700000000 }, [],
                (view) => put.push(view))

    expect(asked).toEqual([['feed.views_of', [expect.any(Number), [5]]],
                          ['feed.synopsis', [expect.any(Number), 5]]])
    expect(put).toEqual([{ item_id: 5, title: 'Своё', synopsis: 'про восстание',
                           cover: 1700000000 }])
  })

  it('отказ чтения текста перечитывания не отменяет', async () => {
    // С перечитанной строкой едет метка момента, а она сбрасывает суточный кеш
    // обложки: пустяковый отказ чтения текста оставил бы перезалитую картинку
    // прежней до завтра. Синопсис при этом не кладётся вовсе — строка остаётся
    // с показанным.
    fake({ 'feed.views_of': { ok: [{ item_id: 5, title: 'Своё', synopsis: '' }] },
           'feed.synopsis': { fail: 'broken', detail: 'сломалось' } })
    const put = []

    await again([{ item_id: 5 }], { item_id: 5, at: 1700000000 }, [],
                (view) => put.push(view))

    expect(put).toEqual([{ item_id: 5, title: 'Своё', cover: 1700000000 }])
  })

  it('не кладёт ничего, если строки не приехало', async () => {
    // Карточку могли удалить из другого окна, пока перечитывание летело: без
    // проверки в ленту легла бы строка без названия и постера.
    fake({ 'feed.views_of': { ok: [] }, 'feed.synopsis': { ok: '' } })
    const put = []

    await again([{ item_id: 5 }], { item_id: 5, at: 1 }, [], (view) => put.push(view))

    expect(put).toEqual([])
  })

  it('гасит ответ круга по той же карточке', async () => {
    // Синопсис читают двое: второй круг на каждое появление карточки и это
    // перечитывание. Читают они одну колонку, а порядок приезда порядку
    // вопросов не равен — разойдись каналы, и ответ круга, отправленный до
    // правки, лёг бы поверх свежего текста. Человек увидел бы, как набранное
    // им откатывается само.
    //
    // Круг зовётся **своей дверью**, `onCardShown`, а не собранным здесь
    // вызовом: имя канала он строит сам, и собери его проверка — она сторожила
    // бы собственную строку, а не то, что канал у двух дверей общий.
    fake({ 'feed.views_of': { ok: [{ item_id: 5, title: 'Своё', synopsis: '' }] },
           'feed.synopsis': slow({ ok: 'прежний' }, { ok: 'свежий' }),
           'world.enrich': { ok: [] }, 'world.refresh_series': { ok: [] } })
    const round = []
    const put = []
    const circle = onCardShown({ item_id: 5, kind: 'movie', source: 'tmdb',
                                 synced_at: null },
                               [], (fields) => round.push(fields))

    await refreshedRow(put)
    await circle

    expect(put).toEqual([{ item_id: 5, title: 'Своё', synopsis: 'свежий',
                           cover: 1 }])
    expect(round.some((one) => 'synopsis' in one)).toBe(false)
  })

  it('кладёт номер операции в список отменяемых', async () => {
    // Уход с раздела гасит начатое: без номера гасить нечего.
    fake({ 'feed.views_of': { ok: [] }, 'feed.synopsis': { ok: '' } })
    const ops = []

    await again([{ item_id: 5 }], { item_id: 5, at: 1 }, ops, () => {})

    // Оба вызова: перечитанная строка и её синопсис.
    expect(ops).toHaveLength(2)
  })
})
