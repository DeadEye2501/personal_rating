import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { merged, without } from '../../client/app/reread.js'

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

describe('чужая половина выдачи доливается к показанной', () => {
  it('приехавшее берёт верх над показанным', () => {
    // Свежая строка правдива обо всём, что лежит в базе: у неё жанры словами,
    // состав и оценки агрегаторов, которых у своей половины могло не быть.
    const shown = [{ ...own, title: 'Старое' }]
    const fresh = [{ ...own, title: 'Новое' }]

    expect(merged(shown, fresh)).toEqual([{ ...own, title: 'Новое' }])
  })

  it('своё, чего в базе нет, переживает долив', () => {
    // Свёрнутость и отметка «круг оценок отработал» живут только на странице.
    // Заменой списка целиком они стирались, а заново их никто не заводит:
    // карточку, о которой уже спросили, память показа второй раз не трогает —
    // и кольца на месте оценок крутились бы до конца сеанса.
    const shown = [{ ...own, collapsed: true, enriched: true }]

    const [row] = merged(shown, [{ ...own }])

    expect(row.collapsed).toBe(true)
    expect(row.enriched).toBe(true)
  })

  it('порядок и состав задаёт приехавшее, а не показанное', () => {
    // Складывает половины бэкенд, и его порядок — ответ: своё целиком, потом
    // чужое. Показанное сюда добавить нечего, даже если оно из выдачи ушло.
    const gone = { item_id: 9, source: 'tmdb', source_id: '999' }

    expect(merged([gone, own], [own, other]).map((one) => one.source_id))
      .toEqual(['157336', '27205'])
  })

  it('строка того же номера у другого источника чужого не подхватывает', () => {
    // Ключ составной: `157336` есть и у TMDB, и у Steam. Половиной ключа
    // свёрнутость одной строки уехала бы на другую.
    const [row] = merged([{ ...own, collapsed: true }], [{ ...twin }])

    expect(row.collapsed).toBe(undefined)
  })
})
