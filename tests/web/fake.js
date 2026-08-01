/* Поддельный мост: отвечает тем, что положили, и записывает, о чём спросили. */

/** Ответ кладётся по пути `домен.метод` — значением или функцией от доводов.
 *  Метода, которого в наборе нет, у подделки нет вовсе: так и ведёт себя
 *  настоящий мост, когда путь написан с опечаткой.
 *
 *  Возвращает список спрошенного: пары «путь, доводы» в порядке вызова. */
export function fake(answers = {}) {
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

/** Окно без моста: он ещё не внедрён, но подписаться уже можно. Возвращает
 *  подписчиков, чтобы проверка могла позвать `pywebviewready` сама.
 *
 *  `api` кладётся, только если попросили: пустой объект — это первое из двух
 *  внедрений pywebview, и обёртка обязана не считать его готовностью. */
export function bare({ empty = false } = {}) {
  const listeners = {}
  globalThis.window = {
    ...(empty ? { pywebview: { api: {} } } : {}),
    addEventListener: (name, run) => { listeners[name] = run },
  }
  return listeners
}

/** Ответ, приезжающий позже: первый вызов ждёт, второй отвечает сразу. Так
 *  проверяется всё, что про очерёдность, — устаревание и отмена. */
export function slow(late, quick, ms = 20) {
  let first = true
  return () => {
    if (!first) return quick
    first = false
    return new Promise((resolve) => setTimeout(() => resolve(late), ms))
  }
}
