<!-- Окно создания и правки карточки: поля показываются своему типу. -->
<script>
  import Confirm from '$components/Confirm.svelte'
  import Field from '$components/Field.svelte'
  import Modal from '$components/Modal.svelte'
  import ModalFoot from '$components/ModalFoot.svelte'
  import Picker from '$components/Picker.svelte'
  import PosterPick from '$components/PosterPick.svelte'
  import AddLine from '$components/AddLine.svelte'
  import Chosen from '$components/Chosen.svelte'
  import Scrollarea from '$components/Scrollarea.svelte'
  import { call } from '$api/bridge.js'
  import { stampOf } from '$state/covers.js'
  import { emptyCard, fieldsOf, formOf, shownFor, wrongNumbers }
    from '$state/card.js'
  import { ROLES } from '$state/credits.js'
  import { GENRE_KINDS } from '$state/genres.js'
  import { MANUAL, linkableOf } from '$state/sources.js'
  import LinkField from './LinkField.svelte'
  import { complaining } from './trouble.js'

  let { view = null, kind, onsave, onclose, ontrouble } = $props()

  // Одно окно на создание и на правку: пустое заводит, заполненное правит, и
  // «Сохранить» само решает, что из двух. У новой тип берётся из тумблера
  // шапки, у открытой на правку — её собственный: тумблер мог с тех пор
  // переключиться, а карточка тип не меняет.
  let form = $state(view ? formOf(view) : emptyCard(kind))

  // Выбранная обложка, base64. Рядом с формой, а не в ней: записывается она
  // отдельным вызовом и после карточки — хранилище обложек ключуется по номеру,
  // а у новой карточки номера ещё нет.
  let picture = $state(null)

  // Найденный тёзка по названию и название, на которое согласие уже дано.
  // Совпадение — это предупреждение, а не запрет: фильмов с одинаковыми
  // названиями много.
  let twin = $state(null)
  let agreed = $state(null)

  // Идёт ли запись. Без этого второе нажатие «Сохранить» заводит вторую
  // карточку: запись начинается с похода через границу потоков, и до возврата
  // номера кнопка остаётся живой.
  let saving = $state(false)

  // Поле ссылки и текущий источник карточки. Привязку выполняет само поле, но
  // зовёт её сохранение: у новой карточки номер появляется только после записи,
  // а привязывать нечего к тому, чего в базе нет.
  let linker = $state()
  let source = $state(view && view.source !== MANUAL ? view.source : '')

  const shown = new Set(shownFor(form.kind))

  // За мостом ходит сборка, а не поле: у компонента своего источника данных не
  // бывает. Роль здесь ключом, потому что полей на экране до трёх, и у каждого
  // свой список совпадений.
  let suggested = $state({})

  // Рядом с каждым списком — номер последнего вопроса, набранное к нему, признак
  // «летит порция» и признак «строки кончились». Не руны: читают их только
  // обработчики, и перерисовки от них не бывает.
  const asked = {}
  const typed = {}
  const loading = {}
  const done = {}

  // Справочник жанров берётся разом и целиком: он короткий, закрытый и от
  // набранного не зависит — спрашивать его на каждую букву значило бы ходить
  // через границу потоков за одним и тем же.
  let genres = $state([])
  let typedGenre = $state('')

  const lost = complaining('окно карточки', ontrouble)

  $effect(() => {
    call('refs.genres', GENRE_KINDS[form.kind])
      .then((rows) => { genres = rows })
      .catch((error) => lost(error, 'Не удалось прочитать список жанров'))
  })

  // Пустая строка — это не «ничего не показывать», а весь список: щёлкнув по
  // полю, выбирают из готового, не набрав ни буквы.
  const matching = $derived(typedGenre
    ? genres.filter((row) => row.name.toLowerCase().includes(typedGenre.toLowerCase()))
    : genres)

  /** Строка подсказки приезжает своим типом границы; полю нужен нейтральный
   *  номер — тем же полем выбирают и жанр, у которого никакого `entity_id`
   *  нет. */
  const hinted = (row) => ({ id: row.entity_id, name: row.name,
                             hint: row.hint, hint_item_id: row.hint_item_id })

  /** Пустая строка спрашивается наравне с набранной: щёлкнув по полю, выбирают
   *  из уже заведённых, не набрав ни буквы.
   *
   *  Ответ принимается, только пока он свой. Мост зовёт бэкенд отдельным
   *  потоком на вызов, порядок приезда порядку вопросов не равен, и «Кри»,
   *  ответивший после «Кристофер», подставил бы в поле чужого человека. */
  async function suggest(role, domain, text) {
    const mine = (asked[role] ?? 0) + 1
    asked[role] = mine
    typed[role] = text
    done[role] = false

    const found = await call('refs.suggest', domain, text)
    if (asked[role] !== mine) return
    suggested = { ...suggested, [role]: found.map(hinted) }
  }

  /** Следующая порция дописывается к показанному: справочник отдаёт список
   *  порциями, потому что за узнаваемой карточкой ходит отдельный запрос на
   *  каждую строку.
   *
   *  Пустая порция значит «больше нет», и спрашивать дальше нечего: прокрутка
   *  у дна дёргает это на каждый пиксель. */
  async function more(role, domain) {
    if (loading[role] || done[role]) return
    loading[role] = true
    const mine = asked[role]
    const shown = suggested[role] ?? []

    try {
      const found = await call('refs.suggest', domain, typed[role] ?? '',
                               shown.length)
      if (asked[role] !== mine) return
      done[role] = !found.length
      if (found.length) {
        suggested = { ...suggested, [role]: [...shown, ...found.map(hinted)] }
      }
    } finally {
      loading[role] = false
    }
  }

  const pick = (role, list) => { form[role] = list }

  /** Единственный вход в запись: и кнопка, и согласие на тёзку идут сюда. Пока
   *  запись летит, второго захода не бывает — иначе их будет две карточки. */
  async function keep() {
    if (saving) return
    saving = true
    try {
      await save()
    } catch (error) {
      lost(error, 'Карточка не сохранилась')
    } finally {
      saving = false
    }
  }

  /** Совпадение названия — предупреждение, а не запрет. Своя же карточка из
   *  находок вычёркивается: правя её, о самой себе спрашивать незачем.
   *
   *  Согласие помнится вместе с названием, на которое его дали: переписав
   *  название после «Вы точно уверены?», человек спрашивает о другом. */
  async function save() {
    const fields = fieldsOf(form)
    if (fields.title === null) {
      ontrouble('У карточки должно быть название')
      return
    }

    const wrong = wrongNumbers(form)
    if (wrong.length) {
      ontrouble('Год, минуты, сезоны и серии — это числа')
      return
    }

    const same = await call('library.same_title', form.kind, fields.title)
    const others = same.filter((one) => one.id !== form.item_id)
    if (others.length && agreed !== fields.title) {
      twin = others[0]
      return
    }
    await write(fields)
  }

  /** Порядок записи принадлежит странице: у новой карточки номер появляется
   *  только после первой записи, а жанрам, составу и обложке без него писать
   *  некуда. Мост тонкий и не оркеструет — это решение плана 5.
   *
   *  Номер запоминается сразу: сорвись состав или обложка, повтор обязан
   *  дописать ту же карточку, а не завести вторую. */
  async function write(fields) {
    if (!form.item_id) form.item_id = await call('library.create', fields)
    else await call('library.replace', form.item_id, fields)

    const item_id = form.item_id
    await call('refs.set_genres', item_id, form.genres.map((one) => one.id))
    await writeCredits(item_id)
    // Своим вызовом, а не полем карточки: колонки под треки у `Item` нет, и
    // уехав в поля, они уронили бы запись лишним доводом сборщика. Список
    // пишется целиком, как и состав, — снять всё и записать заново.
    if (shown.has('tracks')) await call('library.set_tracks', item_id, form.tracks)
    if (picture) await call('covers.store_upload', item_id, picture)

    // Привязка последней: внешнее доливает только пустое, и долить оно должно
    // поверх уже записанного человеком, а не наоборот.
    //
    // Её срыв записи не отменяет: карточка уже в базе, и говорить «не
    // сохранилась» значило бы врать. О самой привязке скажет она сама.
    try {
      await linker?.link(item_id)
    } catch (error) {
      lost(error, 'Не удалось привязать к внешней базе')
    }

    onsave(item_id)
  }

  /** Состав правится целиком: снять всё и расставить заново. Сличать построчно
   *  значило бы решать за человека, что именно он поменял.
   *
   *  Новый заводится по ходу — номера у него нет, потому что его не выбирали из
   *  подсказки, а набрали и подтвердили Enter. */
  async function writeCredits(item_id) {
    for (const domain of ['people', 'companies']) {
      await call('refs.detach_all', domain, item_id)
    }

    for (const { role, domain } of ROLES) {
      let position = 0
      for (const one of form[role]) {
        const entity_id = one.id
          ?? await call('refs.create_person', domain, one.name)
        await call('refs.attach', domain, item_id, entity_id, role, position)
        position += 1
      }
    }
  }
