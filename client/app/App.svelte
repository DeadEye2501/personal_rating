<!-- Корень страницы: шапка, стопка разделов и плашка сообщений. -->
<script>
  import LibraryScreen from './LibraryScreen.svelte'
  import SearchScreen from './SearchScreen.svelte'
  import StatsScreen from './StatsScreen.svelte'
  import Topbar from './Topbar.svelte'
  import Snack from '$components/Snack.svelte'
  import { newSession } from '$state/session.js'

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

  // Плашка одна на всё приложение, и говорят в неё разделы. Сегодня они пусты,
  // сообщать нечем, и она стоит за краем окна.
  let trouble = $state(null)

  // Акцент красит всю страницу, поэтому ставит его тот, кто страницей владеет,
  // а не шапка: она про свои три зоны. И следует он за состоянием, а не за
  // нажатием — иначе тип, пришедший откуда-то ещё, приехал бы со старым цветом.
  $effect(() => {
    const root = document.documentElement.style
    const accent = ACCENTS[session.kind]
    accent ? root.setProperty('--primary', accent) : root.removeProperty('--primary')
  })

  const Screen = $derived(SCREENS[session.section])
</script>

<div class="app">
  <main class="app__main">
    <Topbar {session}
            onsession={(next) => { session = next }}
            onsearch={() => {}} onadd={() => {}} onfilter={() => {}} />

    <div class="content">
      <!-- `{#key}` здесь не украшение: без него Svelte переиспользует ту же
           секцию, `screen-in` не проигрывается, и переход между разделами
           становится мгновенной подменой. -->
      {#key session.section}
        <section class="view is-shown">
          <Screen />
        </section>
      {/key}
    </div>
  </main>

  <Snack message={trouble} />
</div>
