# Мутации по клиентам источников, 02.08.2026

Измерение: `backend/sources/` целиком — TMDB, Steam, GOG, MDBList, OMDB, оба
зеркала Кинопоиска, реестр, сборка, транспорт, предохранитель, общий разбор и
конвертация.

Прогон: отдельное рабочее дерево, `pytest` тем же интерпретатором, что у проекта.
До мутаций набор зелёный: **295 тестов** в `tests/backend/sources/`, **1288** во
всём питоновском наборе.

Рабочий круг каждой мутации — `tests/backend/sources`, `tests/backend/test_outcome.py`,
`tests/backend/test_poster_service.py` (315 тестов, ~2 с). Каждая молчаливая
перепроверена дважды: возврат к чистому коду с зелёным прогоном, повторное
внесение и прогон **всего** набора из 1288 тестов.

**Внесено 152. Поймано 144. Прошло молча 8.**

Из восьми молчаливых: пять — дыры в тестах, две — эквивалентные мутанты
(наблюдаемого следствия нет ни у какого теста, потому что его нет вовсе), одна —
подмена, неразличимая на сегодняшней сборке и названная таковой прямо в коде.

**Ошибок поведения в боевом коде не нашла ни одна из 152 мутаций.**

## Сильные стороны

- **TMDB закрыт полностью: 35 мутаций из 35 поймано.** В том числе весь класс,
  на котором проект горел раньше, — привязка, а не набор: пространство жанра
  (`GenreSource.TMDB` → `STEAM`, `STEAM_TAG`), владелец оценки
  (`RatingSource.TMDB` → `IMDB`), пространство идентификатора (`IdSource.IMDB` →
  `KINOPOISK`), роли состава во всех трёх направлениях (актёр → режиссёр,
  режиссёр → шоураннер, шоураннер → режиссёр), перестановка `_KEYS` целиком и
  перестановка внутри строки (`title` ↔ `original_title`), сезоны с сериями
  местами.
- **Классификация отказов сторожится у всех шести источников поимённо.** Каждая
  подмена причины ловится своим тестом: 429 → `QUOTA` у TMDB, 202 → `QUOTA` у
  MDBList, 403 ↔ 401 у основного зеркала Кинопоиска, `KEY` → `QUOTA` у OMDB,
  `BROKEN` → `NETWORK` в общем `errors.py`. Сроки предохранителя пришпилены
  числом у всех: 15 с у сети, 1 мин у TMDB, 6 ч и 1 мин у зеркал, час у MDBList,
  пять минут у магазинов.
- **Правило «отрицательный факт — только по разобранному телу» держится в
  четырёх местах и во всех четырёх наблюдаемо.** Снятие проверки тела ловится у
  `errors.absent`, у `TmdbClient.classify`, у товарной ручки GOG и у MDBList —
  причём последние два были настоящими поломками закрывающего ревью 31.07, и
  сторожа на них теперь стоят.
- **Инвариант `refuse_until` «названный срок = срок закрытия» наблюдаем с обеих
  сторон**: и снятие `breaker.trip`, и `retry_after=None` роняют разные тесты.
- **Сборка сторожится по каждому проводу.** Перепутанные имена соединений
  (`steam` ↔ `gog`), пустой `connections`, ключ MDBList, уехавший в OMDB, и один
  ключ на оба зеркала Кинопоиска — всё четыре ловятся `test_registry.py`.
  Реестр тоже: порядок магазинов, `people_for` для игр, `client_for` с
  перепутанными магазинами, `rating_sources` для игр, `aclose`.
- **Сеть и предохранитель сторожатся по следствию, а не по объявлению.** Ловятся
  снятая проверка `is_open`, невзведение по сетевому отказу, подмена причины при
  взводе, `>=` → `>` на границе срока, потеря `params`, потеря `headers`, снятый
  `User-Agent`, снятый `follow_redirects`.
- **Пары «жанр против тега» разделены у обоих магазинов.** Обмен пространствами
  `GOG` ↔ `GOG_TAG` и `STEAM` ↔ `STEAM_TAG` ловится, ключ метки (`slug` против
  `name`, `tagid` против `weight`) — тоже.

