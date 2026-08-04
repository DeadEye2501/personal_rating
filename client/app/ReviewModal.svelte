<!-- Своя рецензия к карточке: читают её здесь же, где и правят. -->
<script>
  import { tick } from 'svelte'

  import Modal from '$components/Modal.svelte'
  import ModalFoot from '$components/ModalFoot.svelte'
  import { reviewed } from './marks.js'
  import { complaining } from './trouble.js'

  let { view, onsaved, onclose, ontrouble } = $props()

  // Написанное живёт здесь с открытия и до записи: отмена просто закрывает
  // окно, ничего не вернув наружу.
  let text = $state(view.rating?.review ?? '')
  // Пустой рецензии показывать нечего, и она открывается сразу полем. Фокуса
  // при открытии нет намеренно: каретка появляется от клика, и окно открывается
  // спокойным. Решение пользователя 05.08.2026 — поставленный сюда фокус был
  // отвергнут на живом окне.
  let editing = $state(!text)
  let field = $state()
  let saving = $state(false)

  const lost = complaining('рецензия', ontrouble)

  /** Клик по прочитанному открывает правку в том самом месте, куда ткнули.
   *
   *  Промах мимо букв — обычное дело: ниже последней строки текста нет вовсе, и
   *  браузер отдаёт там не текстовый узел, а сам блок со смещением по детям.
   *  Такой ответ значил бы «в начало», поэтому промах уводит курсор в конец. */
  async function edit(event) {
    const spot = document.caretPositionFromPoint(event.clientX, event.clientY)
    const at = spot?.offsetNode.nodeType === Node.TEXT_NODE
      ? spot.offset
      : text.length

    editing = true
    await tick()
    field.focus()
    field.setSelectionRange(at, at)
  }

  /** Единственный вход в запись. Отказ окна не закрывает: набранное осталось бы
   *  только на экране, а на экране его уже не будет. */
  async function keep() {
    if (saving) return
    saving = true
    try {
      // Строку окно несёт само, а не оставляет её выбор сборке: пока запись
      // летит, окно вправе закрыться — Escape, клик мимо, — и прочитанная
      // после этого карточка сборки будет уже пустой. Разделы правят по ней
      // свою строку, то есть уехало бы `null`.
      onsaved(view, await reviewed(view, text))
      onclose()
    } catch (error) {
      lost(error, 'Рецензия не сохранилась')
    } finally {
      saving = false
    }
  }
</script>

<Modal wide review label="Рецензия" {onclose}>
  {#snippet children()}
    {#if editing}
      <textarea class="review__field" bind:this={field} bind:value={text}
      ></textarea>
    {:else}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- Прочитанное — это текст, а не кнопка: с клавиатуры в правку ведёт
           Tab на само поле, которым область и станет. Предупреждения сняты
           адресно, а не настройкой на весь проект. -->
      <div class="review__text" onclick={edit}>{text}</div>
    {/if}

    <ModalFoot ok="Сохранить" busy={saving} oncancel={onclose} onok={keep} />
  {/snippet}
</Modal>
