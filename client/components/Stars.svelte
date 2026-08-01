<!-- Ряд из десяти звёзд: кликабельный или неподвижный с дробной. -->
<script>
  import Icon from '$components/Icon.svelte'
  import { SCALE, colorOf, partOf } from '$state/scores.js'

  // Кликабельный ряд — своя оценка; неподвижный с дробной звездой —
  // усреднённая у свёрнутой игры. Двух компонентов тут не нужно: отличие в
  // одном свойстве, а строение и оформление общие.
  //
  // Наведённое уходит наружу: слово-ярлык стоит рядом со звёздами, а не внутри
  // них, и показать будущую оценку иначе нечем.
  let { score = null, onpick = null, onhover = null } = $props()

  // Наведённая звезда. Пока курсор над рядом, ряд показывает, что получится, а
  // не то, что стоит.
  let over = $state(null)
  let row = $state()

  const shown = $derived(over ?? score)
  const whole = $derived(Math.floor(shown ?? 0))
  // Дробная звезда бывает только у неподвижного ряда: у кликабельного оценка
  // целая, а наведённая — тем более.
  const part = $derived(score ? partOf(score) : 0)
  const colour = $derived(colorOf(Math.max(1, whole)))

  function mark(step) {
    over = step
    onhover?.(step)
  }

  /** Повторное нажатие по той же звезде снимает оценку: карточка при этом
   *  остаётся. Вспышка тогда не нужна — у снятой оценки нет цвета, которым
   *  вспыхивать.
   *
   *  Класс снимается и ставится заново с пересчётом между: без него второе
   *  нажатие подряд не перезапустит анимацию — класс уже стоит, и браузеру
   *  менять нечего. Своего срока здесь нет, длительность живёт в оформлении:
   *  вторым объявлением она разошлась бы с ним молча. */
  function pick(step) {
    const value = step === score ? null : step
    onpick(value)

    row.classList.remove('is-flash')
    if (value === null) return
    void row.offsetWidth
    row.classList.add('is-flash')
  }
</script>

<!-- Уход считается по всему ряду, а не по каждой звезде: между соседними
     кнопками есть щель, и на ней подсветка мигала бы. -->
<div class="stars" bind:this={row}
     onmouseleave={onpick ? () => mark(null) : null}>
  {#each SCALE as step (step)}
    {#if onpick}
      <button type="button" class:is-on={step <= whole} style:--score={colour}
              aria-label={`Оценка ${step}`}
              onmouseenter={() => mark(step)}
              onclick={() => pick(step)}>
        <Icon name="star" />
      </button>
    {:else if step <= whole}
      <span class="is-on" style:--score={colour}><Icon name="star" /></span>
    {:else if step === whole + 1 && part > 0}
      <span class="star--part" style:--score={colour}
            style:--fill={`${Math.round(part * 100)}%`}>
        <Icon name="star" /><i><Icon name="star" /></i>
      </span>
    {:else}
      <span><Icon name="star" /></span>
    {/if}
  {/each}
</div>
