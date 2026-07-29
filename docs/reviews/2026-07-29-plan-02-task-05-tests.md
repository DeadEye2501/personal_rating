# Ревью тестов — план 2, задача 5 (карточка TMDB)

Измерение: тесты этого слайса. Файл под ревью — `tests/backend/sources/test_tmdb_card.py`
(23 теста), код — `backend/model/card.py`, `backend/sources/tmdb/parse.py`,
`backend/sources/tmdb/client.py`.

## Сильные стороны

- Все тела ответов — записанные фикстуры (`tests/fixtures/tmdb/*.json`), у
  каждой есть `.meta.json` со статусом и заголовками настоящей записи. Ни один
  тест не собирает тело JSON-а вручную "с нуля".
- Синтетические тела есть только там, где случай нельзя записать живьём: тёзки
  (`test_two_namesakes_from_tmdb_stay_apart`), обрезанный блок без `cast`
  (`test_a_block_that_came_without_its_cast_is_incomplete`,
  `test_a_genuinely_empty_cast_is_not_incomplete`), отсутствие довеска у
  сериала (`test_a_series_without_its_appended_block_is_incomplete_too`) — во
  всех случаях это фикстура, у которой руками убран/подменён один ключ, а не
  придуманный документ.
- Значения, с которыми сверяются assert-ы (дата 2014-11-05, режиссёр «Кристофер
  Нолан», жанры `12/18/878`, 2 сезона / 24 серии у «Andor») — реальные данные
  из зафиксированных ответов, а не выдуманные константы: проверено сверкой
  фикстуры с ассертами.
- Список из 22 мутаций закрыт разумно: почти для каждой мутации нашёлся тест,
  единственная ломающая строка которого — это и есть место мутации.

## Находки

### Важно

- **`poster_url` не проверяется ни одним тестом.** Ни `test_movie_card_carries_what_the_search_could_not`,
  ни любой другой тест не читает `card.item.poster_url`. Функция `_poster`
  (`backend/sources/tmdb/parse.py:45-47`) и её вызовы (`parse.py:148`,
  `parse.py:181`) может сломаться (например, вернуть всегда `""`, или собрать
  URL без `POSTER_BASE`) — ни один из 23 тестов не покраснеет. Чинится одним
  ассертом вида `assert card.item.poster_url.startswith(POSTER_BASE)` в
  `test_movie_card_carries_what_the_search_could_not` и в
  `test_series_titles_come_from_their_own_fields` (или отдельным тестом).
- **`synopsis` (overview) не проверяется нигде.** Ни у фильма, ни у сериала.
  Строка `parse.py:147` (`synopsis=payload.get("overview") or ""`) и
  `parse.py:180` не сторожатся. Мелкая правка того же вида, что и выше.

### Мелочь

- **`original_title` фильма не проверяется.** У сериала есть
  `test_series_titles_come_from_their_own_fields`, у фильма аналога нет —
  `parse.py:144` (`original_title=payload.get("original_title") or ""`)
  ничем не сторожится на уровне `parse_movie`. Не критично, потому что общий
  паттерн разбора (`payload.get(...) or ""`) у фильма и сериала идентичный и
  частично покрыт по аналогии, но формально строка непроверена.
- **`item.source_id` сериала не проверяется на уровне `parse_series`.**
  Косвенно ловится в `test_client_requests_aggregate_credits_for_a_series`
  через `item.kind`, но не через `source_id` (там нет `result.value.item.source_id == "83867"`,
  в отличие от аналогичного теста для фильма). `parse.py:174`
  (`source_id=str(payload["id"])`) для сериала не имеет прямого сторожа.
- **Тест 9 (`test_the_rest_of_the_crew_stays_out`) частично перекрывает тест 8.**
  Оба реагируют на одну и ту же мутацию «режиссёрам ставится роль актёра»
  (мутация 6 из списка), и ни один по отдельности не поймал бы гипотетическую
  мутацию «всем crew присваивается роль DIRECTOR» отдельно от теста 8 — множество
  ролей осталось бы тем же `{ACTOR, DIRECTOR}`. Не находка первого порядка, эта
  мутация не входит в список 22 и её отдельно проверять не просили — просто
  отмечаю как слабое дублирование.

## По тестам — что наблюдают и что их ломает

Кратко (все 23, файл `tests/backend/sources/test_tmdb_card.py`):

1. `test_movie_card_carries_what_the_search_could_not` — базовые поля карточки
   фильма реальны (source/kind/runtime/title/genre_ext_ids/id==0). Ломает
   `parse.py:136-151` (любое из перечисленных полей).
2. `test_the_full_release_date_survives_not_only_the_year` — `released_at` и
   `year` сверены со значением фикстуры. Ломает `parse.py:145-146`.
3. `test_genres_come_from_the_named_block_not_the_search_one` — идентификаторы
   жанров из `genres[].id`. Ломает `parse.py:50-54`.
4. `test_movie_imdb_id_is_taken_from_the_top_level` — `imdb_id` с верхнего
   уровня. Ломает `parse.py:135` или `154`.
5. `test_tmdb_own_rating_survives_into_the_card` — своя оценка TMDB попадает в
   `ratings`. Ломает `parse.py:57-63`.
6. `test_every_person_carries_the_tmdb_identity` — у каждого credit есть
   `source`/`source_id`. Ломает `parse.py:69-75` (`_person`).
