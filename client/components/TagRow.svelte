<!-- Строка списка: ручка, переключатель, имя, удаление. -->
<script>
  import Icon from '$components/Icon.svelte'
  import TagBox from '$components/TagBox.svelte'

  let { name, state = 'off', dragging = false, ontoggle, ondelete = null,
        ongrab = null } = $props()
</script>

<li class="tagrow" class:is-dragging={dragging}>
  {#if ongrab}
    <!-- Порядок хранит база: `marks.reorder_tags` пишет `position`, и он
         переживает перезапуск. -->
    <span class="taggrip" onpointerdown={ongrab} aria-hidden="true">
      <i></i><i></i><i></i><i></i><i></i><i></i>
    </span>
  {/if}

  <TagBox {state} label={name} onclick={ontoggle} />

  <span class="tagrow__name">{name}</span>

  {#if ondelete}
    <button type="button" class="icon-btn tagrow__del" aria-label="Удалить тег"
            onclick={ondelete}>
      <Icon name="delete" />
    </button>
  {/if}
</li>
