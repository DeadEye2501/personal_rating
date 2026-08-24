import { describe, expect, it } from 'vitest'

import { EMPTY, chosen, cleared, cycled, forgotten, isEmpty, marked, passes,
  stateOf }
  from '$state/filters.js'

describe('строка фильтра', () => {
  it('перебирает три состояния по кругу', () => {
    const on = cycled(EMPTY, 'tags', 3)
    const excluded = cycled(on, 'tags', 3)
    const off = cycled(excluded, 'tags', 3)

    expect(chosen(on).tag_ids).toEqual([3])
    expect(chosen(excluded).excluded_tag_ids).toEqual([3])
    expect(isEmpty(off)).toBe(true)
  })

  it('исключённое перестаёт быть включённым', () => {
    // Строка не может быть и включена, и исключена разом: иначе запрос сложил
    // бы «покажи драмы» с «ни одной драмы» и вернул пустоту всегда.
    const excluded = cycled(cycled(EMPTY, 'genres', 7), 'genres', 7)

    expect(chosen(excluded).genre_ids).toEqual([])
    expect(chosen(excluded).excluded_genre_ids).toEqual([7])
  })

  it('разные признаки не мешают друг другу', () => {
    // Между признаками сложение по «и», и путаница полями дала бы тег в
    // жанрах — запрос при этом не упал бы, а просто вернул не то.
    const both = cycled(cycled(EMPTY, 'tags', 3), 'genres', 7)
    const request = chosen(both)

    expect(request.tag_ids).toEqual([3])
    expect(request.genre_ids).toEqual([7])
    expect(request.excluded_tag_ids).toEqual([])
  })

  it('складывает включённые внутри признака', () => {
    // Со сравнителем, а не без: `toSorted()` по умолчанию сортирует как
    // строки, и десятка встаёт перед девяткой.
    const two = cycled(cycled(EMPTY, 'scores', 9), 'scores', 10)
    expect(chosen(two).scores.toSorted((one, other) => one - other))
      .toEqual([9, 10])
  })

  it('пустой набор — это отсутствие фильтра, а не пустой признак', () => {
    // Спека: «страница шлёт только то, что человек тронул».
    expect(isEmpty(EMPTY)).toBe(true)
    expect(chosen(EMPTY)).toEqual({
      tag_ids: [], genre_ids: [], scores: [],
      visual: [], narrative: [], gameplay: [],
      excluded_tag_ids: [], excluded_genre_ids: [], excluded_scores: [],
      excluded_visual: [], excluded_narrative: [], excluded_gameplay: [],
    })
  })

  it('знает, что фильтр применён — по нему горит кнопка в шапке', () => {
    expect(isEmpty(cycled(EMPTY, 'tags', 3))).toBe(false)
  })

  it('кнопка горит и от одного исключённого, без единого включённого', () => {
    // «Всё, кроме ужасов» — законный отбор, и кнопка обязана гореть: иначе
    // лента отфильтрована, кнопка тёмная, и снять отбор человеку нечем.
    const noHorror = cycled(cycled(EMPTY, 'genres', 9), 'genres', 9)

    expect(chosen(noHorror).genre_ids).toEqual([])
    expect(isEmpty(noHorror)).toBe(false)
    expect(isEmpty(noHorror, 'genres')).toBe(false)
  })

  it('сброс признака убирает и включённое, и исключённое', () => {
    // Половину сброса не видно ниоткуда: включённое исчезло, кнопка погасла, а
    // исключённое молча продолжает резать выдачу.
    const mixed = cycled(cycled(cycled(EMPTY, 'tags', 3), 'tags', 5), 'tags', 5)
    expect(chosen(mixed).tag_ids).toEqual([3])
    expect(chosen(mixed).excluded_tag_ids).toEqual([5])

    const clean = cleared(mixed, 'tags')

    expect(chosen(clean).tag_ids).toEqual([])
    expect(chosen(clean).excluded_tag_ids).toEqual([])
  })

  it('исключённые оценки уезжают своим полем', () => {
    // Шестое поле запроса — единственное, которое ни один тест не наполнял:
    // перепутанное с соседним, оно вычло бы не оценки, а теги.
    const noThree = cycled(cycled(EMPTY, 'scores', 3), 'scores', 3)
    const request = chosen(noThree)

    expect(request.excluded_scores).toEqual([3])
    expect(request.excluded_tag_ids).toEqual([])
    expect(request.scores).toEqual([])
  })

  it('кнопка фильтра горит и гаснет за свой признак', () => {
    // Три кнопки, и каждая про своё: общая проверка сделала бы сочетание
    // «жанр и тег» недостижимым — сброс одного стирал бы второй.
    const tagged = cycled(EMPTY, 'tags', 3)

    expect(isEmpty(tagged, 'tags')).toBe(false)
    expect(isEmpty(tagged, 'genres')).toBe(true)

    const both = cycled(tagged, 'genres', 7)
    const left = cleared(both, 'genres')

    expect(isEmpty(left, 'genres')).toBe(true)
    expect(isEmpty(left, 'tags')).toBe(false)
  })
})

