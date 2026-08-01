<!-- Окно создания и правки карточки: поля показываются своему типу. -->
<script>
  import Button from '$components/Button.svelte'
  import Field from '$components/Field.svelte'
  import Modal from '$components/Modal.svelte'
  import Picker from '$components/Picker.svelte'
  import { call } from '$api/bridge.js'
  import { emptyCard, shownFor } from '$state/card.js'
  import { ROLES } from '$state/credits.js'
  import { GENRE_KINDS } from '$state/genres.js'
  import { reported } from './trouble.js'

  let { kind, onsave, onclose, ontrouble } = $props()

  // Одно окно на создание и на правку: пустое заводит, заполненное правит.
  // Тип берётся из тумблера шапки и отдельно не спрашивается. Смениться под
  // открытым окном он не может: тумблер закрыт наложением.
  let form = $state(emptyCard(kind))

  const shown = new Set(shownFor(kind))

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

  const lost = (error, text) =>
    reported(error, 'окно карточки', () => ontrouble(text))

  $effect(() => {
    call('refs.genres', GENRE_KINDS[kind])
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
</script>

<Modal card label="Карточка" {onclose}>
  {#snippet children()}
    <div class="cardform__top">
      <div class="cardform__poster"></div>

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

        <Field bind:value={form.synopsis} placeholder="Синопсис"
               variant="field--area" area />
      </div>
    </div>

    <!-- Роли одним перебором, а не пятью почти одинаковыми блоками: различаются
         они подписью, доменом и ключом роли — то есть данными, а не разметкой. -->
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

    <!-- Тем же полем, и второго поведения у него от этого не появляется: оно не
         знает, откуда взялись совпадения. Заводить новое умеет тот, кому
         передали `oncreate`, — набор жанров зашит в миграцию, своего жанра не
         бывает, и здесь его не передают вовсе. -->
    <Picker label="Жанры" hits={matching} chosen={form.genres}
            ontype={(text) => { typedGenre = text }}
            onchosen={(list) => pick('genres', list)} />

    <!-- Кнопки «удалить» внутри окна нет: удаление живёт на карточке, и второго
         входа ему не нужно. -->
    <div class="modalfoot">
      <Button variant="btn--cancel" onclick={onclose}>
        {#snippet children()}Отмена{/snippet}
      </Button>
      <Button variant="btn--go" onclick={() => onsave(form)}>
        {#snippet children()}Сохранить{/snippet}
      </Button>
    </div>
  {/snippet}
</Modal>
