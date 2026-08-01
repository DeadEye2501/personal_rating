<!-- Вопрос и две кнопки. Спрашивают им и то, что пропадёт навсегда, и то, что
     просто выглядит подозрительно, — цвет и слово согласия приходят снаружи. -->
<script>
  import Button from '$components/Button.svelte'
  import Modal from '$components/Modal.svelte'

  let { label, text, ok, danger = false, onyes, onclose } = $props()
</script>

<Modal ask {danger} {label} {onclose}>
  {#snippet children()}
    <p class="ask__text">{text}</p>
    <div class="modalfoot">
      <Button variant="btn--cancel" onclick={onclose}>
        {#snippet children()}Отмена{/snippet}
      </Button>
      <Button variant={danger ? 'btn--danger' : 'btn--go'} onclick={onyes}>
        {#snippet children()}{ok}{/snippet}
      </Button>
    </div>
  {/snippet}
</Modal>