// Спросить источник с фильтром нечем: у TMDB и магазинов нет ни наших тегов,
// ни наших оценок. Ответ приходит целиком, и уже показанное отсеивается по тем
// же признакам, что и лента.
const view = (fields) => ({ genres: [], tags: [], rating: null, ...fields })

describe('отсев выдачи поиска', () => {
  it('без фильтра проходит всё', () => {
    expect(passes(view({}), EMPTY)).toBe(true)
  })

  it('жанр у кандидата есть, и по нему отсев работает', () => {
    // Жанры разворачиваются справочником прямо в выдаче — единственный признак
    // фильтра, который у кандидата вообще есть.
    const only = cycled(EMPTY, 'genres', 7)

    expect(passes(view({ genres: [{ id: 7 }] }), only)).toBe(true)
    expect(passes(view({ genres: [{ id: 9 }] }), only)).toBe(false)
  })

  it('внутри признака складывает по «и»', () => {
    // Решение пользователя 02.08.2026, и правило одно на обе стороны: в
    // разделах отбирает база, в поиске — эта функция. Разойдись они, две
    // выбранные метки давали бы в поиске один список, а в библиотеке другой.
    const two = cycled(cycled(EMPTY, 'genres', 7), 'genres', 9)

    expect(passes(view({ genres: [{ id: 7 }, { id: 9 }] }), two)).toBe(true)
    expect(passes(view({ genres: [{ id: 9 }] }), two)).toBe(false)
  })

  it('оценка остаётся «или», и не по решению, а по устройству', () => {
    // Она у карточки одна, и «семь и восемь разом» не бывает ни у чего: «и»
    // здесь опустошало бы выдачу всегда.
    const two = cycled(cycled(EMPTY, 'scores', 7), 'scores', 8)

    expect(passes(view({ rating: { score: 7.4 } }), two)).toBe(true)
    expect(passes(view({ rating: { score: 8 } }), two)).toBe(true)
    expect(passes(view({ rating: { score: 9 } }), two)).toBe(false)
  })

  it('исключение остаётся «ни одного из этих»', () => {
    // Не «нет всех сразу»: карточка с одним из двух исключённых жанров тоже
    // уходит.
    const neither = cycled(cycled(cycled(cycled(EMPTY, 'genres', 7), 'genres', 7),
                                  'genres', 9), 'genres', 9)

    expect(passes(view({ genres: [{ id: 7 }] }), neither)).toBe(false)
    expect(passes(view({ genres: [{ id: 5 }] }), neither)).toBe(true)
  })

  it('между признаками складывает по «и»', () => {
    const both = cycled(cycled(EMPTY, 'genres', 7), 'tags', 3)

    expect(passes(view({ genres: [{ id: 7 }], tags: [{ id: 3 }] }), both)).toBe(true)
    expect(passes(view({ genres: [{ id: 7 }], tags: [] }), both)).toBe(false)
  })

  it('исключает по каждому признаку, а не по одному жанру', () => {
    // Признак у исключения свой, и жёстко зашитые жанры оставили бы
    // исключённый тег с исключённой оценкой без действия — молча, потому что
    // выдача при этом остаётся законной.
    const noTag = cycled(cycled(EMPTY, 'tags', 3), 'tags', 3)
    const noSeven = cycled(cycled(EMPTY, 'scores', 7), 'scores', 7)

    expect(passes(view({ tags: [{ id: 3 }] }), noTag)).toBe(false)
    expect(passes(view({ tags: [{ id: 4 }] }), noTag)).toBe(true)
    expect(passes(view({ rating: { score: 7.4 } }), noSeven)).toBe(false)
    expect(passes(view({ rating: { score: 8 } }), noSeven)).toBe(true)
  })

  it('исключённое вычитается последним и сильнее включённого', () => {
    // «Показать всё, кроме ужасов» — частый запрос; «показать ужасы, которые я
    // же и исключил» смысла не имеет.
    const drama = cycled(EMPTY, 'genres', 7)
    const noHorror = cycled(cycled(drama, 'genres', 9), 'genres', 9)

    expect(passes(view({ genres: [{ id: 7 }, { id: 9 }] }), noHorror)).toBe(false)
  })

  it('фильтр по тегу прячет всё, чего ещё нет в библиотеке', () => {
    // У кандидата нет ни тегов, ни оценки: они держатся за `item_id`, а выдача
    // поиска в базу не попадает никогда.
    const tagged = cycled(EMPTY, 'tags', 3)
    expect(passes(view({ tags: [] }), tagged)).toBe(false)
  })

  it('фильтр по оценке смотрит на ближайшую ступень', () => {
    // Столбец у оценки тот же, что ступень на карточке: 7.33 — семёрка, 7.9 —
    // восьмёрка. Разойдись они, карточка, подписанная «хорошо», не находилась
    // бы фильтром «Хорошо».
    const seven = cycled(EMPTY, 'scores', 7)
    const eight = cycled(EMPTY, 'scores', 8)
    expect(passes(view({ rating: { score: 7.33 } }), seven)).toBe(true)
    expect(passes(view({ rating: { score: 7.9 } }), seven)).toBe(false)
    expect(passes(view({ rating: { score: 7.9 } }), eight)).toBe(true)
    expect(passes(view({ rating: null }), seven)).toBe(false)
  })
})

