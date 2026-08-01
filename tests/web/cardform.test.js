/** Карточка, открытая на правку, становится формой. */

import { describe, expect, it } from 'vitest'

import { emptyCard, fieldsOf, formOf, wrongNumbers } from '$state/card.js'

const view = (extra = {}) => ({
  item_id: 7,
  kind: 'movie',
  title: 'Интерстеллар',
  original_title: 'Interstellar',
  year: 2014,
  synopsis: 'Про кукурузу и червоточину',
  runtime: 169,
  seasons_count: null,
  episodes_count: null,
  genres: [{ id: 3, name: 'Драма', kind: 'film' }],
  people: [{ entity_id: 1, name: 'Кристофер Нолан', role: 'director' },
           { entity_id: 2, name: 'Мэттью Макконахи', role: 'actor' },
           { entity_id: 5, name: 'Энн Хэтэуэй', role: 'actor' }],
  companies: [],
  ...extra,
})

describe('карточка в форму', () => {
  it('состав раскладывается по ролям, а не сваливается в кучу', () => {
    // Роль решает, в каком поле человек покажется; свалка означала бы, что
    // режиссёр приехал в актёры и уехал бы туда же при сохранении.
    const form = formOf(view())

    expect(form.director.map((one) => one.name)).toEqual(['Кристофер Нолан'])
    expect(form.actor.map((one) => one.name))
      .toEqual(['Мэттью Макконахи', 'Энн Хэтэуэй'])
  })

  it('человек несёт свой номер, а не одно имя', () => {
    // По номеру запись узнаёт, что человек уже есть. Потеряй его форма — при
    // каждом сохранении заводился бы новый тёзка.
    expect(formOf(view()).director[0].id).toBe(1)
  })

  it('студии не попадают к людям, а люди к студиям', () => {
    const form = formOf(view({
      kind: 'game',
      people: [],
      companies: [{ entity_id: 9, name: 'CD Projekt RED', role: 'developer' },
                  { entity_id: 10, name: 'Bandai', role: 'publisher' }],
    }))

    expect(form.developer.map((one) => one.name)).toEqual(['CD Projekt RED'])
    expect(form.publisher.map((one) => one.name)).toEqual(['Bandai'])
    expect(form.director).toEqual([])
  })

  it('жанры приезжают номером и именем', () => {
    // Именем их показывают, номером записывают: потеряй форма номер — записать
    // жанр стало бы нечем.
    expect(formOf(view()).genres).toEqual([{ id: 3, name: 'Драма' }])
  })

  it('номер карточки едет с формой', () => {
    // Он и отличает правку от заведения: без него «Сохранить» завело бы вторую
    // карточку вместо обновления первой.
    expect(formOf(view()).item_id).toBe(7)
  })

  it('незаполненное у карточки остаётся незаполненным в форме', () => {
    const form = formOf(view({ year: null, synopsis: '', runtime: null }))

    expect(form.year).toBeNull()
    expect(form.synopsis).toBe('')
    expect(form.runtime).toBeNull()
  })

  it('тип содержимого берётся у карточки, а не у вкладки', () => {
    // Тумблер мог переключиться, пока карточка лежала в списке; правя игру во
    // вкладке фильмов, форма обязана остаться игрой.
    expect(formOf(view({ kind: 'game' })).kind).toBe('game')
  })
})

describe('форма в поля базы', () => {
  it('незаполненное уезжает пустотой, а не пустой строкой', () => {
    // Мост отбрасывает `null` и оставляет полю умолчание, а пустую строку
    // доносит до базы как есть — в дате она стала бы отказом.
    const fields = fieldsOf({ ...emptyCard('movie'), title: 'Одиссея' })

    expect(fields.original_title).toBeNull()
    expect(fields.synopsis).toBeNull()
    expect(fields.year).toBeNull()
    expect(fields.runtime).toBeNull()
  })

  it('пробелы по краям срезаются', () => {
    const fields = fieldsOf({ ...emptyCard('movie'), title: '  Одиссея  ' })

    expect(fields.title).toBe('Одиссея')
  })

  it('поле из одних пробелов — это незаполненное', () => {
    const fields = fieldsOf({ ...emptyCard('movie'), title: 'Х',
                              original_title: '   ' })

    expect(fields.original_title).toBeNull()
  })

  it('числа уезжают числами, а не строками', () => {
    // Поле ввода отдаёт строку всегда: «2014» дошло бы до базы текстом, и
    // сортировка по году сравнивала бы его посимвольно.
    const fields = fieldsOf({ ...emptyCard('movie'), title: 'Х', year: '2014',
                             runtime: '169' })

    expect(fields.year).toBe(2014)
    expect(fields.runtime).toBe(169)
  })

  it('тип содержимого едет с полями', () => {
    expect(fieldsOf({ ...emptyCard('game'), title: 'Х' }).kind).toBe('game')
  })

  it('состав и жанры в поля карточки не попадают', () => {
    // Они пишутся своими вызовами и после карточки: уехав сюда, они стали бы
    // лишними доводами `new_manual_item` и уронили бы запись.
    const fields = fieldsOf(formOf(view()))

    expect(fields.genres).toBeUndefined()
    expect(fields.director).toBeUndefined()
    expect(fields.item_id).toBeUndefined()
  })
})

describe('число, которым оно не является', () => {
  it('опечатка в году названа, а не выброшена молча', () => {
    // Без этого «19о9» превращается в `NaN`, уезжает пустотой, и год просто
    // пропадает — человек узнаёт об этом, когда откроет карточку снова.
    expect(wrongNumbers({ ...emptyCard('movie'), year: '19о9' }))
      .toEqual(['year'])
  })

  it('пустое поле опечаткой не считается', () => {
    expect(wrongNumbers(emptyCard('movie'))).toEqual([])
  })

  it('целое число проходит', () => {
    expect(wrongNumbers({ ...emptyCard('series'), seasons_count: '2',
                          episodes_count: '24' })).toEqual([])
  })
})
