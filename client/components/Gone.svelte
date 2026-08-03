<!-- Строка списка убранного: слева название, справа кнопка возврата.

     Свёрнутая карточка без возможности развернуть — разворачивать в ней нечего:
     кроме названия, источника и типа в таблице убранного ничего не лежит.
     Решение пользователя 03.08.2026. -->
<script>
  import Icon from './Icon.svelte'

  let { view, onrestore } = $props()
</script>

<article class="film is-collapsed is-gone">
  <!-- Место то же, что у шеврона обычной карточки: колонка под угловые иконки
       в ней уже отведена, и заводить вторую незачем. -->
  <button type="button" class="icon-btn film__toggle"
          aria-label="Вернуть в поиск" onclick={() => onrestore(view)}>
    <Icon name="restore" />
  </button>

  <div class="film__body">
    <h2 class="film__title">{view.title}</h2>
  </div>
</article>
