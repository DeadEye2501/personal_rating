<!-- Оценки агрегаторов: цифра, кружок ожидания или прочерк со ссылкой. -->
<script>
  import { colorOf } from '$state/scores.js'
  import {
    inOrder, nameOf, pagesOf, shownValue, stepOfSource,
  } from '$state/sources.js'

  let { view, expected = [], onopen } = $props()

  // Адрес есть у троих из семи: у IMDb и Кинопоиска он собирается из чужих
  // идентификаторов карточки, у TMDB — из её собственного номера.
  const pages = $derived(pagesOf(view))

  const arrived = $derived(
    new Map((view.external ?? []).map((one) => [one.source, one])))

  // Показываются и ожидаемые, и приехавшие. Только ожидаемых мало: у игр их
  // нет вовсе — оценки Steam, Metacritic и GOG приезжают вместе с карточкой, и
  // спрашивать за них некого. Взяв один `expected`, карточка игры не показала
  // бы ни одной оценки никогда.
  //
  // Порядок постоянный и от порядка приезда не зависит: имя стоит на месте с
  // начала ожидания, и приехавшая цифра встаёт туда, где крутился кружок. Ряд
  // при этом всё же сдвигается — но один раз, когда круг кончился и ответившие
  // пустотой из него ушли.
  //
  // Видов три, и все решены пользователем 02.08.2026: кружок, пока ответа нет;
  // цифра, когда он есть; прочерк у того, чьё имя ведёт на страницу источника.
  // Имя без цифры и без кружка выглядит вечным ожиданием, которого уже не
  // будет, — но у тех троих, чей адрес мы умеем собрать, оно ещё и
  // единственный способ открыть у них карточку. Прочерк говорит, что оценки
  // нет, и ссылку оставляет; остальные уходят из ряда целиком.
  //
  // Просроченная пустая строка попадает в «цифры нет»: у показа нет способа
  // отличить её от свежей, а `stale_sources` есть только у бэкенда. Раз в
  // неделю на карточке без оценки это стоит мигания — прочерком у тех, чьё имя
  // со ссылкой, и исчезновением у остальных.
  const shown = $derived(inOrder(new Set([...expected, ...arrived.keys()]))
    .map((source) => ({
      source,
      page: pages.get(source) ?? null,
      value: arrived.get(source)?.value ?? null,
      waiting: !arrived.has(source),
    }))
    .filter((one) => one.value !== null || one.waiting || one.page))
</script>

<div class="film__aggr">
  {#each shown as one (one.source)}
    <span>
      <!-- Открывает системный браузер, а не саму страницу: окно приложения без
           адресной строки, и вернуться из Кинопоиска было бы нечем. -->
      {#if one.page}
        <a class="aggr" href={one.page}
           onclick={(event) => { event.preventDefault(); onopen(one.page) }}
        >{nameOf(one.source)}</a>
      {:else}
        <span class="aggr aggr--flat">{nameOf(one.source)}</span>
      {/if}
      {#if one.value !== null}
        <b style:--score={colorOf(stepOfSource(one.value, one.source))}
        >{shownValue(one.value, one.source)}</b>
      {:else if one.waiting}
        <i class="aggr-wait" aria-hidden="true"></i>
      {:else}
        <b class="aggr-none">—</b>
      {/if}
    </span>
  {/each}
</div>
