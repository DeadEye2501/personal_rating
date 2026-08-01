<!-- Область, которая прокручивается вместо страницы. -->
<script>
  import Scrollbar from '$components/Scrollbar.svelte'

  // Прокручиваемое отдаётся наружу: ленте оно нужно корнем наблюдателя, а
  // второй такой же области заводить незачем — эта и есть «то, что
  // прокручивается вместо страницы».
  // Значения по умолчанию у него нет намеренно: `bind:` к ещё не привязанной
  // ячейке Svelte отклоняет ровно у того, у кого оно объявлено.
  let { children, box = $bindable() } = $props()

  let area = $state()
</script>

<div class="scrollarea" bind:this={area}>
  <div class="scrollarea__box" bind:this={box}>
    {@render children()}
  </div>
  <Scrollbar {box} {area} />
</div>
