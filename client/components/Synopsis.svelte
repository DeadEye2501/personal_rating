<!-- Описание карточки, обрезанное до трёх строк, с раскрытием и сворачиванием. -->
<script>
  import { wordEnd } from '$state/trim.js'

  let { text = '' } = $props()

  const LINES = 3
  const MORE = '… ещё'

  let full = $state(false)
  let paragraph = $state()
  // Что реально стоит в абзаце: целиком или обрезанное так, чтобы после него
  // поместилась кнопка. До первого замера — целиком: по нему же замер и решает,
  // есть ли что резать, не поднимая двойника.
  let shown = $state(text)
  let cut = $state(false)
  // Ширина, при которой считали. Наблюдатель размеров будит замер и тогда,
  // когда ширина не менялась, — например, когда абзац подрос от подстановки
  // текста, — а перебор стоит десятка принудительных пересчётов разметки.
  let measuredAt = 0

  /** Сколько текста влезает в три строки вместе с кнопкой.
   *
   *  Меряется на двойнике, а не на самом абзаце: у двойника те же стили —
   *  он и создан клонированием, — но он спрятан и лежит вне потока, так что
   *  перебор длин не мигает на экране и не двигает соседей.
   *
   *  Кнопка кладётся в двойник настоящая: место ей нужно **в строке**, а не
   *  поверх текста. Обрезка поверх и была тем, что пользователь назвал
   *  беспорядком: кнопка перекрывала слово на середине.
   *
   *  Возвращает длину видимой части или `null`, если резать нечего. */
  function measured() {
    const twin = paragraph.cloneNode(false)
    twin.style.cssText = 'position:absolute;visibility:hidden;max-height:none'
    twin.style.width = `${paragraph.clientWidth}px`
    const body = document.createTextNode(text)
    twin.append(body)
    paragraph.after(twin)

    const limit = Number.parseFloat(
      getComputedStyle(paragraph).lineHeight) * LINES
    try {
      // Высоты строки может не быть числом — `normal` у неназванного шрифта, —
      // и тогда предел выходит `NaN`, а перебор схлопывается в пустоту: вместо
      // синопсиса пустое место. Лучше показать целиком.
      if (!Number.isFinite(limit) || twin.scrollHeight <= limit + 1) return null

      const button = document.createElement('button')
      button.className = 'more'
      button.textContent = MORE
      twin.append(button)
      return longest(twin, body, limit)
    } finally {
      twin.remove()
    }
  }

  /** Самая длинная начальная часть, которая вместе с кнопкой держится в трёх
   *  строках. Перебор делением пополам: на шестистах знаках это десяток замеров
   *  вместо шестисот. */
  function longest(twin, body, limit) {
    let low = 0
    let high = text.length
    while (low < high) {
      const middle = Math.ceil((low + high) / 2)
      body.data = text.slice(0, middle)
      if (twin.scrollHeight <= limit + 1) low = middle
      else high = middle - 1
    }
    return low
  }

  /** Замер идёт после отрисовки — до неё высоты нулевые, — и повторяется на
   *  смене текста: правка карточки приносит другой синопсис в тот же компонент.
   *
   *  Раскрытым не меряем: там текст стоит целиком, и обрезать нечего.
   *
   *  Эффектом, а не `onMount`: абзаца может не быть вовсе — у каждой игры из
   *  GOG синопсис пуст, — и замер по несуществующему узлу ронял бы исключение,
   *  а с ним и остаток очереди эффектов, то есть соседей по ленте. */
  function fit() {
    // Ширины нет у свёрнутой карточки: `display: none` обнуляет разметку, и
    // замер обрезал бы текст до пустоты. Развернут — наблюдатель размеров
    // разбудит замер сам, потому что коробка сменится с нулевой на настоящую.
    const width = paragraph?.clientWidth
    if (!width || width === measuredAt) return
    measuredAt = width

    // Пока в абзаце полный текст, обрезку видно и без двойника: одно чтение
    // высоты против десятка на перебор. Короткий синопсис этим и кончается.
    if (shown === text && paragraph.scrollHeight <= paragraph.clientHeight) {
      cut = false
      return
    }

    const end = measured()
    cut = end !== null
    shown = cut ? wordEnd(text, end) : text
  }

  // Пересчёт на смене ширины: карточка тянется за окном, и в строку влезает
  // другое число слов. `ResizeObserver`, а не событие окна: он же будит замер,
  // когда карточка выходит из-за края экрана и наконец получает настоящий
  // размер.
  $effect(() => {
    // Смена текста — новый замер: правка карточки приносит другой синопсис в
    // тот же компонент, а ширина при этом не меняется, и отсечка по ней
    // оставила бы обрезку от прежнего.
    text
    measuredAt = 0
    if (!paragraph || full) { shown = text; return }
    fit()
    const watcher = new ResizeObserver(fit)
    watcher.observe(paragraph)
    return () => watcher.disconnect()
  })
</script>

<!-- Кнопка идёт внутри абзаца, следом за текстом: место ей освобождено самим
     замером, и накрывать ею слова больше нечем. Обрезка при этом остаётся —
     высотой, — потому что до первого замера в абзаце стоит полный текст. -->
{#if text}
  <p class="film__synopsis" class:is-cut={!full} bind:this={paragraph}
  >{shown}{#if cut}<button type="button" class="more"
      onclick={() => { full = !full }}
    >{full ? 'свернуть' : MORE}</button>{/if}</p>
{/if}
