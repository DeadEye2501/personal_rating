# Ревью тестов — план 2, задача 9 (клиент MDBList)

Измерение: тесты слайса. Только чтение, без мутаций.

## Сильные стороны

- Разбор (`parse.py`) и сеть (`client.py`) тестируются раздельно: разбор — на
  словарях и на настоящем `found.json` с мусорными владельцами
  (`metacriticuser`, `trakt`, `popcorn`, `letterboxd`, `rogerebert`,
  `myanimelist`), сеть — на кодах ответа и заголовках.
- Адрес (`test_modern_endpoint_is_used`) и запасной срок квоты
  (`test_quota_without_a_named_delay_falls_back_to_an_hour`) сверяются с
  буквальными строкой/значением в тесте, а не с константами `BASE` /
  `QUOTA_FALLBACK` из `client.py` — сверка не переезжает вместе с кодом.
- `test_recorded_quota_is_a_refusal_with_the_named_delay` берёт ожидаемый срок
  из заголовка самой фикстуры (`info["headers"]["retry-after"]`), а не
  дублирует число `900` в теле теста и не сверяется с `QUOTA_FALLBACK` — при
  этом заголовок (900 с = 15 мин) явно отличается от запасного часа, так что
  тест не может случайно пройти на резервном пути.
- Фикстуры `found`, `quota`, `bad_key`, `no_key`, `cloudflare_403` действительно
  читаются из файлов (`fixture()` / `replay()` из `conftest.py`), тела и коды
  разведены по разным файлам, `replay` подставляет код и заголовки из
  `*.meta.json`, а не сочиняет их в тесте.
- Различение «чужой периметр vs битый ключ» проверено на реальной паре тел:
  `error code: 1010` (не JSON) против `{"error": "Invalid API key"}` (JSON) —
  ровно то различие, на которое опирается `_denied`.
- Отдельная реализация breaker (heal после срока) — не в этом слайсе, честно
  вынесена и покрыта в `tests/backend/sources/test_http.py`
  (`test_tripped_breaker_opens_and_then_heals` и рядом); дублировать её здесь
  не нужно.

## Находки

Критичных и важных не нашёл. Мелочи:

- **Мелочь.** `tests/backend/sources/test_mdblist.py:164-170`
  (`test_a_request_without_a_key_is_the_same_refusal`) проходит по тому же коду
  клиента (`client.py:76-91`, ветка `_denied` → JSON без 401/403-специфики), что
  и `test_recorded_bad_key_is_a_refusal`, и не читает `meta("mdblist/no_key.json")`
  сам — полагается, что фикстура действительно 401 (это так, я проверил файл
  руками). Тест не различает «нет ключа» и «битый ключ» на уровне кода — они и
  правда неразличимы для MDBList, так что это осознанно, а не дыра, но факт
  проверки «этот же файл — 401» нигде не заявлен в самом тесте.

## Прогон

```
& "$(pipenv --venv)\Scripts\python.exe" -m pytest tests/backend/sources -q --no-header
```

Результат: `151 passed in 1.04s`. Один прогон, без сети (все ответы —
`MockTransport`/`replay`).

## По каждому тесту: что наблюдает / что его уронит

1. `test_ratings_are_split_by_owner` — множество `source` в `Ratings.values`
   равно всем четырём заведённым владельцам на реальном `found.json` (там же
   есть мусорные `trakt`, `popcorn`, `letterboxd` и т.д.). Уронит правку
   `parse.py:10-14` (например, удалить `"tomatoes": RatingSource.ROTTEN`) или
   `parse.py:22` (перестать отбрасывать неизвестных).
2. `test_each_owner_keeps_its_own_scale` — конкретные значения 8.7 / 74 / 73 не
   приведены к общей шкале. Уронит `parse.py:31`, если туда добавить нормировку
   (например, `value / 10` для стобалльных).
3. `test_null_score_is_reported_as_an_empty_value` — `null` пишется как
   `None`, а не выбрасывается. Уронит `parse.py:25-34`, если строку с
   `value is None` пропускать (`continue`) вместо добавления записи.
4. `test_unknown_owner_is_ignored` — неизвестный `source` не создаёт запись.
   Уронит `parse.py:22-24`, если убрать `continue` на `owner is None`.
5. `test_modern_endpoint_is_used` — в URL актуальный адрес и `apikey=k`, легаси
   `mdblist.com/api` отсутствует. Уронит `client.py:25` (смена `BASE`) или
   `client.py:43` (потеря `params`).
