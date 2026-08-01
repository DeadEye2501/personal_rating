<!-- Капсульный переключатель: один выбранный из нескольких. -->
<script>
  import Icon from '$components/Icon.svelte'

  let { items, chosen, onchoose } = $props()
</script>

<nav class="zone seg">
  {#each items as item (item.value)}
    <button type="button" class="seg__btn" class:is-active={item.value === chosen}
            aria-pressed={item.value === chosen}
            onclick={() => onchoose(item.value)}>
      <Icon name={item.icon} />
      <span class="seg__label">{item.label}</span>
    </button>
  {/each}
</nav>
