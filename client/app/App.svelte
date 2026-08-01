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

  let session = $state(newSession())

  // Плашка одна на всё приложение, и говорят в неё разделы. Сегодня они пусты,
  // сообщать нечем, и она стоит за краем окна.
  let trouble = $state(null)

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
