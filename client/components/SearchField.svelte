<!-- Поле поиска с кнопкой очистки. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Набранное — своё: сверху его сегодня никто не задаёт, а входным параметром
  // оно ещё и не записывалось бы — в Svelte 5 присваивание уходит в пустоту,
  // пока параметр не объявлен двусторонним.
  let { onsearch } = $props()

  let value = $state('')
  let field
  // Очистка возвращает фокус в поле: убрал текст — печатай дальше, а не ищи
  // курсор мышью.
  const clear = () => { value = ''; field.focus() }
</script>

<!-- Поиск идёт по Enter, а не на каждую букву: одна буква — это запрос к
     внешней базе, а их квоты конечны. -->
<label class="search">
  <Icon name="search" extra="search__icon" />
  <input class="search__input" type="search" placeholder="Поиск" aria-label="Поиск"
         spellcheck="false" autocomplete="off"
         bind:this={field} bind:value
         onkeydown={(event) => event.key === 'Enter' && onsearch(value.trim())}>
  {#if value}
    <button type="button" class="icon-btn search__clear" aria-label="Очистить" onclick={clear}>
      <Icon name="close" />
    </button>
  {/if}
</label>
