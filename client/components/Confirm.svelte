<!-- Вопрос и две кнопки. Спрашивают им и то, что пропадёт навсегда, и то, что
     просто выглядит подозрительно, — цвет и слово согласия приходят снаружи. -->
<script>
  import Modal from '$components/Modal.svelte'
  import ModalFoot from '$components/ModalFoot.svelte'

  let { label, text, ok, danger = false, onyes, onclose } = $props()
</script>

<Modal ask {danger} {label} {onclose}>
  {#snippet children()}
    <p class="ask__text">{text}</p>
    <ModalFoot {ok} {danger} oncancel={onclose} onok={onyes} />
  {/snippet}
</Modal>
