<!-- Обложка карточки с заглушкой. -->
<script>
  import Icon from '$components/Icon.svelte'

  let { item_id = null, source = '', poster_url = '' } = $props()

  // У кандидата номера нет — он ещё не в базе, и обложку тогда не сохраняют.
  // Ручка одна, различаются только доводы.
  const address = $derived(item_id
    ? `/poster?item=${item_id}`
    : poster_url && `/poster?source=${source}&url=${encodeURIComponent(poster_url)}`)

  // Помнится сорвавшийся адрес, а не признак «сломано»: признак заглушку уже
  // не снял бы никогда. А снимать надо — бэкенд обещает повторить попытку при
  // следующем показе, кандидат после заведения меняет адрес на номерной, и
  // перезалитая обложка приезжает с меткой момента.
  let failed = $state('')
</script>

<div class="film__poster">
  {#if address && failed !== address}
    <!-- Загрузку обрывает сам браузер, когда карточка уходит из разметки: своей
         отмены тут не нужно ни строки. -->
    <img src={address} alt="" loading="lazy" onerror={() => { failed = address }}>
  {:else}
    <Icon name="theaters" />
  {/if}
</div>
