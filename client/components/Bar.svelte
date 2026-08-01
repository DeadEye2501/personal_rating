<!-- Столбец гистограммы: заливка, число над верхушкой и подпись оценки. -->
<script>
  import { colorOf } from '$state/scores.js'

  let { score, count, share, index } = $props()
</script>

<!-- Доля не округляется: столбец в полпроцента — это не пустой столбец, а
     заглушка в шесть пикселей у них и так общая. -->
<div class="bar" style:--score={colorOf(score)} style:--i={index}
     style:--h={`${share * 100}%`}>
  <span class="bar__plot">
    <span class="bar__fill"><span class="bar__count">{count}</span></span>
  </span>
  <span class="bar__value">{score}</span>
</div>