7. `test_two_namesakes_from_tmdb_stay_apart` — тёзки различаются по `id`, не
   схлопываются. Синтетическая фикстура (обоснованно — тёзок не записать
   живьём). Ломает `parse.py:74` (`source_id=str(row["id"])`).
8. `test_director_is_pulled_from_the_crew` — единственный режиссёр — реальное
   имя из фикстуры. Ломает `parse.py:131` (условие `job == "Director"`) или
   `129` (роль).
9. `test_the_rest_of_the_crew_stays_out` — набор ролей ограничен
   `{ACTOR, DIRECTOR}`. Ломает `parse.py:129-131` (см. находку выше про
   перекрытие с тестом 8).
10. `test_actors_keep_the_order_from_the_credits` — позиции актёров идут по
    `order`, начиная с 0. Ломает `parse.py:80` (`_cast`).
11. `test_series_card_has_seasons_and_episodes` — 2 сезона / 24 серии,
    `runtime is None`. Ломает `parse.py:182-183`.
12. `test_series_cast_comes_from_aggregate_credits` — состав > 50 человек
    (реально в фикстуре есть только ключ `aggregate_credits`, обычного
    `credits` нет вовсе — при подмене ключа тест упал бы `Incomplete`).
    Ломает `parse.py:161`.
13. `test_showrunner_comes_from_created_by` — хотя бы один SHOWRUNNER. Ломает
    `parse.py:163`.
14. `test_series_people_carry_the_identity_too` — та же проверка идентичности,
    что и тест 6, для сериала. Ломает `parse.py:161-163` (через `_person`/`_cast`).
15. `test_series_imdb_id_comes_from_the_appended_block` — `imdb_id` из
    `external_ids`. Ломает `parse.py:168`.
16. `test_series_titles_come_from_their_own_fields` — `title`/`original_title`/`year`
    сериала. Ломает `parse.py:175/177/178`.
17. `test_typo_in_append_to_response_is_caught_by_content` — `Incomplete` на
    реально записанном обрезанном ответе. Ломает `parse.py:90-93` (`_required`).
18. `test_a_series_without_its_appended_block_is_incomplete_too` — то же для
    сериала (ключ убран руками из настоящей фикстуры). Ломает `parse.py:161`
    (вызов `_required(payload, "aggregate_credits")`).
19. `test_a_block_that_came_without_its_cast_is_incomplete` — блок есть, `cast`
    нет → `Incomplete`. Ломает `parse.py:91` (проверка `"cast" not in found`).
20. `test_a_genuinely_empty_cast_is_not_incomplete` — пустой, но
    присутствующий `cast` не бросает `Incomplete`. Ломает `parse.py:90-93`
    (если проверку заменить на непустоту).
21. `test_client_requests_credits_for_a_movie` — клиент запрашивает
    `/movie/{id}` с `credits`, без `aggregate_credits`. Ломает
    `client.py:27-29` или `52-56`.
22. `test_client_requests_aggregate_credits_for_a_series` — клиент запрашивает
    `/tv/{id}` с `aggregate_credits` и `external_ids`. Ломает `client.py:28-29`
    или `52-56`.
23. `test_incomplete_answer_is_a_refusal_not_a_card` — `Incomplete` из парсера
    превращается в `Refusal(BROKEN)`, а не падает наружу и не отдаёт карточку.
    Ломает `client.py:62-66`.

Ни один из 23 тестов не сводится к «прочитать константу и сравнить с самой
собой» — все проверяют следствие разбора настоящего (или обоснованно
синтетического) тела ответа.

## Прогон

```
& "$(pipenv --venv)\Scripts\python.exe" -m pytest tests/backend/sources -q --no-header
```

Результат: `69 passed`, 0.26 c. (Папка `tests/backend/sources` шире одного
слайса — в неё входят и другие источники; тестов задачи 5 в файле 23, все
внутри этих 69 зелёные.)

## Догадки о непокрытом

Не входит в список 22 проверенных мутаций и, на мой взгляд, не поймано ни
одним из 23 тестов (см. находки выше как единый список догадок):

- поломка `_poster` / `POSTER_BASE` (`parse.py:45-47`, `148`, `181`) —
  `poster_url` нигде не сверяется;
- поломка чтения `overview` (`parse.py:147`, `180`) — `synopsis` нигде не
  сверяется;
- поломка `original_title` у фильма конкретно (`parse.py:144`) — проверено
  только у сериала;
- подмена `source_id` сериала на чужое значение (`parse.py:174`) — на уровне
  `parse_series` не проверяется напрямую (только опосредованно через клиентский
  тест по `kind`, не по `source_id`).

Это догадки, не заказ на проверку — вносить будет полное ревью после всех
слайсов плана.

## Вердикт

**Готово к слиянию: Да, с правками.** Мутационный список 22/22 пойман, все
тесты содержательны и опираются на записанные фикстуры. Найденные пробелы
(`poster_url`, `synopsis`, `original_title` фильма, `source_id` сериала)
некритичны — это поля, которые не участвуют в бизнес-логике разбора (прямое
копирование строки), но по правилу «какая одна строка её уронит» для них
сегодня ответа нет. Рекомендую добавить 2-4 ассерта в существующие тесты перед
переходом к следующей задаче плана, не блокируя при этом сам коммит слайса.
