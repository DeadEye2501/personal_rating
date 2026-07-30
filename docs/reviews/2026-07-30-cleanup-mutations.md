# Ревью чистки бэкенда: мутации

Диапазон: `43a7922..569ace6`, семь коммитов чистки. Измерение — правило 14
манифеста: тест обязан уметь падать.

Прогнано **116 мутаций**, каждая — одна строка, возвращалась сразу после
прогона. Гонялись целевые файлы тестов прямым питоном из venv. Молча прошло
**15 мутаций**, из них три оказались моими негодными (семантически равны
исходному коду), а остальные двенадцать сложились в **двенадцать находок**:
одна критическая, шесть важных, три мелких и два измерения, подтверждающих
вердикты исполнителя.

Набор после работы — 925 тестов, зелёный. `git status --short` пуст,
`scripts/module_map.py --check` зелёный. Ни одна мутация в дереве не осталась.

## Strengths

Сторожится по-настоящему хорошо, и это видно по тому, что мутация ловится
**именным** тестом, а не случайной поломкой соседа.

**Классификация отказов у всех шести источников.** Перестановка 401 и 403 у
основного зеркала Кинопоиска, 402 у запасного, «незнакомый 401 = битый ключ» у
OMDB, «чужой периметр = битый ключ» у MDBList, `_ABSENT` без кода 6 и `and`→`or`
в `tmdb.classify` — каждая падает адресно:
`test_primary_bad_key_is_a_refusal`, `test_fallback_quota_has_its_own_code`,
`test_unknown_four_oh_one_is_treated_as_temporary`,
`test_cloudflare_wall_is_not_a_key_problem`,
`test_broken_identifier_is_also_an_answer`,
`test_the_absence_code_alone_is_not_a_negative_fact`.

**Отрицательный факт только по разобранному телу.** `is_json`, поверившая
неразобранному телу, роняет сразу двоих:
`test_a_page_from_the_proxy_is_not_a_negative_fact` и
`test_cloudflare_wall_is_not_a_key_problem`. Общая функция вынесена, и оба
следствия остались на месте.

**Вынесенный `parsed()` сторожится по имени источника в отказе.** Подмена
`broken(source, …)` на `broken(note, …)` падает
(`test_mdblist::test_unexpected_shape_does_not_crash`) — то есть у общей идиомы
проверяется не только «отказ вместо исключения», но и чей это отказ.

**Отмена записи.** Обе мутации по ветке `asyncio.CancelledError` в
`CardWriter.save` — снятый откат и превращение отмены в отказ — падают на
`test_cancelling_the_write_takes_the_card_with_it`. То, что нашло общее ревью,
теперь закрыто наблюдаемым следствием, а не комментарием.

**Порядок двух файлов базы при удалении.** `remove_card` без `posters.delete`
роняет три теста, включая
`test_a_broken_deletion_leaves_the_card_not_the_poster`.

**Переплетение выдач и порция на источник.** Склейка блоками вместо
переплетения падает на `test_two_stores_come_woven_and_not_in_blocks` и
`test_a_shorter_answer_does_not_leave_a_hole`; снятый срез — на
`test_a_portion_is_counted_per_source_and_not_per_page`.

**Люди и студии одним описателем.** `Entity` без `position` у людей и
`to_credit` с вечно пустым порядком падают в трёх местах разом:
`test_attach_keeps_the_order_from_the_credits`,
`test_people_come_in_the_order_of_the_credits`,
`test_people_are_attached_with_their_roles`. Устойчивый порядок студий сторожит
`test_studios_come_in_a_stable_order` — падает и на снятой сортировке, и на
подменённой.

**Обогащение оценками.** Пять мутаций по `Enricher` из шести ловятся адресно:
`test_a_rating_nobody_promised_is_not_written`,
`test_the_first_value_wins_when_two_sources_know_the_same_rating`,
`test_the_expected_set_is_what_the_clients_promise`,
`test_nothing_stale_costs_nothing_extra`,
`test_a_source_absent_from_the_answer_becomes_an_empty_row`.

**Сборка клиентов из настроек.** Подмена ключа OMDB на ключ MDBList, разные
имена у зеркал Кинопоиска, транспорт, не доехавший до одного клиента, — всё три
падают (`test_every_key_from_the_settings_reaches_its_own_source`,
`test_every_source_has_its_own_breaker`). Место, которое в плане 4 было самым
дырявым, теперь закрыто.

**Хранилище постеров.** Ключ upsert-а, `has` наоборот, повторное открытие без
закрытия прежнего движка, незакрытое хранилище — четыре из четырёх падают.
Пустые байты в хранилище отличаются от их отсутствия
(`test_empty_bytes_in_the_store_are_still_an_answer`) — правка плана 4 держится.

## Issues

### Critical (Must Fix)