describe('метка на карточке', () => {
  it('переключает два состояния, а не три', () => {
    // Исключить с карточки нечем: третье состояние живёт только в модалке.
    const on = marked(EMPTY, 'genres', 7)
    expect(chosen(on).genre_ids).toEqual([7])

    const off = marked(on, 'genres', 7)
    expect(isEmpty(off)).toBe(true)
  })

  it('не проводит метку через исключение по дороге', () => {
    // Если бы клик по метке шёл тем же перебором, второе нажатие означало бы
    // «ни одного такого» — то есть скрывало бы карточку, с которой нажали.
    const twice = marked(marked(EMPTY, 'genres', 7), 'genres', 7)
    expect(chosen(twice).excluded_genre_ids).toEqual([])
  })

  it('снимает исключение, выставленное в модалке', () => {
    // Метка знает два состояния, и включённой она обязана стать из любого:
    // иначе исключённый в модалке жанр с карточки было бы не включить.
    const excluded = cycled(cycled(EMPTY, 'genres', 7), 'genres', 7)
    const on = marked(excluded, 'genres', 7)

    expect(chosen(on).genre_ids).toEqual([7])
    expect(chosen(on).excluded_genre_ids).toEqual([])
  })
})

describe('состояние строки в списке', () => {
  it('называет все три состояния перебора', () => {
    const on = cycled(EMPTY, 'genres', 7)
    const ex = cycled(on, 'genres', 7)

    expect(stateOf(EMPTY, 'genres', 7)).toBe('off')
    expect(stateOf(on, 'genres', 7)).toBe('on')
    expect(stateOf(ex, 'genres', 7)).toBe('ex')
  })

  it('спрашивает свой признак, а не любой', () => {
    // Списки жанров и тегов нумеруются порознь, и седьмой тег — не седьмой
    // жанр: спрошенное не по тому признаку показало бы чужую отметку.
    const tagged = cycled(EMPTY, 'tags', 7)

    expect(stateOf(tagged, 'genres', 7)).toBe('off')
  })
})

describe('забытая метка', () => {
  it('убирает метку из обеих половин признака', () => {
    // Тег удалили из набора: номер, оставшийся в фильтре, отбирал бы ленту по
    // мертвецу, и выключить его было бы нечем — строки-то больше нет.
    const on = cycled(EMPTY, 'tags', 3)
    const ex = cycled(cycled(on, 'tags', 5), 'tags', 5)
    const after = forgotten(forgotten(ex, 'tags', 3), 'tags', 5)

    expect(chosen(after).tag_ids).toEqual([])
    expect(chosen(after).excluded_tag_ids).toEqual([])
  })

  it('соседей по признаку не трогает', () => {
    const two = cycled(cycled(EMPTY, 'tags', 3), 'tags', 4)

    expect(chosen(forgotten(two, 'tags', 3)).tag_ids).toEqual([4])
  })

  it('метка с карточки тоже ставится в свой признак, а не в любой', () => {
    // Номера жанров и тегов независимы: третий тег — не третий жанр, и клик по
    // жанру не смеет включить одноимённый по номеру тег.
    const genre = marked(EMPTY, 'genres', 3)

    expect(chosen(genre).genre_ids).toEqual([3])
    expect(chosen(genre).tag_ids).toEqual([])
  })

  it('чужой признак не трогает вовсе', () => {
    // Номера жанров и тегов независимы: третий тег — не третий жанр.
    const both = cycled(cycled(EMPTY, 'tags', 3), 'genres', 3)

    expect(chosen(forgotten(both, 'tags', 3)).genre_ids).toEqual([3])
  })
})

