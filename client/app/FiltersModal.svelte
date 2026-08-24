<!-- Три фильтра одной сборкой: жанры, теги и оценки. Списки разные, поведение
     строки общее; правку набора имеет только теговый. -->
<script>
  import Confirm from '$components/Confirm.svelte'
  import ListModal from '$components/ListModal.svelte'
  import AddLine from '$components/AddLine.svelte'
  import ScoreHead from '$components/ScoreHead.svelte'
  import ScoreRow from '$components/ScoreRow.svelte'
  import TagRow from '$components/TagRow.svelte'
  import { call } from '$api/bridge.js'
  import { worn } from '$state/removal.js'
  import { cycled, stateOf } from '$state/filters.js'
  import { dragging } from '$state/dragging.js'
  import { dragged } from '$state/reorder.js'
  import { GENRE_KINDS } from '$state/genres.js'
  import { ASPECTS, scale } from '$state/scores.js'
  import { created } from './tags.js'
  import { dropped, ordered, wearers } from './tagset.js'
  import { complaining } from './trouble.js'

  // Список открывается на высоких оценках: их ищут чаще.
  const HIGH_FIRST = scale().toReversed()

  let { field, kind, title, filters, onfilters, onforget, onclose, ontrouble }
    = $props()

  let rows = $state([])
  // Тег с носителями спрашивает подтверждения и называет их число.
  let asking = $state(null)
  let moving = $state(null)

  // Набор правят только у тегов: набор жанров зашит в миграцию, набор оценок —
  // это десять чисел.
  const editable = $derived(field === 'tags')

  // Колонки окна оценки. У игры их четыре — общая и три шкалы, — и отбирают
  // они порознь: внутри колонки «или», между колонками «и». У остальных типов
  // шкал не бывает вовсе, колонка одна и безымянная: называть в ней нечего.
  const columns = $derived(kind === 'game'
    ? [{ field: 'scores', label: 'Общая' },
       ...ASPECTS.map((one) => ({ field: one.key, label: one.label }))]
    : [{ field: 'scores' }])

  // Сетка бывает только у окна оценки: `columns` считается по типу содержимого
  // и про признак не знает, так что у жанров с тегами во вкладке игр он тоже
  // насчитал бы четыре.
  const grid = $derived(field === 'scores' && columns.length > 1)

  // Что спрашивать — двумя простыми значениями, а не по месту в эффекте: `kind`
  // приходит геттером над всем сеансом, и прочитанный там он будил бы запрос на
  // каждый щелчок по строке. Наборов тегов три, по одному на тип содержимого.
  const path = $derived(field === 'genres' ? 'refs.genres' : 'marks.tags')
  const asked = $derived(field === 'genres' ? GENRE_KINDS[kind] : kind)

  $effect(() => {
    if (field === 'scores') return
    call(path, asked)
      .then((list) => { rows = list })
      .catch((error) => lost(error, 'Не удалось прочитать список'))
  })

  const lost = complaining(title, ontrouble)

  // Признак называется доводом, а не берётся из `field`: у окна оценки их
  // четыре, по одному на колонку, и общее у них только само окно.
  const toggle = (named, id) => onfilters(cycled(filters, named, id))

  /** Удаление тега бьёт по всей библиотеке и не отменяется, поэтому у тега с
   *  носителями оно спрашивает и называет их число. Ничей уходит молча: терять
   *  нечего, и спрашивать не о чем. */
  async function remove(row) {
    try {
      const count = await wearers(row.id)
      if (count) { asking = { row, count }; return }
    } catch (error) {
      lost(error, 'Не удалось удалить тег')
      return
    }
    drop(row)
  }

  async function drop(row) {
    asking = null
    try {
      rows = await dropped(rows, row.id)
    } catch (error) {
      lost(error, 'Не удалось удалить тег')
      return
    }
    // Номер, оставшийся в фильтре или на карточке ленты, показывал бы отбор по
    // мертвецу, и выключить его было бы нечем: строки в списке уже нет.
    onforget(row.id)
  }

  /** Тот же `created`, что и у модалки тегов карточки. Ответ возвращается
   *  наружу: по нему форма решает, очищать ли набранное. */
  const create = (name) =>
    created(kind, name, ontrouble).then((row) => {
      if (row) rows = [...rows, row]
      return row
    })

  /** Порядок ручной, и пережить перезапуск он обязан: без вызова перестановка
   *  живёт до закрытия окна. */
  function grab(event, at) {
    // Список берётся строением, а не по имени класса: класс принадлежит чужой
    // разметке — списку наложения и строке, — и переименование в ней молча
    // убило бы перетаскивание. Строение своё: строка это `li`, а список — то,
    // что её содержит.
    const list = event.currentTarget.closest('li').parentElement
    const before = rows
    const row = rows[at]
    let from = at
    moving = row.id
    // Курсор «схватил» строку целиком, а не только ручку. Ставится по месту, а
    // не классом: пока таска идёт, он нужен на всём документе, а такого блока
    // оформления не бывает.
    document.body.style.cursor = 'grabbing'

    dragging(list, event, (point) => {
      const middles = [...list.children].map((node) => {
        const box = node.getBoundingClientRect()
        return box.top + box.height / 2
      })
      rows = dragged(rows, from, middles, point.clientY)
      from = rows.indexOf(row)
    }, () => {
      moving = null
      document.body.style.cursor = ''
      if (from === at) return
      ordered(rows, kind)
        .catch((error) => { rows = before; lost(error, 'Порядок не сохранился') })
    })
  }
</script>

{#snippet head()}<ScoreHead {columns} />{/snippet}

{#snippet form()}<AddLine placeholder="+ Новый тег" label="Название нового тега" action="Добавить тег"
                          limit={24} oncreate={create} />{/snippet}

<ListModal narrow={field === 'scores' && !grid} label={title} {onclose}
           head={grid ? head : null} footer={editable ? form : null}>
  {#snippet items()}
    {#if field === 'scores'}
      {#each HIGH_FIRST as score (score)}
        <ScoreRow {score} columns={columns.map((column) => ({
          ...column,
          state: stateOf(filters, column.field, score),
          ontoggle: () => toggle(column.field, score),
        }))} />
      {/each}
    {:else}
      {#each rows as row, at (row.id)}
        <TagRow name={row.name} state={stateOf(filters, field, row.id)}
                moving={moving === row.id}
                ontoggle={() => toggle(field, row.id)}
                ondelete={editable ? () => remove(row) : null}
                ongrab={editable ? (event) => grab(event, at) : null} />
      {/each}
    {/if}
  {/snippet}
</ListModal>

{#if asking}
  <Confirm label="Удалить тег" ok="Удалить" danger
           text={worn(asking.row.name, asking.count, kind)}
           onyes={() => drop(asking.row)}
           onclose={() => { asking = null }} />
{/if}
