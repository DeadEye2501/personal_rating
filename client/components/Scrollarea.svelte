<!-- Область со своей полосой прокрутки. -->
<script>
  import { thumbOf } from '$state/scroll.js'

  // Сколько полоса висит после того, как прокрутка кончилась.
  const FADE = 700

  let { children } = $props()

  let box = $state()
  // Ползунок целиком: высота, смещение, масштаб — или `null`, прокручивать
  // нечего.
  let thumb = $state(null)
  let shown = $state(false)

  // Ни то ни другое не руна: читают их только обработчики, и перерисовки от них
  // не бывает.
  let hovered = false
  let timer

  // Считает `state/scroll.js`, здесь остаётся замер DOM: арифметику ползунка
  // иначе не сторожит ничто — компоненты по решению не проверяются.
  function measure() {
    if (!box) return
    thumb = thumbOf(box.clientHeight, box.scrollHeight, box.scrollTop)
  }

  $effect(() => {
    if (!box) return
    measure()

    const sized = new ResizeObserver(measure)
    sized.observe(box)
    // Размером области смена содержимого не видна: список фильтруется, а
    // область упёрта в свой потолок и не шевелится.
    const filled = new MutationObserver(measure)
    filled.observe(box, { childList: true, subtree: true })

    return () => {
      sized.disconnect()
      filled.disconnect()
      clearTimeout(timer)
    }
  })

  // Показана полоса или нет — про наведение и прокрутку; есть она вообще или
  // нет — про длину содержимого. Признака два, потому что событий два: слив их
  // в один, полосу нечем было бы гасить через паузу.
  const enter = () => { hovered = true; shown = true }
  const leave = () => { hovered = false; clearTimeout(timer); shown = false }

  function scrolled() {
    measure()
    shown = true
    clearTimeout(timer)
    timer = setTimeout(() => { if (!hovered) shown = false }, FADE)
  }

  function drag(event) {
    event.preventDefault()
    const grip = event.currentTarget
    grip.setPointerCapture(event.pointerId)

    const start = event.clientY
    const from = box.scrollTop
    const { scale } = thumb

    const move = (moved) => {
      box.scrollTop = from + (moved.clientY - start) * scale
    }
    grip.addEventListener('pointermove', move)
    // Отпускание считаем по потере захвата, а не по `pointerup`: кнопку могут
    // отпустить за окном приложения, и `pointerup` тогда не придёт вовсе.
    grip.addEventListener('lostpointercapture',
                          () => grip.removeEventListener('pointermove', move),
                          { once: true })
  }
</script>

<div class="scrollarea" onmouseenter={enter} onmouseleave={leave}>
  <div class="scrollarea__box" bind:this={box} onscroll={scrolled}>
    {@render children()}
  </div>
  <div class="scrollbar" class:is-shown={shown} hidden={thumb === null}>
    <div class="scrollbar__thumb" onpointerdown={drag}
         style:height={`${thumb?.height ?? 0}px`}
         style:transform={`translateY(${thumb?.offset ?? 0}px)`}></div>
  </div>
</div>
