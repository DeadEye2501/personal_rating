/** Форма карточки: из каких полей она состоит у каждого типа содержимого. */

import { describe, expect, it } from 'vitest'

import { emptyCard, shownFor } from '$state/card.js'

const KINDS = ['movie', 'series', 'game']

describe('форма карточки', () => {
  it('у фильма длительность, а сезонов нет', () => {
    const shown = shownFor('movie')
    expect(shown).toContain('runtime')
    expect(shown).not.toContain('seasons_count')
  })

  it('у сериала сезоны и серии вместо длительности', () => {
    const shown = shownFor('series')
    expect(shown).toContain('seasons_count')
    expect(shown).toContain('episodes_count')
    expect(shown).not.toContain('runtime')
  })

  it('у игры ни того, ни другого', () => {
    // Сезонов у неё нет, а поля времени прохождения убраны из модели: их не
    // отдавал ни один источник, а вбивать такое руками никто не станет.
    const shown = shownFor('game')
    expect(shown).not.toContain('runtime')
    expect(shown).not.toContain('seasons_count')
    expect(shown).not.toContain('episodes_count')
  })

  it('название спрашивают у всех трёх типов', () => {
    // Обязательно только оно: требовать год у короткометражки, которую помнишь
    // смутно, значит мешать.
    for (const kind of KINDS) expect(shownFor(kind)).toContain('title')
  })

  it('у каждого показанного поля есть свой ключ, и он пуст', () => {
    // Показанное без ключа Svelte не свяжет: `bind:value` на `undefined` молча
    // ничего не делает, и набранное уходило бы в никуда. Непустое же значение
    // означало бы, что новая карточка открывается уже заполненной.
    for (const kind of KINDS) {
      const card = emptyCard(kind)
      expect(card.kind).toBe(kind)

      for (const field of shownFor(kind)) {
        expect(Object.hasOwn(card, field)).toBe(true)
        expect(card[field]).toBeFalsy()
      }
    }
  })
})
