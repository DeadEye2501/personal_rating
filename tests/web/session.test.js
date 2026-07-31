import { describe, expect, it } from 'vitest'

import { EMPTY, cycled, isEmpty } from '$state/filters.js'
import { newSession, withCollapsed, withKind, withSection } from '$state/session.js'

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
