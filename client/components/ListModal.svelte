<!-- Окно со списком строк: шапка над ним, если есть, прокручиваемый список и,
     если есть, форма под ним. -->
<script>
  import Modal from '$components/Modal.svelte'
  import Scrollarea from '$components/Scrollarea.svelte'

  let { label, narrow = false, onclose, items, head = null, footer = null }
    = $props()
</script>

<Modal {narrow} {label} {onclose}>
  {#snippet children()}
    <!-- Шапка стоит снаружи области прокрутки, а не первой строкой списка: она
         обязана остаться на месте, когда список едет, и не добавлять ему
         высоты — иначе полоса прокрутки заводится от самой шапки. -->
    {#if head}{@render head()}{/if}

    <Scrollarea>
      {#snippet children()}
        <ul class="taglist">{@render items()}</ul>
      {/snippet}
    </Scrollarea>

    {#if footer}{@render footer()}{/if}
  {/snippet}
</Modal>
