<!-- Строка с кнопкой добавления: набрал — подтвердил. Теги и треки. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Подписи две, и это не многословие: поле и кнопка — разные органы
  // управления, и чтение с экрана называет их по отдельности. «Название нового
  // тега» у кнопки читалось бы как её имя, а не как действие.
  //
  // `limit` в знаках; ноль означает «без предела». У тегов он из макета —
  // двадцать четыре, — а название трека бывает длинным.
  let { placeholder, label, action, limit = 0, oncreate } = $props()

  let name = $state('')
  let field = $state()

  /** `oncreate` отвечает, приняли ли набранное: занятое имя тега — штатный
   *  отказ, и набранное после него остаётся в поле. Очистить его значило бы
   *  заставить набирать заново то, что человек уже написал.
   *
   *  Фокус возвращается в любом случае: и теги, и треки заводят подряд, и
   *  тянуться мышью за каждым — лишний жест. Так же в макете. */
  async function submit(event) {
    event.preventDefault()
    const clean = name.trim()
    if (!clean) return

    if (await oncreate(clean)) name = ''
    field.focus()
  }
</script>

<form class="addline" class:is-filled={name.trim()} onsubmit={submit}>
  <input class="field__input addline__input" type="text"
         maxlength={limit || undefined}
         spellcheck="false" autocomplete="off" {placeholder}
         aria-label={label} bind:this={field} bind:value={name}>
  <button type="submit" class="icon-btn icon-btn--accent addline__ok" aria-label={action}>
    <Icon name="check" />
  </button>
</form>
