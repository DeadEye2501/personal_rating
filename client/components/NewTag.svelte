<!-- Форма заведения тега. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Ограничение из макета.
  const LIMIT = 24

  let { oncreate } = $props()

  let name = $state('')
  let field = $state()

  /** `oncreate` отвечает, завёлся ли тег: занятое имя — штатный отказ, и
   *  набранное после него остаётся в поле. Очистить его значило бы заставить
   *  набирать заново то, что человек уже написал.
   *
   *  Фокус возвращается в любом случае: теги заводят подряд, и тянуться мышью
   *  за каждым — лишний жест. Так же в макете. */
  async function submit(event) {
    event.preventDefault()
    const clean = name.trim()
    if (!clean) return

    if (await oncreate(clean)) name = ''
    field.focus()
  }
</script>

<form class="newtag" class:is-filled={name.trim()} onsubmit={submit}>
  <input class="field__input newtag__input" type="text" maxlength={LIMIT}
         spellcheck="false" autocomplete="off" placeholder="+ Новый тег"
         aria-label="Название нового тега" bind:this={field} bind:value={name}>
  <button type="submit" class="icon-btn icon-btn--accent newtag__ok" aria-label="Добавить тег">
    <Icon name="check" />
  </button>
</form>
