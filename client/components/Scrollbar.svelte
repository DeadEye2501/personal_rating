<!-- Своя полоса прокрутки для того, что прокручивается. -->
<script>
  import { dragging } from '$state/dragging.js'
  import { thumbFor } from '$state/scroll.js'

  // Сколько полоса висит после того, как прокрутка кончилась.
  const FADE = 700

  // Прокручивается одно, а наводят на другое: у списка это своя коробка внутри
  // области, у синопсиса — сам `textarea` внутри поля. Полоса лежит в `area`,
  // потому что позиционируется от неё.
  let { box, area } = $props()

  // Ползунок целиком: высота, смещение, масштаб — или `null`, прокручивать
  // нечего.
  let thumb = $state(null)
  let shown = $state(false)

  // Ни то ни другое не руна: читают их только обработчики, и перерисовки от них
  // не бывает.
  let hovered = false
  let timer

  // Последний отчёт наблюдателя о размере коробки. Хранится целиком, а не
  // высотой из него: какую мерку брать — решение `state/scroll.js`, и обе
  // прежние поломки полосы были именно на этом выборе.
  let sized = null

  // Считает `state/scroll.js`, вплоть до того, какие мерки снимать: ползунок
  // уезжал за край дорожки именно на выборе мерки, а компоненты по решению не
  // проверяются.
  function measure() {
    // До первого отчёта высоты нет вовсе, а посчитанная от нуля дорожка ушла бы
    // в минус. Ждать долго не приходится: наблюдатель отчитывается сразу на
    // `observe`, тем же кругом.
    if (!box || !sized) return
    thumb = thumbFor(box, sized)
  }

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

  $effect(() => {
    if (!box || !area) return

    // Первый замер делает сам наблюдатель: он отчитывается сразу на `observe`.
    const watcher = new ResizeObserver(([entry]) => { sized = entry; measure() })
    watcher.observe(box)
    // Размером содержимое не видно с двух сторон: список фильтруется, а область
    // упёрта в свой потолок и не шевелится; у `textarea` же набранный текст не
    // меняет вовсе ничего, кроме собственной высоты прокрутки.
    const filled = new MutationObserver(measure)
    filled.observe(box, { childList: true, subtree: true })
    box.addEventListener('input', measure)
    box.addEventListener('scroll', scrolled)
    area.addEventListener('mouseenter', enter)
    area.addEventListener('mouseleave', leave)

    return () => {
      watcher.disconnect()
      filled.disconnect()
      box.removeEventListener('input', measure)
      box.removeEventListener('scroll', scrolled)
      area.removeEventListener('mouseenter', enter)
      area.removeEventListener('mouseleave', leave)
      clearTimeout(timer)
    }
  })

  function drag(event) {
    const start = event.clientY
    const from = box.scrollTop
    const { scale } = thumb

    dragging(event.currentTarget, event, (moved) => {
      box.scrollTop = from + (moved.clientY - start) * scale
    })
  }
</script>

<div class="scrollbar" class:is-shown={shown} hidden={thumb === null}>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- Ползунок тащат мышью; с клавиатуры прокручивают стрелками, и роль ему не
       нужна. Предупреждение снято адресно, а не настройкой на весь проект. -->
  <div class="scrollbar__thumb" onpointerdown={drag}
       style:height={`${thumb?.height ?? 0}px`}
       style:transform={`translateY(${thumb?.offset ?? 0}px)`}></div>
</div>
