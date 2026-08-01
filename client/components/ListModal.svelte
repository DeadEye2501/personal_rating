<!-- Окно со списком строк: прокручиваемый список и, если есть, форма под ним. -->
<script>
  import Modal from '$components/Modal.svelte'
  import Scrollarea from '$components/Scrollarea.svelte'

  let { label, narrow = false, onclose, items, footer = null } = $props()
</script>

<Modal {narrow} {label} {onclose}>
  {#snippet children()}
    <Scrollarea>
      {#snippet children()}
        <ul class="taglist">{@render items()}</ul>
      {/snippet}
    </Scrollarea>

    {#if footer}{@render footer()}{/if}
  {/snippet}
</Modal>
