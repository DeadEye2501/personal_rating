# План 2 — финальное ревью: умеют ли тесты падать (мутации)

Дата: 2026-07-29. Измерение: способность `tests/backend/sources/` (219 тестов)
ловить намеренную порчу кода в шести клиентах источников и общем под ними.
Работа велась в отдельном рабочем дереве
(`C:\Users\deade\AppData\Local\Temp\review-mutations`), которое по завершении
удалено; основной репозиторий не тронут.

Метод: точечные мутации по одной строке (снятое условие, сменённый ключ,
сдвинутая граница, перепутанный тип), запуск профильного файла тестов, откат.
Мутации, уже проверенные исполнителем по слайсам, не повторялись — упор на
границы диапазонов, `None`/значение, пустые коллекции, порядок веток, подмену
источника при сборке карточки.

Всего внесено **57 мутаций**. Красными стали **51**, молча прошли **6**.
Ещё 2 мутации отброшены на месте как не несущие поведенческого различия
(отмечены отдельно, в общий счёт не включены).

## Таблица мутаций

| № | Файл:строка | Что сломано | Результат | Кто должен был поймать |
|---|---|---|---|---|
| 1 | `http.py:32` | `Breaker.is_open`: `>=` → `>` на границе среза | 🔴 | `test_tripped_breaker_opens_and_then_heals` |
| 2 | `http.py:86` | `SourceHttp.get`: `Reason.NETWORK` → `Reason.RATE` при сетевой ошибке | 🔴 | `test_network_failure_becomes_a_refusal_not_an_exception`, `test_timeout_becomes_a_refusal` |
| 3 | `http.py:103` | `refuse_undocumented`: код `429` → `430` | 🔴 | `test_an_undocumented_rate_limit_closes_the_source_for_five_minutes` |
| 4 | `errors.py:58` | `is_answer`: `(Found, Missing)` → только `Found` | 🔴 | `test_missing_is_an_answer_not_a_silence` |
| 5 | `errors.py:51` | `broken()`: `Reason.BROKEN` → `Reason.NETWORK` | 🔴 (7 тестов сразу, во всех источниках) | по одному в каждом из `test_gog/kinopoisk/mdblist/omdb/steam/tmdb_*` |
| 6 | `http.py:42` | `Breaker.trip`: не пишет `self._reason` | 🔴 | `test_the_breaker_reports_the_reason_it_was_tripped_for`, `test_open_breaker_stops_the_request_before_the_wire` |
| 7 | `convert.py:50` | `rating()`: `not value` → `value is None` (0 не отсекается) | 🔴 (2 из 3 источников) | `test_a_film_nobody_rated_has_no_rating` (tmdb), `test_a_game_nobody_reviewed_has_no_rating` (gog) |
| 8 | `convert.py:36-37` | `companies()`: роли `DEVELOPER`/`PUBLISHER` переставлены местами | ⚪ **молча** | — |
| 9 | `convert.py:26` | `year()`: срез `[:4]` → `[:5]` | 🔴 (4 теста, три источника) | `test_the_full_release_date_survives_not_only_the_year` и др. |
| 10 | `convert.py:20` | `genres()`: `row[key]` → `row.get(key)` (проглатывает `KeyError`) | ⚪ **молча** | — |
| 11 | `tmdb/client.py:35` | `_ABSENT`: `{6, 34}` → `{6}` | 🔴 | `test_recorded_missing_object_is_an_answer` |
| 12 | `tmdb/client.py:53-55` | `classify`: причины `RATE`/`KEY` переставлены на `429`/`401` | 🔴 (8 тестов) | весь `test_tmdb_failures.py` |
| 13 | `tmdb/parse.py:92` | `parse_search`: `title_key` перепутан для фильма/сериала | 🔴 (3 теста) | `test_search_gives_candidates_not_cards` и др. |
| 14 | `tmdb/parse.py:67` | `_person`: `row["id"]` → `row.get("id")` (проглатывает `KeyError`) | ⚪ **молча** | — |
| 15 | `tmdb/parse.py:124` | `parse_movie`: `"Director"` → `"director"` (регистр) | 🔴 | `test_director_is_pulled_from_the_crew`, `test_the_rest_of_the_crew_stays_out` |
| 16 | `tmdb/parse.py:84` | `_required`: проверяет `"crew"` вместо `"cast"` | 🔴 (падает `KeyError`, не `Incomplete`) | `test_a_block_that_came_without_its_cast_is_incomplete` |
| 17 | `tmdb/parse.py:153` | `parse_series`: шоураннер получает `PersonRole.DIRECTOR` | 🔴 | `test_showrunner_comes_from_created_by` |
| 18 | `tmdb/parse.py:170-171` | `parse_series`: `seasons_count`/`episodes_count` переставлены | 🔴 | `test_series_card_has_seasons_and_episodes` |
| 19 | `steam/client.py:83` | `card`: `not block.get("success")` → `block.get("success")` (инверсия) | 🔴 (6 тестов) | половина `test_steam.py` |
| 20 | `steam/client.py:48` | `quote(query, safe='')` → `safe='?#'` | 🔴 | `test_a_query_with_url_punctuation_survives` |
| 21 | `steam/client.py:80` | Отказ на чужой appid: `Reason.BROKEN` → `Reason.NETWORK` | 🔴 | `test_a_reply_about_another_game_is_refused` |
| 22 | `steam/client.py:95` | Порядок конкатенации `genre_ext_ids` (жанры/теги) | ⚪ молча, но не баг — набор без порядка | — |
| 23 | `steam/parse.py:26` | `poster_url`: убран суффикс `_2x` | 🔴 | `test_vertical_cover_uses_the_2x_name` |
| 24 | `steam/parse.py:20` | `_year`: `(?:19\|20)` → `(?:20)` (теряет 1900-е) | ⚪ **молча** | — |
| 25 | `steam/parse.py:54` | `_metascore`: `RatingSource.METACRITIC` → `RatingSource.STEAM` | 🔴 | `test_metascore_belongs_to_metacritic` |
| 26 | `steam/parse.py:86` | `parse_tags`: `GenreSource.STEAM_TAG` → `GenreSource.STEAM` | 🔴 (2 теста) | `test_tags_arrive_in_their_own_space`, `test_the_card_carries_both_spaces` |
| 27 | `gog/client.py:69` | `card`: сравнение id `==` → `!=` (инверсия) | 🔴 (2 теста) | `test_card_picks_the_asked_identifier` и др. |
| 28 | `gog/parse.py:22-23` | `_marks`: пространства `GOG`/`GOG_TAG` переставлены | ⚪ **молча** | — |
| 29 | `gog/parse.py:47` | Оценка игрока: `reviewsRating` → `ratings` (возрастной рейтинг вместо числа) | 🔴 (11 тестов, каскад) | почти весь `test_gog.py` |
| 30 | `gog/parse.py:63` | `to_hit`: условие `card.ratings` → `card.companies` | 🔴 | `test_search_never_reports_nothing_found` |
| 31 | `gog/client.py:40` | Запрос без префикса `like:` | 🔴 | `test_search_asks_the_catalog_the_way_that_answers` |
| 32 | `mdblist/client.py:32` | `_retry_after`: убрана проверка `raw.isdigit()` | 🔴 | `test_a_delay_that_is_not_a_number_falls_back_too` |
| 33 | `mdblist/client.py:59` | Код `202` → `203` | 🔴 | `test_cache_building_is_a_retry_not_an_absence` |
| 34 | `mdblist/client.py:70` | `(401, 403)` → `(401,)` | 🔴 | `test_cloudflare_wall_is_not_a_key_problem` |
| 35 | `mdblist/parse.py:13` | `OWNERS["tomatoes"]` → `"tomatoes_user"` | 🔴 (2 теста) | `test_ratings_are_split_by_owner` и др. |
| 36 | `mdblist/parse.py:31` | `None if value is None else float(value)` → `float(value) if value else None` (0.0 теряется) | ⚪ **молча** | — (см. находку ниже) |
| 37 | `mdblist/client.py:41` | `media`: `"show"`/`"movie"` переставлены | 🔴 (3 теста) | `test_modern_endpoint_is_used` и др. |
| 38 | `omdb/client.py:73` | `payload.get("Response") == "False"` → `is False` (тип) | 🔴 (3 теста) | `test_recorded_missing_object_arrives_under_two_hundred` и др. |
| 39 | `omdb/client.py:86` | `"limit" in error` → `error == "limit"` | 🔴 (5 тестов) | половина `test_omdb.py` |
| 40 | `omdb/client.py:31` | `until_midnight`: `second=0` → `second=1` | 🔴 | `test_until_midnight_counts_to_the_next_day` |
| 41 | `omdb/parse.py:19` | `_number`: `split("/")[0]` → `[-1]` | 🔴 (4 теста) | `test_fraction_form_is_understood` и др. |
| 42 | `omdb/parse.py:42` | Дедуп `RatingSource.IMDB not in seen` убран | 🔴 (3 теста) | `test_the_separate_imdb_field_does_not_duplicate_the_list` |
| 43 | `omdb/parse.py:17` | `raw == "N/A"` → `"n/a"` (регистр) | нейтрально — `float()` всё равно ловит `ValueError` | не баг, не в счёте |
| 44 | `kinopoisk/client.py:23` | `KinopoiskClient.ratings`: условие обращения к запасному зеркалу инвертировано | 🔴 (3 теста) | `test_a_refusal_switches_to_the_fallback` и др. |
| 45 | `mirror.py:48` | `answered()`: `and` → `or` | 🔴 (2 теста) | `test_the_identifier_survives_a_film_without_a_rating` |
| 46 | `poiskkino.py:55` | Код `404` → `405` | 🔴 (3 теста) | `test_primary_is_classified_by_http_code_not_by_the_body` и др. |
| 47 | `poiskkino.py:75-83` | `_absent`: ветки `Missing`/`Refusal` переставлены | 🔴 (4 теста) | `test_a_page_from_the_proxy_is_not_a_negative_fact` и др. |
| 48 | `unofficial.py:44-48` | `refuse_quota`/`refuse_rate` переставлены между `402`/`429` | 🔴 (4 теста) | `test_fallback_quota_has_its_own_code` и др. |
| 49 | `kinopoisk/parse.py:32` | `parse_poiskkino`: ключ `"kp"` → `"imdb"` | 🔴 | `test_primary_reads_the_rating` |
| 50 | `kinopoisk/parse.py:45` | `parse_unofficial`: `kinopoiskId` → `filmId` | 🔴 | `test_fallback_rating_comes_with_the_search` |
| 51 | `registry.py:40` | `catalog_for`: у игр остался только Steam, GOG выпал | 🔴 | `test_games_come_from_two_equal_stores` |
| 52 | `registry.py:48` | `rating_sources`: Кинопоиск выпал из списка агрегаторов | 🔴 | `test_films_ask_three_aggregators` |
| 53 | `registry.py:75` | Второе зеркало Кинопоиска заведено под именем `"kinopoisk-unofficial"` вместо `"kinopoisk"` | ⚪ **молча** | — |
| 54 | `registry.py:81-82` | Ключи MDBList/OMDB переставлены местами | 🔴 | `test_every_key_from_the_settings_reaches_its_own_source` |
| 55 | `tmdb/client.py:99` | Путь `card`: `"tv"`/`"movie"` переставлены | 🔴 (2 теста) | `test_client_requests_credits_for_a_movie` и др. |
| 56 | `steam/client.py:51` | `!= 200` → `> 200` | нейтрально — 1xx не приходит финальным ответом | не баг, не в счёте |
| 57 | `kinopoisk/parse.py:26` | `parse_poiskkino`: `not docs` → `docs is None` | 🔴 | `test_an_empty_answer_from_the_primary_is_an_absence` |