#### 1. Идентичность человека на пути страницы не сторожит ничто

**Сломано:** `backend/storage/repository/views.py`, `ViewsRepository._credits`,
список колонок.

```python
# было
columns = [entity.credit.c.item_id, entity.table.c.name,
           entity.credit.c.role, entity.table.c.source,
           entity.table.c.source_id]
# стало
columns = [entity.credit.c.item_id, entity.table.c.name,
           entity.credit.c.role, entity.table.c.source_id.label("source"),
           entity.table.c.source.label("source_id")]
```

**Гонял:** `tests/backend/test_views.py`, `tests/backend/test_credits.py` —
зелено. Затем `tests/backend/test_views.py` целиком — зелено.

**Почему молчали.** В `test_views.py` нет ни одного человека и ни одной студии
с непустым `source`: `grep` по `\.source` даёт только чужие оценки и чужие
идентификаторы (строки 147, 160, 273). Идентичность титров проверяется только
через `CreditRepository` —
`test_credits.py::test_credits_carry_the_identity_back` и
`test_a_manual_person_gets_its_own_identity`, — и та же мутация в `rows.py`
(`source=None`) ими ловится. То есть свойство сторожит **один из двух**
читателей таблицы, а второй — тот, которым рисуется лента, — не покрыт вовсе.

**Почему это критично.** `rows.py` заведён с докстрингом «читателей у каждой
таблицы двое… две копии сборки расходились бы полями молча» — общей стала
сборка, но не выбор колонок, и разойтись они по-прежнему могут. Следствие
перепутанной пары наблюдаемо мгновенно и грубо: `to_credit` делает
`Source(row.source)`, и на строке с `source_id="525"` это `ValueError` —
падает **каждая** карточка ленты, у которой есть человек из TMDB, то есть
главный экран. При этом 925 тестов остаются зелёными.

**Чем закрыть.** Проверено — падает:

```python
async def test_views_carry_the_identity_of_a_person(sessions, item_id):
    repository = people(sessions)
    entity_id = await repository.ensure(
        Credit(name="Кристофер Нолан", role=PersonRole.DIRECTOR,
               source=Source.TMDB, source_id="525")
    )
    await repository.attach(item_id, entity_id, PersonRole.DIRECTOR, None)

    views = await ViewsRepository(sessions).views_for([item_id])
    one = views[item_id].people[0]
    assert (one.source, one.source_id) == (Source.TMDB, "525")
```

### Important (Should Fix)

#### 2. Причина, которую запомнил предохранитель, сторожится только у TMDB

**Сломано, две строки в двух файлах:**

- `backend/sources/ratings/kinopoisk/mirror.py`, `refuse_rate`:
  `http.breaker.trip(RATE_BACKOFF, Reason.RATE)` → `http.breaker.trip(RATE_BACKOFF)`
  (и вариант с `Reason.QUOTA` — тоже молча);
- `backend/sources/undocumented.py`, `refuse_undocumented`:
  `http.breaker.trip(UNDOCUMENTED_BACKOFF, Reason.RATE)` → без причины
  (и с `Reason.QUOTA` — тоже молча).

**Гонял:** `test_kinopoisk.py`, `test_gog.py`, `test_steam.py`,
`test_search.py`, `test_enrich.py` — зелено везде.

**Почему молчали.** Тесты смотрят на **первый** отказ:
`test_primary_rate_limit_trips_the_breaker_too`,
`test_fallback_rate_limit_trips_its_breaker_too`,
`test_rate_limit_trips_the_breaker` (у GOG и у Steam) — все проверяют
`first.reason is Reason.RATE` и `calls == 1`. Но `first` собирается в
`refuse_rate`/`refuse_undocumented` **явным** `Refusal(...)`, а причина, которую
запомнил предохранитель, вылезает наружу только на **втором** запросе:
`SourceHttp.get` отдаёт `Refusal(reason=self.breaker.reason)`. У TMDB это ровно
так и проверяется — `test_the_tripped_breaker_keeps_the_reason_it_was_tripped_for`
смотрит `second.reason`, — и мутация по TMDB падает. У четырёх остальных
источников (оба зеркала Кинопоиска, GOG, Steam) — нет.

**Следствие.** Все минуты отката человек видит в нижней плашке «кончилась
суточная квота» вместо «слишком часто, повтори через минуту». Ровно то, о чём
предупреждает докстринг `Breaker.trip`.

**Чем закрыть.** Проверено — падает на всех трёх мутациях:

```python
async def test_the_rate_breaker_keeps_the_reason_it_was_tripped_for():
    http = SourceHttp("kinopoisk", transport=responding(429, json={}))
    client = PoiskkinoClient(http, api_key="k")
    await client.ratings("tt1", Kind.MOVIE)
    second = await client.ratings("tt2", Kind.MOVIE)
    assert second.reason is Reason.RATE
```

