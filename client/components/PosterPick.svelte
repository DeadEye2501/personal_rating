<!-- Обложка карточки: выбрать файлом, перетаскиванием или из буфера. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Предел на заливаемую картинку. Обложке хватает и десятой доли: рамка 230
  // пикселей шириной, а бэкенд обрезает её до 2:3 и хранит как есть. Предел
  // нужен не ради места, а ради канала: внутрь картинка идёт текстом, и мост
  // держит её строкой целиком.
  const LIMIT = 8 * 1024 * 1024

  let { onpicked, ontrouble } = $props()

  // Что показывать: только что выбранное. Сохранённая обложка приезжает не
  // сюда — её показывает ручка по номеру, а у новой карточки номера нет.
  let preview = $state(null)
  let failed = $state(false)

  /** Внутрь картинка идёт base64: доводы уезжают мосту текстом, и бинарным этот
   *  канал не бывает. Обрезку по центру до 2:3 делает бэкенд — там же, где
   *  картинка и хранится: `PIL` в клиент не пускает граница слоёв.
   *
   *  Читает `FileReader`, а не свой цикл по байтам: цикл на мегабайтном файле
   *  держит поток интерфейса, а этот отдаёт готовую строку и ждёт в стороне. */
  async function take(file) {
    // Не картинка не делает ничего молча только на вид: перетащить в окно можно
    // что угодно, и человек вправе узнать, почему ничего не произошло.
    if (!file) return
    if (!file.type.startsWith('image/')) {
      ontrouble('Это не картинка')
      return
    }
    if (file.size > LIMIT) {
      ontrouble('Картинка слишком большая')
      return
    }

    const data = await read(file)
    if (data === null) {
      ontrouble('Не удалось прочитать файл')
      return
    }

    // Прежний адрес отпускается: браузер держит файл, пока ссылку не отозвали,
    // и подмена за подменой оставляла бы их все.
    if (preview) URL.revokeObjectURL(preview)
    preview = URL.createObjectURL(file)
    failed = false
    onpicked(data)
  }

  /** Отдаёт содержимое base64 или `null`, если прочитать не вышло. Ошибка тут
   *  штатная: файл могли отобрать между выбором и чтением. */
  function read(file) {
    return new Promise((resolve) => {
      const reader = new FileReader()
      // `readAsDataURL` даёт «data:тип;base64,тело» — телу и место после
      // запятой; своего кодировщика заводить незачем.
      reader.onload = () => resolve(String(reader.result).split(',')[1])
      reader.onerror = () => resolve(null)
      reader.readAsDataURL(file)
    })
  }

  /** Тот же файл подряд второй раз: без сброса поле считает, что ничего не
   *  изменилось, и события не даёт вовсе. */
  function chosen(event) {
    const input = event.currentTarget
    take(input.files[0])
    input.value = ''
  }

  $effect(() => () => { if (preview) URL.revokeObjectURL(preview) })
</script>

<!-- Ctrl+V и перетаскивание ловятся на окне, а не на рамке. У буфера причина
     своя: он вставляется туда, где фокус, а фокуса у картинки не бывает. У
     перетаскивания — жёстче: брошенный мимо рамки файл браузер открывает сам,
     и окно уезжает на `file://`, откуда без адресной строки не вернуться.
     Пока открыто окно карточки, картинка в нём означает обложку: других мест
     для картинки тут нет. -->
<svelte:window onpaste={(event) => take(event.clipboardData?.files?.[0])}
               ondragover={(event) => event.preventDefault()}
               ondrop={(event) => { event.preventDefault()
                                    take(event.dataTransfer?.files?.[0]) }} />

<label class="cardform__poster">
  {#if preview && !failed}
    <img src={preview} alt="" onerror={() => { failed = true }}>
  {:else}
    <Icon name="photo_camera" />
  {/if}
  <input type="file" accept="image/*" hidden onchange={chosen}>
</label>
