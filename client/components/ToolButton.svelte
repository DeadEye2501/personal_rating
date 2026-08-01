<!-- Круглая кнопка ряда в шапке. -->
<script>
  // `children` нужен одной кнопке из девяти — статистике: её иконка не глиф, а
  // SVG из трёх столбиков, потому что они растут поодиночке.
  import Icon from '$components/Icon.svelte'

  let { icon, dir = '', label, active = false, pressed = null, onclick,
        children } = $props()
</script>

<button type="button" class="tools__btn" class:is-active={active}
        aria-pressed={pressed} aria-label={label} title={label} {onclick}>
  {#if children}{@render children()}{:else}
    <Icon name={icon} />
    {#if dir}<Icon name={dir} extra="tools__dir" />{/if}
  {/if}
</button>
