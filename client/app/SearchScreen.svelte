<!-- Раздел «Поиск»: сначала своя выдача, потом внешняя. Спрашивают её двумя
     жестами — строкой в шапке и кликом по имени в карточке, — и показывает она
     их одинаково. -->
<script>
  import { untrack } from 'svelte'

  import Feed from '$components/Feed.svelte'
  import { lastOp, numbered } from '$api/bridge.js'
  import { owned } from '$api/owned.svelte.js'
  import { passes } from '$state/filters.js'
  import { refreshed, without } from './reread.js'
  import { complaining } from './trouble.js'
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
  const shown = $derived(views.filter((view) => passes(view, session.filters)))

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

  async function add(view) {
    // Предупреждения о совпадении названия здесь пока нет. Окно для него уже
    // есть — `components/Confirm.svelte`, план 8, — не хватает самой проверки
    // на совпадение; её заводит план 9 вместе с окном карточки. Спека требует его именно тут — у игр два магазина, и одна игра лежит
    // в обоих двумя кандидатами.

    // Тот же номер: кандидата мост берёт из выдачи, которую помнит под ним.
    const outcome = await numbered('search.ensure', view.source, view.source_id,
                                   { channel: 'search', op: lastOp('search') })
    if (outcome.outcome === 'refusal') {
      ontrouble('Внешняя база недоступна')
      return
    }
    if (outcome.outcome === 'missing') {
      ontrouble('Источник больше не знает такой карточки')
      return
    }
    // Карточка записана целиком: перечитываем её одну, чтобы в ленте появились
    // жанры, состав и длительность, которых у кандидата не было.
    const [fresh] = await numbered('feed.views_of', [outcome.value],
                                   { channel: 'views', ops })
    replace(fresh)
  }

  /** Замена идёт по паре «источник плюс идентификатор», а не по ссылке: список
   *  мог смениться, пока карточка заводилась. */
  function replace(fresh) {
    views = views.map((each) =>
      each.source === fresh.source && each.source_id === fresh.source_id
        ? fresh : each)
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
    if (gone) untrack(() => { views = without(views, gone.item_id) })
  })

  function again(done) {
    if (!views.some((each) => each.item_id === done.item_id)) return

    refreshed(done, ops, replace)
      .catch((error) => lost(error, 'Не удалось перечитать карточку'))
  }

  /** Приехавшие оценки кладутся в ту же карточку: иначе кружок на их месте
   *  крутится до конца сеанса, хотя оценки уже в базе. */
  async function enrich(view) {
    const external = await onCardShown(view, ops)
    if (external) replace({ ...view, external })
  }

  const idle = () => {}
</script>

<!-- Порции в поиске не догружаются, и `onmore` отвечает «больше нет» намеренно:
     у TMDB страница выдачи это ровно двадцать кандидатов и один запрос, у игр
     два магазина по двадцать. Второй страницы в спеке нет.

     Оценка кандидата сначала заводит карточку: `item_id` у него нет, и звать
     `marks.score` не с чем. Оценка вторым действием появится вместе с окном
     карточки. -->
<Feed views={shown} collapsed={session.collapsed} {expected} {root}
      onmore={() => false}
      onshown={(view) => enrich(view).catch(lost)}
      on={session.filters.on} {onmark} {onperson} {onopen}
      onscore={(view) => add(view).catch(lost)}
      onaspect={(view) => add(view).catch(lost)}
      oncollapse={idle} {onedit} {ondelete} onwish={idle}
      {ontag} />
