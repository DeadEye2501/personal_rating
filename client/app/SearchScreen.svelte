<!-- Раздел «Поиск»: сначала своя выдача, потом внешняя. Спрашивают её двумя
     жестами — строкой в шапке и кликом по имени в карточке, — и показывает она
     их одинаково. -->
<script>
  import { untrack } from 'svelte'

  import Feed from '$components/Feed.svelte'
  import { lastOp, numbered } from '$api/bridge.js'
  import { owned } from '$api/owned.svelte.js'
  import { passes } from '$state/filters.js'
  import { rowTurns } from './inturn.js'
  import { keyOf, refreshed, same, without } from './reread.js'
  import { aspected, scored } from './rating.js'
  import { complaining, reported } from './trouble.js'
  import { onCardShown } from './visible.js'

  let { session, query = null, person = null, expected = [], root = null,
        saved = null, removed = null, ontrouble, onmark, onperson, onopen,
        onedit, ondelete, ontag } = $props()

  let views = $state([])
  const ops = owned()

  // Тип содержимого отдельной величиной, а не чтением `session` в эффекте:
  // прочитанный там, он пометил бы эффект грязным на любую пересборку сеанса —
  // и клик по жанру на карточке перезапускал бы весь поиск, включая поход в
  // сеть. А метка объявлена мгновенным фильтром, который работает офлайн.
  const kind = $derived(session.kind)

  // Фильтры работают и в поиске. Спросить источник с фильтром нечем — у TMDB и
  // магазинов нет ни наших тегов, ни наших оценок, — поэтому ответ приходит
  // целиком, а отсев идёт здесь, тем же правилом, что и в ленте.
  const cards = $derived(views.filter((view) => passes(view, session.filters)))

  // Ни один вызов моста не остаётся без обработчика: невыполненное обещание в
  // JS не даёт ни плашки, ни записи — то есть ровно то молчание, которое
  // правило отказов запрещает.
  const lost = complaining('поиск', ontrouble)

  // Жест ровно один за раз: строка снимает человека, клик по имени снимает
  // строку — оба снятия делает сборка, здесь остаётся выбор ветки. Ранняя
  // ветка и есть то, что делает жест единственным: при непустом человеке
  // строка не читается вовсе.
  $effect(() => {
    const clicked = person
    // Начатое по прежней выдаче новой не касается: её строки мост помнит под
    // старым номером, и обещание, отданное новому жесту, отвергнется
    // «устаревшим» — молча.
    turns = rowTurns()
    if (clicked) { about(clicked, kind).catch(lost); return }
    if (!query?.text) { views = []; return }
    look(query.text, kind).catch(lost)
  })

  /** Выдача по клику на имя приезжает собранной: своя половина и чужая сложены
   *  на стороне бэкенда, и второго шага у этого жеста нет.
   *
   *  Лента гасится до запроса, а не после: своей половины, которая у строки
   *  приезжает мгновенно, здесь нет, и до двадцати секунд ожидания под пустым
   *  полем поиска висела бы выдача прошлого жеста.
   *
   *  Канал тот же, что у строки: новый жест обязан отменять предыдущий, а
   *  разные каналы оставили бы обе выдачи в гонке. */
  async function about({ domain, entity_id }, forKind) {
    views = []
    arrived(await numbered('search.by_person', domain, entity_id, forKind,
                          { channel: 'search', ops }))
  }

  async function look(text, forKind) {
    // Своё показывается сразу: локальная база отвечает за миллисекунды.
    views = await numbered('search.local', forKind, text,
                           { channel: 'search', ops })

    // Внешнее доливается по готовности и складывается со своим на стороне
    // моста: `merge_results` живёт в модели ровно потому, что складывать
    // приходится клиенту, и второго его объявления быть не должно.
    //
    // Тем же номером, что и первый шаг: мостовая память узнаёт выдачу по нему,
    // и с новым номером сюда всегда приходило бы «устарело».
    try {
      arrived(await numbered('search.external',
                            { channel: 'search', op: lastOp('search') }))
    } catch (error) {
      lost(error, 'Внешняя база недоступна')
    }
  }

  /** Отказ источника — поле в ответе, а не исключение. Пустая выдача при этом
   *  молчит: пустая лента и есть ответ. */
  function arrived(answer) {
    views = answer.views
    if (answer.refusals.length) ontrouble('Внешняя база недоступна')
  }

  /** Кандидат становится карточкой: детальный ответ источника и обложка, запись
   *  в базу целиком, перечитывание строки. Отдаёт свежую карточку либо род
   *  отказа — говорить о нём или молчать, решает тот, кто позвал.
   *
   *  Предупреждения о совпадении названия здесь пока нет. Окно для него уже
   *  есть — `components/Confirm.svelte`, план 8, — не хватает самой проверки на
   *  совпадение; спека требует её именно тут: у игр два магазина, и одна игра
   *  лежит в обоих двумя кандидатами. */
  async function adopt(view) {
    // Тот же номер: кандидата мост берёт из выдачи, которую помнит под ним.
    const outcome = await numbered('search.ensure', view.source, view.source_id,
                                   { channel: 'search', op: lastOp('search') })
    if (outcome.outcome !== 'found') return { refused: outcome.outcome }

    // Перечитываем одну строку: у кандидата не было ни жанров словами, ни
    // состава, ни длительности.
    // Канал на строку, а не общий: у двадцати одновременных догрузок общий
    // пропустил бы только последний ответ, а остальные ушли бы «устаревшими» —
    // молча, и строка осталась бы кандидатом навсегда.
    const [fresh] = await numbered('feed.views_of', [outcome.value],
                                   { channel: `views:${keyOf(view)}`, ops })
    if (fresh) replace(fresh)
    return { fresh }
  }

  const REFUSED = {
    refusal: 'Внешняя база недоступна',
    missing: 'Источник больше не знает такой карточки',
  }

  /** Жест человека: отказ говорится плашкой. Показ карточки — не жест, и там
   *  отказ молчит; см. `shown`. */
  async function asked(view) {
    const { fresh, refused } = await adopting(view)
    if (refused) ontrouble(REFUSED[refused])
    return fresh ?? null
  }

  // Порядок операций по строке: заведение одно на всех, записи идут по
  // очереди. Своя память на каждую выдачу — смена запроса приносит другие
  // строки, и начатое по старым их не касается.
  let turns = rowTurns()

  const adopting = (view) => turns.once(view, () => adopt(view))

  /** Замена целиком — для заведённой карточки: она и есть правда о строке. */
  function replace(fresh) {
    views = views.map((each) => same(each, fresh) ? fresh : each)
  }

  /** Долив полей — для всего остального. Ответы кругов и нажатие человека идут
   *  вперегонки, и снимок строки, взятый до `await`, затирает то, что случилось
   *  после него: так пропадала поставленная оценка — в базе она оставалась, а с
   *  экрана исчезала ровно в тот миг, когда доезжали оценки агрегаторов. */
  function patch(view, fields) {
    views = views.map((each) => same(each, view) ? { ...each, ...fields } : each)
  }

  /** Оба эффекта слушают **только** свой сигнал: `views` они и читают, и пишут,
   *  а такой круг проект уже ловил — эффект по своему же списку не кончается
   *  никогда.
   *
   *  Правленую карточку выдача перечитывает у себя, а не спрашивает источник
   *  заново: это поход в сеть ради того, что уже лежит в базе. */
  $effect(() => {
    const done = saved
    if (done) untrack(() => again(done))
  })

  $effect(() => {
    const gone = removed
    if (gone) untrack(() => { views = without(views, gone) })
  })

  function again(done) {
    if (!views.some((each) => each.item_id === done.item_id)) return

    refreshed(done, ops, replace)
      .catch((error) => lost(error, 'Не удалось перечитать карточку'))
  }

  /** Показанная строка догружается целиком: сначала карточка от источника и
   *  запись в базу, потом оценки агрегаторов. Их спрашивают по `imdb_id`, а он
   *  приезжает только с детальным ответом, — раньше круга 2 круг 3 не начать.
   *
   *  Отказ здесь молчит: двадцать плашек на одну прокрутку — шум, из которого
   *  не видно ни одной настоящей беды. В журнал он идёт всё равно, потому что
   *  ни один вызов моста не остаётся без следа. */
  async function shown(view) {
    const full = view.item_id ? view : await loaded(view)
    if (!full) return

    const external = await onCardShown(full, ops)
    if (external) patch(full, { external })
  }

  async function loaded(view) {
    const { fresh, refused } = await adopting(view)
    if (refused) reported({ kind: refused }, 'догрузка кандидата')
    return fresh ?? null
  }

  /** Оценка ставится по карточке, а карточки у кандидата ещё нет: сначала
   *  заводим, потом ставим. Второе нажатие по той же строке заведения уже не
   *  требует — у неё есть номер.
   *
   *  Записи по строке идут по очереди, и каждая берёт строку заново: у игры три
   *  шкалы уезжают одним вызовом, и вторая, посчитанная от снимка, взятого до
   *  `await`, затирает первую — в базе остаётся последняя. */
  const rate = (view, put) => turns.inTurn(view, async () => {
    const full = view.item_id ? view : await asked(view)
    if (!full) return

    const now = views.find((each) => same(each, full)) ?? full
    patch(now, await put(now))
  })

  /** Правка кандидата открывает окно на заведённой карточке, а не на пустой
   *  форме: иначе «Сохранить» завело бы вторую, ручную карточку того же
   *  фильма. */
  async function edit(view) {
    const full = view.item_id ? view : await asked(view)
    if (full) onedit(full)
  }

  const idle = () => {}
</script>

<!-- Порции в поиске не догружаются, и `onmore` отвечает «больше нет» намеренно:
     у TMDB страница выдачи это ровно двадцать кандидатов и один запрос, у игр
     два магазина по двадцать. Второй страницы в спеке нет.

     Нажатие по звезде у кандидата сначала заводит карточку, а потом ставит
     оценку: `marks.score` зовётся по номеру, а номер появляется только после
     заведения. -->
<Feed views={cards} collapsed={session.collapsed} {expected} {root}
      onmore={() => false}
      onshown={(view) => shown(view).catch(lost)}
      on={session.filters.on} {onmark} {onperson} {onopen}
      onscore={(view, value) => rate(view, (full) => scored(full, value)).catch(lost)}
      onaspect={(view, key, value) =>
        rate(view, (full) => aspected(full, key, value)).catch(lost)}
      oncollapse={idle} onedit={(view) => edit(view).catch(lost)}
      {ondelete} onwish={idle}
      {ontag} />
