<!-- Теги одной карточки: тот же список, но два состояния вместо трёх —
     исключать тег у конкретной карточки нечего. -->
<script>
  import ListModal from '$components/ListModal.svelte'
  import NewTag from '$components/NewTag.svelte'
  import TagRow from '$components/TagRow.svelte'
  import { call } from '$api/bridge.js'
  import { NOUNS } from '$state/kinds.js'
  import { created } from './tags.js'
  import { reported } from './trouble.js'

  // Заголовок собирается из общей таблицы форм, а не пишется вторым списком:
  // «Теги» плюс родительный падеж единственного числа.

  let { view, onview, onclose, ontrouble } = $props()

  // Простыми значениями, а не чтением `view` по месту: карточка приходит
  // геттером над состоянием сборки, и эффект будился бы её обновлением.
  const kind = $derived(view.kind)
  const itemId = $derived(view.item_id)

  let rows = $state([])
  // Пока в окне ничего не трогали, отмечено то, что приехало с карточкой.
  let picked = $state(null)
  const mine = $derived(picked ?? new Set(view.tags.map((tag) => tag.id)))

  $effect(() => {
    call('marks.tags', kind)
      .then((list) => { rows = list })
      .catch((error) => lost(error, 'Не удалось прочитать теги'))
  })

  const lost = (error, text) => reported(error, 'теги карточки', () => ontrouble(text))

  /** Отметка ставится до ответа моста и снимается обратно, если он отказал.
   *
   *  Иначе два быстрых щелчка по одной строке читают одно и то же «сейчас не
   *  отмечено» и оба шлют `assign`: состояние страницы разъезжается с базой на
   *  ровном месте. Заодно строка отзывается сразу, а не через границу потоков. */
  async function toggle(tag) {
    const on = mine.has(tag.id)

    const next = new Set(mine)
    on ? next.delete(tag.id) : next.add(tag.id)
    picked = next
    // Карточка в ленте обязана показать метку сразу: перечитывать её целиком
    // ради одной строки незачем.
    onview(rows.filter((row) => next.has(row.id)))

    try {
      await call(on ? 'marks.unassign' : 'marks.assign', itemId, tag.id)
    } catch (error) {
      // Возвращаем свою метку в то, что стало **сейчас**, а не слепок до
      // границы потоков: соседний щелчок мог успеть записаться, и слепком мы
      // стёрли бы удавшееся вместе с неудавшимся.
      const back = new Set(mine)
      on ? back.add(tag.id) : back.delete(tag.id)
      picked = back
      onview(rows.filter((row) => back.has(row.id)))
      lost(error, 'Метка не сохранилась')
    }
  }

  /** Тот же `created`, что и у модалки фильтра. Ответ возвращается наружу: по
   *  нему форма решает, очищать ли набранное. */
  const create = (name) =>
    created(kind, name, ontrouble).then((row) => {
      if (row) rows = [...rows, row]
      return row
    })
</script>

{#snippet form()}<NewTag oncreate={create} />{/snippet}

<ListModal label={`Теги ${NOUNS[kind][1]}`} {onclose} footer={form}>
  {#snippet items()}
    {#each rows as row (row.id)}
      <TagRow name={row.name} state={mine.has(row.id) ? 'on' : 'off'}
              ontoggle={() => toggle(row)} />
    {/each}
  {/snippet}
</ListModal>
