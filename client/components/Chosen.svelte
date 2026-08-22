<!-- Выбранное рядом с полем: имена подряд, у каждого крестик. -->
<script>
  import Icon from '$components/Icon.svelte'

  // Именами, а не готовыми строками разметки: показывают этот список двое —
  // поле с подсказкой, где у выбранного есть номер, и список треков, где
  // номера нет вовсе. Общее у них ровно имя и то, что его убирают.
  let { names = [], label, ondrop } = $props()
</script>

<ul class="chosen">
  {#each names as name, index (name + index)}
    <li class="chosen__one">
      {name}
      <button type="button" class="icon-btn icon-btn--del chosen__del"
              aria-label={label} onclick={() => ondrop(index)}>
        <Icon name="close" />
      </button>
    </li>
  {/each}
</ul>
