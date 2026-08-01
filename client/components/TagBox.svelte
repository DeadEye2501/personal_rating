<!-- Переключатель строки списка: не выбран, включён, исключён. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Состояний три у фильтров и два у тегов карточки; сам переключатель
  // одинаков, а что за чем следует — решает тот, кто его поставил.
  let { state = 'off', label, onclick } = $props()

  const GLYPH = { off: 'check', on: 'check', ex: 'close' }
  const SAID = { off: 'не выбран', on: 'включён', ex: 'исключён' }
</script>

<!-- Глиф спрятан от чтения вслух, поэтому подпись несёт и то, о чём строка:
     без неё «включён» сказано ни о чём. -->
<button type="button" class="tagbox" data-state={state} {onclick}
        aria-label="{label}: {SAID[state]}">
  <Icon name={GLYPH[state]} />
</button>
