# Ревью задачи 12 плана `sources` — повторы во всём проекте

Измерение одно: повторы. Карты (`docs/module-map.md`, `docs/data-map.md`) — из
кода после задачи 12 (`backend/sources/registry.py`, `tests/backend/sources/test_registry.py`).
`docs/not-duplicates.md` прочитан, размеченные там пары не разбирались заново.

Задача — последняя в плане `sources`, поэтому проход шире обычного: все шесть
клиентов и их тесты разом, а не только новый реестр.

## Сильные стороны

- `backend/sources/convert.py` действительно держит общее: `genres`, `year`,
  `companies`, `rating` используются всеми тремя каталожными парсерами
  (`tmdb/parse.py`, `steam/parse.py`, `gog/parse.py`), и ни один не тащит
  копию. Кинопоисковые `_rating`/`_ident` в `ratings/kinopoisk/parse.py` —
  тот же приём внутри одного источника, тоже вынесены правильно.
- `ratings/kinopoisk/mirror.py` не даёт двум зеркалам разойтись в поведении:
  оба зеркала зовут одни `refuse_quota`/`refuse_rate`/`refuse_key`/`answered`.
- `Sources.catalog_for` и `Sources.rating_sources` совпадают только веткой
  `if kind is Kind.GAME` — тела противоположны по смыслу (см. «Разобранные
  пары»), сливать их значило бы затемнить код ради показной экономии трёх
  строк.

## Находки

### Важно

**Помощник «транспорт, который всегда отвечает одним и тем же телом»
скопирован по сути четыре раза под двумя именами.**

- `tests/backend/sources/test_omdb.py:16-17`
  ```python
  def responding(status, body):
      return httpx.MockTransport(lambda request: httpx.Response(status, json=body))
  ```
- `tests/backend/sources/test_tmdb_failures.py:14-15` — то же тело, только с
  аннотациями типов.
- `tests/backend/sources/test_kinopoisk.py:24-27` — то же тело под именем
  `answering`, разбито на несколько строк форматированием.
- `tests/backend/sources/test_mdblist.py:14-18` — надмножество той же идеи:
  `responding(status, *, json=None, text=None, headers=None)` через отдельный
  `handler`, умеет то же самое плюс `text` и `headers`.
- `tests/backend/sources/test_gog.py:13-17` — близкий вариант: та же лямбда
  `httpx.Response(200, json=body)`, но код зашит (200) и результат обёрнут
  сразу в `SourceHttp`, а не отдан голым `MockTransport`.

Все пять читаются как один и тот же кусок, переписанный вручную под каждый
файл — то самое «повтор короче пяти инструкций», который машинный дедуп не
видит, а ревью по повторам обязано ловить руками. Общая форма уже есть — это
`responding` из `test_mdblist.py`, она покрывает все случаи (для gog и
kinopoisk `json=body` подставляется явно, `text`/`headers` не нужны — не
мешают, потому что необязательные).

**Куда выносить:** перенести форму `responding` из `test_mdblist.py` в
`tests/backend/sources/conftest.py` как обычную функцию-помощник (не фикстуру
— она не читает файлы, аргументы приходят из теста, как у `capture()` в
`test_http.py`). После переноса:
- `test_omdb.py`, `test_tmdb_failures.py`, `test_kinopoisk.py` — удалить
  локальную копию, звать `responding(status, json=body)`.
- `test_gog.py` — эта версия дополнительно оборачивает в `SourceHttp` и
  фиксирует код 200; её стоит оставить отдельной маленькой функцией (она
  делает на шаг больше, чем общая), но её тело пусть строит транспорт через
  общий `responding(200, json=body)`, а не через собственную лямбду.

### Мелочь

**Идиома `if not isinstance(response, httpx.Response): return response`
повторена дословно в десяти местах:** `gog/client.py:_catalog`,
`steam/client.py:search`, `steam/client.py:card`, `steam/client.py:_tags`
(там `return ()`, а не `return response`), `tmdb/client.py:search`,
`tmdb/client.py:card`, `ratings/mdblist/client.py:ratings`,
`ratings/omdb/client.py:ratings`, `ratings/kinopoisk/poiskkino.py:ratings`,
`ratings/kinopoisk/unofficial.py:ratings`.

Проверил, стоит ли выносить: сразу после проверки в каждом месте начинается
разная работа — где `_verdict`, где прямой `try/except` над телом, где
собственный статус-код. Обёртка вида `def unwrap(response)` не сократила бы
ни одного места: вызывающему всё равно нужны те же две строки — вызвать
обёртку и проверить результат. Это guard-идиома, а не бизнес-логика; она и
заведена короткой нарочно, ниже порога в пять инструкций из манифеста.
**Вывод — не выносить**, занёс парой представителей в «Разобранные пары»
ниже, чтобы больше не всплывало.

## Разобранные пары

- `backend/sources/registry.py:Sources.catalog_for` ≠
  `backend/sources/registry.py:Sources.rating_sources` — общая только ветка
  `if kind is Kind.GAME`; `catalog_for` для игр отдаёт два магазина,
  `rating_sources` для игр отдаёт пустой список — у игр оценки уже едут с
  карточкой, отдельный агрегатор не нужен. Слитые, потребовали бы параметр
  «что отдавать при GAME», то есть ту же развилку, только спрятанную
- `backend/sources/ratings/mdblist/parse.py:parse_ratings` ≠
  `backend/sources/ratings/omdb/parse.py:parse_ratings` — обе переводят
  список `{source, value}` в `ExternalRating` через словарь `OWNERS`, но
  формы разные по существу: у MDBList `None` — валидное значение и остаётся в
  ответе, у OMDB `_number` разбирает три разных текстовых формата
  (`8.6/10`, `72%`, `74/100`) и результат без числа отбрасывается; вдобавок
  у OMDB отдельная развилка на IMDb-дубль (`imdbRating` вне списка), которой у
  MDBList нет вовсе. Общий вид `for row: owner = OWNERS.get(...)` — это форма
  перевода словаря, а не общий код
- `backend/sources/gog/client.py:GogClient._catalog` ≠
  `backend/sources/steam/client.py:SteamClient.search` — обе начинаются с
  `if not isinstance(response, httpx.Response): return response`, но это
  guard-идиома в две строки, а не общая логика: сразу после неё пути
  расходятся (GOG проверяет код и парсит каталог, Steam уходит в тот же
  паттерн ещё дважды на своих запросах). Заведение общей обёртки не сократило
  бы вызывающий код — тот же двухстрочный guard остался бы на месте вызова
- `backend/sources/ratings/mdblist/client.py:MdbListClient.ratings` ≠
  `backend/sources/ratings/omdb/client.py:OmdbClient.ratings` — тот же
  guard-идиома в начале; дальше MDBList классифицирует по коду ответа через
  `_verdict`, а OMDB сперва обязан разобрать JSON и проверить, что это
  словарь, прежде чем смотреть на код — это два разных контракта отказа
  (см. существующую пару в `not-duplicates.md` про `refuse_undocumented` ≠
  `classify`)

## Вердикт

**С правками.** Один настоящий повтор — helper `responding`/`answering` в
четырёх тестовых файлах источников — стоит вынести до коммита: он уже сейчас
разошёлся бы при следующей правке одного из четырёх копий незаметно для
остальных трёх. Остальное осмотренное (каталожные парсеры на фоне
`convert.py`, три оценочных разбора, `catalog_for` против `rating_sources`,
guard-идиома `isinstance` в клиентах) — либо уже правильно вынесено, либо
похоже только по форме и разбирается разной логикой сразу за местом
совпадения.
