<!-- Три фильтра одной сборкой: жанры, теги и оценки. Списки разные, поведение
     строки общее; правку набора имеет только теговый. -->
<script>
  import Confirm from '$components/Confirm.svelte'
  import ListModal from '$components/ListModal.svelte'
  import NewTag from '$components/NewTag.svelte'
  import ScoreRow from '$components/ScoreRow.svelte'
  import TagRow from '$components/TagRow.svelte'
  import { call } from '$api/bridge.js'
  import { plural } from '$state/facts.js'
  import { cycled, stateOf } from '$state/filters.js'
  import { dragging } from '$state/dragging.js'
  import { dragged } from '$state/reorder.js'
  import { SCALE } from '$state/scores.js'
  import { created } from './tags.js'
  import { reported } from './trouble.js'

  // Наборов жанров два на три типа содержимого: фильмы и сериалы делят один.
  // Таблицей, а не тернарником: таблицу сторожит `test_page_contract.py` — это
  // имена `Kind` и `GenreKind`, а страница питон не читает.
  const GENRE_KINDS = { movie: 'film', series: 'film', game: 'game' }

  // Существительное — по открытой вкладке, как в макете: «3 фильма», «3 игры».
  const NOUNS = { movie: ['фильм', 'фильма', 'фильмов'],
                  series: ['сериал', 'сериала', 'сериалов'],
                  game: ['игра', 'игры', 'игр'] }
  const WEARS = ['имеет', 'имеют', 'имеют']

  // Список открывается на высоких оценках: их ищут чаще.
  const HIGH_FIRST = SCALE.toReversed()

  let { field, kind, title, filters, onfilters, onforget, onclose, ontrouble }
    = $props()

  let rows = $state([])
  // Тег с носителями спрашивает подтверждения и называет их число.
  let asking = $state(null)
  let moving = $state(null)

  // Набор правят только у тегов: набор жанров зашит в миграцию, набор оценок —
  // это десять чисел.
  const editable = $derived(field === 'tags')

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

  const lost = (error, text) => reported(error, title, () => ontrouble(text))

  const toggle = (id) => onfilters(cycled(filters, field, id))

  /** Удаление тега бьёт по всей библиотеке и не отменяется, поэтому у тега с
   *  носителями оно спрашивает и называет их число. Ничей уходит молча: терять
   *  нечего, и спрашивать не о чем. */
  async function remove(row) {
    try {
      const worn = await call('marks.tag_usage', row.id)
      if (worn) { asking = { row, worn }; return }
    } catch (error) {
      lost(error, 'Не удалось удалить тег')
      return
    }
    drop(row)
  }

  async function drop(row) {
    asking = null
    try {
      await call('marks.delete_tag', row.id)
    } catch (error) {
      lost(error, 'Не удалось удалить тег')
      return
    }
    rows = rows.filter((each) => each.id !== row.id)
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
    const list = event.currentTarget.closest('.taglist')
    const before = rows
    const row = rows[at]
    let from = at
    moving = row.id
    // Курсор «схватил» строку целиком, а не только ручку. Ставится по месту, а
    // не классом: пока таска идёт, он нужен на всём документе, а такого блока
    // оформления не бывает.
    document.body.style.cursor = 'grabbing'

    dragging(list, event, (point) => {
      const middles = [...list.querySelectorAll('.tagrow')].map((node) => {
        const box = node.getBoundingClientRect()
        return box.top + box.height / 2
      })
      rows = dragged(rows, from, middles, point.clientY)
      from = rows.indexOf(row)
    }, () => {
      moving = null
      document.body.style.cursor = ''
      if (from === at) return
      call('marks.reorder_tags', kind, rows.map((row) => row.id))
        .catch((error) => { rows = before; lost(error, 'Порядок не сохранился') })
    })
  }
</script>

{#snippet form()}<NewTag oncreate={create} />{/snippet}

<ListModal narrow={field === 'scores'} label={title} {onclose}
           footer={editable ? form : null}>
  {#snippet items()}
    {#if field === 'scores'}
      {#each HIGH_FIRST as score (score)}
        <ScoreRow {score} state={stateOf(filters, field, score)}
                  ontoggle={() => toggle(score)} />
      {/each}
    {:else}
      {#each rows as row, at (row.id)}
        <TagRow name={row.name} state={stateOf(filters, field, row.id)}
                dragging={moving === row.id}
                ontoggle={() => toggle(row.id)}
                ondelete={editable ? () => remove(row) : null}
                ongrab={editable ? (event) => grab(event, at) : null} />
      {/each}
    {/if}
  {/snippet}
</ListModal>

{#if asking}
  <Confirm label="Удалить тег" ok="Удалить" danger
           text={`Удалить тег «${asking.row.name}»? ${asking.worn} `
                 + `${plural(asking.worn, NOUNS[kind])} `
                 + `${plural(asking.worn, WEARS)} этот тег.`}
           onyes={() => drop(asking.row)}
           onclose={() => { asking = null }} />
{/if}
