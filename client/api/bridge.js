/* Единственное место страницы, которое знает про `window.pywebview`. */

/** Отказ операции: род один на все семь исключений бэкенда. */
export class Failed extends Error {
  constructor(kind, detail = '') {
    super(detail || kind)
    this.name = 'Failed'
    this.kind = kind
    this.detail = detail
    // Отменённое и устаревшее плашкой не показываются: за уход со страницы
    // человеку сообщать не о чем.
    this.silent = kind === 'cancelled' || kind === 'stale'
  }
}

let counter = 0

// Последний номер на канал. Канал — это то, что вытесняет само себя: новая
// выдача поиска отменяет прежнюю, но не отменяет страницу ленты.
const latest = new Map()

/** Мост приезжает двумя внедрениями: первое объявляет `window.pywebview` с
 *  пустым `api`, второе заполняет его и только тогда шлёт событие. Пустой `api`
 *  за готовность не считается — следом идёт `api.<домен>.<метод>`, а звать там
 *  ещё нечего. */
const arrived = () => Object.keys(window.pywebview?.api ?? {}).length > 0

/** Инъекция моста идёт после навигации: до неё `window.pywebview` не существует.
 *
 *  Проверка синхронная, а не только по событию: внедрение идёт на каждой
 *  навигации, и подписка, поставленная после него, события уже не увидит. */
export function ready() {
  if (arrived()) return Promise.resolve()
  return new Promise((resolve) => {
    window.addEventListener('pywebviewready', () => resolve())
  })
}

/** Вызов без номера: мгновенные операции, которые нечем отменять. */
export async function call(path, ...args) {
  await ready()
  return unwrap(await asked(path, args))
}

/**
 * Вызов с номером: его есть чем отменить, и его ответ может устареть.
 *
 * Номер уходит наружу двумя путями, и оба обязательны. `options.op` — чужой
 * номер: второй шаг двухшаговой операции обязан прийти с тем же, что и первый,
 * иначе мостовая память его не узнает и ответит «устарело», а это весь поиск,
 * заведение кандидата и привязка ссылки разом. `options.ops` — список, куда
 * номер кладётся: без него уход с раздела гасить нечего, и `cancel` зовётся с
 * пустотой всегда.
 */
export async function numbered(path, ...args) {
  const options = tail(args)
  const channel = options.channel ?? path
  const op = options.op ?? (counter += 1)
  latest.set(channel, op)
  options.ops?.push(op)

  await ready()
  const answer = await asked(path, [op, ...args])

  // Номер читается в момент доставки, а не отправки: пока летел ответ,
  // страница могла спросить заново.
  if (latest.get(channel) !== op) throw new Failed('stale')
  return unwrap(answer)
}

/** Номер последней операции канала — им зовётся второй шаг. */
export function lastOp(channel) {
  return latest.get(channel)
}

/** Канал больше никого не ждёт: всё, что по нему в полёте, устарело.
 *
 *  Нужен там, где выдача снимается **без нового запроса** — очистка строки и
 *  смена вкладки. Устаревшее отбрасывается сравнением с номером канала, а тот
 *  меняется только при новом вызове; без этого ответ прежней операции считался
 *  бы своевременным, и выдача по игровому запросу легла бы во вкладку сериалов.
 *
 *  Номер берётся из общего счётчика, а не выдумывается: он обязан быть больше
 *  всех живых и не совпасть ни с одним будущим. */
export function drop(channel) {
  counter += 1
  latest.set(channel, counter)
}

/** Страница ушла — гасим всё, что начала, одним пересечением границы. */
export function cancel(ops) {
  // Мост проверяется, а не предполагается: уход с раздела бывает и до инъекции,
  // и после закрытия окна, а `ready()` тут ждать нечего — гасить уже нечего.
  // Проверка тем же `arrived()`, что и везде: между двумя внедрениями объект
  // уже есть, а `api.cancel` ещё нет.
  if (ops.length && arrived()) window.pywebview.api.cancel(ops)
}

/** Мост отвечает своим форматом не всегда: опечатку в пути, лишний довод и
 *  неизвестный домен pywebview ловит у себя и отклоняет промис голым `Error` —
 *  ни рода, ни признака молчания у такого нет. Род ему даём тот же, каким мост
 *  называет непредвиденное у себя, иначе разметка покажет плашку со словом
 *  `undefined`. */
async function asked(path, args) {
  try {
    return await at(path)(...args)
  } catch (error) {
    if (error instanceof Failed) throw error
    throw new Failed('broken', error.message)
  }
}

function at(path) {
  const [domain, method] = path.split('.')
  return (...args) => window.pywebview.api[domain][method](...args)
}

function unwrap(answer) {
  if ('ok' in answer) return answer.ok
  throw new Failed(answer.fail, answer.detail)
}

const OPTIONS = ['channel', 'op', 'ops']

/** Последний довод — настройки вызова, а не часть запроса. */
function tail(args) {
  const last = args.at(-1)
  if (last && typeof last === 'object' && OPTIONS.some((one) => one in last)) {
    args.pop()
    return last
  }
  return {}
}
