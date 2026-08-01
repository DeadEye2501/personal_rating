<!-- Кнопка ответного ряда внизу окна. -->
<script>
  let { variant, onclick, children } = $props()
</script>

<button type="button" class="btn {variant}" {onclick}>{@render children()}</button>