## Находки

#### Critical

Нет.

#### Important

**1. `convert.identifier`: ноль и пустота не различаются ничем.**

`backend/sources/convert.py:26` — `if value is None or value == "":` заменено на
`if not value:`. Гонялись `tests/backend/sources` + `test_outcome` +
`test_poster_service` (315), затем весь набор (1288). Молча оба раза.

Свойство без сторожа: **числовой ноль обязан стать идентификатором `"0"`, а
пустая строка — нет.** Пустую половину сторожит
`test_tmdb_card.py::test_an_empty_imdb_id_is_not_an_identifier` (обратная
мутация — снятие `or value == ""` — ловится им сразу). Нулевую не сторожит
ничто, хотя докстринг функции называет её первой причиной, по которой отбор идёт
по `is None`, а не по ложности.

Разрыв виден и по соседям: у `convert.py` есть прямой тестовый модуль
`tests/backend/sources/test_convert.py`, и в нём проверены `companies`, `genres`,
`year`, `rating`, `from_search` — **все, кроме `identifier`**. У парной `rating`
при этом стоит тест ровно про этот случай,
`test_nothing_and_zero_are_both_an_absence_here`, и он утверждает **обратное**
правило. То есть две функции одного модуля живут по противоположным правилам, и
доказано только одно из двух.

Это тот самый класс, на котором проект горел дважды («слипшиеся ноль и пустота»).

Как наблюдать: в `test_convert.py` — `identifier(IdSource.KINOPOISK, 0) ==
(ExternalId(IdSource.KINOPOISK, "0"),)` рядом с уже имеющимся утверждением про
пустую строку, одним тестом на обе половины правила.

**2. Синопсис карточки Steam не сторожит ни один тест.**

`backend/sources/steam/parse.py:71` — `data.get("short_description")` заменено на
`data.get("detailed_description")`. Молча на 315 и на 1288.

Свойство без сторожа: **синопсис игры — короткое описание, а не подробное.**
В записанной фикстуре `tests/fixtures/steam/appdetails.json` есть оба поля, и
`detailed_description` — это HTML с `<h1>`, `<p class="bb_paragraph">` и пятью
`<img>`. Такой синопсис уехал бы в базу и в карточку ленты разметкой, и ни один
из 1288 тестов не сказал бы ни слова.

Слово `synopsis` в `tests/backend/sources/` встречается четыре раза, и все
четыре — у TMDB. Steam — единственный игровой источник, у которого синопсис
вообще есть (у GOG `parse_catalog` его не заполняет), и он не проверен.

Как наблюдать: в `test_steam.py`, там же где сверяются жанры и метакритик,
утверждать `card.item.synopsis.startswith("Вы — Геральт")` — или, устойчивее к
фикстуре, `"<" not in card.item.synopsis`.

**3. `gog.title_of`: защита от пустого названия не наблюдается.**

`backend/sources/gog/parse.py:86` — `if not isinstance(title, str) or not title:`
заменено на `if title is None:`. Молча на 315 и на 1288.

Свойство без сторожа: **пустое название и не-строка — это неразобранный ответ, а
не название.** Докстринг функции называет цену прямо: пустой запрос каталог
понимает буквально и отдаёт весь каталог, шесть с лишним тысяч наименований.
Под мутацией товарная ручка с `"title": ""` отдала бы пустую строку, `card()`
приняла бы её за название и ушла бы в каталог с запросом `like:` — то есть
карточка либо не нашлась бы с отказом «каталог не вернул N», либо, что хуже,
совпала бы с чужой строкой из общей выдачи.

Сторожа на этой функции нет вовсе: `test_gog.py` проверяет 404 без JSON, отказ
ручки и цепочку «ручка → каталог», но пустого и нестрокового названия не подаёт
ни разу.

Как наблюдать: два утверждения в `test_gog.py` — товарная ручка отвечает
`{"title": ""}` и `{"title": null}`, ожидаемое `Refusal(reason=BROKEN)`; заодно
проверяется, что второго запроса (в каталог) не было.

