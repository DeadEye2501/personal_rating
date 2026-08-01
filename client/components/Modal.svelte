<!-- Оболочка любого наложения: затемнение, окно и два способа его закрыть. -->
<script module>
  // Стопка общая на все окна: она про порядок наложений, а не про одно из них.
  const stack = []
</script>

<script>
  let { narrow = false, label, onclose, children } = $props()

  // Место в стопке занимается при создании, а не в эффекте: слушатель окна
  // ставится синхронно, и между созданием и первым эффектом окно уже ловит
  // Escape. Личностью, а не номером: Svelte заводит новую ветку раньше, чем
  // гасит старую, и счётчик от такой смены разъехался бы навсегда.
  const mine = {}
  stack.push(mine)

  $effect(() => () => { stack.splice(stack.indexOf(mine), 1) })

  // Escape убирает **верхнее** окно: подтверждение удаления открывается поверх
  // списка тегов, и одно нажатие не должно складывать оба.
  const escaped = (event) => {
    if (event.key === 'Escape' && stack.at(-1) === mine) onclose()
  }

  // Закрывает клик, начатый и законченный на затемнении. Только конец проверять
  // мало: `click` приходит общему предку нажатия и отпускания, поэтому ползунок,
  // схваченный у правого края окна и отпущенный мимо, закрыл бы окно.
  let pressed = false
  const press = (event) => { pressed = event.target === event.currentTarget }
  const outside = (event) => {
    if (pressed && event.target === event.currentTarget) onclose()
  }
</script>

<svelte:window onkeydown={escaped} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- Затемнение — не кнопка: клавиатуре тут делать нечего, окно закрывает
     Escape. Предупреждения сняты адресно, а не настройкой на весь проект. -->
<div class="overlay" onpointerdown={press} onclick={outside}>
  <div class="modal" class:modal--narrow={narrow} role="dialog" aria-modal="true"
       aria-label={label}>
    {@render children()}
  </div>
</div>
