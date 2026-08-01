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
