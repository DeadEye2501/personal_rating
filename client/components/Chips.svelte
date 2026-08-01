<!-- Метки карточки: жанры, теги и кнопка добавления тега. -->
<script>
  // У метки здесь два состояния, а не три: включён и не активен. Исключить с
  // карточки нечем — третье живёт только в модалке фильтра. Переключает сборка:
  // `onmark` уходит наверх, там меняется состояние, и оттуда же приезжает `on`.
  let { genres = [], tags = [], on = { genres: [], tags: [] }, onmark, ontag }
    = $props()
</script>

<div class="film__chips">
  <!-- Клик по метке включает фильтр по ней, повторный выключает. Не поиск:
       «найти во внешней базе все боевики» — не тот вопрос, который задают, а
       фильтр по своей библиотеке отвечает мгновенно и работает без сети. -->
  {#each genres as genre (genre.id)}
    <button type="button" class="chip" class:is-on={on.genres.includes(genre.id)}
            aria-pressed={on.genres.includes(genre.id)}
            onclick={() => onmark('genres', genre.id)}>{genre.name}</button>
  {/each}
  {#each tags as tag (tag.id)}
    <button type="button" class="chip chip--tag" class:is-on={on.tags.includes(tag.id)}
            aria-pressed={on.tags.includes(tag.id)}
            onclick={() => onmark('tags', tag.id)}>{tag.name}</button>
  {/each}
  <!-- Кнопка всегда последняя. У кандидата поиска её нет вовсе: теги держатся
       за номер карточки, а его у него ещё не существует. -->
  {#if ontag}
    <button type="button" class="chip chip--add" onclick={ontag}>± Тег</button>
  {/if}
</div>
