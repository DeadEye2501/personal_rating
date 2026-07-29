# Ревью повторов — план 2, задача 7 (клиент Steam)

Измерение: повторы во всём проекте, не только в диффе задачи 7.

## Сильные стороны

- Второй источник переиспользует общий транспорт целиком: `SteamClient` и
  `TmdbClient` оба построены поверх одного `SourceHttp`/`Breaker`
  (`backend/sources/http.py`) и общей таксономии исходов
  (`Found`/`Missing`/`Refusal` из `backend/sources/errors.py`), а не заводят
  свои варианты успеха/отказа.
- `RATE_BACKOFF` у обоих клиентов — разные значения (5 минут у Steam, 1 минута
  у TMDB), и это осознанно прокомментировано на месте, а не забытая
  рассинхронизация: совпадение имени по модулям — конвенция, не повод сливать.
- Docstring'и объясняют именно неочевидное («теги живут отдельно от карточки»,
  «country_code: RU отдаёт пустой ответ»), а не пересказывают код.

## Находки

### Важно

1. **`_BROKEN` (`backend/sources/steam/client.py:32`) и `BROKEN_BY_PARSING`
   (`backend/sources/tmdb/client.py:23`) — буквально одна и та же константа.**
   Оба объявлены как `(ValueError, TypeError, KeyError, AttributeError)` и
   используются с одной целью — поймать поломку разбора ответа
   (`response.json()`/доступ по ключу) и превратить её в
   `Refusal(reason=Reason.BROKEN)`. Значение совпадает дословно, второй
   источник — ровно тот момент по правилу 7, чтобы вынести общую константу
   (например, `PARSING_ERRORS` в `backend/sources/errors.py`), а не заводить
   третью копию под GOG.

2. **Извлечение id жанров: `backend/sources/tmdb/parse.py:_genres` (50-54)
   против встроенного генератора в `backend/sources/steam/parse.py:parse_card`
   (94-96).**
   ```python
   # tmdb/parse.py:_genres
   tuple((GenreSource.TMDB, str(genre["id"])) for genre in payload.get("genres", []))

   # steam/parse.py:parse_card, инлайн
   tuple((GenreSource.STEAM, str(genre["id"])) for genre in data.get("genres", []))
   ```
   Форма совпадает вплоть до имени ключа `"id"` и умолчания `[]`, отличается
   только источник-константа. TMDB уже вынес это в именованную функцию, Steam —
   нет. Стоит завести общий помощник (`def genre_ids(source: GenreSource,
   payload: dict) -> tuple[tuple[GenreSource, str], ...]`) и звать его из
   обоих `parse.py`, оставив специфичным для Steam только `parse_tags`, где
   ключ другой (`tagid`) и структура ответа вложенная.

3. **Обёртка внешней оценки в `ExternalRating`: `backend/sources/tmdb/parse.py:
   _own_rating` (57-63) против `backend/sources/steam/parse.py:_metascore`
   (65-74).** Отличается только извлечение сырого значения (`vote_average` по
   плоскому ключу против `metacritic.score` по вложенному) и то, какой
   `RatingSource` проставляется. Обвязка идентична: `if value is None: return
   ()`, иначе кортеж из одного `ExternalRating(source=..., value=float(value),
   fetched_at=now)`. Второй источник — повод вынести общий `def rating(source:
   RatingSource, value: float | None, now: datetime) -> tuple[ExternalRating,
   ...]`, и оба `parse.py` сведутся к передаче своего способа достать `value`.

### Мелочь

4. **Лог + `Refusal(BROKEN)` на исключении разбора повторяется четыре раза**:
   `steam/client.py:search` (66-68), `steam/client.py:card` (98-100),
   `tmdb/client.py:search` (88-90), `tmdb/client.py:card` (107-109). Везде одна
   форма — `logger.warning("<source>: <что> не разобралась — %s", error)` и
   `return Refusal(source="<source>", reason=Reason.BROKEN, detail=str(error))`.
   Ниже приоритетом находок 1-3, потому что тела `try` вокруг этого места
   разной сложности (у Steam в `card` в `try` ещё живёт проверка `success` и
   `Missing()`, у TMDB `try` — голый вызов `parse(...)`), так что обернуть
   весь `try/except` одним хелпером не выйдет без потери читаемости. Годится
   вынести именно хвост — помощник вида `def parse_failed(source: str, what:
   str, error: Exception) -> Refusal`, чтобы не копировать форматную строку и
   сборку `Refusal` в четвёртый раз, когда появится GOG.

