import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Failed, call, cancel, lastOp, numbered, ready } from '$api/bridge.js'

/** Поддельный мост: отвечает тем, что положили, и записывает, о чём спросили. */
function fake(answers = {}) {
  const asked = []
  const api = {
    cancel: (ops) => { asked.push(['cancel', ops]); return { ok: null } },
  }
  for (const [path, answer] of Object.entries(answers)) {
    const [domain, method] = path.split('.')
    api[domain] ??= {}
    api[domain][method] = (...args) => {
      asked.push([path, args])
      return typeof answer === 'function' ? answer(...args) : answer
    }
  }
  globalThis.window = { pywebview: { api }, addEventListener: () => {} }
  return asked
}

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
    const listeners = {}
    globalThis.window = {
      addEventListener: (name, handler) => { listeners[name] = handler },
    }

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

  it('нумерованная операция получает свой номер первым доводом', async () => {
    const asked = fake({ 'world.enrich': { ok: [] } })

    await numbered('world.enrich', 12, 'movie')

    const [path, args] = asked[0]
    expect(path).toBe('world.enrich')
    expect(typeof args[0]).toBe('number')
    expect(args.slice(1)).toEqual([12, 'movie'])
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
    const slow = new Promise((resolve) => setTimeout(() => resolve({ ok: 'старое' }), 20))
    let first = true
    fake({
      'search.local': () => {
        if (first) { first = false; return slow }
        return { ok: 'новое' }
      },
    })

    const stale = numbered('search.local', 'movie', 'один', { channel: 'stale-search' })
    const fresh = await numbered('search.local', 'movie', 'два', { channel: 'stale-search' })

    expect(fresh).toBe('новое')
    await expect(stale).rejects.toThrow(Failed)
    // Молча: плашка на каждую букву набранного запроса — это не сообщение об
    // ошибке, а мигающий экран.
    await stale.catch((error) => { expect(error.silent).toBe(true) })
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
    const listeners = {}
    globalThis.window = {
      pywebview: { api: {} },
      addEventListener: (name, handler) => { listeners[name] = handler },
    }

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
    const listeners = {}
    globalThis.window = {
      addEventListener: (name, handler) => { listeners[name] = handler },
    }

    const waiting = ready()
    globalThis.window.pywebview = { api: {} }
    listeners.pywebviewready()

    await expect(waiting).resolves.toBeUndefined()
  })
})