#### Minor

**4. `steam.YEAR`: строгость шаблона года не наблюдается.**

`backend/sources/steam/parse.py:20` — `(?:19|20)\d{2}` заменено на `\d{4}`. Молча.

Свойство без сторожа: **годом считается только 19xx или 20xx.** Все записанные и
рукописные даты в тестах («18 мая. 2015 г.», «26 Nov, 2015», «Coming soon»)
различают строгий шаблон и слабый одинаково. Разойдутся они на строке, где
четыре цифры подряд стоят перед годом и годом не являются.

Стоит того, чтобы завести: перебор в
`test_steam.py::test_the_year_is_read_from_a_human_written_date` дополнить
строкой вида `"1080p trailer, 26 Nov, 2015"` → `2015`.

**5. `TAGS_WANTED["include_tag_count"]` пришпилен нестрого.**

`backend/sources/steam/client.py:26` — `20` заменено на `5`. Молча, потому что
`test_the_tag_request_asks_the_way_that_answers` утверждает
`wanted["data_request"]["include_tag_count"] > 0`, а не равенство.

Ослабление выглядит намеренным (не пришпиливать произвольное число), и потому
это Minor, а не Important. Но следствие у величины есть, и оно названо в
решениях проекта: своих жанров у Steam двенадцать на весь магазин, и без тегов у
игры остаётся один-два. Двадцать против пяти — это разница в наполнении каждой
игровой карточки, и заметить её можно только глазами.

Стоит того, чтобы завести: заменить `> 0` на `== TAGS_WANTED["include_tag_count"]`
и сверять саму константу с числом двадцать одним отдельным утверждением — тогда
изменение величины становится сознательной правкой теста, а не молчаливым
следствием.

**6. `refuse_until(source=...)`: подмена имени источника именем соединения
неразличима — и это записано в коде.**

`backend/sources/backoff.py:31` — `source=source or http.name` заменено на
`source=http.name`. Молча.

Докстринг `refuse_until` называет это прямо: «Сегодня оба имени совпадают и
подмена не наблюдалась бы, но имя соединения — дело сборки, а имя источника едет
в плашку человеку». То есть свойство известно и осознано.

Наблюдать его дёшево: `refuse_quota(SourceHttp("зеркало-2"))` → `.source ==
"kinopoisk"`. Один тест в `test_kinopoisk.py` закрывает разрыв между именем
соединения и именем источника навсегда, не дожидаясь дня, когда сборка их
разведёт.

#### Правило 8: код без наблюдаемого следствия

Не находки по тестам — находки по коду. Обе строки можно снять, и ни поведение,
ни один из 1288 тестов этого не заметят.

**7. `Breaker.is_open`: `self._until = None` не делает ничего.**
`backend/sources/http.py:38`. Строка снята — молча на 315 и на 1288, и это
эквивалентный мутант, а не дыра. `_until` читается ровно в двух местах, оба в
`is_open` (`http.py:35`, `http.py:37`), и пишется в `trip` (`http.py:47`);
внешних читателей нет ни одного (проверено по всему `backend/`, `bridge/`,
`tests/`). Просроченный срок даёт `False` и без сброса — сравнение
пересчитывается на каждом вызове. Это уборка памяти на одном `datetime`,
выглядящая как часть логики: читатель `is_open` вправе решить, что сброс
что-то значит.

**8. `omdb._number`: проверка `raw == "N/A"` избыточна.**
`backend/sources/ratings/omdb/parse.py:18`. Условие сужено до `if not raw:` —
молча, и снова эквивалентно: `"N/A".split("/")[0]` даёт `"N"`, `float("N")`
падает `ValueError`, и `except` ниже отдаёт тот же `None`. Быстрый путь работает
как комментарий про форму ответа OMDB, а не как ветка: убери его — ничего не
изменится.

## Полный список мутаций

Обозначения: **П** — поймана, **М** — прошла молча.

