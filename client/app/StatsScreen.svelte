<!-- Раздел «Статистика»: гистограмма своих оценок по тому же отфильтрованному
     набору, что и разделы с карточками. -->
<script>
  import Bar from '$components/Bar.svelte'
  import { numbered } from '$api/bridge.js'
  import { owned } from '$api/owned.svelte.js'
  import { chosen } from '$state/filters.js'
  import { heightsOf } from '$state/histogram.js'
  import { complaining } from './trouble.js'

  let { session, ontrouble } = $props()

  // Пусто до первого ответа и между запросами: прежний ответ — про другой
  // набор, а десять безымянных чисел от чужого типа содержимого не отличить ни
  // по чему. В ленте то же самое видно по названиям карточек, здесь — нет.
  const NOTHING = { buckets: [], total: 0, average: null }

  let histogram = $state(NOTHING)
  const ops = owned()

  // Простыми значениями, а не чтением сеанса в эффекте: `session` приходит
  // геттером, и любая его пересборка — свёрнутость, сортировка — перезапрашивала
  // бы гистограмму.
  //
  // Запрос собирается здесь, а не общим `requestOf`: у статистики нет ни своего
  // порядка, ни страницы, и `requestOf` за неё падает намеренно.
  const kind = $derived(session.kind)
  const asked = $derived(JSON.stringify(chosen(session.filters)))

  const lost = complaining('гистограмма', ontrouble)

  $effect(() => {
    histogram = NOTHING
    numbered('feed.histogram', kind, JSON.parse(asked), { channel: 'feed', ops })
      .then((answer) => { histogram = answer })
      .catch((error) => lost(error, 'Не удалось построить гистограмму'))
  })

  const shares = $derived(heightsOf(histogram.buckets))
</script>

<div class="chart">
  <!-- Столбцы пересоздаются на каждый новый набор, а не переезжают высотой:
       так в макете, и только так они отрастают из пола, а не прыгают. -->
  {#key asked + kind}
    <div class="chart__bars">
      {#each histogram.buckets as bucket, index (bucket.score)}
        <Bar score={bucket.score} count={bucket.count} share={shares[index]}
             {index} />
      {/each}
    </div>
  {/key}

  <!-- Оба числа считает база по неокруглённым значениям: сумма по столбцам у
       игр занижала бы среднюю почти на полбалла. -->
  <p class="chart__foot">
    Средняя оценка <b>{histogram.average?.toFixed(2) ?? '—'}</b>,
    всего <b>{histogram.total}</b>
  </p>
</div>
