import { describe, expect, it } from 'vitest'

import { stepOf } from '$state/scores.js'
import { nameOf, pagesOf, shownValue, stepOfSource } from '$state/sources.js'

describe('оценка агрегатора в строке', () => {
  it('десятибалльная всегда с десятой долей', () => {
    // «IMDb 8» рядом с «Кинопоиск 8.7» читается как другая шкала, а не как
    // круглая оценка.
    expect(shownValue(8, 'imdb')).toBe('8.0')
    expect(shownValue(8.7, 'kinopoisk')).toBe('8.7')
  })

  it('лишняя точность отрезается до десятой', () => {
    // У TMDB приезжает 8.483, и три знака после запятой читаются как чужая
    // точность, а не как оценка.
    expect(shownValue(8.483, 'imdb')).toBe('8.5')
  })

  it('у Rotten Tomatoes доля со знаком процента', () => {
    // У них это доля положительных рецензий, а не балл: «86» рядом с
    // «Metacritic 74» читается как оценка той же природы, хотя природа разная.
    expect(shownValue(86, 'rotten')).toBe('86%')
  })

  it('у TMDB она стобалльная и без дроби', () => {
    // Обе стороны пишут её сотней: своё `vote_average` клиент приводит, MDBList
    // отдаёт так сразу. Дробь здесь выдумывала бы точность чужой шкалы.
    expect(shownValue(88, 'tmdb')).toBe('88')
    expect(stepOfSource(88, 'tmdb')).toBe(9)
  })

  it('стобалльная и пятидесятибалльная — целыми', () => {
    // Проценты дробей не имеют: «Rotten Tomatoes 73.0» — это выдумка точности,
    // которой у источника нет.
    expect(shownValue(46, 'gog')).toBe('46')
    expect(shownValue(87.4, 'steam')).toBe('87')
  })
})

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