### `convert.py` (8)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M01 | `identifier`: отбор по ложности вместо `is None` | **М** | — |
| M02 | `identifier`: пустая строка становится идентификатором | П | `test_tmdb_card::test_an_empty_imdb_id_is_not_an_identifier` |
| M03 | `genres`: ключ по умолчанию `slug` вместо `id` | П | `test_convert::test_the_space_travels_with_the_identifier` |
| M04 | `year`: хвост строки вместо головы | П | `test_convert::test_the_year_starts_the_date` |
| M05 | `companies`: разработчик и издатель местами | П | `test_convert::test_the_developer_is_not_the_publisher` |
| M06 | `FREE_IN_SEARCH`: оценка GOG приписана TMDB | П | `test_convert::test_the_free_rating_of_the_source_belongs_to_its_owner` |
| M07 | `FREE_IN_SEARCH`: GOG выброшен из таблицы | П | то же |
| M08 | `rating`: ноль перестал быть отсутствием | П | `test_convert::test_nothing_and_zero_are_both_an_absence_here` |

### `errors.py` (6)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M09 | `absent`: отрицательный факт без проверки тела | П | `test_gog::test_a_404_without_json_is_not_a_missing_product` |
| M10 | `broken`: причина `NETWORK` вместо `BROKEN` | П | `test_gog::test_a_broken_product_answer_does_not_crash_the_client` |
| M11 | `BROKEN_BY_PARSING` без `KeyError` | П | то же |
| M12 | `BROKEN_BY_PARSING` только `ValueError` | П | то же |
| M13 | `is_json`: всегда «разобралось» | П | `test_gog::test_a_404_without_json_is_not_a_missing_product` |
| M14 | `refuse_code`: причина `NETWORK` | П | `test_gog::test_a_product_endpoint_failure_is_a_refusal` |

### `http.py` (11)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M15 | `NETWORK_BACKOFF` 15 с → 60 с | П | `test_http::test_the_source_is_asked_again_once_the_network_may_be_back` |
| M16 | `is_open`: `>=` → `>` | П | `test_http::test_tripped_breaker_opens_and_then_heals` |
| M17 | `is_open`: сброс `_until` снят | **М** | — (эквивалент) |
| M18 | `trip`: причина всегда `QUOTA` | П | `test_http::test_a_network_refusal_stays_a_network_refusal_while_it_waits` |
| M19 | `get`: предохранитель не смотрится | П | `test_gog::test_rate_limit_trips_the_breaker` |
| M20 | `get`: сетевой отказ не взводит предохранитель | П | `test_http::test_a_dead_network_costs_one_wait_not_one_per_card` |
| M21 | `get`: сетевой отказ взводит как `QUOTA` | П | `test_http::test_a_network_refusal_stays_a_network_refusal_while_it_waits` |
| M22 | `get`: `params` не уходят | П | `test_gog::test_search_asks_the_catalog_the_way_that_answers` |
| M23 | `get`: `headers` не уходят | П | `test_http::test_request_headers_join_the_common_ones_without_settling_in` |
| M24 | клиент без `User-Agent` | П | `test_http::test_user_agent_is_always_sent` |
| M25 | клиент без `follow_redirects` | П | `test_http::test_answer_behind_a_redirect_is_still_reached` |

### `backoff.py` (3)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M26 | `refuse_until` не взводит предохранитель | П | `test_gog::test_rate_limit_trips_the_breaker` |
| M27 | `retry_after=None` вместо срока | П | `test_http::test_an_undocumented_rate_limit_closes_the_source_for_five_minutes` |
| M28 | имя источника берётся у соединения | **М** | — |

