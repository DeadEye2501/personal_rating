<!-- Корень страницы: шапка, стопка разделов и плашка сообщений. -->
<script>
  import CardTagsModal from './CardTagsModal.svelte'
  import FiltersModal from './FiltersModal.svelte'
  import LibraryScreen from './LibraryScreen.svelte'
  import SearchScreen from './SearchScreen.svelte'
  import StatsScreen from './StatsScreen.svelte'
  import Topbar from './Topbar.svelte'
  import Snack from '$components/Snack.svelte'
  import { call, numbered } from '$api/bridge.js'
  import { isEmpty } from '$state/filters.js'
  import { newSession, withClearedFilter, withFilters, withForgotten, withMark,
    withSection } from '$state/session.js'
  import { reported } from './trouble.js'

  // Раздел, которого здесь нет, откроется пустым и молча: `Screen` станет
  // `undefined`, а Svelte на этом не жалуется. Значения обязаны совпадать с
  // теми, что перебирает шапка и знает `sorting.js`.
  const SCREENS = {
    search: SearchScreen,
    // Оба раздела библиотеки — один экран: различает их `session.section`,
    // и он же уезжает в запрос.
    rated: LibraryScreen,
    wishlist: LibraryScreen,
    stats: StatsScreen,
  }

  // Фильмам достаётся значение по умолчанию из палитры, поэтому его тут нет:
  // положить одно значение в два места значит дать ему разойтись. Остальные два
  // подставляются токенами, а не литералами — цвет живёт в палитре.
  const ACCENTS = { series: 'var(--accent-series)', game: 'var(--accent-game)' }

  let session = $state(newSession())

  // Запрос живёт здесь, а не в разделе: набирают его в шапке, а показывает
  // выдачу поиск, и общего у них только это состояние.
  //
  // Своим объектом, а не строкой: повторный Enter с той же строкой обязан
  // спросить заново — иначе после отказа сети повторить поиск было бы нечем.
  let query = $state(null)

  // Плашка одна на всё приложение, и говорят в неё разделы: своей они не
  // заводят.
  let trouble = $state(null)

  // Сколько оценок агрегаторов ждать. Спрашивается здесь, а не в каждом
  // разделе: зависит это от типа содержимого, а он общий, и два одинаковых
  // запроса разошлись бы молча.
  let expected = $state([])

  // Прокручивается область содержимого, и знает об этом только сборка. Ленте
  // она нужна корнем наблюдателя: иначе запас догрузки не действует.
  let content = $state()

  // Карточка, которой правят теги, и её метки, уже сохранённые.
  let tagging = $state(null)
  // Метки, доехавшие до ленты раньше, чем она перечитается: карточка обязана
  // показать их сразу. Накладываются производной, а не эффектом по ленте:
  // эффект, читающий и пишущий один список, — это бесконечный круг.
  let tagged = $state({})

  // Какое наложение открыто, знает сборка: `null` либо признак с подписью.
  // Подпись едет от кнопки, которая окно открыла: заголовок окна и есть её
  // подпись, и вторым объявлением они разъехались бы молча.
  let modal = $state(null)

  $effect(() => {
    numbered('world.expected', session.kind, { channel: 'expected' })
      .then((sources) => { expected = sources })
      .catch(idle)
  })

  // Акцент красит всю страницу, поэтому ставит его тот, кто страницей владеет,
  // а не шапка: она про свои три зоны. И следует он за состоянием, а не за
  // нажатием — иначе тип, пришедший откуда-то ещё, приехал бы со старым цветом.
  $effect(() => {
    const root = document.documentElement.style
    const accent = ACCENTS[session.kind]
    accent ? root.setProperty('--primary', accent) : root.removeProperty('--primary')
  })

  const Screen = $derived(SCREENS[session.section])

  // Клик по человеку открывает поиск по нему; тело появится вместе с
  // `search.by_person` — план 11 задачей 5.
  const idle = () => {}

  /** Повторное нажатие по горящей кнопке сбрасывает свой признак, а не
   *  открывает модалку: так в макете, где у каждого из трёх фильтров свой
   *  `isActive()` и свой `reset()`. */
  function filter(field, title) {
    if (!isEmpty(session.filters, field)) {
      session = withClearedFilter(session, field)
      return
    }
    modal = { field, title }
  }

  /** Тега больше нет в наборе, и помнить его номер не должен никто: ни отбор
   *  ленты, ни метки, доехавшие до неё раньше базы. */
  function forget(id) {
    session = withForgotten(session, 'tags', id)
    tagged = Object.fromEntries(Object.entries(tagged).map(
      ([item, tags]) => [item, tags.filter((tag) => tag.id !== id)]))
  }

  /** Ссылку открывает системный браузер: окно приложения без адресной строки, и
   *  вернуться из Кинопоиска было бы нечем. Отказ у этого свой — чужая схема
   *  адреса заведена в мосте отдельным классом ровно затем, чтобы плашка
   *  назвала причину, а не промолчала. */
  function open(url) {
    call('world.open', url).catch((error) =>
      reported(error, 'ссылка', () => { trouble = { text: 'Не удалось открыть ссылку' } }))
  }
</script>

<div class="app">
  <main class="app__main">
    <Topbar {session}
            onsession={(next) => { session = next }}
            onsearch={(text) => { query = { text }
                                  session = withSection(session, 'search') }}
            onadd={() => {}} onfilter={filter} />

    <div class="content" bind:this={content}>
      <!-- `{#key}` здесь не украшение: без него Svelte переиспользует ту же
           секцию, `screen-in` не проигрывается, и переход между разделами
           становится мгновенной подменой. -->
      {#key session.section}
        <section class="view is-shown">
          <!-- Метка и человек решаются здесь, а не в разделе: клик по жанру
               включает фильтр, клик по имени открывает поиск по человеку — и
               то и другое меняет общее состояние. -->
          <Screen {session} {query} {expected} root={content}
                  ontrouble={(text) => { trouble = { text } }}
                  onmark={(field, id) => { session = withMark(session, field, id) }}
                  onperson={idle}
                  onopen={open}
                  {tagged}
                  ontag={(view) => { tagging = view }} />
        </section>
      {/key}
    </div>
  </main>

  <!-- `{#key}` не украшение: без него смена признака переиспользует то же окно
       вместе с уже прочитанным чужим списком, и щелчок по строке в этот
       промежуток ставит фильтр по жанру номером тега. -->
  {#if modal}
    {#key modal.field}
      <FiltersModal field={modal.field} title={modal.title} kind={session.kind}
                    filters={session.filters}
                    onfilters={(next) => { session = withFilters(session, next) }}
                    onforget={forget}
                    ontrouble={(text) => { trouble = { text } }}
                    onclose={() => { modal = null }} />
    {/key}
  {/if}

  {#if tagging}
    <CardTagsModal view={tagging}
                   onview={(tags) => { tagged = { ...tagged, [tagging.item_id]: tags } }}
                   ontrouble={(text) => { trouble = { text } }}
                   onclose={() => { tagging = null }} />
  {/if}

  <Snack message={trouble} />
</div>
