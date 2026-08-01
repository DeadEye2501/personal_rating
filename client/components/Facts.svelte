<!-- Строки фактов карточки: длительность или сезоны, кто сделал, кто играл. -->
<script>
  import { castOf, runtimeOf, seriesOf } from '$state/facts.js'

  let { view, onperson } = $props()

  // Кто сделал — раньше, чем кто играл: у фильма режиссёр, у сериала
  // шоураннер, у игры разработчик и издатель.
  const ROWS = [
    { label: 'Режиссёр', from: 'people', role: 'director' },
    { label: 'Шоураннер', from: 'people', role: 'showrunner' },
    { label: 'Разработчик', from: 'companies', role: 'developer' },
    { label: 'Издатель', from: 'companies', role: 'publisher' },
    { label: 'В ролях', from: 'people', role: 'actor' },
  ]

  const length = $derived(view.kind === 'series'
    ? seriesOf(view.seasons_count, view.episodes_count)
    : runtimeOf(view.runtime))

  // Строки несут не имена, а сами титры: клик по имени зовёт поиск по
  // **номеру строки** человека — имя тёзку не различает.
  const rows = $derived(ROWS
    .map((row) => ({ ...row, credits: castOf(view[row.from] ?? [], row.role) }))
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
                onclick={() => onperson(row.from, credit.entity_id)}
        >{credit.name}</button>
      {/each}
    </dd>
  {/each}
</dl>