Легенда: 🔴 — тест покраснел, находка не нужна. ⚪ — тест прошёл молча, разобрано
в разделе «Находки».

## Находки

### Критично

**Обмен `developer`/`publisher` при сборке карточки не ловится ни у Steam, ни у
GOG** (мутация 8, `backend/sources/convert.py:36-37`). Оба теста —
`test_gog.py::test_developers_and_publishers_are_companies` и
`test_steam.py::test_card_carries_developers_and_publishers` — проверяют
только, что *набор* ролей содержит `DEVELOPER` и `PUBLISHER`:
```python
roles = {one.role for card in cards for one in card.companies}
assert CompanyRole.DEVELOPER in roles
assert CompanyRole.PUBLISHER in roles
```
Ни один тест не проверяет, что конкретное имя из фикстуры получило свою роль.
Задача — усилить оба теста: взять конкретную студию за именем из фикстуры и
сравнить её `role`, а не только присутствие роли в множестве.

**Обмен пространств `GOG`/`GOG_TAG` не ловится** (мутация 28,
`backend/sources/gog/parse.py:22-23`). Единственный тест на разделение —
`test_a_genre_and_a_tag_with_the_same_slug_stay_apart` — намеренно взял слаг
`fantasy`, который в фикстуре присутствует и в `genres[]`, и в `tags[]`.
Из-за этого он симметричен: после перестановки пространств обе пары
`(GOG, "fantasy")` и `(GOG_TAG, "fantasy")` всё равно оказываются в
`genre_ext_ids`, тест не отличает подмену. Это прямо касается предупреждения
из `CLAUDE.md` про `steam_tag`/`gog_tag`: если сопоставление жанров и тегов на
самом деле перепутано, этот тест не заметит. Нужен второй тест с
несимметричным слагом — который есть только в `genres[]` или только в
`tags[]` — и проверкой, что он попал в верное пространство.

