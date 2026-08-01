<!-- Оценки агрегаторов: цифра, кружок ожидания или пустое место. -->
<script>
  import { colorOf } from '$state/scores.js'
  import { nameOf, pagesOf, shownValue, stepOfSource } from '$state/sources.js'

  let { external = [], expected = [], ids = [], onopen } = $props()

  // Адрес собирается из чужих идентификаторов карточки, и есть он у двоих из
  // семи: у Rotten и Metacritic идентификатора не хранится вовсе, у TMDB он
  // лежит в самой карточке, а Steam и GOG сегодня не пишет ни один клиент.
  const pages = $derived(pagesOf(ids))

  const arrived = $derived(new Map(external.map((one) => [one.source, one])))

  // Показываются и ожидаемые, и приехавшие. Только ожидаемых мало: у игр их
  // нет вовсе — оценки Steam, Metacritic и GOG приезжают вместе с карточкой, и
  // спрашивать за них некого. Взяв один `expected`, карточка игры не показала
  // бы ни одной оценки никогда.
  //
  // Порядок: сперва ожидаемые, потом приехавшее сверх них — имя источника
  // стоит на месте с самого начала, и строка не прыгает, когда цифра приедет.
  //
  // Три состояния различаются так же, как в базе: строки нет — крутится
  // кружок; строка с пустым значением — на месте оценки просто ничего;
  // строка со значением — цифра.
  const shown = $derived([...new Set([...expected, ...arrived.keys()])]
    .map((source) => ({
      source,
      value: arrived.get(source)?.value ?? null,
      asked: arrived.has(source),
    })))
</script>

<div class="film__aggr">
  {#each shown as one (one.source)}
    <span>
      <!-- Открывает системный браузер, а не саму страницу: окно приложения без
           адресной строки, и вернуться из Кинопоиска было бы нечем. -->
      {#if pages.get(one.source)}
        <a class="aggr" href={pages.get(one.source)}
           onclick={(event) => { event.preventDefault()
                                 onopen(pages.get(one.source)) }}
        >{nameOf(one.source)}</a>
      {:else}
        <span class="aggr aggr--flat">{nameOf(one.source)}</span>
      {/if}
      {#if one.value !== null}
        <b style:--score={colorOf(stepOfSource(one.value, one.source))}
        >{shownValue(one.value, one.source)}</b>
      {:else if !one.asked}
        <i class="aggr-wait" aria-hidden="true"></i>
      {/if}
    </span>
  {/each}
</div>
