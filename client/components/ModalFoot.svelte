<!-- Ряд ответных кнопок внизу окна: отмена и согласие. -->
<script>
  import Button from '$components/Button.svelte'

  // Слово согласия и его цвет приходят снаружи: у карточки это «Сохранить»
  // акцентом, у необратимого — своё слово красным.
  //
  // `busy` гасит только согласие. Отмена остаётся живой нарочно: запись ходит
  // через мост со своим сроком, и погашенная отмена на зависшей записи не
  // оставила бы окну выхода вовсе.
  let { ok, danger = false, busy = false, oncancel, onok } = $props()
</script>

<div class="modalfoot">
  <Button variant="btn--cancel" onclick={oncancel}>
    {#snippet children()}Отмена{/snippet}
  </Button>
  <Button variant={danger ? 'btn--danger' : 'btn--go'} disabled={busy} onclick={onok}>
    {#snippet children()}{ok}{/snippet}
  </Button>
</div>
