import { describe, expect, it } from 'vitest'

import { EMPTY, chosen, cycled, isEmpty } from '$state/filters.js'
import { collapsedOf, flipped, newSession, swept, withClearedFilter,
  withCollapsed, withFilters,
  withForgotten, withKind, withMark, withNextSort, withSection,
  withToggledSection }
  from '$state/session.js'

const filtered = () => ({ ...newSession(), filters: cycled(EMPTY, 'tags', 3) })

describe('состояние приложения', () => {
  it('открывается на поиске, на фильмах и ничем не стеснённым', () => {
    // При запуске карточек нет, и первый раздел — поиск. Остальные три поля
    // проверяются здесь же: дальше их перезаписывают помощники, и подменённое
    // объявление — свёрнутая шапка при старте, выставленный фильтр — прошло бы
    // молча.
    const session = newSession()

    expect(session.section).toBe('search')
    expect(session.kind).toBe('movie')
    expect(isEmpty(session.filters)).toBe(true)
    expect(session.sort).toBe(null)
    expect(session.collapsed).toBe(false)
  })

  it('смена типа сбрасывает все фильтры', () => {
    // Наборы тегов у типов независимы, а наборов жанров меньше, чем типов, —
    // фильтр после переключения указывал бы на строки, которых в новом наборе
    // нет.
    // Раздел берётся непустой нарочно: на стартовом «поиске» унесённый раздел
    // был бы неотличим от оставленного.
    const after = withKind({ ...filtered(), section: 'rated' }, 'game')

    expect(after.kind).toBe('game')
    expect(isEmpty(after.filters)).toBe(true)
    // И только фильтры: вкладка первична, но уносить с собой открытый раздел
    // она не вправе.
    expect(after.section).toBe('rated')
  })

  it('смена типа на тот же самый ничего не сбрасывает', () => {
    // Щелчок по уже включённой кнопке — не смена, и терять из-за него
    // выставленный фильтр человек не согласится.
    const before = filtered()
    expect(withKind(before, before.kind)).toBe(before)
  })

  it('смена раздела фильтры не трогает', () => {
    // Иначе отфильтрованную гистограмму не увидеть никогда.
    const after = withSection(filtered(), 'stats')

    expect(after.section).toBe('stats')
    expect(isEmpty(after.filters)).toBe(false)
  })

  it('свёрнутость переживает смену раздела', () => {
    // Это тумблер всего приложения, а не настройка раздела.
    const collapsed = withCollapsed(newSession(), true)
    expect(withSection(collapsed, 'wishlist').collapsed).toBe(true)
  })

  it('свёрнутость переживает и смену типа', () => {
    const collapsed = withCollapsed(newSession(), true)
    expect(withKind(collapsed, 'series').collapsed).toBe(true)
  })

  it('сортировка живёт сеанс раздела', () => {
    // Ушёл с раздела — переключатель вернулся к порядку по умолчанию.
    const touched = { ...newSession(), section: 'wishlist', sort: 5 }
    expect(withSection(touched, 'rated').sort).toBe(null)
  })
})

describe('клик по метке на карточке', () => {
  it('включает фильтр по ней, повторный выключает', () => {
    const on = withMark(newSession(), 'genres', 7)
    expect(isEmpty(on.filters, 'genres')).toBe(false)

    expect(isEmpty(withMark(on, 'genres', 7).filters)).toBe(true)
  })

  it('ничего, кроме фильтров, не трогает', () => {
    // Считанный в разметке, этот переход молча терял бы раздел или свёрнутость:
    // там его не сторожит ничто.
    const before = { ...newSession(), section: 'rated', collapsed: true,
                     sort: 3 }
    const after = withMark(before, 'tags', 3)

    expect(after.section).toBe('rated')
    expect(after.collapsed).toBe(true)
    expect(after.sort).toBe(3)
    expect(after.kind).toBe(before.kind)
  })
})

describe('повторный щелчок по разделу', () => {
  it('возвращает поиск, а не оставляет раздел включённым', () => {
    // Раздел — это подмена содержимого, а не переключатель с залипанием, и
    // отдельной кнопки «обратно» под него нет.
    const rated = withToggledSection(newSession(), 'rated')
    expect(rated.section).toBe('rated')

    expect(withToggledSection(rated, 'rated').section).toBe('search')
  })

  it('щелчок по другому разделу просто переводит в него', () => {
    const rated = withToggledSection(newSession(), 'rated')
    expect(withToggledSection(rated, 'stats').section).toBe('stats')
  })

  it('возврат в поиск тоже сбрасывает переключатель', () => {
    // Иначе позиция пережила бы уход и вернулась бы в раздел чужой.
    const touched = { ...newSession(), section: 'wishlist', sort: 3 }
    expect(withToggledSection(touched, 'wishlist').sort).toBe(null)
  })
})

