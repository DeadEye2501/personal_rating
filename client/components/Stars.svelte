<!-- Ряд из десяти звёзд: кликабельный или неподвижный с дробной. -->
<script>
  import Icon from '$components/Icon.svelte'
  import { SCALE, colorOf, partOf } from '$state/scores.js'

  // Кликабельный ряд — своя оценка; неподвижный с дробной звездой —
  // усреднённая у свёрнутой игры. Двух компонентов тут не нужно: отличие в
  // одном свойстве, а строение и оформление общие.
  let { score = null, onpick = null } = $props()

  const whole = $derived(Math.floor(score ?? 0))
  const part = $derived(score ? partOf(score) : 0)
  const colour = $derived(colorOf(Math.max(1, whole)))
</script>

<div class="stars">
  {#each SCALE as step (step)}
    {#if onpick}
      <!-- Повторное нажатие по той же звезде снимает оценку: карточка при этом
           остаётся. -->
      <button type="button" class:is-on={step <= whole} style:--score={colour}
              aria-label={`Оценка ${step}`}
              onclick={() => onpick(step === score ? null : step)}>
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
