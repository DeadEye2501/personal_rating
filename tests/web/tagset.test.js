import { describe, expect, it } from 'vitest'

// Относительным путём, а не псевдонимом: у слоя сборки его нет и заводить
// незачем — внутрь `app/` не импортирует никто, кроме проверок.
import { dropped, ordered, wearers } from '../../client/app/tagset.js'
import { fake } from './fake.js'

const rows = () => [{ id: 1, name: 'нуар' }, { id: 2, name: 'долгий' }]

describe('правка набора тегов', () => {
  it('спрашивает, сколько карточек носит тег', async () => {
    // По этому числу удаление решает, спрашивать ли подтверждения: ничей тег
    // уходит молча, терять на нём нечего.
    const asked = fake({ 'marks.tag_usage': { ok: 3 } })

    expect(await wearers(7)).toBe(3)
    expect(asked).toEqual([['marks.tag_usage', [7]]])
  })

  it('удалённый уходит и из базы, и из набора', async () => {
    const asked = fake({ 'marks.delete_tag': { ok: null } })

    expect(await dropped(rows(), 1)).toEqual([{ id: 2, name: 'долгий' }])
    expect(asked).toEqual([['marks.delete_tag', [1]]])
  })

  it('на отказе базы набор не трогается вовсе', async () => {
    // Иначе строка исчезает с экрана, а тег остаётся в базе: следующий заход в
    // окно вернёт его, и человек решит, что удаление работает через раз.
    fake({ 'marks.delete_tag': { fail: 'broken', detail: 'мост лёг' } })

    await expect(dropped(rows(), 1)).rejects.toThrow()
  })

  it('удаляет по номеру, а не по месту в списке', async () => {
    // Список успевает переехать перетаскиванием между вопросом и ответом.
    fake({ 'marks.delete_tag': { ok: null } })

    expect(await dropped(rows(), 2)).toEqual([{ id: 1, name: 'нуар' }])
  })

  it('порядок уезжает номерами и в том порядке, в каком лежит', async () => {
    // Без вызова перестановка живёт до закрытия окна: `position` пишет база.
    const asked = fake({ 'marks.reorder_tags': { ok: null } })

    await ordered([{ id: 2 }, { id: 1 }, { id: 5 }], 'movie')

    expect(asked).toEqual([['marks.reorder_tags', ['movie', [2, 1, 5]]]])
  })
})