describe('переключатель сортировки в состоянии', () => {
  it('двигает позицию по кругу своего раздела', () => {
    const rated = { ...newSession(), section: 'rated' }

    expect(withNextSort(rated).sort).toBe(1)
    expect(withNextSort(withNextSort(rated)).sort).toBe(2)
  })

  it('нетронутый переключатель двигается с первого состояния', () => {
    // `sort: null` — стартовое значение раздела, и первый щелчок обязан вести
    // во второе состояние, а не в никуда.
    const wishlist = { ...newSession(), section: 'wishlist' }
    expect(wishlist.sort).toBe(null)
    expect(withNextSort(wishlist).sort).toBe(1)
  })

  it('замыкается по набору своего раздела', () => {
    // В отложенном круг вчетверо короче, чем в оценённых.
    let session = { ...newSession(), section: 'wishlist' }
    for (let step = 0; step < 4; step += 1) session = withNextSort(session)
    expect(session.sort).toBe(0)
  })

  it('ничего, кроме позиции, не трогает', () => {
    const before = { ...filtered(), section: 'rated', collapsed: true }
    const after = withNextSort(before)

    expect(after.kind).toBe(before.kind)
    expect(after.section).toBe(before.section)
    expect(after.collapsed).toBe(true)
    expect(after.filters).toBe(before.filters)
  })
})

describe('фильтры сеанса', () => {
  it('гасит названный признак и не трогает соседний', () => {
    // Кнопка фильтра гасит свой отбор: сбрасывая заодно чужой, «Жанры» стирали
    // бы теговый, которого человек не трогал.
    const both = cycled(cycled(EMPTY, 'genres', 7), 'tags', 3)
    const after = withClearedFilter({ ...newSession(), filters: both }, 'genres')

    expect(chosen(after.filters).genre_ids).toEqual([])
    expect(chosen(after.filters).tag_ids).toEqual([3])
  })

  it('кладёт готовые фильтры и ничего, кроме них, не трогает', () => {
    const before = { ...newSession(), section: 'rated', collapsed: true, sort: 2 }
    const after = withFilters(before, cycled(EMPTY, 'scores', 9))

    expect(chosen(after.filters).scores).toEqual([9])
    expect(after.section).toBe('rated')
    expect(after.collapsed).toBe(true)
    expect(after.sort).toBe(2)
  })
})

describe('удалённый тег', () => {
  it('уходит из фильтров сеанса', () => {
    const session = { ...newSession(), filters: cycled(EMPTY, 'tags', 3) }

    expect(chosen(withForgotten(session, 'tags', 3).filters).tag_ids).toEqual([])
  })

  it('уносит только себя, а не весь признак', () => {
    // Иначе удаление одного тега гасило бы отбор по соседям, которых человек не
    // трогал: это `cleared`, а не забвение.
    const two = cycled(cycled(EMPTY, 'tags', 3), 'tags', 4)
    const after = withForgotten({ ...newSession(), filters: two }, 'tags', 3)

    expect(chosen(after.filters).tag_ids).toEqual([4])
  })

  it('исключённый не становится включённым', () => {
    // Под `marked` удалённая метка перешла бы во включённые, и лента
    // отбиралась бы по мертвецу — а выключить его нечем, строки уже нет.
    const excluded = cycled(cycled(EMPTY, 'tags', 3), 'tags', 3)
    const after = withForgotten({ ...newSession(), filters: excluded }, 'tags', 3)

    expect(chosen(after.filters).tag_ids).toEqual([])
    expect(chosen(after.filters).excluded_tag_ids).toEqual([])
  })
})

