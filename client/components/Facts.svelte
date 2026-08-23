<!-- Строки фактов карточки: длительность или сезоны, кто сделал, кто играл, а
     у альбома — треки. Длинный список свёрнут до пятерых, пока не развернут. -->
<script>
  import { ROLES } from '$state/credits.js'
  import { castOf, firstOf, hiddenOf, leftOf, runtimeOf, seriesOf }
    from '$state/facts.js'

  let { view, onperson } = $props()

  // Единственная подпись, которая на карточке звучит иначе, чем в форме:
  // «В ролях» — про эту карточку, «Актёры» — про поле ввода.
  const CAST = 'В ролях'

  const ROWS = ROLES.map((one) =>
    one.role === 'actor' ? { ...one, label: CAST } : one)

  // Строки, которые человек развернул. Свёрнуто по умолчанию, а не наоборот:
  // почему — сказано у предела в `state/facts.js`. Треки стоят в том же
  // списке под своим именем: сворачиваются они так же, а роли у них нет.
  const TRACKS = 'tracks'

  // Чем треки отделяются друг от друга. Не запятой: у названий она бывает
  // внутри — «Закрой за мной дверь, я ухожу» и «Мама, мы все сошли с ума» у
  // одного альбома, — и одиннадцать треков читались бы как тринадцать, причём
  // второй кусок с маленькой буквы. Решение пользователя 23.08.2026.
  //
  // Свой, а не общий с точкой из `Picker.svelte`: там она делит имя и подсказку
  // одной строки, здесь — соседние названия списка, и менять их надо порознь.
  const DOT = '•'

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

  // Треки не титры: у них нет ни номера строки, ни роли, и клик по ним не
  // ведёт никуда — искать по названию трека нечего. Решение 22.08.2026.
  const tracks = $derived(opened.includes(TRACKS)
    ? { shown: firstOf(view.tracks, Infinity), hidden: 0, full: true }
    : { shown: firstOf(view.tracks), hidden: leftOf(view.tracks), full: false })

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

  {#if view.tracks.length}
    <dt>Треки</dt>
    <dd>
      <!-- Разделитель выражением, а не разметкой: `{#if index}, {/if}` теряет
           свой пробел — Svelte срезает пробельный хвост блока, а между ним и
           названием другого пробельного узла нет. У соседей выше пробел
           выживает случайно: там следом идёт `<button>` с переводом строки
           перед ним. -->
      {#each tracks.shown as title, index (index)}{index ? ` ${DOT} ` : ''}{title}{/each}
      {#if tracks.hidden || tracks.full}
        <button type="button" class="more" onclick={() => flip(TRACKS)}
        >{tracks.full ? 'свернуть' : `… ещё ${tracks.hidden}`}</button>
      {/if}
    </dd>
  {/if}
</dl>
