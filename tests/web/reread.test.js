import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { refreshed, without, withoutText } from '../../client/app/reread.js'
import { fake } from './fake.js'

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

describe('строка из базы кладётся без пустого синопсиса', () => {
  it('поле снимается, остальные остаются', () => {
    // Лента синопсис не возит вовсе, и положенное доливом пустое поле стёрло бы
    // показанный текст: у кандидата выдачи он от источника, у своей карточки от
    // второго круга.
    const fresh = { item_id: 5, title: 'Своё', synopsis: '' }

    expect(withoutText(fresh)).toEqual({ item_id: 5, title: 'Своё' })
  })
})

describe('перечитывание одной правленой карточки', () => {
  it('просит именно эту строку и кладёт приехавшую с меткой момента', async () => {
    // Метка едет в `cover`: адрес ручки обложки от содержимого не зависит, а
    // отдаёт она сутки кеша — без метки перезалитая картинка осталась бы
    // прежней и в ленте, и в окне правки.
    const asked = fake({ 'feed.views_of': { ok: [{ item_id: 5, title: 'Своё' }] },
                         'feed.synopsis': { ok: 'про восстание' } })
    const put = []

    await refreshed({ item_id: 5, at: 1700000000 }, [], (view) => put.push(view))

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
    fake({ 'feed.views_of': { ok: [{ item_id: 5, title: 'Своё' }] },
           'feed.synopsis': { fail: 'broken', detail: 'сломалось' } })
    const put = []

    await refreshed({ item_id: 5, at: 1700000000 }, [], (view) => put.push(view))

    expect(put).toEqual([{ item_id: 5, title: 'Своё', cover: 1700000000 }])
  })

  it('не кладёт ничего, если строки не приехало', async () => {
    // Карточку могли удалить из другого окна, пока перечитывание летело: без
    // проверки в ленту легла бы строка без названия и постера.
    fake({ 'feed.views_of': { ok: [] }, 'feed.synopsis': { ok: '' } })
    const put = []

    await refreshed({ item_id: 5, at: 1 }, [], (view) => put.push(view))

    expect(put).toEqual([])
  })

  it('кладёт номер операции в список отменяемых', async () => {
    // Уход с раздела гасит начатое: без номера гасить нечего.
    fake({ 'feed.views_of': { ok: [] }, 'feed.synopsis': { ok: '' } })
    const ops = []

    await refreshed({ item_id: 5, at: 1 }, ops, () => {})

    // Оба вызова: перечитанная строка и её синопсис.
    expect(ops).toHaveLength(2)
  })
})
