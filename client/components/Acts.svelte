<!-- Ряд действий карточки: правка, удаление, закладка. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Правка и удаление — только у того, что лежит в библиотеке: у кандидата из
  // выдачи править нечего и удалять нечего. Закладка остаётся у обоих, но в
  // выдаче она пока молчит — отложить ненайденное можно будет тогда же, когда
  // его можно будет оценить, то есть с заведением карточки первым действием.
  let { saved = true, wished = false, onedit, ondelete, onwish } = $props()
</script>

<div class="film__acts">
  {#if saved}
    <button type="button" class="icon-btn film__act" data-act="edit" aria-label="Править"
            onclick={onedit}>
      <Icon name="edit" />
    </button>
    <button type="button" class="icon-btn film__act" data-act="delete" aria-label="Удалить"
            onclick={ondelete}>
      <Icon name="delete" />
    </button>
  {/if}
  <button type="button" class="icon-btn film__wish" class:is-on={wished}
          aria-pressed={wished} aria-label="Хочу посмотреть" onclick={onwish}>
    <Icon name="bookmark" />
  </button>
</div>
