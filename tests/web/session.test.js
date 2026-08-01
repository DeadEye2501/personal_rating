import { describe, expect, it } from 'vitest'

import { EMPTY, cycled, isEmpty } from '$state/filters.js'
import { newSession, withCollapsed, withKind, withNextSort, withSection, withToggledSection }
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
    // Наборы тегов у трёх типов независимы, а жанров наборов два — фильтр
    // после переключения указывал бы на строки, которых в новом наборе нет.
    const after = withKind(filtered(), 'game')

    expect(after.kind).toBe('game')
    expect(isEmpty(after.filters)).toBe(true)
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
