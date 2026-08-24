<!-- Строка окна фильтра по оценке: одна ступень шкалы.
     Переключатель у неё один и стоит слева, а у игры их четыре — колонками
     справа, по одной на общую оценку и три шкалы. -->
<script>
  import Icon from '$components/Icon.svelte'
  import TagBox from '$components/TagBox.svelte'
  import { colorOf, labelOf, scale } from '$state/scores.js'

  let { score, columns } = $props()

  // Раскладка выводится из числа колонок, а не приходит отдельным признаком:
  // одна колонка бывает ровно там, где шкал не бывает вовсе.
  const many = $derived(columns.length > 1)
  const word = $derived(labelOf(score))
</script>

<!-- Глиф в переключателе спрятан от чтения вслух, поэтому подпись несёт и то, о
     чём строка. В сетке одного слова мало: колонок четыре, и «Отлично» сказано
     сразу о четырёх разных отборах. -->
{#snippet box(column)}
  <TagBox state={column.state} onclick={column.ontoggle}
          label={column.label ? `${column.label}, ${word}` : word} />
{/snippet}

<li class="tagrow" class:scoregrid={many} style:--columns={columns.length}>
  {#if !many}{@render box(columns[0])}{/if}

  <span class="scorerow" style:--score={colorOf(score)}>
    <span class="scorerow__stars">
      <!-- Признак пустоты висит на самом глифе, а не на обёртке: заливку ему
           ставит правило по `.material-symbols-outlined`, и с обёртки оно бы не
           перебилось — пустые звёзды вышли бы закрашенными. -->
      {#each scale() as step (step)}
        <Icon name="star" extra={step > score ? 'is-empty' : ''} />
      {/each}
    </span>
    <!-- В сетке слова нет: колонок четыре, и сказанное один раз оно говорило бы
         сразу о четырёх отборах. Читающему вслух оно достаётся от каждого
         переключателя, где названо вместе со своей колонкой. -->
    {#if !many}<span class="scorerow__label">{word}</span>{/if}
  </span>

  {#if many}
    {#each columns as column (column.field)}{@render box(column)}{/each}
  {/if}
</li>
