import { describe, expect, it } from 'vitest'

import { stepOf } from '$state/scores.js'
import { nameOf, pagesOf, stepOfSource } from '$state/sources.js'

describe('шкала источника', () => {
  it('у GOG она пятидесятибалльная, и 46 — девятая ступень', () => {
    // Литералом, а не сверкой с `stepOf(46, 50)`: та сравнивает реализацию с
    // собой и зеленеет даже при `gog: 5`, то есть ровно при той поломке, ради
    // которой написана.
    expect(stepOfSource(46, 'gog')).toBe(9)
    // Второе значение — не у потолка: на 46 в пятибалльной шкале выходит
    // десятка, а зажим прячет ошибку. На 39 прятать нечем.
    expect(stepOfSource(39, 'gog')).toBe(8)
  })

  it('у Steam и Metacritic она стобалльная', () => {
    // Подмена сотни десяткой делает шедевром каждую игру Steam: доля
    // положительных отзывов у них почти всегда выше десяти.
    expect(stepOfSource(87, 'steam')).toBe(9)
    expect(stepOfSource(87, 'metacritic')).toBe(9)
  })

  it('у IMDb и Кинопоиска она десятибалльная', () => {
    expect(stepOfSource(8.7, 'imdb')).toBe(9)
    expect(stepOfSource(8.7, 'kinopoisk')).toBe(9)
  })

  it('незнакомый источник считается десятибалльным', () => {
    // Молчать тут нельзя, а гадать не о чем: шкала 0–10 у трёх из семи.
    expect(stepOfSource(8.7, 'кто-то новый')).toBe(stepOf(8.7, 10))
  })
})

describe('имя источника', () => {
  it('пишется так, как пишет себя сам источник', () => {
    // Подпись рядом с цифрой — имя владельца оценки, а не наш ключ.
    expect(nameOf('imdb')).toBe('IMDb')
    expect(nameOf('rotten')).toBe('Rotten Tomatoes')
    expect(nameOf('kinopoisk')).toBe('Кинопоиск')
  })

  it('незнакомый показывается как есть', () => {
    // Пустая подпись хуже неказистой: цифра без имени не значит ничего.
    expect(nameOf('кто-то новый')).toBe('кто-то новый')
  })
})

describe('адрес страницы источника', () => {
  it('собирает адрес там, где идентификатор хранится', () => {
    // Адрес целиком, а не по кусочку: перепутанный путь `/name/` вместо
    // `/title/` даёт живую ссылку в никуда, и видно это только там, куда
    // человек уже ушёл.
    const found = pagesOf([{ source: 'imdb', value: 'tt0816692' }])

    expect(found.get('imdb')).toBe('https://www.imdb.com/title/tt0816692/')
  })

  it('каждый источник ведёт на свой сайт', () => {
    const found = pagesOf([
      { source: 'imdb', value: 'tt0816692' },
      { source: 'kinopoisk', value: '258687' },
    ])

    expect(found.get('kinopoisk')).toBe('https://www.kinopoisk.ru/film/258687/')
    expect(found.size).toBe(2)
  })

  it('молчит там, где идентификатора нет вовсе', () => {
    // У Rotten и Metacritic оценки приезжают внутри чужого ответа, своего
    // идентификатора мы не храним — и адреса у них нет.
    const found = pagesOf([{ source: 'rotten', value: 'что угодно' }])

    expect(found.has('rotten')).toBe(false)
    expect(found.size).toBe(0)
  })

  it('молчит и там, где идентификатор есть, а собрать из него нечего', () => {
    // У GOG в адресе стоит слаг, а хранится номер каталога. Сам номер при этом
    // настоящий и нужен — им спрашивают каталог.
    const found = pagesOf([{ source: 'gog', value: '1207658930' }])

    expect(found.has('gog')).toBe(false)
  })
})