### `registry.py` и `build.py` (9)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M29 | `catalog_for`: магазины в обратном порядке | П | `test_registry::test_games_come_from_two_equal_stores` |
| M30 | `people_for`: игры тоже идут к TMDB | П | `test_registry::test_games_ask_nobody_about_people` |
| M31 | `client_for`: Steam и GOG местами | П | `test_registry::test_a_card_goes_back_to_the_client_it_came_from` |
| M32 | `rating_sources`: игры спрашивают OMDB | П | `test_registry::test_games_ask_nobody_for_ratings` |
| M33 | `aclose` не закрывает ничего | П | `test_registry::test_closing_closes_every_connection` |
| M34 | сборка: имена соединений магазинов местами | П | `test_registry::test_each_catalog_client_sits_on_the_connection_of_its_own_name[steam]` |
| M35 | сборка: `connections` пуст | П | то же, `[tmdb]` |
| M36 | сборка: OMDB получил ключ MDBList | П | `test_registry::test_every_key_from_the_settings_reaches_its_own_source` |
| M37 | сборка: оба зеркала на одном ключе | П | то же |

### TMDB — клиент (13)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M38 | `_ABSENT` без кода 6 | П | `test_tmdb_failures::test_broken_identifier_is_also_an_answer` |
| M39 | 404 без проверки тела | П | `test_tmdb_failures::test_a_404_without_json_is_not_a_negative_fact` |
| M40 | 429 как `QUOTA` | П | `test_tmdb_card::test_a_rate_limit_on_the_cheap_request_trips_the_breaker` |
| M41 | 401 как `BROKEN` | П | `test_tmdb_failures::test_recorded_bad_key_is_a_refusal` |
| M42 | `RATE_BACKOFF` 1 мин → 5 мин | П | `test_tmdb_failures::test_the_breaker_lets_go_when_the_backoff_has_passed` |
| M43 | `_verdict` не взводит предохранитель | П | `test_tmdb_card::test_a_rate_limit_on_the_cheap_request_trips_the_breaker` |
| M44 | `_params` без языка | П | `test_tmdb_search::test_client_asks_the_right_endpoint_and_language` |
| M45 | `search`: ручки фильма и сериала местами | П | то же |
| M46 | `credits_of`: ручки местами | П | `test_tmdb_people::test_the_client_asks_the_movie_door` |
| M47 | `_APPEND`: сериал без `external_ids` | П | `test_tmdb_card::test_client_requests_aggregate_credits_for_a_series` |
| M48 | `_APPEND`: фильм просит `aggregate_credits` | П | `test_tmdb_card::test_client_requests_credits_for_a_movie` |
| M49 | `find_people` ходит в `/search/multi` | П | `test_tmdb_people::test_the_person_search_asks_by_name` |
| M50 | `card`: тип в пути местами | П | `test_tmdb_card::test_client_requests_credits_for_a_movie` |

### TMDB — разбор (22)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M51 | `_hundred` без пересчёта шкалы | П | `test_tmdb_card::test_the_tmdb_rating_is_stored_on_the_hundred_scale` |
| M52 | `_cast`: позиция по номеру строки | П | `test_tmdb_card::test_actors_are_placed_by_the_billing_of_the_source` |
| M53 | `_cast`: актёр записан режиссёром | П | `test_tmdb_card::test_director_is_pulled_from_the_crew` |
| M54 | режиссёр ищется по `Producer` | П | то же |
| M55 | режиссёр записан шоураннером | П | то же |
| M56 | шоураннер записан режиссёром | П | `test_tmdb_card::test_showrunner_comes_from_created_by` |
| M57 | `_required` не смотрит на `cast` | П | `test_tmdb_card::test_a_block_that_came_without_its_cast_is_incomplete` |
| M58 | `_KEYS`: фильм и сериал местами | П | `test_tmdb_card::test_movie_card_carries_what_the_search_could_not` |
| M59 | `_KEYS`: название и оригинал местами | П | `test_tmdb_people::test_a_director_is_found_in_the_crew` |
| M60 | `_genres`: пространство `STEAM` | П | `test_tmdb_card::test_genres_come_from_the_named_block_not_the_search_one` |
| M61 | `_hits`: пространство `STEAM_TAG` | П | `test_tmdb_people::test_a_work_carries_everything_a_candidate_needs` |
| M62 | `_poster` без базы адреса | П | `test_tmdb_card::test_movie_card_carries_what_the_search_could_not` |
| M63 | `parse_credits` только `cast` | П | `test_tmdb_people::test_a_director_is_found_in_the_crew` |
| M64 | `parse_credits`: дубли по названию | П | `test_tmdb_people::test_two_works_with_one_name_are_two_works` |
| M65 | сезоны и серии местами | П | `test_tmdb_card::test_series_card_has_seasons_and_episodes` |
| M66 | своя оценка приписана IMDB | П | `test_tmdb_card::test_tmdb_own_rating_survives_into_the_card` |
| M67 | `imdb_id` записан как кинопоисковый | П | `test_tmdb_card::test_movie_imdb_id_is_taken_from_the_top_level` |
| M68 | у сериала `imdb_id` с верхнего уровня | П | `test_tmdb_card::test_series_imdb_id_comes_from_the_appended_block` |
| M69 | `_item`: источник `STEAM` | П | `test_tmdb_card::test_movie_card_carries_what_the_search_could_not` |
| M70 | `_released`: формат даты перевёрнут | П | `test_tmdb_card::test_the_full_release_date_survives_not_only_the_year` |
| M71 | `_hits`: оценка кандидата без пересчёта | П | `test_tmdb_search::test_tmdb_rating_comes_free_with_the_search` |
| M72 | `parse_people`: имя вместо номера | П | `test_tmdb_people::test_everyone_found_comes_back` |

