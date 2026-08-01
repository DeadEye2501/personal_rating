<!-- Ряд действий карточки: правка, удаление, закладка. -->
<script>
  import Icon from '$components/Icon.svelte'

  let { wished = false, onedit, ondelete, onwish } = $props()
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
  <button type="button" class="icon-btn film__wish" class:is-on={wished}
          aria-pressed={wished} aria-label="Хочу посмотреть" onclick={onwish}>
    <Icon name="bookmark" />
  </button>
</div>