6. `test_series_go_to_the_show_path` — сериал идёт по `/show/`. Уронит
   `client.py:41` (например, свести оба случая к `"movie"`).
7. `test_movies_go_to_the_movie_path` — фильм идёт по `/movie/{id}`. Уронит
   тот же `client.py:41` или `client.py:42-44`.
8. `test_recorded_quota_is_a_refusal_with_the_named_delay` — срок отказа берётся
   из заголовка фикстуры (900 с), а не из запасного часа. Уронит `client.py:67`
   (`_retry_after(response) or QUOTA_FALLBACK`), если поменять на
   `QUOTA_FALLBACK or _retry_after(...)` или просто игнорировать заголовок.
9. `test_quota_without_a_named_delay_falls_back_to_an_hour` — без заголовка срок
   — час. Уронит `client.py:27` (значение `QUOTA_FALLBACK`).
10. `test_quota_trips_the_breaker` — второй запрос не уходит в сеть
    (`calls == 1`). Уронит `client.py:68` (пропуск `self._http.breaker.trip(...)`)
    или `http.py:76` (пропуск проверки `is_open()`).
11. `test_recorded_bad_key_is_a_refusal` — 401 с JSON-телом → `Reason.KEY`.
    Уронит `client.py:89-91` (например, вернуть `Reason.NETWORK`).
12. `test_a_request_without_a_key_is_the_same_refusal` — тот же путь, другая
    фикстура. Уронит тот же `client.py:89-91`.
13. `test_cloudflare_wall_is_not_a_key_problem` — 403 с не-JSON телом →
    `Reason.NETWORK`. Уронит `client.py:80-88` (например, убрать `try/except
    ValueError` и всегда падать в ветку `KEY`).
14. `test_missing_object_is_an_answer` — 404 → `Missing`. Уронит `client.py:57-58`.
15. `test_cache_building_is_a_retry_not_an_absence` — 202 + `Retry-After: 5` →
    `Refusal(RATE, 5с)`. Уронит `client.py:59-65`.
16. `test_server_error_is_a_refusal` — 500 → `Refusal(BROKEN)`. Уронит
    `client.py:72-74`.
17. `test_unexpected_shape_does_not_crash` — `ratings` строкой вместо списка →
    `Refusal(BROKEN)`, без падения процесса. Уронит `client.py:52-56` (например,
    убрать `try/except BROKEN_BY_PARSING`) или `errors.py:45`, если сузить
    кортеж исключений и потерять `AttributeError`.
18. `test_recorded_found_ratings_come_back` — сквозной путь: `replay` реального
    200-ответа даёт `Found` с непустыми `values`. Уронит любой из шагов 200-ветки
    (`client.py:51-56`, `parse.py:18-35`) сразу — это интеграционная страховка
    поверх модульных тестов 1-4.

## Догадки о непокрытом (не заказ на проверку)

- `_retry_after` (`client.py:30-32`) требует `raw.isdigit()`. Нецелый или
  отрицательный `Retry-After` (например, `"5.5"` или `"-1"`) во всех фикстурах
  и inline-ответах отсутствует — мутация, ослабляющая эту проверку (скажем,
  `raw.isdigit()` → `raw` без проверки, с падением на `int("5.5")`), скорее
  всего не поймается ни одним из 18 тестов, эта ветка просто не исполняется.
- Заголовок `Retry-After` матчится по имени `"Retry-After"` с заглавной буквы
  (`client.py:31`), тогда как `responding()`-хелпер в некоторых тестах передаёт
  `headers={"Retry-After": ...}`, а `replay` — заголовок `retry-after` в нижнем
  регистре из `*.meta.json`. Оба регистра фактически прогнаны (httpx сам
  нормализует регистр заголовков), так что это не дыра, а просто неочевидно на
  первый взгляд — упоминаю, чтобы не тратить на это время при следующем ревью.

## Вердикт

**Да.** Прогон зелёный (151 passed), все 18 тестов слайса привязаны к
конкретной строке кода и падают при её поломке, фикстуры читаются из файлов
без подмешивания сочинённых данных, а сверка с константой из тестируемого
модуля (антипаттерн из задания) нигде не встречается — оба места, где могло
быть искушение, сверяются с буквальными значениями или значением из фикстуры.
