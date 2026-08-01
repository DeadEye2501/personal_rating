import { describe, expect, it } from 'vitest'

import { EMPTY, cycled } from '$state/filters.js'
import { requestOf } from '$state/section.js'
import { newSession } from '$state/session.js'

describe('запрос раздела', () => {
  it('несёт раздел и тип содержимого', () => {
    const asked = requestOf({ ...newSession(), section: 'wishlist',
                              kind: 'game' })

    expect(asked.section).toBe('wishlist')
    expect(asked.kind).toBe('game')
  })

  it('раскладывает фильтры так, как их ждёт мост', () => {
    // Шесть кортежей, и имена полей — контракт: мост кладёт их прямо в
    // `Filters`, а не разбирает по-своему.
    // Раздел непременно библиотечный: запрос строится только для тех двух, что
    // спрашивают базу, — у поиска и статистики ни порядка, ни страницы нет.
    const session = { ...newSession(), section: 'rated',
                      filters: cycled(EMPTY, 'tags', 3) }
    const asked = requestOf(session)

    expect(asked.filters.tag_ids).toEqual([3])
    expect(asked.filters.excluded_tag_ids).toEqual([])
  })

  it('нетронутый переключатель — первое состояние своего набора', () => {
    // В отложенном свежие сверху, в оценённых высокие: наборы разные, и
    // позиция 0 означает в них разное.
    const wished = requestOf({ ...newSession(), section: 'wishlist' })
    const rated = requestOf({ ...newSession(), section: 'rated' })

    expect(wished.order.key).toBe('added_at')
    expect(rated.order.key).toBe('score')
  })

  it('тронутый переключатель уезжает своей позицией', () => {
    // Иначе порядок в запросе всегда был бы первым, а кнопка перебирала бы
    // состояния вхолостую.
    const asked = requestOf({ ...newSession(), section: 'rated', sort: 1 })

    expect(asked.order).toEqual({ key: 'score', descending: false })
  })
})
