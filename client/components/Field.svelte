<!-- Строка ввода окна карточки: однострочная или абзацем. -->
<script>
  import Scrollbar from '$components/Scrollbar.svelte'

  // Подписи отдельной от подсказки у поля нет: в покое оно обозначает себя
  // подсказкой, и второе имя было бы параметром без сегодняшнего потребителя.
  //
  // Набор и клавиши уезжают наружу: полю с подсказкой нужно и то, и другое, а
  // держать их у себя оно не может — совпадения ему приносят параметром.
  let { value = $bindable(''), placeholder, variant = '', area = false,
        oninput, onkeydown, onfocus, onblur } = $props()

  // Абзац прокручивает сам себя, а не обёртку: `textarea` по содержимому не
  // растёт, и коробка вокруг него не прокрутилась бы никогда.
  let label = $state()
  let box = $state()
</script>

<label class="field {variant}" class:scrollarea={area} bind:this={label}>
  {#if area}
    <textarea class="field__input" {placeholder} aria-label={placeholder}
              spellcheck="false" bind:this={box} bind:value
              {oninput} {onkeydown} {onfocus} {onblur}></textarea>
    <Scrollbar {box} area={label} />
  {:else}
    <input class="field__input" type="text" {placeholder} aria-label={placeholder}
           spellcheck="false" autocomplete="off" bind:value
           {oninput} {onkeydown} {onfocus} {onblur}>
  {/if}
</label>
