import { describe, expect, it } from 'vitest'

import { stepOf } from '$state/scores.js'
import {
  inOrder, linkableOf, nameOf, pagesOf, shownValue, stepOfSource,
} from '$state/sources.js'

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

describe('порядок оценок в ряду', () => {
  it('один и тот же, каким бы ни был порядок прихода', () => {
    // Решено пользователем 02.08.2026: TMDB, IMDb, Кинопоиск, Metacritic,
    // Rotten Tomatoes. Раньше порядок выводился из объявлений оценочных
    // клиентов и ехал от их перестановки в сборке.
    expect(inOrder(['rotten', 'imdb', 'tmdb', 'metacritic', 'kinopoisk']))
      .toEqual(['tmdb', 'imdb', 'kinopoisk', 'metacritic', 'rotten'])
  })

  it('у игр свои источники, и магазин идёт впереди агрегатора', () => {
    // Список один на все семь, а карточка бывает либо кино, либо игрой:
    // столкнуться источникам негде.
    expect(inOrder(['metacritic', 'gog', 'steam']))
      .toEqual(['steam', 'gog', 'metacritic'])
  })

  it('незнакомый уходит в конец, не роняя остальных', () => {
    // Восьмой источник когда-нибудь появится, и до правки списка он обязан
    // просто показаться, а не пропасть и не встать в середину.
    expect(inOrder(['кто-то новый', 'imdb', 'tmdb']))
      .toEqual(['tmdb', 'imdb', 'кто-то новый'])
  })
})

describe('адрес страницы источника', () => {
  const view = (fields) => ({ source: 'tmdb', source_id: '157336',
                              kind: 'movie', external_ids: [], ...fields })

  it('собирает адрес там, где идентификатор хранится', () => {
    // Адрес целиком, а не по кусочку: перепутанный путь `/name/` вместо
    // `/title/` даёт живую ссылку в никуда, и видно это только там, куда
    // человек уже ушёл.
    const found = pagesOf(view({
      external_ids: [{ source: 'imdb', value: 'tt0816692' }],
    }))

    expect(found.get('imdb')).toBe('https://www.imdb.com/title/tt0816692/')
  })

  it('каждый источник ведёт на свой сайт', () => {
    const found = pagesOf(view({
      external_ids: [
        { source: 'imdb', value: 'tt0816692' },
        { source: 'kinopoisk', value: '258687' },
      ],
    }))

    expect(found.get('kinopoisk')).toBe('https://www.kinopoisk.ru/film/258687/')
  })

  it('у карточки из TMDB адрес собирается из неё самой', () => {
    // Номер TMDB не чужой: он собственный номер карточки, и в списке чужих
    // идентификаторов его нет вовсе. Отсюда и не было ссылки на основной для
    // нас источник.
    expect(pagesOf(view({})).get('tmdb'))
      .toBe('https://www.themoviedb.org/movie/157336')
  })

  it('у сериала путь другой, чем у фильма', () => {
    // У TMDB фильмы и сериалы нумеруются порознь, и номера пересекаются:
    // общий путь увёл бы на чужую карточку, а не в никуда.
    expect(pagesOf(view({ kind: 'series', source_id: '83867' })).get('tmdb'))
      .toBe('https://www.themoviedb.org/tv/83867')
  })

  it('у карточки из магазина адреса TMDB нет', () => {
    // Номер там свой, магазинный, и подставить его в адрес TMDB значит увести
    // человека на чужую карточку.
    const found = pagesOf(view({ source: 'steam', source_id: '292030',
                                 kind: 'game' }))

    expect(found.has('tmdb')).toBe(false)
  })

  it('молчит там, где идентификатора нет вовсе', () => {
    // У Rotten и Metacritic оценки приезжают внутри чужого ответа, своего
    // идентификатора мы не храним — и адреса у них нет.
    const found = pagesOf(view({
      source: 'steam', kind: 'game',
      external_ids: [{ source: 'rotten', value: 'что угодно' }],
    }))

    expect(found.has('rotten')).toBe(false)
    expect(found.size).toBe(0)
  })

  it('молчит и там, где идентификатор есть, а собрать из него нечего', () => {
    // У GOG в адресе стоит слаг, а хранится номер каталога. Сам номер при этом
    // настоящий и нужен — им спрашивают каталог.
    const found = pagesOf(view({
      source: 'steam', kind: 'game',
      external_ids: [{ source: 'gog', value: '1207658930' }],
    }))

    expect(found.has('gog')).toBe(false)
  })
})

describe('адрес в источник', () => {
  it('бывает только там, где источник есть', () => {
    // Клиент есть у каждого типа, и поле показывается всем. Набор при этом
    // остаётся: он сторожит тип, у которого источника нет, — такому полю
    // вставки ссылки показывать нечего, и отказ приходил бы на каждое нажатие
    // клавиши. Незнакомое имя в набор не входит и поля не получает.
    expect(linkableOf('movie')).toBe(true)
    expect(linkableOf('series')).toBe(true)
    expect(linkableOf('game')).toBe(true)
    expect(linkableOf('book')).toBe(true)
    expect(linkableOf('music')).toBe(true)
    expect(linkableOf('подкаст')).toBe(false)
  })
})
