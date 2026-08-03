import { afterEach, describe, expect, it } from 'vitest'

import { ASPECTS, average, colorOf, labelOf, meanOf, partOf, scale, setScale,
  sourceColorOf, stepOf, toneOf, verdictOf } from '$state/scores.js'

describe('нотация оценок', () => {
  it('десять ступеней, и ни одна не повторяется', () => {
    const colours = Array.from({ length: 10 }, (_, index) => colorOf(index + 1))
    expect(new Set(colours).size).toBe(10)
  })

  it('цвет ступени зовётся так же, как переменная палитры', () => {
    // Имя собирается строкой, и разъехавшись с палитрой оно даёт не отказ, а
    // цифру без цвета: неопределённая переменная просто ничего не красит.
    expect(colorOf(7)).toBe('var(--score-7)')
    expect(colorOf(10)).toBe('var(--score-10)')
  })

  it('приводит чужую шкалу к десяти', () => {
    // У агрегаторов шкалы разные: 0–10 у IMDb, 0–100 у Metacritic. Цвет обязан
    // браться из той же нотации, что и своя оценка.
    expect(stepOf(8.7, 10)).toBe(9)
    expect(stepOf(87, 100)).toBe(9)
  })

  it('ступень берётся ближайшая, а не следующая вверх', () => {
    // Округление вверх сдвинуло бы всю чужую шкалу: десятая доставалась бы
    // всему выше девяноста процентов, тогда как своя десятка — ровно десять.
    expect(stepOf(9.2, 10)).toBe(9)
    expect(stepOf(6.1, 10)).toBe(6)
    expect(stepOf(10, 10)).toBe(10)
  })

  it('зажимает выход за границы шкалы', () => {
    // Чужой ответ бывает и нулём, и больше максимума: ступень 0 или 11 дала бы
    // `var(--score-0)`, то есть отсутствие цвета и невидимую цифру.
    expect(stepOf(0, 10)).toBe(1)
    expect(stepOf(-3, 10)).toBe(1)
    expect(stepOf(140, 100)).toBe(10)
  })

  it('ярлык следует оценке', () => {
    // Литералом, а не через `LABELS[10]`: сверка таблицы с собой переживает
    // любую перестановку её же значений.
    expect(verdictOf(10)).toBe('Шедевр')
    expect(verdictOf(7)).toBe('Интересно')
    expect(verdictOf(1)).toBe('Отвратительно')
    expect(scale()).toHaveLength(10)
  })

  it('дробная оценка берёт ярлык по целой части', () => {
    // У игры оценка — среднее трёх шкал. Проба выше половины нарочно: на 7.33
    // округление к ближайшему дало бы ту же семёрку, и подмена прошла бы
    // незамеченной.
    expect(verdictOf(7.33)).toBe('Интересно')
    expect(verdictOf(7.67)).toBe('Интересно')
  })

  it('снятая оценка не имеет ярлыка', () => {
    // Карточка остаётся, а вердикт исчезает: сказать о ней нечего.
    expect(verdictOf(null)).toBe('')
    expect(verdictOf(0)).toBe('')
  })

  it('среднее считается по выставленным шкалам, а не по трём всегда', () => {
    // Инвариант держит приложение: у игры может быть заполнена одна шкала из
    // трёх, и делить на три значило бы занизить втрое.
    expect(average([8, 7, 7])).toBeCloseTo(7.333, 3)
    expect(average([9, null, null])).toBe(9)
    expect(average([null, null, null])).toBe(null)
  })

  it('ноль в шкале — это оценка, а не пустое место', () => {
    // Ноль ложный, и отброшенный вместе с пустотой он поднял бы среднее.
    expect(average([0, 10])).toBe(5)
  })

  it('у кино оценка своя, у игры — среднее сторон', () => {
    // Одна функция на оба случая: карточка не должна знать, что у игры их три.
    expect(meanOf({ score: 8 }, 'movie')).toBe(8)
    expect(meanOf({ score: 8 }, 'series')).toBe(8)
    expect(meanOf({ visual: 8, narrative: 7, gameplay: 7 }, 'game'))
      .toBeCloseTo(7.333, 3)
  })

  it('у игры считаются выставленные стороны, а не поле оценки', () => {
    // База кладёт среднее в `score` сама, но приезжает оно позже нажатия. Взяв
    // его, число под ползунками не менялось бы до ответа.
    expect(meanOf({ score: 3, visual: 9, narrative: null, gameplay: null },
                  'game')).toBe(9)
  })

  it('неоценённое не имеет числа ни у кино, ни у игры', () => {
    expect(meanOf(null, 'movie')).toBe(null)
    expect(meanOf(null, 'game')).toBe(null)
    expect(meanOf({ visual: null, narrative: null, gameplay: null }, 'game'))
      .toBe(null)
  })

  it('сторон у игры три, и ключи у них те же, что в базе', () => {
    expect(ASPECTS.map((one) => one.key))
      .toEqual(['visual', 'narrative', 'gameplay'])
  })

  it('цвет своей оценки берётся по целой части', () => {
    // Ярлык и цифра красятся одним и тем же: разъехавшись, они дали бы
    // «Интересно» восьмой ступенью.
    expect(toneOf(7.9)).toBe(colorOf(7))
    expect(toneOf(10)).toBe(colorOf(10))
  })

  it('у снятой оценки цвет всё равно есть', () => {
    // Неопределённая переменная не красит ничем, и ярлык — пустой строкой —
    // пропал бы вместе с ней, а с ним и место под него.
    expect(toneOf(null)).toBe(colorOf(1))
    expect(toneOf(0)).toBe(colorOf(1))
  })

  it('доля дробной звезды — остаток, а не сама оценка', () => {
    // Закрашенная часть лежит поверх контурной и обрезается по ширине: ошибка
    // здесь красит целую звезду вместо трети. Проба выше половины — по той же
    // причине, что и у ярлыка.
    expect(partOf(7.33)).toBeCloseTo(0.33, 2)
    expect(partOf(7.67)).toBeCloseTo(0.67, 2)
    expect(partOf(7)).toBe(0)
  })
})