### Steam (18)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M73 | `poster_url` без `_2x` | П | `test_steam::test_vertical_cover_uses_the_2x_name` |
| M74 | `YEAR` — любые четыре цифры | **М** | — |
| M75 | `_year`: год с конца строки | П | `test_steam::test_the_year_is_read_from_a_human_written_date` |
| M76 | metascore приписан Rotten Tomatoes | П | `test_steam::test_metascore_belongs_to_metacritic` |
| M77 | жанры берутся из `categories` | П | `test_steam::test_genres_come_from_the_genres_and_not_from_the_neighbours` |
| M78 | жанры уехали в пространство тега | П | то же |
| M79 | теги уехали в пространство жанра | П | `test_steam::test_tags_arrive_in_their_own_space` |
| M80 | тег берётся по весу, а не по номеру | П | `test_steam::test_a_tag_is_its_number_and_not_its_weight` |
| M81 | синопсис из `detailed_description` | **М** | — |
| M82 | название кандидата из `title` | П | `test_steam::test_search_returns_candidates` |
| M83 | `success` перестал различать отсутствие | П | `test_steam::test_missing_game_answers_under_two_hundred` |
| M84 | ответ про чужой appid как отсутствие | П | `test_registry::test_a_client_signs_refusals_with_the_name_it_calls_itself[steam]` |
| M85 | теги: код ответа не смотрится | П | `test_steam::test_tags_that_did_not_arrive_do_not_break_the_card` |
| M86 | теги не доливаются к карточке | П | `test_steam::test_the_card_carries_both_spaces` |
| M87 | `TAGS_CONTEXT`: страна `RU` | П | `test_steam::test_the_tag_request_asks_the_way_that_answers` |
| M88 | `include_tag_count` 20 → 5 | **М** | — |
| M89 | строка поиска не экранируется | П | `test_steam::test_a_query_with_url_punctuation_survives` |
| M90 | карточка запрошена без языка | П | `test_steam::test_the_tag_request_asks_the_way_that_answers` |

