<!-- Ряд действий карточки: правка, удаление, рецензия, закладка. -->
<script>
  import Icon from '$components/Icon.svelte'

  // `onreview` пустует у строки, которой ещё нет в базе: писать рецензию не к
  // чему, пока нет карточки. То же правило, что у кнопки тега.
  // Подпись закладки приходит параметром: она зависит от типа карточки, а
  // компонент про общее состояние не знает.
  let { wished = false, wish, reviewed = false, onedit, ondelete, onreview,
        onwish } = $props()
</script>

<div class="film__acts">
  <button type="button" class="icon-btn film__act" data-act="edit" aria-label="Править"
          onclick={onedit}>
    <Icon name="edit" />
  </button>
  <button type="button" class="icon-btn film__act" data-act="delete" aria-label="Удалить"
          onclick={ondelete}>
    <Icon name="delete" />
  </button>
  {#if onreview}
    <button type="button" class="icon-btn film__act" class:is-on={reviewed}
            data-act="review" aria-label="Рецензия" onclick={onreview}>
      <Icon name="description" />
    </button>
  {/if}
  <button type="button" class="icon-btn film__wish" class:is-on={wished}
          aria-pressed={wished} aria-label={wish} onclick={onwish}>
    <Icon name="bookmark" />
  </button>
</div>