describe('ступени шкалы', () => {
  afterEach(() => setScale(10))

  it('начинаются с первой, а не с нулевой', () => {
    // Нулевая ступень — это `var(--score-0)`, которого в палитре нет вовсе:
    // первая звезда покрасилась бы ничем, а ярлыка у неё не нашлось бы.
    expect(scale().map(colorOf)).not.toContain('var(--score-0)')
    expect(scale().every((step) => labelOf(step))).toBe(true)
  })

  it('у каждой ступени обеих шкал есть и ярлык, и цвет', () => {
    // Разойдясь с ярлыками, шкала дала бы звезду без подписи или подпись без
    // звезды: перебирают их порознь ряд звёзд и список фильтра. Ряд цветов
    // короче ступеней даёт `var(--score-undefined)` — то есть цифру без цвета,
    // и молча.
    for (const steps of [10, 5]) {
      setScale(steps)

      expect(scale().every((step) => labelOf(step))).toBe(true)
      expect(scale().map(colorOf)).not.toContain('var(--score-undefined)')
      expect(labelOf(steps + 1)).toBe('')
    }
  })
})

describe('две шкалы', () => {
  afterEach(() => setScale(10))

  it('на пяти ступенях свои ярлыки и свои цвета', () => {
    // Своих цветов у пятёрки нет: она берёт пять из тех же десяти, и таблица
    // взята из спеки, а не выведена делением.
    setScale(5)

    expect(scale()).toEqual([1, 2, 3, 4, 5])
    expect(labelOf(3)).toBe('средне')
    expect(colorOf(4)).toBe('var(--score-8)')
    expect(colorOf(5)).toBe('var(--score-10)')
  })

  it('на десяти ступенях всё как было', () => {
    setScale(10)

    expect(scale()).toHaveLength(10)
    expect(labelOf(10)).toBe('Шедевр')
    expect(colorOf(4)).toBe('var(--score-4)')
  })

  it('оценки агрегаторов от своей шкалы не зависят вовсе', () => {
    // Иначе IMDb 8.6 при пятибалльной своей шкале красился бы девятой ступенью
    // из пяти — то есть ничем, а цифра пропала бы. Решение пользователя: у
    // агрегаторов не меняется ничто.
    setScale(5)

    expect(stepOf(8.6, 10)).toBe(9)
    expect(sourceColorOf(9)).toBe('var(--score-9)')
    expect(sourceColorOf(stepOf(46, 100))).toBe('var(--score-5)')
  })
})
