<!-- Строки фактов карточки: длительность или сезоны, кто сделал, кто играл. -->
<script>
  import { ROLES } from '$state/credits.js'
  import { castOf, runtimeOf, seriesOf } from '$state/facts.js'

  let { view, onperson } = $props()

  // Единственная подпись, которая на карточке звучит иначе, чем в форме:
  // «В ролях» — про эту карточку, «Актёры» — про поле ввода.
  const CAST = 'В ролях'

  const ROWS = ROLES.map((one) =>
    one.role === 'actor' ? { ...one, label: CAST } : one)

  const length = $derived(view.kind === 'series'
    ? seriesOf(view.seasons_count, view.episodes_count)
    : runtimeOf(view.runtime))

  // Строки несут не имена, а сами титры: клик по имени зовёт поиск по
  // **номеру строки** человека — имя тёзку не различает.
  const rows = $derived(ROWS
    .map((row) => ({ ...row, credits: castOf(view[row.domain] ?? [], row.role) }))
    .filter((row) => row.credits.length))
</script>

<dl class="film__facts">
  {#if length}
    <dt>{view.kind === 'series' ? 'Сезоны' : 'Длительность'}</dt>
    <dd>{length}</dd>
  {/if}

  {#each rows as row (row.label)}
    <dt>{row.label}</dt>
    <dd>
      {#each row.credits as credit, index (credit.entity_id)}
        {#if index}, {/if}
        <button type="button" class="person"
                onclick={() => onperson(row.domain, credit.entity_id)}
        >{credit.name}</button>
      {/each}
    </dd>
  {/each}
</dl>
