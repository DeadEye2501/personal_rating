import { describe, expect, it } from 'vitest'

import { castOf, plural, runtimeOf, seriesOf } from '$state/facts.js'

const named = (credit) => credit.name

describe('строки фактов', () => {
  it('длительность показывается часами и минутами', () => {
    expect(runtimeOf(158)).toBe('2 ч 38 мин')
    expect(runtimeOf(47)).toBe('47 мин')
  })

  it('ровный час не тянет за собой нулевые минуты', () => {
    expect(runtimeOf(120)).toBe('2 ч')
  })

  it('неизвестной длительности нет вовсе', () => {
    // У кандидата поиска строка пустует, пока не приехал круг деталей.
    expect(runtimeOf(null)).toBe('')
  })

  it('сериал склоняет оба числительных', () => {
    // «2 сезона, 24 серии» — оба числа приходят одним ответом.
    expect(seriesOf(2, 24)).toBe('2 сезона, 24 серии')
    expect(seriesOf(1, 8)).toBe('1 сезон, 8 серий')
    expect(seriesOf(5, 101)).toBe('5 сезонов, 101 серия')
  })

  it('склонение не путается на подвохах русского счёта', () => {
    // 11–14 идут по правилу «много», а не по последней цифре.
    expect(seriesOf(11, 12)).toBe('11 сезонов, 12 серий')
    expect(seriesOf(21, 22)).toBe('21 сезон, 22 серии')
  })

  it('без числа серий показывает только сезоны', () => {
    expect(seriesOf(3, null)).toBe('3 сезона')
    expect(seriesOf(null, null)).toBe('')
  })

  it('счёт открыт наружу и считает чужие слова тоже', () => {
    // Тем же правилом план 8 считает носителей тега: «3 фильма имеют этот тег».
    // Второго такого правила в проекте быть не должно.
    const film = ['фильм', 'фильма', 'фильмов']

    expect(plural(1, film)).toBe('фильм')
    expect(plural(3, film)).toBe('фильма')
    expect(plural(13, film)).toBe('фильмов')
    // Два трудных места русского счёта: четырнадцать идёт по правилу «много»
    // вопреки последней цифре, а круглый десяток — тоже, вопреки нулю.
    expect(plural(14, film)).toBe('фильмов')
    expect(plural(10, film)).toBe('фильмов')
  })

  it('состав берёт своих по роли, а не всех подряд', () => {
    // Роли лежат в одном списке, и путаница ролью показала бы режиссёра в
    // строке «В ролях».
    const credits = [
      { entity_id: 1, name: 'Дэвид Финчер', role: 'director', position: null },
      { entity_id: 2, name: 'Руни Мара', role: 'actor', position: 0 },
      { entity_id: 3, name: 'Дэниел Крейг', role: 'actor', position: 1 },
    ]

    expect(castOf(credits, 'director').map(named)).toEqual(['Дэвид Финчер'])
    expect(castOf(credits, 'actor').map(named))
      .toEqual(['Руни Мара', 'Дэниел Крейг'])
  })

  it('актёры идут по позиции в титрах, а не по тому, как легли в ответе', () => {
    // Топ-5 — это первые пять по `position`, и сортировка тут и есть смысл.
    const credits = [
      { entity_id: 3, name: 'Третий', role: 'actor', position: 2 },
      { entity_id: 1, name: 'Первый', role: 'actor', position: 0 },
      { entity_id: 2, name: 'Второй', role: 'actor', position: 1 },
    ]

    expect(castOf(credits, 'actor').map(named))
      .toEqual(['Первый', 'Второй', 'Третий'])
  })

  it('отдаёт титры целиком, а не одни имена', () => {
    // Клик по имени зовёт поиск по номеру строки человека: имя тёзку не
    // различает, и по нему звать было бы нечего.
    const credits = [{ entity_id: 9, name: 'Нолан', role: 'director' }]

    expect(castOf(credits, 'director')[0].entity_id).toBe(9)
  })

  it('показывает первых, а не последних', () => {
    // У сериала состав приезжает из aggregate_credits — у «Andor» это 302
    // человека, и вся лента превратилась бы в список имён. Длины тут мало:
    // срез с хвоста даёт ту же пятёрку, но из статистов вместо главных.
    const many = Array.from({ length: 20 }, (_, index) =>
      ({ entity_id: index, name: `Актёр ${index}`, role: 'actor',
         position: index }))

    expect(castOf(many, 'actor', 5).map(named))
      .toEqual(['Актёр 0', 'Актёр 1', 'Актёр 2', 'Актёр 3', 'Актёр 4'])
  })

  it('и по умолчанию тоже показывает первых пятерых', () => {
    // Забытый довод у актёров вывалил бы в ленту весь состав, и заметить это
    // было бы негде: у режиссёра и студий их всё равно единицы.
    const many = Array.from({ length: 20 }, (_, index) =>
      ({ entity_id: index, name: `Актёр ${index}`, role: 'actor',
         position: index }))

    expect(castOf(many, 'actor').map(named))
      .toEqual(['Актёр 0', 'Актёр 1', 'Актёр 2', 'Актёр 3', 'Актёр 4'])
  })
})
