<!-- Строка оценки в списке: неподвижные звёзды и ярлык словом. -->
<script>
  import Icon from '$components/Icon.svelte'
  import TagBox from '$components/TagBox.svelte'
  import { colorOf, labelOf, scale } from '$state/scores.js'

  let { score, state = 'off', ontoggle } = $props()
</script>

<li class="tagrow">
  <TagBox {state} label={labelOf(score)} onclick={ontoggle} />

  <span class="scorerow" style:--score={colorOf(score)}>
    <span class="scorerow__stars">
      <!-- Признак пустоты висит на самом глифе, а не на обёртке: заливку ему
           ставит правило по `.material-symbols-outlined`, и с обёртки оно бы не
           перебилось — пустые звёзды вышли бы закрашенными. -->
      {#each scale() as step (step)}
        <Icon name="star" extra={step > score ? 'is-empty' : ''} />
      {/each}
    </span>
    <span class="scorerow__label">{labelOf(score)}</span>
  </span>
</li>
