/** Что пропадёт вместе с карточкой. */

import { describe, expect, it } from 'vitest'

import { question, worn } from '$state/removal.js'

const nothing = { has_rating: false, has_review: false, tags: 0,
                  in_wishlist: false }

describe('фраза потери', () => {
  it('называет карточку по имени', () => {
    // Удаляют из ленты, где карточек много: без названия человек соглашается
    // вслепую.
    expect(question({ title: 'Одиссея' }, nothing)).toContain('Одиссея')
  })

  it('перечисляет только непустое', () => {
    // «Оценка и 3 тега пропадут вместе с ней» на карточке без оценки читается
    // как угроза потерять то, чего нет.
    const said = question({ title: 'Одиссея' }, nothing)

    expect(said).not.toContain('Оценка')
    expect(said).not.toContain('тег')
    expect(said).not.toContain('закладка')
  })

  it('склоняет число тегов', () => {
    const one = question({ title: 'Х' }, { ...nothing, tags: 1 })
    const few = question({ title: 'Х' }, { ...nothing, tags: 3 })
    const many = question({ title: 'Х' }, { ...nothing, tags: 5 })

    expect(one).toContain('1 тег')
    expect(few).toContain('3 тега')
    expect(many).toContain('5 тегов')
  })

  it('согласует глагол с числом того, что пропадёт', () => {
    // «Оценка пропадут вместе с ней» — то, что человек читает перед
    // необратимым, и читается оно как машинный текст.
    expect(question({ title: 'Х' }, { ...nothing, has_rating: true }))
      .toContain('Оценка пропадёт')
    expect(question({ title: 'Х' }, { ...nothing, tags: 1 })).toContain('1 тег пропадёт')
    expect(question({ title: 'Х' }, { ...nothing, tags: 3 })).toContain('3 тега пропадут')
    expect(question({ title: 'Х' }, { ...nothing, has_rating: true, in_wishlist: true }))
      .toContain('Оценка и закладка пропадут')
  })

  it('называет всё сразу, когда всё сразу и есть', () => {
    // Целиком, а не по кускам: запятая, союз перед последним, название и хвост
    // порознь наблюдаются, а вместе — нет, и разъехаться они могут молча.
    expect(question({ title: 'Одиссея' },
                { has_rating: true, has_review: true, tags: 2, in_wishlist: true }))
      .toBe('Удалить «Одиссея»? Оценка, рецензия, 2 тега и закладка'
            + ' пропадут вместе с ней.')
  })

  it('рецензию называет своим словом, а не оценкой', () => {
    // Живут они в одной строке базы, и слитые в одно «Оценка» соврали бы дважды:
    // обещали бы потерю того, чего нет, и умолчали бы о том, что пропадёт.
    const said = question({ title: 'Х' }, { ...nothing, has_review: true })

    expect(said).toContain('Рецензия пропадёт')
    expect(said).not.toContain('Оценка')
  })

  it('согласует глагол с формой числительного, а не с его величиной', () => {
    // «21 тег пропадут» — то же машинное чтение, что и «Оценка пропадут»:
    // двадцать один больше единицы, а по-русски он единственного числа.
    expect(question({ title: 'Х' }, { ...nothing, tags: 21 }))
      .toContain('21 тег пропадёт')
    expect(question({ title: 'Х' }, { ...nothing, tags: 11 }))
      .toContain('11 тегов пропадут')
  })

  it('оценку называет и без тегов, и без закладки', () => {
    // Три признака независимы: связанные по ошибке, они молчали бы поодиночке.
    const said = question({ title: 'Х' }, { ...nothing, has_rating: true })

    expect(said).toContain('Оценка')
    expect(said).not.toContain('тег')
    expect(said).not.toContain('закладка')
  })

  it('закладку называет и без оценки', () => {
    const said = question({ title: 'Х' }, { ...nothing, in_wishlist: true })

    // С прописной: перечисление начинает новое предложение, и первым в нём
    // стоит она. Прежде на этом месте была строчная — вопрос читался как
    // оборванный.
    expect(said).toContain('Закладка пропадёт')
    expect(said).not.toContain('Оценка')
  })
})

describe('фраза удаления тега', () => {
  it('склоняет и носителей, и глагол при них', () => {
    // Носители называются по открытой вкладке: у тега свой набор на каждый тип
    // содержимого, и «3 игры имеют этот тег» во вкладке фильмов было бы ложью.
    expect(worn('Ужасы', 1, 'movie')).toBe('Удалить тег «Ужасы»? 1 фильм имеет этот тег.')
    expect(worn('Ужасы', 3, 'series'))
      .toBe('Удалить тег «Ужасы»? 3 сериала имеют этот тег.')
    expect(worn('Ужасы', 5, 'game')).toBe('Удалить тег «Ужасы»? 5 игр имеют этот тег.')
  })
})
