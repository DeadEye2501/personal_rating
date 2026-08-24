<!-- Шапка сетки фильтра по оценке: имена колонок над переключателями. -->
<script>
  let { columns } = $props()
</script>

<!-- От чтения вслух скрыта: колонку называет подпись самого переключателя, и
     сказанная дважды она превратила бы список в перечисление заголовков. Пустая
     ячейка держит место звёзд — без неё имена уехали бы на колонку влево. -->
<div class="scorehead" style:--columns={columns.length} aria-hidden="true">
  <span></span>
  {#each columns as column (column.field)}
    <span class="scorehead__name">{column.label}</span>
  {/each}
</div>
