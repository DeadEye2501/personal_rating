<!-- Обложка карточки с заглушкой. -->
<script>
  import Icon from '$components/Icon.svelte'
  import { bySource, byItem } from '$state/covers.js'
  import { squareOf } from '$state/kinds.js'

  // У кандидата номера нет — он ещё не в базе, и обложку тогда не сохраняют.
  // Ручка одна, различаются только доводы.
  //
  // Тип нужен рамке: у альбома обложка квадратная. Модификатор вешается на тот
  // же `div`, что и класс, а не на обёртку вокруг него: лишняя обёртка ломает
  // соседние селекторы молча.
  let { item_id = null, source = '', poster_url = '', cover = 0,
        kind = '' } = $props()

  const address = $derived(item_id
    ? byItem(item_id, cover)
    : poster_url && bySource(source, poster_url, kind))

  // Помнится сорвавшийся адрес, а не признак «сломано»: признак заглушку уже
  // не снял бы никогда. А снимать надо — бэкенд обещает повторить попытку при
  // следующем показе, кандидат после заведения меняет адрес на номерной, и
  // перезалитая обложка приезжает с меткой момента.
  let failed = $state('')
</script>

<div class="film__poster" class:is-square={squareOf(kind)}>
  {#if address && failed !== address}
    <!-- Загрузку обрывает сам браузер, когда карточка уходит из разметки: своей
         отмены тут не нужно ни строки. -->
    <img src={address} alt="" loading="lazy" onerror={() => { failed = address }}>
  {:else}
    <Icon name="theaters" />
  {/if}
</div>
