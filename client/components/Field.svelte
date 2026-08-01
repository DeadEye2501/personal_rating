<!-- Строка ввода окна карточки: однострочная или абзацем. -->
<script>
  import Scrollbar from '$components/Scrollbar.svelte'

  // Подписи отдельной от подсказки у поля нет: в покое оно обозначает себя
  // подсказкой, и второе имя было бы параметром без сегодняшнего потребителя.
  let { value = $bindable(''), placeholder, variant = '', area = false }
    = $props()

  // Абзац прокручивает сам себя, а не обёртку: `textarea` по содержимому не
  // растёт, и коробка вокруг него не прокрутилась бы никогда.
  let label = $state()
  let box = $state()
</script>

<label class="field {variant}" class:scrollarea={area} bind:this={label}>
  {#if area}
    <textarea class="field__input" {placeholder} aria-label={placeholder}
              spellcheck="false" bind:this={box} bind:value></textarea>
    <Scrollbar {box} area={label} />
  {:else}
    <input class="field__input" type="text" {placeholder} aria-label={placeholder}
           spellcheck="false" autocomplete="off" bind:value>
  {/if}
</label>
