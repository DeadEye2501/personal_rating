<!-- Обе половины библиотеки: «Оценённые» и «Хочу посмотреть». Черновик: спрашивает
     одно и то же и ничем не управляет — настоящий раздел собирает задача 6. -->
<script>
  import Film from '$components/Film.svelte'
  import { numbered } from '$api/bridge.js'

  let views = $state([])

  $effect(() => {
    numbered('feed.page', { section: 'rated', kind: 'movie', filters: {},
                            order: { key: 'score', descending: true } }, 0, 50,
             { channel: 'feed' })
      .then((page) => { views = page })
  })
</script>

<div class="feed">
  {#each views as view (view.source + ' ' + view.source_id)}
    <Film {view} onperson={() => {}} ontag={() => {}} oncollapse={() => {}} />
  {/each}
</div>
