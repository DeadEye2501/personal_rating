<!-- Обе половины библиотеки: «Оценённые» и «Хочу посмотреть». Черновик: раздел
     не выбирается, фильтры и сортировка не передаются — это задача 6. -->
<script>
  import Feed from '$components/Feed.svelte'
  import { numbered } from '$api/bridge.js'
  import { onCardShown } from './visible.js'

  // Сколько карточек в порции. Число из спеки поиска и загрузки.
  const PAGE = 50

  let views = $state([])
  // Сколько оценок агрегаторов ждать. Без этого списка на их месте не будет
  // даже кружков: у кино они приезжают отдельным кругом.
  let expected = $state([])
  let ops = $state([])
  let done = $state(false)

  const feed = { section: 'rated', kind: 'movie', filters: {},
                 order: { key: 'score', descending: true } }

  $effect(() => {
    numbered('world.expected', 'movie', { channel: 'expected' })
      .then((sources) => { expected = sources })
  })

  /** Отвечает, есть ли смысл просить ещё: конец знает тот, кто просил. */
  async function more() {
    if (done) return false
    const page = await numbered('feed.page', feed, views.length, PAGE,
                                { channel: 'feed', ops })
    done = page.length < PAGE
    views = [...views, ...page]
    return !done
  }

  /** Приехавшие оценки кладутся в ту же карточку: иначе кружок на их месте
   *  крутится до перезахода в раздел, хотя оценки уже в базе. */
  async function shown(view) {
    const external = await onCardShown(view, ops)
    if (!external) return
    views = views.map((one) =>
      one.item_id === view.item_id ? { ...one, external } : one)
  }

  // Обработчики черновика молчат: жесты карточки заводит задача 6, а до неё
  // нажатие обязано хотя бы не ронять страницу.
  const idle = () => {}
</script>

<Feed {views} {expected} onmore={more} onshown={shown}
      onperson={idle} ontag={idle} oncollapse={idle} onmark={idle} onopen={idle}
      onscore={idle} onaspect={idle} onedit={idle} ondelete={idle}
      onwish={idle} />
