<!-- Окно создания и правки карточки: поля показываются своему типу. -->
<script>
  import Button from '$components/Button.svelte'
  import Field from '$components/Field.svelte'
  import Modal from '$components/Modal.svelte'
  import { emptyCard, shownFor } from '$state/card.js'

  let { kind, onsave, onclose } = $props()

  // Тип берётся из тумблера шапки и отдельно не спрашивается. Смениться под
  // открытым окном он не может: тумблер закрыт наложением.
  let form = $state(emptyCard(kind))

  const shown = new Set(shownFor(kind))
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