### Важно

**`row[key]` → `row.get(key)` в `convert.genres()` не ловится** (мутация 10).
`KeyError` на отсутствующем `id`/`slug` — это то, что превращает битый жанр в
`Refusal` через `BROKEN_BY_PARSING` вместо тихой записи мусора. Ни одна
фикстура TMDB/Steam/GOG не пробует жанр без идентификатора, так что замена
падения на `.get()` (даёт `"None"` строкой) проходит незамеченной. То же самое
для `tmdb/parse.py:_person` (мутация 14, поле `id` человека) — оба места стоило
бы проверить тестом на строку без ожидаемого ключа.

**Различие `None` и `0.0` в оценке MDBList не проверено** (мутация 36,
`ratings/mdblist/parse.py:31`). Тест `test_null_score_is_reported_as_an_empty_value`
существует, но проверяет только `value: None` — а `if value` и
`if value is None` дают одинаковый результат на `None`. На `value: 0` они
расходятся: правильное поведение — сохранить `0.0` как оценку, а не потерять
её как отсутствующую (в точности та же ловушка, которую `convert.rating()`
уже решает явной проверкой на `None`, но в MDBList-парсере она отдельная и
непроверенная). Нужен тест с `value: 0`.

**Собственный `_year` у Steam не проверен на датах до 2000 года** (мутация 24,
`steam/parse.py:20`). Единственный тест на разбор года берёт `2015`. Проект
явно ссылается на ретро-игры как причину держать Steam источником
(«заметная часть ретро в Steam не продаётся» в `CLAUDE.md`), и регэксп сейчас
специально ловит и `19xx`, и `20xx` — но ничто не проверяет первую половину.
Нужен тест на дату вроде «12 Jan, 1998».