и то же двумя строками для `GogClient` и `SteamClient`.

#### 3. Срок отката у магазинов без объявленных лимитов не сторожится

**Сломано:** `backend/sources/undocumented.py`,
`UNDOCUMENTED_BACKOFF = timedelta(minutes=5)` → `timedelta(seconds=5)`.

**Гонял:** `test_gog.py`, `test_steam.py` — зелено.

**Почему молчали.** `test_rate_limit_trips_the_breaker` у обоих магазинов
проверяет причину и `calls == 1`, но не `retry_after`. Сравните с Кинопоиском:
там у шести часов есть свой тест на `FakeClock` —
`test_the_quota_closes_the_mirror_for_six_hours`, — и мутация
`QUOTA_BACKOFF` минутой падает сразу двумя тестами. Пять минут у магазинов —
такое же решение, записанное комментарием («Пять минут — догадка, но лучше, чем
долбиться в закрытую дверь»), и его не сторожит никто.

**Чем закрыть.** Одна строка в существующий тест —
`assert first.retry_after == timedelta(minutes=5)`. Проверено: падает.

#### 4. Порядок актёров сериала берётся из ответа, и это не проверено

**Сломано:** `backend/sources/tmdb/parse.py`, `_cast`:
`_person(row, PersonRole.ACTOR, row.get("order", index))` →
`_person(row, PersonRole.ACTOR, index)`.

**Гонял:** `tests/backend/sources/test_tmdb_card.py` — зелено.

**Почему молчали.** Порядок сторожит
`test_actors_keep_the_order_from_the_credits`, и он смотрит **фильм**. В
`tests/fixtures/tmdb/movie_detail.json` поле `order` совпадает с номером строки
на всех пятнадцати проверенных записях — `[(0,0),(1,1),(2,2)…]`, — поэтому
`row.get("order", index)` и `index` там неотличимы, а `positions == sorted(positions)`
и `positions[0] == 0` держатся при обеих версиях.

У сериала всё иначе, и это тоже записанный ответ:
в `tests/fixtures/tmdb/tv_detail.json` из 302 строк `aggregate_credits.cast`
**301** имеет `order`, не равный своему номеру — `(1, 503), (2, 501), (3, 500),
(7, 1)`. То есть на пути сериала подмена меняет позиции полностью, а проверяет
этот путь только `test_series_cast_comes_from_aggregate_credits`, и он смотрит
`len(actors) > 50`. Карточка показывает топ-5 актёров и сортирует по `position` —
состав первой пятёрки под мутацией другой.

**Чем закрыть.** Проверено — падает:

```python
def test_series_positions_come_from_the_response(fixture):
    card = parse_series(fixture("tmdb/tv_detail.json"))
    actors = [one for one in card.people if one.role is PersonRole.ACTOR]
    assert [one.position for one in actors] != list(range(len(actors)))
```

Лучше — назвать ожидаемое: у строки с `order == 1` позиция обязана быть 1.

#### 5. Алфавитный порядок жанров на пути страницы не сторожится

**Сломано:** `backend/storage/repository/views.py`, `_genres`:
`.order_by(genre.c.name)` → `.order_by(genre.c.id)` (и `genre.c.id.desc()` —
тоже молча).

**Гонял:** `test_views.py`, `test_genres.py`, `test_feed.py`, `test_sections.py`,
`test_search_local.py` — зелено везде.

**Почему молчали.** В `test_views.py` жанр на карточке всегда один:
`test_genres_come_with_the_card` ставит `["18"]`, а
`test_my_marks_do_not_mix_between_cards` — по одному на карточку. На одном
элементе сортировка ненаблюдаема по определению.

Тот же порядок на **других** путях сторожится нарочно и с объяснением:
`test_search.py::test_a_compound_genre_comes_in_the_order_of_the_alphabet`
(«пара выбрана так, что алфавит обратен номерам»),
`test_genres.py::test_list_for_kind_keeps_the_two_sets_apart` («в справочнике он
лежит не по алфавиту, и сортировка по номеру строки дала бы другой порядок»).
Третий читатель той же таблицы — тот, которым рисуется лента, — забыт.

**Чем закрыть.** Материал в фикстуре `reference` уже есть: `10759` разворачивается
в «Боевик» (id 1) и «Приключения» (id 2), а `18` — это «Драма» (id 3), то есть
алфавит обратен номерам. Проверено — падает:

```python
async def test_views_genres_come_in_the_alphabet(sessions, reference, item_id):
    genres = GenresRepository(sessions)
    await genres.set_for_item(
        item_id, await genres.resolve(GenreSource.TMDB, ["10759", "18"])
    )
    views = await ViewsRepository(sessions).views_for([item_id])
    assert [g.name for g in views[item_id].genres] == [
        "Боевик", "Драма", "Приключения"
    ]
```

