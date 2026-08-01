import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  Failed, call, cancel, drop, lastOp, numbered, ready,
} from '$api/bridge.js'
import { bare, fake, slow } from './fake.js'

beforeEach(() => { vi.restoreAllMocks() })

describe('обёртка моста', () => {
  it('разворачивает удачный ответ и довозит доводы', async () => {
    // Доводы проверяются здесь же: через `call` идут все мгновенные записи, и
    // «переименовали тег ничем» — это порча данных, а не пустой экран.
    const asked = fake({ 'marks.tags': { ok: [{ id: 1, name: 'драма' }] } })

    await expect(call('marks.tags', 'movie')).resolves.toEqual([
      { id: 1, name: 'драма' },
    ])
    expect(asked).toEqual([['marks.tags', ['movie']]])
  })

  it('вызов до внедрения моста ждёт его, а не падает', async () => {
    // Инъекция идёт после навигации, и раздел, спросивший раньше, нашёл бы
    // `undefined` вместо `api`. Ожидание внутри вызова — первая из четырёх
    // обязанностей обёртки, и наблюдается она только отсюда: во всех
    // остальных проверках мост уже стоит к началу вызова.
    const listeners = bare()

    const asked = []
    const answer = call('marks.tags', 'movie')

    globalThis.window.pywebview = {
      api: { marks: { tags: (...args) => { asked.push(args); return { ok: [] } } } },
    }
    listeners.pywebviewready()

    await expect(answer).resolves.toEqual([])
    expect(asked).toEqual([['movie']])
  })

  it('отказ операции превращается в исключение с родом', async () => {
    // Ловить семь исключений бэкенда в разметке нельзя, а один род — можно.
    fake({ 'marks.rename_tag': { fail: 'tag-exists', detail: 'драма' } })

    await expect(call('marks.rename_tag', 3, 'драма'))
      .rejects.toThrow(Failed)
    await call('marks.rename_tag', 3, 'драма').catch((error) => {
      expect(error.kind).toBe('tag-exists')
      expect(error.detail).toBe('драма')
    })
  })

  it('пустой удачный ответ — это удача, а не отказ', async () => {
    // Мост заворачивает в `{"ok": ...}` и `None`: у девятнадцати методов
    // хранилища возврата нет вовсе, и через мост на них выходят записи меток,
    // оценок и закладок. Смотреть на значение вместо наличия ключа значит
    // поднимать плашку на каждой удачной записи.
    fake({ 'marks.assign': { ok: null } })

    await expect(call('marks.assign', 1, 3)).resolves.toBe(null)
  })

  it('обычный отказ не молчит', async () => {
    // Молчание — это про уход со страницы, а не про беду. Зашей его всем
    // отказам, и приложение перестанет сообщать хоть что-нибудь: плашка
    // читает именно этот признак.
    fake({ 'marks.rename_tag': { fail: 'tag-exists', detail: 'драма' } })

    await call('marks.rename_tag', 3, 'драма').catch((error) => {
      expect(error.silent).toBe(false)
    })
  })

  it('чужое исключение моста приезжает тем же родом, что и его отказ', async () => {
    // Опечатку в пути, лишний довод и неизвестный домен pywebview ловит у
    // себя и отклоняет промис голым `Error`: ни рода, ни признака молчания у
    // него нет. Разметка ветвится по признаку — и показала бы плашку со
    // словом `undefined`.
    globalThis.window = {
      pywebview: {
        api: { marks: { tags: () => Promise.reject(new Error('нет такого метода')) } },
      },
      addEventListener: () => {},
    }

    await expect(call('marks.tags', 'movie')).rejects.toThrow(Failed)
    await call('marks.tags', 'movie').catch((error) => {
      expect(error.kind).toBe('broken')
      expect(error.detail).toBe('нет такого метода')
      expect(error.silent).toBe(false)
    })
  })

  it('нумерованная операция получает свой номер первым доводом', async () => {
    const asked = fake({ 'world.enrich': { ok: [] } })

    await numbered('world.enrich', 12, 'movie')

    const [path, args] = asked[0]
    expect(path).toBe('world.enrich')
    expect(typeof args[0]).toBe('number')
    expect(args.slice(1)).toEqual([12, 'movie'])
  })

  it('нумерованный вызов до внедрения моста тоже ждёт', async () => {
    // Половина поверхности — не половина обязанности: нумерованными идут как
    // раз первые запросы страницы, лента и поиск, а внедрение моста случается
    // после навигации.
    const listeners = bare()

    const asked = []
    const answer = numbered('feed.page', {}, 0, 50)

    globalThis.window.pywebview = {
      api: { feed: { page: (...args) => { asked.push(args); return { ok: [] } } } },
    }
    listeners.pywebviewready()

    await expect(answer).resolves.toEqual([])
    expect(asked).toHaveLength(1)
  })

  it('снятые настройки не съедают запрос с головы', async () => {
    // Настройки — хвост доводов, и срезаются с хвоста. Срежь их с головы, и
    // мост получит вызов со сдвинутыми доводами: смещения он не заметит, а
    // ответит не на то.
    const ops = []
    const asked = fake({ 'feed.page': { ok: [] } })

    await numbered('feed.page', { tag_ids: [3] }, 40, 20, { channel: 'feed', ops })

    expect(asked[0][1].slice(1)).toEqual([{ tag_ids: [3] }, 40, 20])
  })

  it('номера не повторяются', async () => {
    const asked = fake({ 'world.enrich': { ok: [] } })

    await numbered('world.enrich', 1, 'movie')
    await numbered('world.enrich', 2, 'movie')

    expect(asked[0][1][0]).not.toBe(asked[1][1][0])
  })

  it('второй шаг зовётся тем же номером, что и первый', async () => {
    // Без этого мостовая память второй шаг не узнаёт и отвечает «устарело» —
    // а это весь поиск, заведение кандидата и привязка ссылки разом.
    const asked = fake({ 'search.local': { ok: [] }, 'search.external': { ok: [] } })

    await numbered('search.local', 'movie', 'один', { channel: 'search' })
    await numbered('search.external', { channel: 'search', op: lastOp('search') })

    expect(asked[1][1][0]).toBe(asked[0][1][0])
  })

  it('номер ложится в список отменяемых', async () => {
    // Иначе `cancel` зовётся с пустотой всегда, и обещание «страница ушла —
    // начатое отменяется» не наступает нигде.
    const ops = []
    const asked = fake({ 'world.enrich': { ok: [] } })

    await numbered('world.enrich', 12, 'movie', { ops })

    // Сверяется с тем, что уехало мосту, а не просто «число». Положенный сюда
    // ноль выглядел бы живой отменой и гасил бы ноль операций.
    expect(ops).toEqual([asked[0][1][0]])
  })

  it('устаревший ответ не затирает свежий', async () => {
    // Набрал новый запрос, пока летел старый. Обещание старого обязано
    // отклониться, а не вернуть данные, которых уже никто не ждёт.
    fake({ 'search.local': slow({ ok: 'старое' }, { ok: 'новое' }) })

    const stale = numbered('search.local', 'movie', 'один', { channel: 'stale-search' })
    const fresh = await numbered('search.local', 'movie', 'два', { channel: 'stale-search' })

    expect(fresh).toBe('новое')
    await expect(stale).rejects.toThrow(Failed)
    // Молча и своим родом: плашка на каждую букву набранного запроса — это не
    // сообщение об ошибке, а мигающий экран.
    await stale.catch((error) => {
      expect(error.kind).toBe('stale')
      expect(error.silent).toBe(true)
    })
  })

  it('снятый канал не ждёт больше никого', async () => {
    // Выдачу снимают и без нового запроса — очисткой строки и сменой вкладки.
    // Номер канала при этом меняться некому, и ответ прежней операции считался
    // бы своевременным: выдача по игровому запросу легла бы во вкладку
    // сериалов через двадцать секунд после того, как её очистили.
    fake({ 'search.local': slow({ ok: 'старое' }, { ok: 'никем не ждано' }) })

    const flying = numbered('search.local', 'game', 'fallout',
                            { channel: 'dropped-search' })
    drop('dropped-search')

    await expect(flying).rejects.toMatchObject({ kind: 'stale', silent: true })
  })

  it('снятый канал не мешает следующему запросу', async () => {
    // Снятие — это не закрытие: следом человек набирает новую строку, и её
    // ответ обязан доехать.
    fake({ 'search.local': { ok: 'новое' } })
    drop('dropped-twice')

    await expect(numbered('search.local', 'movie', 'дюна',
                          { channel: 'dropped-twice' })).resolves.toBe('новое')
  })

  it('ответы разных каналов друг друга не гасят', async () => {
    // Лента и поиск идут разом, и номер у них общий: без канала свежая
    // страница ленты отменяла бы свежую выдачу поиска.
    //
    // Оба вызова идут **одним путём** нарочно. Пути у них и так разные, и на
    // разных путях тест зеленел бы даже с выброшенным каналом: вытеснение
    // тогда шло бы по пути, и различить одно от другого было бы нечем.
    fake({ 'feed.page': { ok: [] } })

    const page = numbered('feed.page', {}, 0, 50, { channel: 'feed' })
    const histogram = numbered('feed.page', {}, 0, 50, { channel: 'histogram' })

    await expect(page).resolves.toEqual([])
    await expect(histogram).resolves.toEqual([])
  })

  it('без канала вытесняет само себя по пути вызова', async () => {
    // Пока это записанное поведение, а не решение: два одновременных вызова
    // одного метода без канала гасят друг друга, и вытесненный уходит молча.
    // Плановому обогащению видимых карточек это выйдет боком — вопрос отложен.
    fake({ 'world.enrich': slow({ ok: 'старое' }, { ok: 'новое' }) })

    const evicted = numbered('world.enrich', 1, 'movie')
    await expect(numbered('world.enrich', 2, 'movie')).resolves.toBe('новое')
    await expect(evicted).rejects.toThrow(Failed)
  })

  it('словарь запроса не съедается как настройки вызова', async () => {
    // Настройки узнаются по ключам, и `feed.histogram` шлёт фильтры словарём
    // последним доводом. Отпади проверка — он уехал бы в настройки, а мост
    // получил бы запрос без единого фильтра и ответил бы законным «ничего не
    // отобрано».
    const asked = fake({ 'feed.histogram': { ok: [] } })

    await numbered('feed.histogram', 'movie', { tag_ids: [3], genre_ids: [] })

    expect(asked[0][1].slice(1))
      .toEqual(['movie', { tag_ids: [3], genre_ids: [] }])
  })

  it('отмена до внедрения моста молчит, а не падает', async () => {
    // Между двумя внедрениями `window.pywebview` уже есть, а `api.cancel` ещё
    // нет. Достижимо на старте: номер ложится в список отменяемых **до**
    // ожидания моста, и раздел, закрытый в этот миг, уронил бы уборку
    // синхронным `TypeError` — а ловить его в уборке эффекта некому.
    globalThis.window = { pywebview: { api: {} }, addEventListener: () => {} }

    expect(() => cancel([1, 2])).not.toThrow()
  })

  it('отмена уходит одним пересечением границы', async () => {
    // Страница ушла целиком: восемнадцать вызовов вместо одного — это
    // восемнадцать потоков на стороне питона.
    const asked = fake({})

    cancel([1, 2, 3])

    expect(asked[0]).toEqual(['cancel', [1, 2, 3]])
  })

  it('отменённая операция молчит, а не поднимает плашку', async () => {
    fake({ 'world.enrich': { fail: 'cancelled' } })

    await expect(numbered('world.enrich', 12, 'movie')).rejects.toThrow(Failed)
    await numbered('world.enrich', 12, 'movie').catch((error) => {
      expect(error.silent).toBe(true)
    })
  })

  it('пустой мост за готовность не считает', async () => {
    // pywebview внедряет мост двумя заходами: первый объявляет
    // `window.pywebview` с пустым `api`, второй заполняет его и только тогда
    // шлёт событие. Поверив первому, обёртка тут же позвала бы
    // `api.<домен>.<метод>` у пустоты — и это `TypeError` через границу.
    const listeners = bare({ empty: true })

    let arrived = false
    ready().then(() => { arrived = true })
    await Promise.resolve()
    expect(arrived).toBe(false)

    globalThis.window.pywebview.api = { marks: {} }
    listeners.pywebviewready()
    await Promise.resolve()

    expect(arrived).toBe(true)
  })

  it('ждёт готовности моста, а не падает на его отсутствии', async () => {
    // Инъекция идёт после навигации, и обращение до неё нашло бы undefined.
    const listeners = bare()

    const waiting = ready()
    globalThis.window.pywebview = { api: {} }
    listeners.pywebviewready()

    await expect(waiting).resolves.toBeUndefined()
  })
})
