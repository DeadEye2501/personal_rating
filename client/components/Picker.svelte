<!-- Поле с подсказкой: печатаешь — снизу совпадения, выбранное ложится справа. -->
<script>
  import Chosen from '$components/Chosen.svelte'
  import Field from '$components/Field.svelte'
  import { byItem } from '$state/covers.js'
  import { squareOf } from '$state/kinds.js'
  import { beside } from '$state/popup.js'

  // Разделитель строки подсказки: `U+2022 BULLET`. Обычная точка не годится —
  // она читается как конец предложения и слипается с названием.
  const DOT = '•'

  // Размер всплывающего постера. Числом здесь, а не в оформлении: по нему же
  // считается место у края окна, и вторым объявлением они разъехались бы.
  //
  // Высота одна на оба вида, разная ширина: у афиши пропорция 2:3, у альбома
  // квадрат — та же пара, что у обложки ленты и у рамки окна.
  const POSTER = { width: 120, height: 180 }
  // Квадрат считается из высоты афиши, а не пишется числом: третье число той же
  // высоты разъехалось бы с первыми двумя молча.
  const SQUARE_POSTER = { width: POSTER.height, height: POSTER.height }

  // За сколько до конца списка просить следующую порцию. Не ноль: докрученный
  // до самого дна список успел бы упереться раньше, чем приедет ответ.
  const EDGE = 40

  // Зазор между полем и списком, он же отступ от края окна. Числом здесь, а не
  // в оформлении: место списка считает разметка, и вторым объявлением зазор
  // разъехался бы с ним.
  const GAP = 4

  // Строка собирается целиком, а не разметкой из трёх кусков: пробел перед
  // маркером стоял бы на границе блока `{#if}`, а её Svelte подчищает — имя и
  // маркер слипались бы.
  const line = (hit) => hit.hint ? `${hit.name} ${DOT} ${hit.hint}` : hit.name

  // Совпадения приходят параметром, а за мостом ходит сборка: компонент, у
  // которого есть свой источник данных, перестаёт быть показом переданного.
  // Отсюда же и закрытый список жанров — он просто не передаёт `oncreate`, а
  // догружать ему нечего, и `onmore` там тоже нет.
  let { label, hits = [], chosen = [], ontype, onchosen, oncreate, onmore }
    = $props()


  // Уже выбранного в списке нет: предложить его второй раз значит предложить
  // завести того же человека дважды.
  const offered = $derived(hits.filter(
    (hit) => !chosen.some((one) => one.id === hit.id)))

  let text = $state('')
  // Подсветки нет, пока её не поставили стрелкой: пока в списке ничего не
  // подсвечено, Enter заводит нового.
  let marked = $state(-1)
  let hovered = $state(null)

  // Форма всплывающей обложки берётся от **показываемой** карточки, а не от
  // той, которую правят: человек бывает и в фильмах, и в альбомах, а подсказка
  // показывает его самое высоко оценённое, какого бы типа оно ни было. Тип
  // приезжает в самой строке подсказки, вместе с названием и номером.
  const shape = $derived(squareOf(hovered?.hint_kind) ? SQUARE_POSTER : POSTER)
  // Постер идёт за указателем, поэтому запоминается точка, а не строка: у
  // длинной строки её край и её середина — разные места экрана.
  let at = $state({ left: 0, top: 0 })
  // Помнится сорвавшийся адрес, а не признак «сломано»: признак не дал бы
  // показать следующий постер, приехавший исправно.
  let failed = $state('')
  // Открыт список или нет — отдельно от того, есть ли в нём строки: выбранное
  // закрывает его, не трогая совпадений, а уход из поля закрывает тем более.
  let open = $state(false)
  // Место списка в координатах окна — по нему же считается его ширина: у поля
  // она своя, а список обязан быть не уже.
  let under = $state({ left: 0, top: 0, width: 0 })
  let anchor = $state()
  let list = $state()
  let shot = $state()

  const showing = $derived(open && offered.length > 0)

  const poster = $derived(hovered?.hint_item_id
    ? byItem(hovered.hint_item_id) : '')

  // Обе всплывашки живут в верхнем слое браузера, а не рядом с полем: у области
  // с полями своя прокрутка, и всё, что вылезает за её край, она обрезает —
  // список совпадений обрывался на середине, а постер срезался наполовину.
  // Верхний слой не обрезает ничто, и отсчёт в нём идёт от окна: место обеих
  // считается в координатах окна.
  const raise = (node) => { if (!node.matches(':popover-open')) node.showPopover() }
  const lower = (node) => { if (node.matches(':popover-open')) node.hidePopover() }

  // Место считается после показа, а не до: у спрятанного popover-а нет ни
  // высоты, ни ширины, а без высоты не решить, влезает он под полем или нет.
  // Оба действия идут в одном обороте, поэтому промежуточного места не видно.
  $effect(() => {
    if (!list) return
    if (showing) { raise(list); place() } else lower(list)
  })

  // Постер показывается сразу, как появился: место у него своё, за указателем.
  $effect(() => { if (shot) raise(shot) })

  // Прокрутка области с полями увозит поле, а верхний слой стоит на месте: без
  // пересчёта список остался бы висеть там, где поле было. Своя прокрутка
  // списка сюда тоже приходит и пересчитывает то же самое — отсеивать её
  // дороже, чем один замер.
  $effect(() => {
    if (!showing) return
    const again = () => place()
    window.addEventListener('scroll', again, true)
    window.addEventListener('resize', again)
    return () => {
      window.removeEventListener('scroll', again, true)
      window.removeEventListener('resize', again)
    }
  })

  /** Под полем, а не влезает — над ним: у нижних полей окна карточки места вниз
   *  нет вовсе, и список уходил бы за край окна, где его не достать. */
  function place() {
    const box = anchor.getBoundingClientRect()
    const below = box.bottom + GAP
    const fits = below + list.offsetHeight <= window.innerHeight - GAP
    under = { left: box.left,
              top: fits ? below : box.top - GAP - list.offsetHeight,
              width: box.width }
  }

  // Набранное расходится обработчиком, а не эффектом по `text`: эффект читал бы
  // и `ontype`, а его сборка пересоздаёт на каждой перерисовке — вышел бы
  // бесконечный круг «спросил → перерисовался → спросил».
  function typing(event) {
    marked = -1
    open = true
    ontype(event.currentTarget.value.trim())
  }

  // Щелчок по пустому полю показывает список целиком: выбрать уже заведённого
  // человека можно, не набрав ни буквы.
  function focus() {
    open = true
    ontype(text.trim())
  }

  /** Клавиши работают по показанному, а не по помнимому: у закрытого списка
   *  стрелка подсветила бы строку, которой не видно, и Enter взял бы её. */
  function keydown(event) {
    if (!open) return

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      move(Math.min(marked + 1, offered.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      move(Math.max(marked - 1, -1))
    } else if (event.key === 'Escape') {
      open = false
    } else if (event.key === 'Enter') {
      event.preventDefault()
      // Строки под подсветкой может уже не быть: пока тянулись до Enter, могла
      // приехать другая порция. Тогда это Enter по неподсвеченному — то есть
      // заведение нового, а не выбор соседа.
      offered[marked] ? take(offered[marked]) : create()
    }
  }

  /** Подсвеченное обязано быть видно: в список влезает шесть строк из десяти, и
   *  подсветка ниже шестой уходила бы за край без единого признака. */
  function move(next) {
    marked = next
    list?.children[marked]?.scrollIntoView({ block: 'nearest' })
  }

  const take = (hit) => add({ id: hit.id, name: hit.name })

  // Enter при неподсвеченном списке заводит нового — и человека, и студию.
  // Совпадение имени само по себе не решает ничего: полные тёзки существуют.
  // У закрытого списка (жанры) заводить нечего, и `oncreate` там не передан —
  // отсутствие обработчика и есть закрытость.
  function create() {
    const name = text.trim()
    if (!name || !oncreate) return
    oncreate({ id: null, name })
    clear()
  }

  function add(one) {
    onchosen([...chosen, one])
    clear()
  }

  // Выбранное закрывает список, а совпадения оставляет как есть: спрашивать их
  // заново незачем — следующий щелчок по полю и так спросит.
  function clear() {
    text = ''
    marked = -1
    hovered = null
    open = false
  }

  /** Место считает `state/popup.js` в координатах окна — у края картинка обязана
   *  поджаться, и эта арифметика единственное, что тут проверяется тестом.
   *  Переводить его никуда не надо: верхний слой и отсчитывается от окна. */
  function follow(event, hit) {
    hovered = hit
    at = beside({ x: event.clientX, y: event.clientY }, shape,
                { width: window.innerWidth, height: window.innerHeight })
  }

  /** Следующая порция просится, не доходя до дна: список короткий, и упёршись в
   *  край, человек увидел бы остановку раньше, чем приедет продолжение. */
  function scrolled(event) {
    const box = event.currentTarget
    if (onmore && box.scrollTop + box.clientHeight >= box.scrollHeight - EDGE) {
      onmore()
    }
  }

  const drop = (index) => onchosen(chosen.filter((_, at_) => at_ !== index))
</script>

<div class="cardform__pick">
  <div class="picker" bind:this={anchor}>
    <!-- Уход из поля закрывает список; выбор при этом не теряется — см. ниже. -->
    <Field bind:value={text} placeholder={label} oninput={typing}
           onkeydown={keydown} onfocus={focus}
           onblur={() => { open = false; hovered = null }} />
    <!-- `popover` — не украшение: без него список обрезает прокрутка области с
         полями. Показывает и прячет его эффект по `showing`, поэтому здесь нет
         ни `hidden`, ни `{#if}`: у скрытого popover-а нет своего `display`. -->
    <ul class="picker__hits" popover="manual" bind:this={list} onscroll={scrolled}
        style:left={`${under.left}px`} style:top={`${under.top}px`}
        style:min-width={`${under.width}px`}>
      {#each offered as hit, index (hit.id)}
        <li>
          <!-- `preventDefault` на mousedown держит фокус в поле: без него он
               уходит в тело страницы, и следующее имя набирать некуда. Он же
               делает выбор мышью возможным вообще — клик состоялся бы уже
               после того, как потеря фокуса закрыла список. -->
          <button type="button" class="picker__hit" class:is-marked={index === marked}
                  onmousemove={(event) => follow(event, hit)}
                  onmouseleave={() => { hovered = null }}
                  onmousedown={(event) => { event.preventDefault(); take(hit) }}>
            {line(hit)}
          </button>
        </li>
      {/each}
    </ul>

    <!-- Всплывает только постер: название уже стоит в самой строке, после
         маркера. Не приехал — строка живёт дальше, ничего не двигая.

         В верхнем слое, а не внутри списка: у того своя прокрутка, а она
         обрезает всё, что вылезает за его край. -->
    {#if poster && failed !== poster}
      <img class="picker__poster" popover="manual" bind:this={shot}
           class:is-square={squareOf(hovered?.hint_kind)}
           src={poster} alt=""
           style:width={`${shape.width}px`}
           style:left={`${at.left}px`} style:top={`${at.top}px`}
           onerror={() => { failed = poster }}>
    {/if}
  </div>

  <Chosen names={chosen.map((one) => one.name)} label="Убрать" ondrop={drop} />
</div>