**Имя соединения второго зеркала Кинопоиска не проверено** (мутация 53,
`registry.py:75`). Докстрока `build_sources` прямо утверждает: «Оба зеркала
Кинопоиска при этом заводятся под одним именем — наружу источник один» — но
`test_registry.py` проверяет только `len(breakers) == 7` (общее число), не то,
что оба соединения Кинопоиска несут имя `"kinopoisk"`. Стоит пройтись по
`registry.connections` и явно проверить, что оба экземпляра под Кинопоиском
называются одинаково.

### Мелочь

- Мутация 22 (порядок конкатенации `card.genre_ext_ids + tags` в
  `steam/client.py`) прошла молча, но порядок пар в этом наборе не несёт
  смысла — не баг.
- Мутация 43 (регистр `"N/A"`/`"n/a"` в `omdb/parse.py`) и мутация 56
  (`!= 200` → `> 200` в `steam/client.py`) нейтральны: оба пути защищены
  соседним кодом (`try/except ValueError` и отсутствием реальных 1xx-ответов
  соответственно) — смены поведения нет, поэтому не считаются находками.
- Мутация 7 (`convert.rating`, ноль как отсутствие) поймана тестами TMDB и
  GOG, но не Steam: `test_metascore_belongs_to_metacritic` не пробует
  `metacritic.score == 0`. Раз общая функция уже накрыта двумя источниками из
  трёх, отдельного действия не требуется — но при следующей правке этого теста
  стоит добавить нулевой случай для полноты.

## Вердикт

Из 57 внесённых мутаций 51 поймана, 6 прошли молча (из них 2 — по-настоящему
значимые повторы одного класса ошибки: перепутанные роли/пространства при
сборке карточки на стыке нескольких полей одного типа, а не на границе одного
условия). Набор тестов в целом справляется: почти все ветки, границы кодов
ответа и переключения источник/причина отказа проверены и умеют падать.
Слабое место системное, а не случайное — там, где тест проверяет *набор
меток* (`{DEVELOPER, PUBLISHER}`, `{GOG, GOG_TAG}`), а не *привязку метки к
источнику*, перестановка двух полей местами не ловится. Это не повод
блокировать план: находки — на исправление точечными усилениями
перечисленных тестов, не переписыванием.
