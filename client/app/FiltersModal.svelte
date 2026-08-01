<!-- Три фильтра одной сборкой: жанры, теги и оценки. Списки разные, поведение
     строки общее. -->
<script>
  import Modal from '$components/Modal.svelte'
  import ScoreRow from '$components/ScoreRow.svelte'
  import Scrollarea from '$components/Scrollarea.svelte'
  import TagRow from '$components/TagRow.svelte'
  import { call } from '$api/bridge.js'
  import { cycled, stateOf } from '$state/filters.js'
  import { SCALE } from '$state/scores.js'
  import { reported } from './trouble.js'

  // Наборов жанров два на три типа содержимого: фильмы и сериалы делят один.
  // Таблицей, а не тернарником: таблицу сторожит `test_page_contract.py` — это
  // имена `Kind` и `GenreKind`, а страница питон не читает.
  const GENRE_KINDS = { movie: 'film', series: 'film', game: 'game' }

  // Список открывается на высоких оценках: их ищут чаще.
  const HIGH_FIRST = SCALE.toReversed()

  let { field, kind, title, filters, onfilters, onclose, ontrouble } = $props()

  let rows = $state([])

  // Что спрашивать — двумя простыми значениями, а не по месту в эффекте: `kind`
  // приходит геттером над всем сеансом, и прочитанный там он будил бы запрос на
  // каждый щелчок по строке. Наборов тегов три, по одному на тип содержимого.
  const path = $derived(field === 'genres' ? 'refs.genres' : 'marks.tags')
  const asked = $derived(field === 'genres' ? GENRE_KINDS[kind] : kind)

  $effect(() => {
    if (field === 'scores') return
    call(path, asked)
      .then((list) => { rows = list })
      .catch((error) => reported(error, title,
                                 () => ontrouble('Не удалось прочитать список')))
  })

  const toggle = (id) => onfilters(cycled(filters, field, id))
</script>

<Modal narrow={field === 'scores'} label={title} {onclose}>
  {#snippet children()}
    <Scrollarea>
      {#snippet children()}
        <ul class="taglist">
          {#if field === 'scores'}
            {#each HIGH_FIRST as score (score)}
              <ScoreRow {score} state={stateOf(filters, field, score)}
                        ontoggle={() => toggle(score)} />
            {/each}
          {:else}
            {#each rows as row (row.id)}
              <TagRow name={row.name} state={stateOf(filters, field, row.id)}
                      ontoggle={() => toggle(row.id)} />
            {/each}
          {/if}
        </ul>
      {/snippet}
    </Scrollarea>
  {/snippet}
</Modal>
