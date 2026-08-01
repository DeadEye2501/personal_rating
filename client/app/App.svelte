<!-- Корень страницы: шапка и место под содержимое разделов. -->
<script>
  import Topbar from './Topbar.svelte'
  import { newSession } from '$state/session.js'

  let session = $state(newSession())
</script>

<div class="app">
  <main class="app__main">
    <Topbar {session}
            onsession={(next) => { session = next }}
            onsearch={() => {}} onadd={() => {}} onfilter={() => {}} />
    <div class="content"></div>
  </main>
</div>