## Разобранные пары

- `backend/sources/steam/parse.py:_year` ≠ `backend/sources/tmdb/parse.py:_year`
  — одно имя и одна сигнатура, но разные гарантии входа: TMDB отдаёт дату
  всегда как ISO `YYYY-MM-DD` либо пустую строку, поэтому взять первые четыре
  символа безопасно и не теряет фильмы до 1900 года, которые в TMDB есть.
  Steam отдаёт дату человеком написанным текстом на языке запроса («18 мая.
  2015 г.», «Coming soon»), и там наивный префикс сломался бы, поэтому регэксп
  нарочно ищет `19|20` где угодно в строке. Слияние в любую сторону меняет
  поведение: регэксп молча теряет доTMDB-шные 1890-е, префиксный разбор ловит
  случайные четыре цифры в свободном тексте Steam. Разное по существу.
- `backend/sources/steam/parse.py:poster_url` ≠ `backend/sources/tmdb/parse.py:_poster`
  — разный контракт: `poster_url` детерминированно строит адрес ассета из
  голого `appid` (у Steam в ответе нет `poster_path` вовсе), `_poster` читает
  и охраняет необязательное поле `poster_path` в payload, возвращая `""` при
  отсутствии. Разные сигнатуры (`str -> str` против `dict -> str`), и
  `poster_url` экспортируется и переиспользуется в `parse_search` и
  `parse_card` внутри своего модуля, а `_poster` остаётся частным. Не повтор.
- `backend/sources/steam/parse.py:parse_search` ≠ `backend/sources/tmdb/parse.py:parse_search`
  — тот же случай, что уже записан для `TmdbClient.search` ≠ `parse_search`:
  общий глагол «собери выдачу поиска» над разными предметами. Steam получает
  голый список без `kind` (Steam — только игры, жанров в поиске нет вовсе),
  TMDB — словарь с `results` и переключением имён полей по `kind is
  Kind.SERIES`. Форма несовместима, а не просто раздельно реализована.
- `backend/sources/steam/client.py:SteamClient._fail` ≠
  `backend/sources/tmdb/client.py:classify`/`TmdbClient._verdict` — `_fail`
  вызывается только когда статус уже не 200 (это проверил вызывающий), и
  никогда не возвращает `Missing`: у Steam «такой игры нет» приходит внутри
  200 через `success: false` в теле, а не через код ответа. `classify` —
  чистая функция на все статусы разом (200/404/429/401/иное), включая ветку
  `Missing`, ключуемую разобранным `status_code`; она нарочно без побочных
  эффектов, чтобы предохранитель дёргал только `_verdict`-обёртка (это explicit
  в её докстринге). Совпадает только исход на 429 — `Refusal(RATE,
  retry_after=BACKOFF)` плюс `breaker.trip`, — но слияние этого фрагмента
  потребовало бы либо испортить чистоту `classify` побочным эффектом, либо
  городить третий слой ради трёх строк. Текущее разделение — решение, а не
  случайное совпадение.
- `backend/sources/steam/client.py:RATE_BACKOFF` ≠
  `backend/sources/tmdb/client.py:RATE_BACKOFF` — одно имя по модульной
  конвенции, разные значения, подобранные под каждый источник и
  прокомментированные на месте (5 минут против 1 минуты). Делить нечего.

## Вердикт

**С правками.** Структурных проблем и блокеров нет — новый код Steam-клиента
корректно переиспользует общий транспорт и таксономию отказов. Но нашлись три
подтверждённых повтора между `steam/` и `tmdb/` (константа исключений разбора,
сборка id жанров, обёртка внешней оценки), которые машинная проверка не видит
именно потому, что они короче порога и лежат в разных файлах — ровно то, что
манифест просит ловить ревью повторов. Второй источник — правильный момент
вынести их по правилу 7, до того как появится третий (GOG) и повторит снова.