#### 6. `Enricher._imdb_id` зелен по алфавитному совпадению

**Сломано:** `backend/service/enrich.py`, `_imdb_id`:

```python
# было
for external in await self._ids.ids_of(item_id):
    if external.source is IdSource.IMDB:
        return external.value
# стало
for external in await self._ids.ids_of(item_id):
    return external.value
```

**Гонял:** `test_enrich.py`, `test_external_ids.py`, `test_link_loading.py`,
`test_card_writer.py` — зелено.

**Почему молчали.** Ни в одном тесте у карточки нет двух чужих
идентификаторов сразу. А в бою фильтр держится не собой, а везением:
`ExternalIdsRepository.ids_of` сортирует по `source`, и из четырёх значений
`IdSource` — `imdb`, `kinopoisk`, `steam`, `gog` — раньше `imdb` идёт только
`gog`, которого у фильма не бывает. Отсюда «правильный» ответ и без фильтра.
Заведи кто-нибудь пятое значение, сортирующееся раньше `imdb`, или смени
`ids_of` порядок — и агрегаторов начнут спрашивать по чужому номеру, молча и
на каждой карточке.

**Чем закрыть.** Проверено — падает: карточка с двумя идентификаторами,
`gog="the_witcher"` и `imdb="tt0816692"`, и подставной оценочный клиент,
записывающий, о чём его спросили; `assert asked == ["tt0816692"]`.

#### 7. Размер порции объявлен, но его величина не сторожится ни у ленты, ни у поиска

**Сломано, две строки:**

- `backend/service/library.py`: `PAGE_SIZE = 50` → `20`;
- `backend/service/search.py`: `SEARCH_SIZE = 20` → `5`.

**Гонял:** `test_feed.py`, `test_search.py`, `test_search_local.py` — зелено.

**Почему молчали.** Оба теста берут константу из кода и ставят её по обе стороны
проверки:

```python
async def test_a_portion_is_fifty_and_it_is_applied(sessions, feed):
    for number in range(PAGE_SIZE + 1):
        await rated(sessions, str(number), 8.0)
    page = await feed.page(RATED)
    assert len(page) == PAGE_SIZE
```

и `assert len(result.views) == 2 * SEARCH_SIZE` при
`for number in range(50)` у каждого магазина. Половину своего обещания они
держат — потерянный `limit=limit` в `page` падает (мутация со сменой `limit` и
`offset` местами роняет четыре теста), — но **величину** не проверяют ни одним
байтом. Имя `test_a_portion_is_fifty_and_it_is_applied` обещает пятьдесят, а
докстринг у поиска говорит «по 20 у каждого — это два запроса, как и сказано в
спеке»; и то, и другое можно поменять на любое число молча.

Это тот самый род дыры, который слайс объявил закрытым («снятые зеркала
констант»), — в двух местах он остался.

**Чем закрыть.** Число в проверке пишется литералом, а материал набирается
литералом же: `for number in range(51)` … `assert len(page) == 50`. Тогда имя
перестаёт врать, а «применяет ли» по-прежнему проверяется — предел из
`page(RATED)` берётся по умолчанию.

### Minor (Nice to Have)

#### 8. Порядок магазинов спрятан за сравнением множеств

**Сломано:** `backend/sources/registry.py`, `catalog_for`:
`return [self.steam, self.gog]` → `return [self.gog, self.steam]`.

**Гонял:** `test_registry.py`, `test_search.py` — зелено.

**Почему молчали.** `test_games_come_from_two_equal_stores` сравнивает
**множество** типов:

```python
assert {type(one) for one in registry.catalog_for(Kind.GAME)} == {
    SteamClient, GogClient,
}
```

а тесты переплетения (`test_two_stores_come_woven_and_not_in_blocks` и прочие)
получают клиентов прямо в фикстуру `service(steam, gog)` и `catalog_for` не
зовут вовсе. Порядок, в котором магазины попадают в переплетение, — а значит и
то, чей кандидат стоит в выдаче первым, — не наблюдает никто.

Мелким это записано потому, что магазины объявлены равноправными и «первый» —
не решение. Но множество здесь скрывает ровно то, что скрывало шесть проверок,
которые слайс переписал: набор вместо привязки. Одна строка —
`assert [type(one) for one in registry.catalog_for(Kind.GAME)] == [SteamClient, GogClient]` —
закрывает и её.

#### 9. Имя источника в записи `parsed()` не сторожится

**Сломано:** `backend/sources/errors.py`:
`log.warning("%s: %s — %s", source, note, error)` →
`log.warning("%s: %s", note, error)`.

**Гонял:** `test_errors.py`, `test_kinopoisk.py`, `test_tmdb_card.py` — зелено.