### GOG (15)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M91 | каталог спрашивается без `like:` | П | `test_gog::test_search_asks_the_catalog_the_way_that_answers` |
| M92 | товарная ручка: 404 без проверки тела | П | `test_gog::test_a_404_without_json_is_not_a_missing_product` |
| M93 | `card` берёт не тот идентификатор | П | `test_gog::test_card_picks_the_asked_identifier` |
| M94 | промах каталога как отрицательный факт | П | `test_gog::test_card_that_the_catalog_did_not_return_is_not_a_negative_fact` |
| M95 | `resolve_slug`: одна форма запроса вместо двух | П | `test_gog_slug::test_the_second_form_is_asked_when_the_first_misses` |
| M96 | `resolve_slug`: отсутствие как отказ | П | `test_gog_slug::test_a_slug_the_catalog_does_not_have_is_missing` |
| M97 | `find_slug`: нестрогое совпадение | П | `test_gog_slug::test_a_prefix_of_a_real_slug_is_not_enough` |
| M98 | `_marks`: жанры и теги пространствами местами | П | `test_gog::test_a_genre_is_not_labelled_as_a_tag` |
| M99 | `_marks`: метка по названию, а не по слагу | П | `test_gog::test_a_genre_and_a_tag_with_the_same_slug_stay_apart` |
| M100 | оценка из возрастных рейтингов | П | `test_gog::test_catalog_row_is_already_a_card` |
| M101 | оценка приписана Metacritic | П | `test_gog::test_player_rating_belongs_to_gog` |
| M102 | обложка горизонтальная | П | `test_gog::test_the_cover_is_the_vertical_one` |
| M103 | оценка не едет в кандидата поиска | П | `test_gog::test_a_card_folds_into_a_candidate` |
| M104 | `title_of`: пустое название сходит за название | **М** | — |
| M105 | год из другого поля | П | `test_gog::test_the_year_is_read_from_a_dotted_date` |

### MDBList (13)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M106 | 404 без проверки тела | П | `test_mdblist::test_missing_object_is_an_answer` |
| M107 | 202 как квота | П | `test_mdblist::test_cache_building_is_a_retry_not_an_absence` |
| M108 | 429 как частота | П | `test_mdblist::test_recorded_quota_is_a_refusal_with_the_named_delay` |
| M109 | `Retry-After` не читается | П | то же |
| M110 | 403 не разбирается отдельно | П | `test_mdblist::test_cloudflare_wall_is_not_a_key_problem` |
| M111 | `_denied`: чужой периметр не отличается | П | то же |
| M112 | `_denied`: периметр как битый ключ | П | то же |
| M113 | `PROVIDES` без `ROTTEN` | П | `test_rating_provides::test_a_client_brings_nothing_it_did_not_declare[mdblist]` |
| M114 | тип содержимого в пути местами | П | `test_mdblist::test_modern_endpoint_is_used` |
| M115 | ключ не уходит в запрос | П | то же |
| M116 | `OWNERS`: томаты и метакритик местами | П | `test_mdblist::test_each_owner_keeps_its_own_scale` |
| M117 | `null` становится нулём | П | `test_mdblist::test_null_score_is_reported_as_an_empty_value` |
| M118 | `OWNERS`: заведён чужой владелец `metacriticuser` | П | `test_mdblist::test_each_owner_keeps_its_own_scale` |

### OMDB (13)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M119 | `Response` сверяется другим регистром | П | `test_omdb::test_recorded_missing_object_arrives_under_two_hundred` |
| M120 | квота ищется по слову `quota` | П | `test_omdb::test_recorded_quota_is_told_apart_from_a_bad_key` |
| M121 | битый ключ как квота | П | то же |
| M122 | битый ключ взводит предохранитель | П | `test_omdb::test_a_bad_key_does_not_trip_the_breaker` |
| M123 | `until_midnight` считает через сутки | П | `test_omdb::test_until_midnight_counts_to_the_next_day` |
| M124 | тело не обязано быть объектом | П | `test_omdb::test_a_json_array_does_not_crash` |
| M125 | 401 не разбирается | П | `test_omdb::test_recorded_quota_is_told_apart_from_a_bad_key` |
| M126 | `PROVIDES` с лишним TMDB | П | `test_rating_provides::test_a_client_declares_nothing_it_cannot_bring[omdb]` |
| M127 | `_number` берёт знаменатель | П | `test_omdb::test_imdb_rating_is_taken_from_its_own_field` |
| M128 | `_number` не срезает процент | П | `test_omdb::test_every_owner_omdb_knows_is_taken` |
| M129 | `OWNERS`: томаты и метакритик местами | П | `test_omdb::test_rotten_tomatoes_keeps_its_own_scale` |
| M130 | IMDb записывается дважды | П | `test_omdb::test_imdb_rating_is_taken_from_its_own_field` |
| M131 | `N/A` перестал отбрасываться заранее | **М** | — (эквивалент) |

