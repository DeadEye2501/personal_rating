<!-- Раздел «Поиск»: сначала своя выдача, потом внешняя. -->
<script>
  import Feed from '$components/Feed.svelte'
  import { lastOp, numbered } from '$api/bridge.js'
  import { owned } from '$api/owned.svelte.js'
  import { passes } from '$state/filters.js'
  import { reported } from './trouble.js'
  import { onCardShown } from './visible.js'

  let { session, query = null, expected = [], root = null, ontrouble, onmark,
        onperson, onopen } = $props()

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
  const lost = (error) =>
    reported(error, 'поиск', () => ontrouble('Не удалось выполнить операцию'))

  $effect(() => {
    if (!query?.text) { views = []; return }
    look(query.text, kind).catch(lost)
  })

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
      const outer = await numbered('search.external',
                                   { channel: 'search', op: lastOp('search') })
      views = outer.views
      // Отказ источника — поле в ответе, а не исключение. Пустая выдача при
      // этом молчит: пустая лента и есть ответ.
      if (outer.refusals.length) ontrouble('Внешняя база недоступна')
    } catch (error) {
      reported(error, 'внешняя выдача',
               () => ontrouble('Внешняя база недоступна'))
    }
  }

  async function add(view) {
    // Предупреждения о совпадении названия здесь пока нет: оно показывается тем
    // же окном подтверждения, что и удаление, а оболочку модалки заводит план
    // 8. Спека требует его именно тут — у игр два магазина, и одна игра лежит
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

  /** Приехавшие оценки кладутся в ту же карточку: иначе кружок на их месте
   *  крутится до конца сеанса, хотя оценки уже в базе. */
  async function shownCard(view) {
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
      onshown={(view) => shownCard(view).catch(lost)}
      on={session.filters.on} {onmark} {onperson} {onopen}
      onscore={(view) => add(view).catch(lost)}
      onaspect={(view) => add(view).catch(lost)}
      oncollapse={idle} onedit={idle} ondelete={idle} onwish={idle}
      ontag={idle} />
