<!-- Кнопка ответного ряда внизу окна. -->
<script>
  let { variant, disabled = false, onclick, children } = $props()
</script>

<button type="button" class="btn {variant}" {disabled} {onclick}>
  {@render children()}
</button>
