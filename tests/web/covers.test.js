/** Адрес обложки: по номеру карточки и по адресу у источника. */

import { describe, expect, it } from 'vitest'

import { bySource, byItem } from '$state/covers.js'

describe('адрес обложки', () => {
  it('своя карточка спрашивается по номеру', () => {
    expect(byItem(12)).toBe('/poster?item=12')
  })

  it('у кандидата номера нет, и обложка идёт через источник', () => {
    // Кандидат в базу ещё не попал: спросить его обложку можно только тем, чем
    // он сам себя называет.
    expect(bySource('tmdb', 'https://i.tmdb/p/x.jpg'))
      .toBe('/poster?source=tmdb&url=https%3A%2F%2Fi.tmdb%2Fp%2Fx.jpg')
  })

  it('адрес источника уезжает закодированным целиком', () => {
    // В адресе обложки бывает и `&`, и `?`: подставленный как есть, он стал бы
    // вторым доводом ручки, и она получила бы обрезанный адрес.
    const asked = bySource('gog', 'https://x/y?a=1&b=2')

    expect(asked).toContain('%3Fa%3D1%26b%3D2')
    expect(asked.split('&')).toHaveLength(2)
  })
})
