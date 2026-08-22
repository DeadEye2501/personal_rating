/** Форма карточки: из каких полей она состоит у каждого типа содержимого. */

import { describe, expect, it } from 'vitest'

import { emptyCard, shownFor } from '$state/card.js'
import { ROLES } from '$state/credits.js'

const KINDS = ['movie', 'series', 'game', 'book', 'music']

// Пустым бывает и строкой, и списком: у полей ввода это `''` или `null`, у
// полей с подсказкой — набор, в котором пока никого.
const empty = (value) => Array.isArray(value) ? value.length === 0 : !value

// Что выбирают подсказкой, а не набирают: этим полям нужен именно список —
// пустая строка прошла бы проверку на пустоту, а поле на ней сломалось бы.
const PICKED = new Set([...ROLES.map((one) => one.role), 'genres'])

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

  it('название спрашивают у всех типов', () => {
    // Обязательно только оно: требовать год у короткометражки, которую помнишь
    // смутно, значит мешать.
    for (const kind of KINDS) expect(shownFor(kind)).toContain('title')
  })

  it('роли состава разные у разных типов', () => {
    // Режиссёр у фильма, шоураннер у сериала, разработчик с издателем у игры.
    // Актёры есть у кино и сериалов, а у игры состава не бывает вовсе.
    expect(shownFor('movie')).toContain('director')
    expect(shownFor('movie')).toContain('actor')
    expect(shownFor('series')).toContain('showrunner')
    expect(shownFor('series')).toContain('actor')
    expect(shownFor('game')).toContain('developer')
    expect(shownFor('game')).toContain('publisher')

    expect(shownFor('movie')).not.toContain('showrunner')
    expect(shownFor('movie')).not.toContain('developer')
    expect(shownFor('series')).not.toContain('director')
    expect(shownFor('series')).not.toContain('publisher')
    expect(shownFor('game')).not.toContain('actor')
    expect(shownFor('game')).not.toContain('director')
  })

  it('у каждой роли состава есть своё поле в форме', () => {
    // Роль, которую форма не показывает ни одному типу, не заполнить ничем —
    // а в базе она при этом остаётся, и карточка молча теряет своих людей.
    for (const one of ROLES) {
      const shows = KINDS.some((kind) => shownFor(kind).includes(one.role))
      expect(shows).toBe(true)
    }
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
        expect(empty(card[field])).toBe(true)
        if (PICKED.has(field)) expect(Array.isArray(card[field])).toBe(true)
      }
    }
  })
})
