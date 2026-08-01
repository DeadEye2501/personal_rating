<!-- Корень страницы: показывает, дождалась ли она моста. -->
<script>
  // Заглушка до задачи 5: там корень соберёт шапку и стопку разделов.
  import { ready } from '$api/bridge.js'

  let here = $state(false)
  ready().then(() => { here = true })
</script>

<div class="app">
  <p>{here ? 'мост на месте' : 'жду мост'}</p>
</div>
