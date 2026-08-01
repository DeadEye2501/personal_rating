<!-- Привязка карточки к внешней базе вставленной ссылкой — и отвязка. -->
<script>
  import Field from '$components/Field.svelte'
  import Icon from '$components/Icon.svelte'
  import TagBox from '$components/TagBox.svelte'
  import { call, lastOp, numbered } from '$api/bridge.js'
  import { nameOf } from '$state/sources.js'
  import { reported } from './trouble.js'

  // Единственный род отказа, который тут не поломка, а ответ: за этой ссылкой в
  // библиотеке уже есть карточка. Занятую идентичность человека (`IdentityTaken`)
  // сюда не берём — она про состав, и «карточка уже есть» о ней врёт.
  const TAKEN = 'item-exists'

  // `source` пуст у ручной карточки; у привязанной вместо поля ссылки стоит имя
  // источника и крестик — второго входа отвязке не нужно.
  let { item_id = null, kind, source = '', onunlinked, ontrouble } = $props()

  let raw = $state('')
  let parsed = $state(null)
  let overwrite = $state(false)

  /** Разбор без сети и без диска: чистая функция на стороне питона. Вторую
   *  регулярку на тот же адрес заводить нельзя — разойдутся молча.
   *
   *  Ответ принимается, только пока он свой: разбор идёт на каждое нажатие
   *  клавиши, а мост зовёт бэкенд отдельным потоком на вызов. */
  let asked = 0

  function typing(event) {
    const text = event.currentTarget.value.trim()
    const mine = ++asked

    if (!text) { parsed = null; return }
    call('world.parse', text, kind)
      .then((link) => { if (asked === mine) parsed = link })
      .catch((error) => lost(error, 'Не удалось разобрать ссылку'))
  }

  const lost = (error, text) =>
    reported(error, 'привязка', () => ontrouble(text))

  /** Зовётся сохранением и после того, как карточка записана: у новой номер
   *  появляется только там. Ссылки нет — привязывать нечего, и молчание тут
   *  правильный ответ. */
  export async function link(id) {
    if (!parsed) return

    const found = await numbered('world.card_for_link', raw.trim(), kind,
                                 { channel: 'link' })
    if (found.outcome !== 'found') {
      ontrouble(found.outcome === 'missing'
        ? 'Источник не знает такой карточки'
        : 'Внешняя база недоступна')
      return
    }

    try {
      // Тем же номером, что и запрос: карточку мост помнит под ним, и с новым
      // номером сюда всегда приходило бы «устарело».
      await numbered('world.link', id, overwrite,
                     { channel: 'link', op: lastOp('link') })
    } catch (error) {
      // «Такое уже есть» — не поломка, а ответ: привязка к занятой карточке
      // завела бы дубль. Сказать это надо словами, иначе человек читает
      // «не сохранилось» и ищет, что он сделал не так.
      if (error.kind !== TAKEN) throw error
      ontrouble('Эта карточка уже есть в библиотеке')
    }
  }

  async function unlink() {
    await call('library.unlink', item_id)
    onunlinked()
  }
</script>

<div class="cardform__row">
  {#if source}
    <span class="cardform__linked">{nameOf(source)}</span>
    <button type="button" class="icon-btn icon-btn--del cardform__unlink"
            aria-label="Отвязать от источника"
            onclick={() => unlink().catch((error) =>
              lost(error, 'Не удалось отвязать'))}>
      <Icon name="close" />
    </button>
  {:else}
    <Field bind:value={raw} placeholder="Ссылка на внешнюю базу"
           oninput={typing} />

    <!-- Галочка и есть единственный признак, что адрес понят: разбор идёт без
         сети, и другого ответа у него нет. -->
    {#if parsed}
      <span class="cardform__valid material-symbols-outlined" role="img"
            aria-label="Ссылка разобрана">check</span>
    {/if}

    <span class="cardform__check" title="Перезаписать данные">
      <TagBox state={overwrite ? 'on' : 'off'} label="Перезаписать данные"
              onclick={() => { overwrite = !overwrite }} />
    </span>
  {/if}
</div>