</script>

<Modal wide card label="Карточка" {onclose}>
  {#snippet children()}
    <div class="cardform__top">
      <!-- Картинка лежит рядом с формой, а не в ней: поля формы — это поля
           карточки, а обложка живёт вторым файлом базы и уезжает отдельным
           вызовом уже после записи, когда у карточки появился номер. -->
      <!-- Момент едет вместе с карточкой: ручка обложки отдаёт сутки кеша, а
           её адрес от содержимого не зависит — без метки перезалитая картинка
           осталась бы в окне правки прежней, пока лента показывает новую. -->
      <PosterPick item_id={form.item_id} stamp={stampOf(view)}
                  onpicked={(data) => { picture = data }}
                  ontrouble={(text) => ontrouble(text)} />

      <div class="cardform__fields">
        <Field bind:value={form.title} placeholder="Название" variant="field--title" />

        <div class="cardform__row">
          <Field bind:value={form.original_title} placeholder="Оригинальное название" />
          <Field bind:value={form.year} placeholder="Год" variant="field--short" />
          {#if shown.has('runtime')}
            <Field bind:value={form.runtime} placeholder="Минуты" variant="field--short" />
          {/if}
          {#if shown.has('seasons_count')}
            <Field bind:value={form.seasons_count} placeholder="Сезоны" variant="field--short" />
            <Field bind:value={form.episodes_count} placeholder="Серии" variant="field--short" />
          {/if}
        </div>

        <!-- У типа без каталога вставленную ссылку разбирать нечего: любая
             строка ответила бы отказом. С 23.08.2026 источник есть у всех пяти,
             и ветка истинна всегда; набор она читает, а не литерал, потому что
             сверяется он с реестром сторожем границы — исчезнет там строка,
             исчезнет и поле. -->
        {#if linkableOf(form.kind)}
          <LinkField bind:this={linker} item_id={form.item_id} kind={form.kind}
                     {source} onunlinked={() => { source = '' }}
                     ontrouble={(text) => ontrouble(text)} />
        {/if}

        <Field bind:value={form.synopsis} placeholder="Синопсис"
               variant="field--area" area />
      </div>
    </div>

    <!-- Поля с подсказкой прокручиваются вместе: у сериала состав бывает в три
         сотни имён, и без этого окно вырастало за экран, а ряд кнопок уезжал за
         нижний край. -->
    <Scrollarea>
      {#snippet children()}
        <!-- Роли одним перебором, а не пятью почти одинаковыми блоками:
             различаются они подписью, доменом и ключом роли — то есть данными,
             а не разметкой. -->
        {#each ROLES as one (one.role)}
          {#if shown.has(one.role)}
            <Picker label={one.label} hits={suggested[one.role] ?? []}
                    chosen={form[one.role]}
                    ontype={(text) => suggest(one.role, one.domain, text)
                      .catch((error) => lost(error, 'Не удалось спросить подсказку'))}
                    onmore={() => more(one.role, one.domain)
                      .catch((error) => lost(error, 'Не удалось спросить подсказку'))}
                    oncreate={(made) => pick(one.role, [...form[one.role], made])}
                    onchosen={(list) => pick(one.role, list)} />
          {/if}
        {/each}

        <!-- Треки стоят после состава, там же, где у фильма актёры, и той же
             строкой из двух колонок. Ролью состава они при этом не являются:
             за треком нет ни человека, ни студии, и подсказывать по нему
             нечего — вместо поля с подсказкой стоит поле с кнопкой.

             Повтор названия не отказ: на альбоме бывают две части одной вещи с
             одним именем, — отсюда `true` без условий. -->
        {#if shown.has('tracks')}
          <div class="cardform__pick">
            <AddLine placeholder="Треки" label="Название трека"
                     action="Добавить трек"
                     oncreate={(name) => {
                       form.tracks = [...form.tracks, name]
                       return true
                     }} />
            <Chosen names={form.tracks} label="Убрать трек"
                    ondrop={(index) => {
                      form.tracks = form.tracks.filter((_, at) => at !== index)
                    }} />
          </div>
        {/if}

        <!-- Тем же полем, и второго поведения у него от этого не появляется:
             оно не знает, откуда взялись совпадения. Заводить новое умеет тот,
             кому передали `oncreate`, — набор жанров зашит в миграцию, своего
             жанра не бывает, и здесь его не передают вовсе. -->
        <Picker label="Жанры" hits={matching} chosen={form.genres}
                ontype={(text) => { typedGenre = text }}
                onchosen={(list) => pick('genres', list)} />
      {/snippet}
    </Scrollarea>

    <!-- Кнопки «удалить» внутри окна нет: удаление живёт на карточке, и второго
         входа ему не нужно. -->
    <ModalFoot ok="Сохранить" busy={saving} oncancel={onclose} onok={keep} />
  {/snippet}
</Modal>

<!-- Тем же окном, что и подтверждение удаления, но акцентным: красное отведено
     тому, что пропадает навсегда, а тут ничего не пропадает. -->
{#if twin}
  <Confirm label="Такое уже есть" ok="OK"
           text={`«${twin.title}» уже есть в библиотеке. Вы точно уверены?`}
           onyes={() => { agreed = fieldsOf(form).title
                          twin = null
                          keep() }}
           onclose={() => { twin = null }} />
{/if}
