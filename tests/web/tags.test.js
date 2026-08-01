import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { created } from '../../client/app/tags.js'
import { fake } from './fake.js'

describe('заведение тега', () => {
  it('отдаёт заведённый тег с номером от базы', async () => {
    // Номер нужен сразу: по нему строка отмечается и по нему же уходит
    // `marks.assign` — перечитывать набор ради него незачем.
    const asked = fake({ 'marks.create_tag': { ok: 42 } })
    const said = []

    const tag = await created('movie', 'нуар', (text) => said.push(text))

    expect(tag).toEqual({ id: 42, name: 'нуар' })
    expect(asked).toEqual([['marks.create_tag', ['movie', 'нуар']]])
    expect(said).toEqual([])
  })

  it('на занятом имени говорит про занятое имя и не отдаёт тега', async () => {
    // Занятое имя — штатный ход, а не сбой: набор один на тип содержимого, и
    // повторить в нём имя человек может запросто.
    fake({ 'marks.create_tag': { fail: 'tag-exists', detail: 'movie:нуар' } })
    const said = []

    const tag = await created('movie', 'нуар', (text) => said.push(text))

    expect(tag).toBe(null)
    expect(said).toEqual(['Такой тег уже есть'])
  })

  it('на любом другом отказе говорит другое', async () => {
    // Иначе оборванный мост объявлял бы имя занятым, и человек искал бы в
    // наборе тег, которого там нет.
    fake({ 'marks.create_tag': { fail: 'broken', detail: 'мост лёг' } })
    const said = []

    const tag = await created('movie', 'нуар', (text) => said.push(text))

    expect(tag).toBe(null)
    expect(said).toEqual(['Не удалось завести тег'])
  })
})