describe('фильтр по шкалам игры', () => {
  it('шкала отбирает сама по себе, а не через общую оценку', () => {
    // У обеих игр среднее ровно три, и общей оценкой они неразличимы: подмена
    // шкалы на `score` прошла бы молча на любой другой паре.
    const fun = cycled(EMPTY, 'gameplay', 5)

    expect(chosen(fun).gameplay).toEqual([5])
    expect(passes(view({ rating: { score: 3, visual: 2, narrative: 2, gameplay: 5 } }), fun))
      .toBe(true)
    expect(passes(view({ rating: { score: 3, visual: 5, narrative: 2, gameplay: 2 } }), fun))
      .toBe(false)
  })

  it('внутри шкалы «или», между шкалами «и»', () => {
    // «Геймплей и нарратив равны 4 или 5» — это два условия, а не одно: со
    // «или» между шкалами отбор по паре расширял бы выдачу вместо сужения.
    const both = cycled(cycled(cycled(EMPTY, 'gameplay', 4), 'gameplay', 5),
                        'narrative', 5)

    expect(passes(view({ rating: { narrative: 5, gameplay: 4 } }), both)).toBe(true)
    expect(passes(view({ rating: { narrative: 5, gameplay: 2 } }), both)).toBe(false)
    expect(passes(view({ rating: { narrative: 2, gameplay: 5 } }), both)).toBe(false)
  })

  it('невыставленная шкала не проходит отбор ни по одной ступени', () => {
    // Среднее у такой игры считается по двум сторонам и равно пяти: отбор,
    // спутавший шкалу с общей оценкой, привёл бы её на «геймплей 5».
    const played = cycled(EMPTY, 'gameplay', 5)
    const untouched = { score: 5, visual: 5, narrative: 5, gameplay: null }

    expect(passes(view({ rating: untouched }), played)).toBe(false)
  })

  it('исключение по шкале невыставленную не задевает', () => {
    const notFive = cycled(cycled(EMPTY, 'gameplay', 5), 'gameplay', 5)

    expect(passes(view({ rating: { gameplay: 5 } }), notFive)).toBe(false)
    expect(passes(view({ rating: { gameplay: null } }), notFive)).toBe(true)
  })

  it('кнопка оценки горит и гаснет за все четыре колонки разом', () => {
    // Окно одно, значит и кнопка одна: выставленное в колонке шкалы иначе нечем
    // ни увидеть, ни снять — повторное нажатие по горящей кнопке гасит признак,
    // а модалку не открывает вовсе.
    const fun = cycled(EMPTY, 'gameplay', 5)

    expect(isEmpty(fun, 'scores')).toBe(false)
    expect(isEmpty(cleared(fun, 'scores'), 'scores')).toBe(true)
    expect(isEmpty(fun, 'tags')).toBe(true)
  })

  it('каждая шкала отсеивает по своей колонке', () => {
    // Средние у всех трёх карточек равны, так что общей оценкой они
    // неразличимы: подмена колонки на соседнюю прошла бы молча на паре.
    const cards = {
      visual: { score: 7 / 3, visual: 5, narrative: 1, gameplay: 1 },
      narrative: { score: 7 / 3, visual: 1, narrative: 5, gameplay: 1 },
      gameplay: { score: 7 / 3, visual: 1, narrative: 1, gameplay: 5 },
    }

    for (const key of Object.keys(cards)) {
      const only = cycled(EMPTY, key, 5)
      for (const [whose, rating] of Object.entries(cards)) {
        expect(passes(view({ rating }), only)).toBe(whose === key)
      }
    }
  })

  it('каждая шкала уезжает мосту своим полем, обеими половинами', () => {
    // Значения все разные нарочно: с одинаковыми перепутанные местами поля
    // неотличимы, и исключение вычитало бы по чужой шкале при зелёном наборе.
    const included = [['visual', 10], ['narrative', 9], ['gameplay', 8]]
    const excluded = [['visual', 1], ['narrative', 2], ['gameplay', 3]]
    let filters = EMPTY
    for (const [key, step] of included) filters = cycled(filters, key, step)
    for (const [key, step] of excluded) {
      filters = cycled(cycled(filters, key, step), key, step)
    }
    const request = chosen(filters)

    expect([request.visual, request.narrative, request.gameplay])
      .toEqual([[10], [9], [8]])
    expect([request.excluded_visual, request.excluded_narrative,
            request.excluded_gameplay]).toEqual([[1], [2], [3]])
  })

  it('гашение оценки не трогает чужие признаки', () => {
    // Кнопка ★ гасит четыре колонки, а не всё подряд: попади в её группу теги,
    // отбор по тегу пропадал бы вместе с оценкой — и молча.
    const both = cycled(cycled(EMPTY, 'gameplay', 5), 'tags', 3)
    const left = cleared(both, 'scores')

    expect(isEmpty(left, 'scores')).toBe(true)
    expect(chosen(left).tag_ids).toEqual([3])
  })
})