### Кинопоиск, оба зеркала (21)

| # | Что изменено | Итог | Кто поймал |
|---|---|---|---|
| M132 | запасное зеркало не спрашивается | П | `test_kinopoisk::test_a_refusal_switches_to_the_fallback` |
| M133 | `PROVIDES` как IMDB | П | `test_rating_provides::test_a_client_brings_nothing_it_did_not_declare[kinopoisk]` |
| M134 | `QUOTA_BACKOFF` 6 ч → 1 ч | П | `test_kinopoisk::test_primary_quota_is_a_refusal_and_trips_the_breaker` |
| M135 | `RATE_BACKOFF` 1 мин → 10 мин | П | `test_kinopoisk::test_primary_rate_limit_trips_the_breaker_too` |
| M136 | `answered`: пустое только по значениям | П | `test_kinopoisk::test_the_identifier_survives_a_film_without_a_rating` |
| M137 | квота как частота | П | `test_kinopoisk::test_primary_quota_is_a_refusal_and_trips_the_breaker` |
| M138 | битый ключ как `BROKEN` | П | `test_kinopoisk::test_primary_bad_key_is_a_refusal` |
| M139 | основное: 404 без проверки тела | П | `test_kinopoisk::test_primary_is_classified_by_http_code_not_by_the_body` |
| M140 | основное: 403 и 401 местами | П | `test_kinopoisk::test_primary_quota_is_a_refusal_and_trips_the_breaker` |
| M141 | основное: `FIELDS` без `rating` | П | `test_kinopoisk::test_primary_asks_for_the_fields_it_needs` |
| M142 | основное ищет по `externalId.tmdb` | П | то же |
| M143 | основное: 429 не разбирается | П | `test_kinopoisk::test_primary_rate_limit_trips_the_breaker_too` |
| M144 | запасное: 402 перестал быть квотой | П | `test_kinopoisk::test_fallback_quota_has_its_own_code` |
| M145 | запасное ищет ключевым словом | П | `test_kinopoisk::test_fallback_sends_the_key_in_the_header_and_keeps_the_tt_prefix` |
| M146 | `_rating`: ноль как отсутствие | П | `test_kinopoisk::test_an_honest_zero_is_not_an_absence` |
| M147 | основное: оценка `imdb` вместо `kp` | П | `test_kinopoisk::test_primary_reads_the_rating` |
| M148 | запасное: оценка `ratingImdb` | П | `test_kinopoisk::test_an_honest_zero_is_not_an_absence` |
| M149 | идентификатор записан как IMDB | П | `test_kinopoisk::test_primary_hands_out_the_kinopoisk_identifier` |
| M150 | `_first_row`: последняя строка вместо первой | П | `test_kinopoisk::test_only_the_first_row_of_the_answer_is_read` |
| M151 | `_first_row`: ключ прибит к `docs` | П | `test_kinopoisk::test_fallback_rating_comes_with_the_search` |
| M152 | владелец оценки TMDB | П | `test_kinopoisk::test_primary_reads_the_rating` |

## Вердикт

**Готово к продолжению работы?** Да

**Обоснование:** 152 мутации по всему `backend/sources/` не нашли в боевом коде
ни одной ошибки поведения — восемь молчаливых распались на пять дыр в тестах,
две эквивалентные строки и одну подмену, неразличимую на сегодняшней сборке и
названную таковой прямо в докстринге. Ни одна из пяти дыр не мешает работе: это
невыверенные свойства, а не сломанные — три Important стоит закрыть тремя
короткими тестами (ноль в `identifier`, синопсис Steam, пустое название GOG), и
делать это можно параллельно с работой над клиентом.

Дерево возвращено в исходное состояние: `git status` чист, `.env` скопирован из
основного дерева и в индекс не попадает.
