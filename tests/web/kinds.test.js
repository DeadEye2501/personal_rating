/** Как тип содержимого называется человеку: склонение и глагол второго раздела. */

import { describe, expect, it } from 'vitest'

import { NOUNS, squareOf, wishOf } from '$state/kinds.js'

describe('подписи типа содержимого', () => {
  it('второй раздел называется своим глаголом у каждого типа', () => {
    // Раздел в базе один, `wishlist`, — своё у каждого типа только слово.
    // Читателей у таблицы двое, шапка и кнопка закладки на карточке, и
    // разъехаться им нельзя.
    expect(wishOf('movie')).toBe('Хочу посмотреть')
    expect(wishOf('series')).toBe('Хочу посмотреть')
    expect(wishOf('game')).toBe('Хочу поиграть')
    expect(wishOf('book')).toBe('Хочу прочитать')
    expect(wishOf('music')).toBe('Хочу послушать')
  })

  it('глагол есть у каждого типа, который умеет склоняться', () => {
    // Привязка выводится, а не переписывается списком: список в тесте
    // расходится не с ожидаемым, а с самим собой. Пропущенный тип роняет
    // подпись кнопки в `undefined` — молча, потому что рисуется она как есть.
    for (const kind of Object.keys(NOUNS)) {
      expect(typeof wishOf(kind), kind).toBe('string')
    }
  })
})

describe('форма обложки', () => {
  it('квадратная только у альбома', () => {
    // Значением, а не набором ключей: сторож границы в питоне собирает ключи
    // таблицы, и `{ music: false }` его не роняет — а рамка при этом
    // становится афишной у всех альбомов сразу.
    expect(squareOf('music')).toBe(true)
    expect(squareOf('movie')).toBe(false)
    expect(squareOf('series')).toBe(false)
    expect(squareOf('game')).toBe(false)
    expect(squareOf('book')).toBe(false)
  })

  it('незнакомый тип получает афишу, а не квадрат', () => {
    // Умолчание названо: рамка рисуется и до того, как тип доедет, — у
    // кандидата выдачи и у подсказки он бывает пустым.
    expect(squareOf('')).toBe(false)
    expect(squareOf(undefined)).toBe(false)
  })
})