**Почему молчали.** Про запись проверяется два свойства — что она вообще есть и
что фраза у двух зеркал разная, — а имя источника в тексте не проверяет никто.

Следствие при этом почти незаметно: `log` передаётся снаружи и это логгер
модуля источника, так что `record.name` называет источник и без `source` в
тексте. Ради чего `source` в строке и остался — читаемость `caplog` — а не
ради различимости. Мелкое, но сломанное, и одна проверка текста его закрывает.

#### 10. Ранний выход по отказу обложки в `Loader.ensure` ничего не решает

**Сломано:** `backend/service/loading.py`, `ensure`:

```python
# было
if isinstance(poster, Refusal):
    return poster
# стало
if isinstance(poster, Refusal):
    poster = None
```

**Гонял:** `tests/backend/test_loading.py` — все 16 зелёные, включая
`test_a_poster_that_did_not_arrive_stops_the_writing`.

**Почему молчали, и почему это не дыра в тесте.** `CardWriter.save` на
`poster is None` **сам** идёт за обложкой и сам отказывает:

```python
if poster is None:
    poster = await self.posters.fetch(card.item.source, card.item.poster_url)
    if isinstance(poster, Refusal):
        return poster
```

То есть правило «не скачалась — карточка не пишется вовсе» держит писатель, а
ветка в `ensure` — второй слой обороны, и наблюдаемое следствие у неё одно:
**лишний запрос в сеть** на отказавшем источнике. Его не считает никто:
`test_the_cover_is_fetched_once` считает вызовы `fetch`, но на успешной обложке,
где эта ветка не срабатывает.

Закрывается тем же приёмом, что и `test_the_cover_is_fetched_once`, — счётчиком
`fetch` на пути отказа. Либо ветка объявляется украшением и убирается: правило
всё равно проверяется тестом писателя.

### Два измерения, а не находки

Исполнитель объявил ненаблюдаемыми два свойства. **Согласен с обоими**, и вот
чем проверено.

**Второй ключ сортировки библиотеки** (`LibraryRepository.list_by_kind`,
`order_by(title, id)`). Замерено напрямую: 2000 карточек с одинаковым названием,
план запроса — `SCAN item` + `USE TEMP B-TREE FOR ORDER BY`, то есть сортировка
идёт временным b-tree, а не индексом. На трёх смещениях (0, 500, 1500) выдача
`ORDER BY title` совпала с `ORDER BY title, id` полностью. Сортировщик SQLite
сохраняет порядок сканирования, а он rowid-восходящий и равен порядку `id`.
Наблюдать разницу нечем, и вердикт «страховка, тестом не сторожится» верен —
довод в докстринге стоит на месте.

**Порядок чужих оценок и идентификаторов** (`ViewsRepository._by_source`,
`order_by(table.c.source)`). Замерено: строки записаны в обратном алфавиту
порядке источников (`rotten, metacritic, kinopoisk, imdb` и
`steam, kinopoisk, imdb, gog`), прочитаны без `order_by` — пришли
отсортированными по источнику. План: `SEARCH … USING INDEX
sqlite_autoindex_external_rating_1 (item_id=?)`, то есть порядок и правда
следствие составного первичного ключа, ровно как написано в докстринге.
Заставить планировщик уйти на скан не удалось: автоиндекс по `(item_id, source)`
есть всегда, а отбор идёт по его ведущей колонке.

### Негодные мутации (мои)

Три мутации прошли молча не потому, что тест плох, а потому, что мутация
оказалась равна исходному коду. Записываю, чтобы их не приняли за находки.

1. `views._tags`: `order_by(tag.c.position)` → `order_by(tag.c.id.desc())`. В
   `test_tags_come_in_their_manual_order` набор ровно из двух тегов, и
   `reorder` меняет их местами — обратный номер совпал с ручным порядком.
   Мутация `order_by(tag.c.id)` **падает** на этом тесте. Порядок тегов на пути
   страницы сторожится.
2. `entity.link`: моя подстановка выводила то же имя колонки другим выражением.
   Настоящая мутация — `self.credit.c["person_id"]` — падает на четырёх тестах
   `test_credits.py`.
3. `series.refresh`: снятый `return` из ветки `Missing` — не мутация: ниже стоит
   `if not isinstance(outcome, Found): return`, и `Missing` в него попадает.
   Снятая целиком ветка **падает** на `test_a_vanished_series_is_logged_and_kept`.

## Сводка мутаций

Все 116, включая поймавшиеся. `—` в третьей колонке означает «прошла молча».

