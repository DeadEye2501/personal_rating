<!-- Поле поиска с кнопкой очистки. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Набранное — своё, но сборка вправе его снять: клик по имени в карточке
  // отменяет строку, и оставшийся в поле текст утверждал бы, что выдача по
  // нему. Двусторонним, потому что печатают сюда же.
  let { onsearch, value = $bindable('') } = $props()
  let field
  // Очистка снимает и запрос, а не только текст: поле говорит, что ничего не
  // искали, и выдача обязана согласиться. Молчащая очистка оставляла запрос в
  // памяти сборки, и он воскресал при смене вкладки — выдача по строке,
  // которой в поле уже нет.
  //
  // Фокус возвращается в поле: убрал текст — печатай дальше, а не ищи курсор
  // мышью.
  const clear = () => { value = ''; onsearch(''); field.focus() }
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
