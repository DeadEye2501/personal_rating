<!-- Описание карточки, обрезанное до трёх строк, с раскрытием. -->
<script>
  let { text = '' } = $props()

  let full = $state(false)
  let paragraph = $state()
  let cut = $state(false)

  // Кнопка появляется, только когда есть что раскрывать: обрезанный текст
  // отличается от целого высотой прокрутки. Замер идёт после отрисовки — до
  // неё обе высоты нулевые.
  //
  // Эффектом, а не `onMount`: абзаца может не быть вовсе — у каждой игры из
  // GOG синопсис пуст, — и замер по несуществующему узлу ронял бы исключение,
  // а с ним и остаток очереди эффектов, то есть соседей по ленте. Заодно
  // пересчитывается, когда текст приезжает позже разметки.
  $effect(() => {
    if (!paragraph) return
    cut = paragraph.scrollHeight > paragraph.clientHeight
  })
</script>

{#if text}
  <p class="film__synopsis" class:is-cut={!full} bind:this={paragraph}>
    {text}{#if cut && !full}<button type="button" class="more"
      onclick={() => { full = true }}>ещё</button>{/if}
  </p>
{/if}