| # | Что сломано | Итог | Каким тестом |
|---|---|---|---|
| K1 | `mirror.answered`: `and` → `or` | поймана | `test_the_identifier_survives_a_film_without_a_rating` |
| K2 | `mirror.refuse_rate`: предохранитель без `Reason.RATE` | **молча** | — |
| K3 | `poiskkino`: 401 и 403 местами | поймана | `test_primary_bad_key_is_a_refusal` |
| K4 | `poiskkino`: `FIELDS` без `rating` | поймана | `test_primary_asks_for_the_fields_it_needs` |
| K5 | `poiskkino`: параметр `externalId.imdb` → `imdb` | поймана | `test_primary_asks_for_the_fields_it_needs` |
| K6 | `unofficial`: 402 отдаёт отказ по ключу | поймана | `test_fallback_quota_has_its_own_code` |
| K7 | `unofficial`: параметр `imdbId` → `imdb` | поймана | `test_fallback_sends_the_key_in_the_header_and_keeps_the_tt_prefix` |
| KQ1 | `mirror`: `QUOTA_BACKOFF` 6 ч → 1 мин | поймана | `test_the_quota_closes_the_mirror_for_six_hours` |
| K2b | `mirror.refuse_rate`: предохранитель с `Reason.QUOTA` | **молча** | — |
| T1 | `tmdb`: у сериала `credits` вместо `aggregate_credits` | поймана | `test_client_requests_aggregate_credits_for_a_series` |
| T2 | `tmdb`: `_ABSENT` без кода 6 | поймана | `test_broken_identifier_is_also_an_answer` |
| T3 | `tmdb`: предохранитель на 429 без `Reason.RATE` | поймана | `test_the_tripped_breaker_keeps_the_reason_it_was_tripped_for` |
| T4 | `tmdb.parse._required`: не смотрит на `cast` | поймана | `test_a_block_that_came_without_its_cast_is_incomplete` |
| T5 | `tmdb.parse._cast`: позиция из перечисления, а не из `order` | **молча** | — |
| T6 | `tmdb.parse._item`: `title` и `original_title` местами | поймана | `test_the_series_original_title_is_not_the_translated_one` |
| T7 | `tmdb.parse`: сезоны и серии местами | поймана | `test_series_card_has_seasons_and_episodes` |
| T8 | `tmdb.parse`: `source_rating` всегда пуст | поймана | `test_tmdb_rating_comes_free_with_the_search` |
| TC1 | `tmdb.classify`: `and` → `or` | поймана | `test_the_absence_code_alone_is_not_a_negative_fact` |
| TP1 | `tmdb.parse`: `POSTER_BASE` w500 → w200 | поймана | `test_poster_path_becomes_a_full_url` |
| TR1 | `tmdb`: `RATE_BACKOFF` 1 мин → 1 ч | поймана | `test_the_breaker_lets_go_when_the_backoff_has_passed` |
| G1 | `gog`: запрос без префикса `like:` | поймана | `test_search_asks_the_catalog_the_way_that_answers` |
| G2 | `gog`: слаг не разбирается на слова | поймана | `test_the_slug_becomes_words_in_the_query` |
| GC1 | `gog.card`: берётся первая находка каталога | поймана | `test_card_picks_the_asked_identifier` |
| S1 | `steam`: свои жанры теряются, остаются теги | поймана | `test_the_card_carries_both_spaces` |
| S2 | `steam`: `country_code` US → RU | поймана | `test_the_tag_request_asks_the_way_that_answers` |
| ST1 | `steam`: `include_tag_count` 20 → 0 | поймана | `test_the_tag_request_asks_the_way_that_answers` |
| C1 | `convert.genres`: ключ по умолчанию `slug` | поймана | `test_the_space_travels_with_the_identifier` |
| C2 | `convert.rating`: ноль считается значением | поймана | `test_nothing_and_zero_are_both_an_absence_here` |
| E1 | `outcome.is_answer`: `Missing` не ответ | поймана | `test_missing_is_an_answer_not_a_silence` |
| E2 | `errors.refuse_code`: причина `NETWORK` | поймана | `test_server_error_is_a_refusal` |
| E3 | `undocumented`: откат 5 мин → 5 с | **молча** | — |
| U1 | `undocumented`: предохранитель без `Reason.RATE` | **молча** | — |
| U1b | `undocumented`: предохранитель с `Reason.QUOTA` | **молча** | — |
| IJ1 | `errors.is_json`: неразобранному телу верим | поймана | `test_a_page_from_the_proxy_is_not_a_negative_fact` |
| PA1 | `errors.parsed`: имя источника ушло из лога | **молча** | — |
| PA2 | `errors.parsed`: отказ под именем фразы | поймана | `test_unexpected_shape_does_not_crash` |
| M1 | `mdblist`: 202 отдаёт `QUOTA` | поймана | `test_cache_building_is_a_retry_not_an_absence` |
| M2 | `mdblist`: `Retry-After` читается минутами | поймана | `test_recorded_quota_is_a_refusal_with_the_named_delay` |
| MD1 | `mdblist._denied`: чужой периметр = битый ключ | поймана | `test_cloudflare_wall_is_not_a_key_problem` |
| MQ1 | `mdblist`: `QUOTA_FALLBACK` 1 ч → 1 мин | поймана | `test_quota_without_a_named_delay_falls_back_to_an_hour` |
| O1 | `omdb`: незнакомый 401 = битый ключ | поймана | `test_unknown_four_oh_one_is_treated_as_temporary` |
| O2 | `omdb._answer`: `Response == "True"` даёт `Missing` | поймана | `test_recorded_missing_object_arrives_under_two_hundred` |
| OM1 | `omdb.until_midnight`: сутки → двое | поймана | `test_until_midnight_counts_to_the_next_day` |
| HT1 | `http`: `DEFAULT_TIMEOUT` 20 → 200 с | поймана | `test_http.py` |
| R1 | `registry.catalog_for`: магазины местами | **молча** | — |
| R2 | `registry.client_for`: Steam и GOG местами | поймана | `test_a_card_goes_back_to_the_client_it_came_from` |
| R3 | `registry.rating_sources`: у игр спрашиваем агрегаторов | поймана | `test_games_ask_nobody_for_ratings` |
| B1 | `build`: ключ OMDB достаётся MDBList | поймана | `test_every_key_from_the_settings_reaches_its_own_source` |
| B2 | `build`: зеркала под разными именами | поймана | `test_every_source_has_its_own_breaker` |
| B3 | `build`: транспорт не доезжает до Кинопоиска | поймана | `test_every_key_from_the_settings_reaches_its_own_source` |
| P1b | `posters`: WebP больше не изображение | поймана | `test_webp_is_a_picture_too` |
| P2 | `posters`: пустые байты = отсутствие | поймана | `test_empty_bytes_in_the_store_are_still_an_answer` |
| P3 | `posters`: залитая картинка не обрезается | поймана | `test_an_upload_is_cropped` |
| P4 | `posters`: хранилище не закрывается | поймана | `test_closing_the_service_closes_the_store` |
| P5 | `PosterStore.open`: прежний движок не закрывается | поймана | `test_opening_twice_does_not_lose_the_first_engine` |
| PS1 | `PosterStore.has`: наоборот | поймана | `test_a_stored_poster_is_there` |
| PS2 | `PosterStore.put`: upsert без ключа | поймана | `test_put_and_get` |
| V1 | `views.in_order`: порядок номеров теряется | поймана | `test_the_alphabet_orders_the_found` |
| V2 | `views._genres`: сортировка по `id` | **молча** | — |
| GN1 | `views._genres`: сортировка по `id.desc()` | **молча** | — |
| V3 | `views._tags`: `id.desc()` (негодная мутация) | молча | равна ручному порядку в тесте |
| V3b | `views._tags`: сортировка по `id` | поймана | `test_tags_come_in_their_manual_order` |
| V4 | `views._credits`: `source` и `source_id` местами | **молча** | — |
| V5 | `views._fetch_all`: закладка наоборот | поймана | `test_a_bookmark_is_a_flag` |
| CR1 | `views._credits`: студии по алфавиту наоборот | поймана | `test_studios_come_in_a_stable_order` |
| VW1 | `views._by_card`: строки в одну карточку | поймана | `test_my_marks_do_not_mix_between_cards` |
| VW2 | `views._fetch_all`: оценка достаётся чужой карточке | поймана | `test_my_marks_do_not_mix_between_cards` |
| N1 | `entity.link` (негодная мутация) | молча | выражение равно исходному |
| N1b | `entity.link`: всегда `person_id` | поймана | `test_companies_work_the_same_way` |
| N2 | `Entity`: у людей отобран `position` | поймана | `test_attach_keeps_the_order_from_the_credits` |
| W1 | `rows.to_credit`: `position` всегда пуст | поймана | `test_people_come_in_the_order_of_the_credits` |
| W2 | `rows.to_credit`: `source` всегда пуст | поймана | `test_credits_carry_the_identity_back` |
| W3 | `rows.to_item`: пустой текст уезжает `None` | поймана | `test_texts_written_past_the_repository_come_back_empty` |
| TT1 | `rows.to_tag`: имя из номера | поймана | `test_list_shows_only_the_current_kind` |
| TG1 | `tags.list_for_kind`: порядок по имени | поймана | `test_a_new_tag_goes_to_the_end_of_its_set` |
| TG2 | `tags.tags_of`: порядок по имени | поймана | `test_tags_of_a_card_keep_the_manual_order` |
| SU1 | `credits.suggest`: порядок по номеру | поймана | `test_suggest_respects_the_limit_and_keeps_the_order` |
| SR1 | `series._kept`: пустое стирает известное | поймана | `test_a_half_empty_answer_does_not_erase_what_was_known` |
| SR2 | `series`: фильм тоже перезапрашивается | поймана | `test_a_film_is_never_re_asked` |
| SR3 | `series`: ручная карточка перезапрашивается | поймана | `test_a_manual_card_is_never_re_asked` |
| SR4 | `series`: снятый `return` из `Missing` (негодная) | молча | ниже стоит та же проверка |
| SR4b | `series`: ветка `Missing` снята целиком | поймана | `test_a_vanished_series_is_logged_and_kept` |
| SR5 | `series`: отметка времени не обновляется | поймана | `test_the_refreshed_card_gets_a_new_moment` |
| L1 | `loading`: обложка не доезжает до записи | поймана | `test_the_cover_is_fetched_once` |
| L2 | `loading`: лежащая карточка ищется не по своему id | поймана | `test_a_card_already_in_the_base_is_not_asked_for_again` |
| L3 | `loading`: слаг разрешается у Steam | поймана | `test_a_gog_slug_becomes_a_number_before_the_card` |
| L4 | `loading`: отказ обложки не мешает записи | **молча** | — |
| SE1 | `search._weave`: блоками вместо переплетения | поймана | `test_two_stores_come_woven_and_not_in_blocks` |
| SE2 | `search`: порция не ограничивается | поймана | `test_a_portion_is_counted_per_source_and_not_per_page` |
| SE3 | `search._genres_of`: повторы не снимаются | поймана | `test_overlapping_identifiers_do_not_duplicate_a_genre` |
| SE4 | `search`: незнакомый жанр роняет выдачу | поймана | `test_an_unknown_genre_is_dropped_without_a_word` |
| SS1 | `search`: `SEARCH_SIZE` 20 → 5 | **молча** | — |
| EN1 | `enrich._take`: берём необъявленное | поймана | `test_a_rating_nobody_promised_is_not_written` |
| EN2 | `enrich._take`: побеждает последний | поймана | `test_the_first_value_wins_when_two_sources_know_the_same_rating` |
| EN3 | `enrich.expected`: повторы не снимаются | поймана | `test_the_expected_set_is_what_the_clients_promise` |
| EN4 | `enrich._imdb_id`: первый попавшийся номер | **молча** | — |
| IE1 | то же, с более широким набором тестов | **молча** | — |
| EN5 | `enrich`: просроченного нет — идём в сеть | поймана | `test_nothing_stale_costs_nothing_extra` |
| EN6 | `enrich._record`: пустое под чужим источником | поймана | `test_a_source_absent_from_the_answer_becomes_an_empty_row` |
| EN7 | `enrich._keep`: чужой номер не сохраняется | поймана | `test_a_found_identifier_is_kept` |
| CW1 | `cards`: отмена не откатывает | поймана | `test_cancelling_the_write_takes_the_card_with_it` |
| CW2 | `cards`: отмена превращается в отказ | поймана | `test_cancelling_the_write_takes_the_card_with_it` |
| LK1 | `linking`: своя обложка перезаписывается | поймана | `test_an_own_poster_is_not_replaced` |
| VH1 | `view_from_hit`: оценка кандидата отброшена | поймана | `test_the_free_rating_reaches_the_candidate` |
| AP1 | `removal`: обложка не убирается | поймана | `test_a_broken_deletion_leaves_the_card_not_the_poster` |
| AP2 | `app.aclose`: движок не отпускается | поймана | `test_everything_closes_and_lets_go` |
| AP3 | `app`: перезапрос собран на чужом клиенте | поймана | `test_everything_closes_and_lets_go` |
| LB1 | `library`: гистограмма без фильтров | поймана | `test_the_histogram_asks_with_the_filters_it_was_given` |
| LP1 | `library.page`: `limit` и `offset` местами | поймана | `test_a_page_keeps_the_order_of_the_section` |
| LP2 | `library`: `PAGE_SIZE` 50 → 20 | **молча** | — |
| Q1–Q7 | те же семь молчаливых против черновых проверок | поймана | все семь падают, см. разборы |

## Assessment

**Ready to merge?** With fixes

**Reasoning:** Чистка сама по себе прочная — 101 мутация из 116 ловится
адресными тестами, и переписанное в этом слайсе (`parsed()`, `Entity`,
`removal.py`, `build.py`, откат отмены) сторожится лучше всего. Но одна дыра
критическая: идентичность человека на пути страницы не наблюдает никто, а
перепутанная пара колонок роняет главный экран при 925 зелёных тестах. Плюс
шесть важных, из которых две — оставшиеся зеркала констант, то есть ровно тот
род дыр, который слайс объявил закрытым. Все двенадцать закрываются проверенными
следствиями, и каждое из них проверено падением.
