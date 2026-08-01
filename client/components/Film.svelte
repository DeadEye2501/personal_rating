<!-- Карточка ленты целиком. -->
<script>
  import Chips from '$components/Chips.svelte'
  import Facts from '$components/Facts.svelte'
  import Icon from '$components/Icon.svelte'
  import Poster from '$components/Poster.svelte'
  import Synopsis from '$components/Synopsis.svelte'

  let { view, collapsed = false, on, oncollapse, onmark, onperson, ontag }
    = $props()

  // Год приклеивается здесь, а не в разметке: ведущий пробел текстового узла в
  // блоке `{#if}` Svelte срезает, и получается «Интерстеллар(2014)».
  const title = $derived(view.year ? `${view.title} (${view.year})` : view.title)
</script>

<article class="film" class:is-collapsed={collapsed}>
  <button type="button" class="film__toggle" aria-expanded={!collapsed}
          aria-label={collapsed ? 'Развернуть' : 'Свернуть'}
          onclick={() => oncollapse(view)}>
    <Icon name="expand_less" />
  </button>

  <Poster item_id={view.item_id} source={view.source} poster_url={view.poster_url} />

  <div class="film__body">
    <h2 class="film__title">{title}</h2>

    <Chips genres={view.genres} tags={view.tags} {on} {onmark}
           ontag={() => ontag(view)} />
    <Facts {view} {onperson} />
    <Synopsis text={view.synopsis} />
  </div>
</article>
