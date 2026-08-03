<!-- Обе половины библиотеки: «Оценённые» и «Хочу посмотреть». Различает их
     `session.section`, он же уезжает в запрос; второй файл был бы дословной
     копией, которую планы 8 и 9 правили бы дважды. -->
<script>
  import { untrack } from 'svelte'

  import Feed from '$components/Feed.svelte'
  import { numbered } from '$api/bridge.js'
  import { owned } from '$api/owned.svelte.js'
  import { retagged } from '$state/marking.js'
  import { requestOf } from '$state/section.js'
  import { flipped, swept } from '$state/session.js'
  import { aspected, scored, wished } from './marks.js'
  import { refreshed, without } from './reread.js'
  import { complaining } from './trouble.js'
  import { onCardShown } from './visible.js'

  // Порция ленты. Число из спеки: читается с диска и стоит дёшево.
  const PAGE = 50

  let { session, expected = [], root = null, tagged = {}, forgotten = [],
        ontrouble, onmark, onperson, onopen, onedit, ondelete, ontag,
        saved = null, removed = null } = $props()

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

  const cards = $derived(retagged(views, tagged, forgotten))

  const lost = complaining('раздел библиотеки', ontrouble)

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
    // Отказ разбирается здесь, а не в ленте: `silent` — поле отказа моста, а
    // мост компонентам закрыт. Лента от этого не замирает — «больше нет»
    // отвечает и сорвавшаяся догрузка.
    try {
      const next = await numbered('feed.page', JSON.parse(asked), views.length,
                                  PAGE, { channel: 'feed', ops })
      done = next.length < PAGE
      views = [...views, ...next]
      return !done
    } catch (error) {
      lost(error, 'Не удалось прочитать библиотеку')
      return false
    }
  }

  /** Приехавшие оценки кладутся в ту же карточку: иначе кружок на их месте
   *  крутится до перезахода в раздел, хотя оценки уже в базе. */
  async function enrich(view) {
    const external = await onCardShown(view, ops)
    // Признак ставится и когда не приехало ничего: он гасит кружки у тех, за
    // кого спрашивать было нечем или некому. Круг кончился — ждать больше
    // нечего, и имя без цифры из ряда уходит.
    patch(view, external ? { external, enriched: true } : { enriched: true })
  }

  // Записи идут без номера: отменять запись нельзя. Отказ у них показывается
  // плашкой, а не гасится — человек должен знать, что оценка не сохранилась.
  const score = async (view, value) => patch(view, await scored(view, value))

  const aspect = async (view, key, value) =>
    patch(view, await aspected(view, key, value))

  const wish = async (view) => patch(view, await wished(view))

  // Свёрнутость принадлежит элементу ленты: тумблер шапки — состояние всего
  // приложения, шеврон карточки — свойство её самой.
  const collapse = (view) => patch(view, flipped(view, session.collapsed))

  // Отдельной величиной, а не чтением `session` в эффекте: прочитанный там, он
  // метил бы эффект грязным на любую пересборку сеанса — и клик по жанру
  // распрямлял бы карточки, свёрнутые шевроном.
  const all = $derived(session.collapsed)

  // Нажали тумблер — он забирает власть у тронутых шевроном строк. Слушается
  // ровно он: `views` здесь и читаются, и пишутся, а такой круг эффект уже
  // ловил.
  $effect(() => {
    const pressed = all
    untrack(() => { views = swept(views, pressed) })
  })

  /** Замена идёт по номеру строки, а не по ссылке: список мог смениться, пока
   *  запись доезжала до базы. */
  function patch(view, fields) {
    views = views.map((each) =>
      each.item_id === view.item_id ? { ...each, ...fields } : each)
  }

  /** Оба эффекта слушают **только** свой сигнал: `views` они и читают, и пишут,
   *  а такой круг проект уже ловил — эффект по своему же списку не кончается
   *  никогда.
   *
   *  Записанной заново в списке может не быть — тогда перечитывать нечего, она
   *  придёт со следующей порцией. */
  $effect(() => {
    const done = saved
    if (done) untrack(() => again(done))
  })

  // Только удаление по номеру: строка без номера — это кандидат выдачи поиска,
  // и убирается он там же. Здесь такой сигнал попал бы по паре «источник плюс
  // идентификатор» в свою карточку той же вещи, которая никуда не девалась.
  $effect(() => {
    const gone = removed
    if (gone?.item_id) untrack(() => { views = without(views, gone) })
  })

  function again(done) {
    if (!views.some((each) => each.item_id === done.item_id)) return

    refreshed(done, ops, (fresh) => patch(fresh, fresh))
      .catch((error) => lost(error, 'Не удалось перечитать карточку'))
  }
</script>

<Feed views={cards} {expected} {root} collapsed={session.collapsed} onmore={more}
      onshown={(view) => enrich(view).catch((error) =>
        lost(error, 'Не удалось прочитать библиотеку'))}
      onscore={(view, value) => score(view, value).catch((error) =>
        lost(error, 'Оценка не сохранилась'))}
      onaspect={(view, key, value) => aspect(view, key, value).catch((error) =>
        lost(error, 'Оценка не сохранилась'))}
      onwish={(view) => wish(view).catch((error) =>
        lost(error, 'Закладка не сохранилась'))}
      oncollapse={collapse}
      on={session.filters.on} {onmark} {onperson} {onopen}
      {onedit} {ondelete} {ontag} />
