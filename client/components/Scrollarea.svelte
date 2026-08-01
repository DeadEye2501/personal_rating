<!-- Область, которая прокручивается вместо страницы. -->
<script>
  import Scrollbar from '$components/Scrollbar.svelte'

  let { children } = $props()

  let area = $state()
  let box = $state()
</script>

<div class="scrollarea" bind:this={area}>
  <div class="scrollarea__box" bind:this={box}>
    {@render children()}
  </div>
  <Scrollbar {box} {area} />
</div>