describe('переходы оставляют сеанс сеансом', () => {
  // Снятый спред уносит всё, чего переход не касается: тип, раздел, сортировку,
  // свёрнутость, фильтры. Сторож семейный нарочно — у семьи он либо есть у
  // всех, либо не значит ничего: разъезжается он молча, и находили это дважды,
  // оба раза ревью, а не прогоном.
  const full = () => ({ ...newSession(), kind: 'game', section: 'rated',
                        sort: 3, collapsed: true,
                        filters: cycled(EMPTY, 'tags', 3) })

  it('withCollapsed не трогает ничего, кроме свёрнутости', () => {
    // Своим случаем, а не в общем переборе: у остальных проверяется всё, кроме
    // фильтров, а этот меняет как раз не их — и фильтры обязан сохранить.
    const after = withCollapsed(full(), false)

    expect([after.kind, after.section, after.sort]).toEqual(['game', 'rated', 3])
    expect(after.filters).toEqual(cycled(EMPTY, 'tags', 3))
    expect(after.collapsed).toBe(false)
  })

  it('withSection не трогает ничего, кроме раздела и сортировки', () => {
    // Сортировку сбрасывает нарочно: круг состояний у разделов разный. А тип,
    // свёрнутость и фильтры к разделу отношения не имеют — отфильтрованную
    // гистограмму иначе не увидеть никогда.
    const after = withSection(full(), 'wishlist')

    expect([after.kind, after.collapsed]).toEqual(['game', true])
    expect(after.filters).toEqual(cycled(EMPTY, 'tags', 3))
    expect([after.section, after.sort]).toEqual(['wishlist', null])
  })

  it('withKind не трогает ничего, кроме типа и фильтров', () => {
    // Фильтры сбрасывает нарочно: наборы тегов у типов независимы. А
    // раздел, сортировка и свёрнутость к типу отношения не имеют.
    const after = withKind(full(), 'series')

    expect([after.section, after.sort, after.collapsed])
      .toEqual(['rated', 3, true])
    expect([after.kind, after.filters]).toEqual(['series', EMPTY])
  })

  for (const [name, run] of [
    ['withClearedFilter', (one) => withClearedFilter(one, 'tags')],
    ['withForgotten', (one) => withForgotten(one, 'tags', 3)],
  ]) {
    it(`${name} не трогает ничего, кроме фильтров`, () => {
      const after = run(full())

      expect([after.kind, after.section, after.sort, after.collapsed])
        .toEqual(['game', 'rated', 3, true])
    })
  }
})

describe('свёрнутость карточки', () => {
  it('своё сильнее общего в обе стороны', () => {
    // Тумблер шапки — состояние всего приложения, шеврон карточки — её
    // собственное. Поменяй их местами, и шеврон перестанет значить что-либо:
    // общее значение всегда булево, то есть всегда «сказано».
    expect(collapsedOf({ collapsed: true }, false)).toBe(true)
    expect(collapsedOf({ collapsed: false }, true)).toBe(false)
  })

  it('нетронутая карточка слушается тумблера', () => {
    expect(collapsedOf({ collapsed: null }, true)).toBe(true)
    expect(collapsedOf({}, false)).toBe(false)
  })
})

describe('нажатие тумблера шапки', () => {
  it('забирает власть у строки, тронутой шевроном', () => {
    // Без этого «своё сильнее общего» становится «своё сильнее общего
    // навсегда»: первый же щелчок по шеврону уводил карточку из-под тумблера
    // до самого перечитывания ленты.
    const touched = { item_id: 1, ...flipped({ item_id: 1 }, false) }
    const [after] = swept([touched], false)

    expect(collapsedOf(after, false)).toBe(false)
  })

  it('и шеврон снова волен с ним спорить', () => {
    // Порядок такой: тумблер задаёт всем, шеврон спорит у одной строки,
    // следующее нажатие тумблера снова забирает власть.
    const [after] = swept([{ item_id: 1, collapsed: true }], false)

    expect(flipped(after, false)).toEqual({ collapsed: true })
  })

  it('ничего, кроме свёрнутости, в строке не трогает', () => {
    // Строка ленты — это вся карточка целиком: снятый спред унёс бы и оценку,
    // и метки, и постер, а увидеть это можно только глазами на живом окне.
    const rows = swept([{ item_id: 7, title: 'Дюна', collapsed: true }], false)

    expect(rows).toEqual([{ item_id: 7, title: 'Дюна', collapsed: false }])
  })
})

describe('свёрнутость строки', () => {
  it('переворачивает своё, когда своё есть', () => {
    expect(flipped({ collapsed: true }, false)).toEqual({ collapsed: false })
    expect(flipped({ collapsed: false }, true)).toEqual({ collapsed: true })
  })

  it('без своего отталкивается от общего', () => {
    // Первый щелчок по шеврону обязан спорить с тумблером шапки, а не
    // повторять его: своё сильнее общего.
    expect(flipped({}, true)).toEqual({ collapsed: false })
    expect(flipped({}, false)).toEqual({ collapsed: true })
  })
})
