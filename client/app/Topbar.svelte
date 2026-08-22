<!-- Сборка шапки: три зоны и всё, что в них нажимается. -->
<script>
  import SearchField from '$components/SearchField.svelte'
  import Segmented from '$components/Segmented.svelte'
  import ToolButton from '$components/ToolButton.svelte'
  import { isEmpty } from '$state/filters.js'
  import { redrawn } from '$state/redraw.js'
  import { wishOf } from '$state/kinds.js'
  import { withCollapsed, withKind, withNextSort, withToggledSection }
    from '$state/session.js'
  import { IDLE_SORT, hasSort, stateAt } from '$state/sorting.js'

  let { session, typed = $bindable(''), onsession, onsearch, onadd,
        onfilter } = $props()

  let bar = $state()
  let seg = $state()
  let tools = $state()

  /**
   * Ширина боковых зон считается замером, а не числом: подписи «Хочу
   * посмотреть» и «Фильтр по оценке» длиннее любой догадки, и на глаз шапка
   * разъедется на первом же шрифте.
   *
   * Замер живёт здесь, а не в сборке: шапка владеет обеими зонами и своей
   * переменной, а сборка добиралась бы до них `querySelector` по именам
   * классов — то есть знала бы про чужую разметку, а не про входные параметры.
   *
   * Следим за самой капсулой, а не за окном и не за готовностью шрифтов.
   * Замерено: одного замера по `document.fonts.ready` не хватает — шрифт
   * подменяется позже, чем тот срабатывает, и капсула успевает съёжиться с 460
   * до 367 уже после замера. Переспросить в той схеме некому, и шапка остаётся
   * шире окна с обрезанным рядом кнопок.
   */
  $effect(() => {
    if (!seg || !bar) return
    const watch = new ResizeObserver(() => {
      bar.style.setProperty('--side-w', `${Math.ceil(seg.offsetWidth)}px`)
      // Содержимое шириной с полосу шапки: иначе лента разъедется с ней ровно
      // на столько, на сколько замер поправил боковые зоны.
      //
      // Считается из зон, а не из самой шапки: `.topbar` — растянутый элемент
      // колоночного флекса, и его ширина это ширина окна. Полоса — три зоны по
      // ширине капсулы плюс два зазора между ними; зазор читается из
      // оформления, чтобы не оказаться числом в двух местах.
      //
      // Величина уходит на корень документа, а не на шапку: читают её разделы,
      // а шапка ею только владеет — она единственная, кто знает свою ширину.
      const gap = parseFloat(getComputedStyle(bar).columnGap) || 0
      document.documentElement.style.setProperty(
        '--content-w', `${Math.ceil(seg.offsetWidth * 3 + gap * 2)}px`)
    })
    watch.observe(seg)
    return () => watch.disconnect()
  })

  const KINDS = [
    { value: 'movie',  icon: 'movie',           label: 'Фильмы' },
    { value: 'series', icon: 'live_tv',         label: 'Сериалы' },
    { value: 'game',   icon: 'sports_esports',  label: 'Игры' },
    { value: 'book',   icon: 'menu_book',       label: 'Книги' },
    { value: 'music',  icon: 'music_note',      label: 'Музыка' },
  ]

  // Подпись второго раздела зависит от типа, поэтому список считается, а не
  // объявляется: у книги читают, у музыки слушают.
  const VIEWS = $derived([
    { value: 'rated',    icon: 'thumb_up', label: 'Оценённые' },
    { value: 'wishlist', icon: 'bookmark', label: wishOf(session.kind) },
  ])

  const FILTERS = [
    { field: 'genres', icon: 'category', label: 'Жанры' },
    { field: 'tags',   icon: 'label',    label: 'Теги' },
    { field: 'scores', icon: 'star',     label: 'Фильтр по оценке' },
  ]

  // Вид кнопки — из состояния своего раздела: позиция 0 в отложенном и в
  // оценённых означает разное. У раздела без переключателя своего набора нет, и
  // спрошенный за него `stateAt` обязан не отвечать вовсе — поэтому вид ему
  // достаётся готовый, из `IDLE_SORT`.
  const off = $derived(!hasSort(session.section))
  const sort = $derived(off ? IDLE_SORT : stateAt(session.section, session.sort))

  function chooseStats() {
    // Признак вешается на каждый заход, а не держится состоянием: иначе
    // столбики иконки отрастут один раз за всё время работы. Идёт он прямо на
    // узел, потому что перезапуск требует пересчёта стилей между снятием и
    // возвратом, а через реактивную ячейку такого зазора не сделать.
    redrawn(tools, 'is-drawing')
    onsession(withToggledSection(session, 'stats'))
  }
</script>

<header class="topbar" bind:this={bar}>
  <SearchField {onsearch} bind:value={typed} />

  <!-- Замеряется обёртка, а не сам переключатель: ссылку на свой корень
       компонент наружу не отдаёт, и просить её значило бы завести ему входной
       параметр ради чужой раскладки. -->
  <div bind:this={seg} class="topbar__seg">
    <Segmented items={KINDS} chosen={session.kind}
               onchoose={(kind) => onsession(withKind(session, kind))} />
  </div>

  <div class="zone tools" bind:this={tools}>
    {#each VIEWS as view (view.value)}
      <ToolButton icon={view.icon} label={view.label}
                  active={session.section === view.value}
                  pressed={session.section === view.value}
                  onclick={() => onsession(withToggledSection(session, view.value))} />
    {/each}

    <ToolButton label="Статистика" active={session.section === 'stats'}
                pressed={session.section === 'stats'} onclick={chooseStats}>
      {#snippet children()}
        <svg class="tools__chart" viewBox="0 0 24 24" aria-hidden="true">
          <rect x="4"  y="9"  width="4" height="11" />
          <rect x="10" y="4"  width="4" height="16" />
          <rect x="16" y="13" width="4" height="7" />
        </svg>
      {/snippet}
    </ToolButton>

    {#each FILTERS as filter (filter.field)}
      <ToolButton icon={filter.icon} label={filter.label}
                  active={!isEmpty(session.filters, filter.field)}
                  pressed={!isEmpty(session.filters, filter.field)}
                  onclick={() => onfilter(filter.field, filter.label)} />
    {/each}

    <!-- Подсветки нет намеренно, и это макет: в этом ряду акцентом горит то,
         что отбирает содержимое — раздел и фильтр. Тумблер свёрнутости
         содержимого не отбирает и сообщает состояние сменой глифа. -->
    <ToolButton icon={session.collapsed ? 'unfold_more' : 'unfold_less'}
                label={session.collapsed ? 'Развернуть всё' : 'Свернуть всё'}
                pressed={session.collapsed}
                onclick={() => onsession(withCollapsed(session, !session.collapsed))} />

    <!-- Кнопка стоит в ряду всегда, а там, где сортировки нет, гаснет и молчит.
         Снятая, она двигала бы восьмерых соседей на каждом переходе между
         разделами; работающая — обманывала бы, перебирая восемь состояний без
         последствий: в поиске порядок задан склейкой двух половин, в статистике
         сортировать нечего. -->
    <ToolButton icon={sort.icon} dir={sort.dir} disabled={off}
                label={off ? 'В этом разделе сортировки нет'
                           : 'Сортировка: ' + sort.label.toLowerCase()}
                onclick={() => onsession(withNextSort(session))} />

    <ToolButton icon="add" label="Завести карточку" onclick={onadd} />
  </div>
</header>
