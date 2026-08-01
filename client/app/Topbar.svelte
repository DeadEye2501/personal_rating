<!-- Сборка шапки: три зоны и всё, что в них нажимается. -->
<script>
  import SearchField from '$components/SearchField.svelte'
  import Segmented from '$components/Segmented.svelte'
  import ToolButton from '$components/ToolButton.svelte'
  import { isEmpty } from '$state/filters.js'
  import { redrawn } from '$state/redraw.js'
  import { withCollapsed, withKind, withNextSort, withToggledSection }
    from '$state/session.js'
  import { hasSort, stateAt } from '$state/sorting.js'

  let { session, onsession, onsearch, onadd, onfilter } = $props()

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
    })
    watch.observe(seg)
    return () => watch.disconnect()
  })

  const KINDS = [
    { value: 'movie',  icon: 'movie',           label: 'Фильмы' },
    { value: 'series', icon: 'live_tv',         label: 'Сериалы' },
    { value: 'game',   icon: 'sports_esports',  label: 'Игры' },
  ]

  // Фильмам достаётся значение по умолчанию из палитры, поэтому его тут нет:
  // положить одно значение в два места значит дать ему разойтись. Остальные два
  // подставляются токенами, а не литералами — цвет живёт в палитре.
  const ACCENTS = { series: 'var(--accent-series)', game: 'var(--accent-game)' }

  const VIEWS = [
    { value: 'rated',    icon: 'thumb_up', label: 'Оценённые' },
    { value: 'wishlist', icon: 'bookmark', label: 'Хочу посмотреть' },
  ]

  const FILTERS = [
    { field: 'genres', icon: 'category', label: 'Жанры' },
    { field: 'tags',   icon: 'label',    label: 'Теги' },
    { field: 'scores', icon: 'star',     label: 'Фильтр по оценке' },
  ]

  // Вид кнопки — из состояния своего раздела: позиция 0 в отложенном и в
  // оценённых означает разное. Раздел без переключателя даёт `null`, а не
  // состояние: своего набора у него нет, и спрошенный за него `stateAt`
  // обязан не отвечать вовсе.
  const sort = $derived(hasSort(session.section)
    ? stateAt(session.section, session.sort)
    : null)

  // Акцент следует за состоянием, а не за нажатием: перекрась его в
  // обработчике — и тип, восстановленный откуда-то ещё, приедет со старым
  // цветом, а расхождения не увидит никто.
  $effect(() => {
    const root = document.documentElement.style
    const accent = ACCENTS[session.kind]
    accent ? root.setProperty('--primary', accent) : root.removeProperty('--primary')
  })

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
  <SearchField {onsearch} />

  <!-- Замеряется обёртка, а не сам переключатель: ссылку на свой корень
       компонент наружу не отдаёт, и просить её значило бы завести ему входной
       параметр ради чужой раскладки. -->
  <div bind:this={seg} class="topbar__seg">
    <Segmented items={KINDS} chosen={session.kind}
               onchoose={(kind) => onsession(withKind(session, kind))} />
  </div>

  <div class="tools" bind:this={tools}>
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
                  onclick={() => onfilter(filter.field)} />
    {/each}

    <!-- Подсветки нет намеренно, и это макет: в этом ряду акцентом горит то,
         что отбирает содержимое — раздел и фильтр. Тумблер свёрнутости
         содержимого не отбирает и сообщает состояние сменой глифа. -->
    <ToolButton icon={session.collapsed ? 'unfold_more' : 'unfold_less'}
                label={session.collapsed ? 'Развернуть всё' : 'Свернуть всё'}
                pressed={session.collapsed}
                onclick={() => onsession(withCollapsed(session, !session.collapsed))} />

    <!-- Только там, где сортировка действует. В поиске порядок задан склейкой
         двух половин, в статистике сортировать нечего — кнопка, которая
         перебирает восемь состояний и не меняет ничего, обманывает. -->
    {#if sort}
      <ToolButton icon={sort.icon} dir={sort.dir}
                  label={'Сортировка: ' + sort.label.toLowerCase()}
                  onclick={() => onsession(withNextSort(session))} />
    {/if}

    <ToolButton icon="add" label="Завести карточку" onclick={onadd} />
  </div>
</header>
