<!-- Вопрос и две кнопки. Спрашивают им и то, что пропадёт навсегда, и то, что
     просто выглядит подозрительно, — цвет и слово согласия приходят снаружи. -->
<script>
  import Modal from '$components/Modal.svelte'

  let { label, text, ok, danger = false, onyes, onclose } = $props()
</script>

<Modal ask {danger} {label} {onclose}>
  {#snippet children()}
    <p class="ask__text">{text}</p>
    <div class="modalfoot">
      <button type="button" class="btn btn--cancel" onclick={onclose}>Отмена</button>
      <button type="button" class="btn" class:btn--danger={danger}
              class:btn--go={!danger} onclick={onyes}>{ok}</button>
    </div>
  {/snippet}
</Modal>
