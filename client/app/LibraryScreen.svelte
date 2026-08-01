<!-- Обе половины библиотеки: «Оценённые» и «Хочу посмотреть». Черновик: спрашивает
     одно и то же и ничем не управляет — настоящий раздел собирает задача 6. -->
<script>
  import Film from '$components/Film.svelte'
  import { numbered } from '$api/bridge.js'

  let views = $state([])
  // Сколько оценок агрегаторов ждать. Без этого списка блок оценок пуст у
  // кино: у него они приезжают отдельным кругом, и до ответа сети на их месте
  // должны крутиться кружки.
  let expected = $state([])

  $effect(() => {
    numbered('feed.page', { section: 'rated', kind: 'movie', filters: {},
                            order: { key: 'score', descending: true } }, 0, 50,
             { channel: 'feed' })
      .then((page) => { views = page })
    numbered('world.expected', 'movie', { channel: 'expected' })
      .then((sources) => { expected = sources })
  })

  // Обработчики черновика молчат: жесты карточки заводит задача 6, а до неё
  // нажатие обязано хотя бы не ронять страницу.
  const idle = () => {}
</script>

<div class="feed">
  {#each views as view (view.source + ' ' + view.source_id)}
    <Film {view} {expected} onperson={idle} ontag={idle} oncollapse={idle}
          onmark={idle} onopen={idle} onscore={idle} onaspect={idle}
          onedit={idle} ondelete={idle} onwish={idle} />
  {/each}
</div>
