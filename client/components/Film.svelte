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
  import { wishOf } from '$state/kinds.js'
  import { ASPECTS, average, meanOf, scale, toneOf, verdictOf } from '$state/scores.js'

  let { view, collapsed = false, expected = [], on, oncollapse, onmark,
        onperson, onopen, ontag, onreview, onscore, onaspect, onedit, ondelete,
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

  // Три стороны игры встают в один ряд только на короткой шкале: на длинной их
  // тридцать звёзд с подписями, и ряд всё равно сложился бы в три строки —
  // тогда пусть он и остаётся тремя, как был. Решение пользователя 04.08.2026.
  const inRow = $derived(scale().length <= 5)

  // Средняя из показываемых сторон, а не из выставленных: пока курсор над
  // рядом, слово говорит о будущей оценке — правило то же, что у слова у
  // каждой стороны, которое оно заменило.
  const shownMean = $derived(average(
    ASPECTS.map((one) => showing(one.key, rating?.[one.key]) ?? null)))
</script>

<!-- Ряд действий стоит в четырёх раскладках сразу — у каждой строки оценок
     своей, — и разъехаться они не вправе: кнопки на карточке одни и те же.
     Рецензии у строки без номера нет вовсе, как и тега: писать её не к чему,
     пока нет карточки. -->
{#snippet acts()}
  <Acts wished={view.in_wishlist} wish={wishOf(view.kind)}
        reviewed={Boolean(view.rating?.review)}
        onedit={() => onedit(view)} ondelete={() => ondelete(view)}
        onreview={view.item_id ? () => onreview(view) : null}
        onwish={() => onwish(view)} />
{/snippet}

<article class="film" class:is-collapsed={collapsed}>
  <button type="button" class="icon-btn film__toggle" aria-expanded={!collapsed}
          aria-label={collapsed ? 'Развернуть' : 'Свернуть'}
          onclick={() => oncollapse(view)}>
    <Icon name="expand_less" />
  </button>

  <!-- `cover` — метка перезаливки: её ставит раздел, перечитавший карточку
       после правки, и только она сбрасывает суточный кеш ручки. -->
  <Poster item_id={view.item_id} source={view.source} poster_url={view.poster_url}
          kind={view.kind}
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
        {#if inRow}
          <!-- Три стороны подряд, одной строкой у нижнего края: слово тут одно
               на все три и берётся по средней — три слова в строку не встают. -->
          <div class="film__scores film__scores--sides">
            {#each ASPECTS as aspect (aspect.key)}
              <span class="film__side">
                <span class="film__aspect">{aspect.label}</span>
                <Stars score={rating?.[aspect.key] ?? null}
                       onpick={(value) => onaspect(view, aspect.key, value)}
                       onhover={(step) => { over = { ...over, [aspect.key]: step } }} />
              </span>
            {/each}
            <span class="film__verdict" style:--score={toneOf(shownMean)}
            >{verdictOf(shownMean)}</span>
            {@render acts()}
          </div>
        {:else}
          {#each ASPECTS as aspect, index (aspect.key)}
            <div class="film__scores film__scores--aspect">
              <span class="film__aspect">{aspect.label}</span>
              <Stars score={rating?.[aspect.key] ?? null}
                     onpick={(value) => onaspect(view, aspect.key, value)}
                     onhover={(step) => { over = { ...over, [aspect.key]: step } }} />
              <!-- Ярлык стоит у каждой стороны своим, а не один на все три: так
                   в макете, и иначе «Отлично» у визуала было бы неотличимо от
                   «Отлично» у геймплея. -->
              <span class="film__verdict"
                    style:--score={toneOf(showing(aspect.key, rating?.[aspect.key]))}
              >{verdictOf(showing(aspect.key, rating?.[aspect.key]))}</span>
              {#if index === ASPECTS.length - 1}
                {@render acts()}
              {/if}
            </div>
          {/each}
        {/if}

        <!-- Свёрнутая карточка показывает одну усреднённую строку вместо
             сторон, и это общее у обеих раскладок: длинной шкале она заменяет
             три строки, короткой — ряд.
             Слова здесь нет: `.film__verdict` скрыт у свёрнутой, а сама строка
             только у свёрнутой и показывается — увидеть его было нельзя
             никогда. Значит цвет звёзд тут единственное, что говорит об
             оценке. -->
        <div class="film__scores film__scores--avg">
          <Stars score={mean} />
          <!-- Свой ряд, а не тот, что стоит в строках сторон: у игры видимая
               строка меняется со свёрнутостью, и ряд обязан ехать с ней. -->
          {@render acts()}
        </div>
      {:else}
        <div class="film__scores">
          <Stars score={mean} onpick={(value) => onscore(view, value)}
                 onhover={(step) => { over = { ...over, score: step } }} />
          <span class="film__verdict" style:--score={toneOf(showing('score', mean))}
          >{verdictOf(showing('score', mean))}</span>
          {@render acts()}
        </div>
      {/if}
    </div>
  </div>
</article>
