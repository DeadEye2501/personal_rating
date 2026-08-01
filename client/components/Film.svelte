<!-- Карточка ленты целиком. -->
<script>
  import Acts from '$components/Acts.svelte'
  import Aggregates from '$components/Aggregates.svelte'
  import Chips from '$components/Chips.svelte'
  import Facts from '$components/Facts.svelte'
  import Icon from '$components/Icon.svelte'
  import Poster from '$components/Poster.svelte'
  import Stars from '$components/Stars.svelte'
  import Synopsis from '$components/Synopsis.svelte'
  import { ASPECTS, meanOf, toneOf, verdictOf } from '$state/scores.js'

  let { view, collapsed = false, expected = [], on, oncollapse, onmark,
        onperson, onopen, ontag, onscore, onaspect, onedit, ondelete,
        onwish } = $props()

  // Год приклеивается здесь, а не в разметке: ведущий пробел текстового узла в
  // блоке `{#if}` Svelte срезает, и получается «Интерстеллар(2014)».
  const title = $derived(view.year ? `${view.title} (${view.year})` : view.title)

  const rating = $derived(view.rating)
  const mean = $derived(meanOf(rating, view.kind))

  // Наведённое по шкалам: у кино одна, у игры три, и своё слово у каждой. Пока
  // курсор над рядом, слово говорит о будущей оценке, а не о поставленной, —
  // иначе непонятно, что получится от нажатия.
  let over = $state({})
  const showing = (key, real) => over[key] ?? real
</script>

<article class="film" class:is-collapsed={collapsed}>
  <button type="button" class="icon-btn film__toggle" aria-expanded={!collapsed}
          aria-label={collapsed ? 'Развернуть' : 'Свернуть'}
          onclick={() => oncollapse(view)}>
    <Icon name="expand_less" />
  </button>

  <!-- `cover` — метка перезаливки: её ставит раздел, перечитавший карточку
       после правки, и только она сбрасывает суточный кеш ручки. -->
  <Poster item_id={view.item_id} source={view.source} poster_url={view.poster_url}
          cover={view.cover} />

  <!-- Две группы вместо строк подряд: зачем — в `film.css`, у раскладки тела. -->
  <div class="film__body">
    <div class="film__top">
      <h2 class="film__title">{title}</h2>

      <Chips genres={view.genres} tags={view.tags} {on} {onmark}
             ontag={view.item_id ? () => ontag(view) : null} />
      <Facts {view} {onperson} />
      <Synopsis text={view.synopsis} />
    </div>

    <div class="film__bottom">
      <!-- Кружок ожидания — только у того, кого действительно спрашивают, и
           только пока спрашивают. У кандидата поиска номера строки нет, оценки
           агрегаторов за него никто не просит; у карточки, чей круг 3 уже
           отработал, ждать нечего — спросить могло оказаться нечем (нет
           `imdb_id`) или некого (источник отказал), и строки в базе не
           появится. И там и там кольца крутились бы вечно. -->
      <Aggregates {view} {onopen}
                  expected={view.item_id && !view.enriched ? expected : []} />

      <!-- Ряд действий живёт внутри строки оценки, а не рядом с телом: он
           отсчитывает своё место от её правого края, и вынесенный выше уезжает
           за карточку. У игры это последняя из трёх строк. -->
      {#if view.kind === 'game'}
        {#each ASPECTS as aspect, index (aspect.key)}
          <div class="film__scores film__scores--aspect">
            <span class="film__aspect">{aspect.label}</span>
            <Stars score={rating?.[aspect.key] ?? null}
                   onpick={(value) => onaspect(view, aspect.key, value)}
                   onhover={(step) => { over = { ...over, [aspect.key]: step } }} />
            <!-- Ярлык стоит у каждой стороны своим, а не один на все три: так в
                 макете, и иначе «Отлично» у визуала было бы неотличимо от
                 «Отлично» у геймплея. -->
            <span class="film__verdict"
                  style:--score={toneOf(showing(aspect.key, rating?.[aspect.key]))}
            >{verdictOf(showing(aspect.key, rating?.[aspect.key]))}</span>
            {#if index === ASPECTS.length - 1}
              <Acts wished={view.in_wishlist}
                    onedit={() => onedit(view)}
                    ondelete={() => ondelete(view)} onwish={() => onwish(view)} />
            {/if}
          </div>
        {/each}
        <div class="film__scores film__scores--avg">
          <Stars score={mean} />
          <span class="film__verdict" style:--score={toneOf(mean)}
          >{verdictOf(mean)}</span>
        </div>
      {:else}
        <div class="film__scores">
          <Stars score={mean} onpick={(value) => onscore(view, value)}
                 onhover={(step) => { over = { ...over, score: step } }} />
          <span class="film__verdict" style:--score={toneOf(showing('score', mean))}
          >{verdictOf(showing('score', mean))}</span>
          <Acts wished={view.in_wishlist}
                onedit={() => onedit(view)}
                ondelete={() => ondelete(view)} onwish={() => onwish(view)} />
        </div>
      {/if}
    </div>
  </div>
</article>
