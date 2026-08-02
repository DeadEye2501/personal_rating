<!-- Строки фактов карточки: длительность или сезоны, кто сделал, кто играл.
     Длинный состав свёрнут до пятерых, пока не развернут. -->
<script>
  import { ROLES } from '$state/credits.js'
  import { castOf, hiddenOf, runtimeOf, seriesOf } from '$state/facts.js'

  let { view, onperson } = $props()

  // Единственная подпись, которая на карточке звучит иначе, чем в форме:
  // «В ролях» — про эту карточку, «Актёры» — про поле ввода.
  const CAST = 'В ролях'

  const ROWS = ROLES.map((one) =>
    one.role === 'actor' ? { ...one, label: CAST } : one)

  // Роли, которые человек развернул. Свёрнуто по умолчанию, а не наоборот:
  // почему — сказано у предела в `state/facts.js`.
  let opened = $state([])

  const length = $derived(view.kind === 'series'
    ? seriesOf(view.seasons_count, view.episodes_count)
    : runtimeOf(view.runtime))

  // Строки несут не имена, а сами титры: клик по имени зовёт поиск по
  // **номеру строки** человека — имя тёзку не различает.
  const rows = $derived(ROWS
    .map((row) => {
      const credits = view[row.domain] ?? []
      return opened.includes(row.role)
        ? { ...row, credits: castOf(credits, row.role, Infinity),
            hidden: 0, full: true }
        : { ...row, credits: castOf(credits, row.role),
            hidden: hiddenOf(credits, row.role), full: false }
    })
    .filter((row) => row.credits.length))

  /** Одна кнопка на оба хода, на своём месте: у сериала состав бывает в две
   *  сотни имён, и без обратного хода карточка занимала три экрана до конца
   *  сеанса — свёрнутой её возвращало только перечитывание. */
  const flip = (role) => {
    opened = opened.includes(role)
      ? opened.filter((one) => one !== role)
      : [...opened, role]
  }
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
      {#if row.hidden || row.full}
        <button type="button" class="more" onclick={() => flip(row.role)}
        >{row.full ? 'свернуть' : `… ещё ${row.hidden}`}</button>
      {/if}
    </dd>
  {/each}
</dl>
