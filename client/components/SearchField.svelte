<!-- Поле поиска с кнопкой очистки. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Набранное — своё, но сборка вправе его снять: клик по имени в карточке
  // отменяет строку, и оставшийся в поле текст утверждал бы, что выдача по
  // нему. Двусторонним, потому что печатают сюда же.
  let { onsearch, value = $bindable('') } = $props()
  let field
  // Очистка возвращает фокус в поле: убрал текст — печатай дальше, а не ищи
  // курсор мышью.
  const clear = () => { value = ''; field.focus() }
</script>

<!-- Поиск идёт по Enter, а не на каждую букву: одна буква — это запрос к
     внешней базе, а их квоты конечны. -->
<label class="zone search">
  <Icon name="search" extra="search__icon" />
  <input class="field__input search__input" type="search" placeholder="Поиск" aria-label="Поиск"
         spellcheck="false" autocomplete="off"
         bind:this={field} bind:value
         onkeydown={(event) => event.key === 'Enter' && onsearch(value.trim())}>
  {#if value}
    <button type="button" class="icon-btn icon-btn--accent search__clear" aria-label="Очистить" onclick={clear}>
      <Icon name="close" />
    </button>
  {/if}
</label>
