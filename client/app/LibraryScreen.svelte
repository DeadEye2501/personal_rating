<!-- Обе половины библиотеки: «Оценённые» и «Хочу посмотреть». Различает их
     `session.section`, он же уезжает в запрос; второй файл был бы дословной
     копией, которую планы 8 и 9 правили бы дважды. -->
<script>
  import Feed from '$components/Feed.svelte'
  import { call, numbered } from '$api/bridge.js'
  import { owned } from '$api/owned.svelte.js'
  import { requestOf } from '$state/section.js'
  import { collapsedOf } from '$state/session.js'
  import { reported } from './trouble.js'
  import { onCardShown } from './visible.js'

  // Порция ленты. Число из спеки: читается с диска и стоит дёшево.
  const PAGE = 50

  let { session, expected = [], root = null, tagged = {}, forgotten = [],
        ontrouble, onmark, onperson, onopen, ontag } = $props()

  let views = $state([])
  let done = $state(false)
  // Пока первая страница нового запроса не приехала, догружать нечего: у ленты
  // ещё старое содержимое, и её длина — смещение в чужой набор.
  let ready = $state(false)
  const ops = owned()

  // Ключ запроса строкой, а не объектом: производная сличает строгим
  // равенством, а `requestOf` отдаёт каждый раз новый объект — эффект
  // срабатывал бы на любую пересборку сеанса, и «Свернуть всё» перечитывало бы
  // ленту с начала, роняя прокрутку.
  const asked = $derived(JSON.stringify(requestOf(session)))

  // Правки набора накладываются поверх прочитанного: перечитывать страницу
  // ленты ради одной метки незачем, а следующее чтение привезёт их уже из базы.
  // Проставленное в модалке заменяет метки карточки целиком, удалённое
  // вычитается у всех — оно приехало из базы вместе с карточками.
  const cards = $derived(views.map((view) => {
    const tags = (tagged[view.item_id] ?? view.tags)
      .filter((tag) => !forgotten.includes(tag.id))
    return tags.length === view.tags.length && !tagged[view.item_id]
      ? view : { ...view, tags }
  }))

  const lost = (error, text) => reported(error, 'раздел библиотеки',
                                         () => ontrouble(text))

  // Смена фильтра, сортировки, типа или раздела перезапрашивает ленту с
  // начала: догружать поверх чужого набора нечего.
  $effect(() => {
    const request = JSON.parse(asked)
    ready = false
    done = false
    numbered('feed.page', request, 0, PAGE, { channel: 'feed', ops })
      .then((page) => {
        views = page
        done = page.length < PAGE
        ready = true
      })
      .catch((error) => lost(error, 'Не удалось прочитать библиотеку'))
  })

  /** Отвечает, есть ли смысл просить ещё: конец знает тот, кто просил. */
  async function more() {
    if (done || !ready) return false
    const next = await numbered('feed.page', JSON.parse(asked), views.length,
                                PAGE, { channel: 'feed', ops })
    done = next.length < PAGE
    views = [...views, ...next]
    return !done
  }

  /** Приехавшие оценки кладутся в ту же карточку: иначе кружок на их месте
   *  крутится до перезахода в раздел, хотя оценки уже в базе. */
  async function shown(view) {
    const external = await onCardShown(view, ops)
    if (external) patch(view, { external })
  }

  // Записи идут без номера: отменять запись нельзя. Отказ у них показывается
  // плашкой, а не гасится — человек должен знать, что оценка не сохранилась.
  async function score(view, value) {
    await call('marks.score', view.item_id, value)
    patch(view, { rating: { ...view.rating, score: value } })
  }

  async function aspect(view, key, value) {
    const next = { ...view.rating, [key]: value }
    // Ответ — выведенный балл: у игр оценка это среднее выставленных шкал, и
    // считает его база.
    next.score = await call('marks.aspects', view.item_id, next.visual,
                            next.narrative, next.gameplay)
    patch(view, { rating: next })
  }

  async function wish(view) {
    await call(view.in_wishlist ? 'marks.unwish' : 'marks.wish', view.item_id)
    patch(view, { in_wishlist: !view.in_wishlist })
  }

  // Свёрнутость принадлежит элементу ленты: тумблер шапки — состояние всего
  // приложения, шеврон карточки — свойство её самой, и своё сильнее общего.
  const collapse = (view) =>
    patch(view, { collapsed: !collapsedOf(view, session.collapsed) })

  /** Замена идёт по номеру строки, а не по ссылке: список мог смениться, пока
   *  запись доезжала до базы. */
  function patch(view, fields) {
    views = views.map((each) =>
      each.item_id === view.item_id ? { ...each, ...fields } : each)
  }

  const idle = () => {}
</script>

<Feed views={cards} {expected} {root} collapsed={session.collapsed} onmore={more}
      onshown={(view) => shown(view).catch((error) =>
        lost(error, 'Не удалось прочитать библиотеку'))}
      onscore={(view, value) => score(view, value).catch((error) =>
        lost(error, 'Оценка не сохранилась'))}
      onaspect={(view, key, value) => aspect(view, key, value).catch((error) =>
        lost(error, 'Оценка не сохранилась'))}
      onwish={(view) => wish(view).catch((error) =>
        lost(error, 'Закладка не сохранилась'))}
      oncollapse={collapse}
      on={session.filters.on} {onmark} {onperson} {onopen}
      onedit={idle} ondelete={idle} {ontag} />
