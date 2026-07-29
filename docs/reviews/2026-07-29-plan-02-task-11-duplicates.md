# Ревью повторов — план 2, задача 11 (Кинопоиск)

Измерение: повторы во всём проекте. Дифф не читался — разбор идёт по
`docs/module-map.md`, `docs/data-map.md` и живому коду источников оценок.

## Сильные стороны

- `_rating` и `_ident` в `backend/sources/ratings/kinopoisk/parse.py` уже
  вынесены и переиспользуются обоими `parse_poiskkino`/`parse_unofficial` —
  ровно то место, где общее стоило вынести, и это сделано.
- `backend/sources/ratings/kinopoisk/limits.py` централизует `QUOTA_BACKOFF` и
  `RATE_BACKOFF` для обоих зеркал — константы не разъехались по файлам.
- Разные HTTP-коды у зеркал (404/403/401/429 против 402/429/401) оставлены
  раздельно в каждом `_verdict`, а не сведены в одну таблицу «код → причина» —
  это верно: код триггера у зеркал разный и совмещать его нельзя (тот же
  довод, что уже записан для `refuse_undocumented` ≠ `classify`).
- `KinopoiskClient.ratings` не дублирует логику зеркал — только
  последовательный вызов и решение, когда переключаться.

## Находки

### Важно

**1. `PoiskkinoClient._answer` и хвост `UnofficialClient._verdict` — один и тот
же блок «разобрать безопасно → пусто целиком = Missing» дословно.**

- `backend/sources/ratings/kinopoisk/poiskkino.py:90-102` (`_answer`):
  ```python
  try:
      answer = parse_poiskkino(response.json())
  except BROKEN_BY_PARSING as error:
      logger.warning("poiskkino: ответ не разобрался — %s", error)
      return broken("kinopoisk", error)
  if not answer.values and not answer.external_ids:
      return Missing()
  return Found(answer)
  ```
- `backend/sources/ratings/kinopoisk/unofficial.py:63-71` (хвост `_verdict`):
  ```python
  try:
      answer = parse_unofficial(response.json())
  except BROKEN_BY_PARSING as error:
      logger.warning("kinopoisk unofficial: ответ не разобрался — %s", error)
      return broken("kinopoisk", error)
  if not answer.values and not answer.external_ids:
      return Missing()
  return Found(answer)
  ```
  Отличаются только вызываемая функция разбора и текст в `logger.warning` —
  восемь строк повторены целиком. Это тот самый случай из задания: у трёх
  оценочных клиентов «пусто → Missing» на деле общее не для всех троих. У
  MDBList `Found` возвращается сразу по коду `200`, без проверки на пустоту
  (`backend/sources/ratings/mdblist/client.py:51-56`), у OMDB `Missing`
  решается по явному `payload.get("Response") == "False"`
  (`backend/sources/ratings/omdb/client.py:73-74`), а не по пустоте
  разобранного. Проверка «раз `values` и `external_ids` пустые — это Missing»
  нужна только Кинопоиску, потому что у обоих его зеркал успешный код не
  гарантирует непустой результат — и она продублирована ровно между двумя
  зеркалами, не шире.

  **Что оставить:** вынести общую часть в `parse.py` (он и так уже
  импортируется обоими файлами) — например `def outcome(name, parse, payload)
  -> Outcome`, оборачивающую try/except и проверку пустоты, и звать её из
  обоих `ratings()`. `_absent` (404 у poiskkino) остаётся на месте — у
  unofficial аналога нет и быть не должно.

**2. Тела веток `QUOTA`/`RATE`/`KEY`/фолбэк `BROKEN` в обоих `_verdict`
совпадают дословно — различаются только код-триггер и комментарий.**

- `poiskkino.py:51-72`:
  ```python
  if status == 403:
      self._http.breaker.trip(QUOTA_BACKOFF)
      return Refusal(source="kinopoisk", reason=Reason.QUOTA, retry_after=QUOTA_BACKOFF)
  if status == 401:
      return Refusal(source="kinopoisk", reason=Reason.KEY)
  if status == 429:
      self._http.breaker.trip(RATE_BACKOFF, Reason.RATE)
      return Refusal(source="kinopoisk", reason=Reason.RATE, retry_after=RATE_BACKOFF)
  if status != 200:
      return Refusal(source="kinopoisk", reason=Reason.BROKEN, detail=f"HTTP {status}")
  ```
- `unofficial.py:45-61` — те же четыре действия под кодами 402/401/429/иначе,
  тело каждого действия побайтно совпадает (кроме комментариев).

  Здесь важно не путать с уже разобранным `refuse_undocumented` ≠ `classify`:
  там смешение потребовало бы таблицы «код → причина» на источник, потому что
  у каждого источника свой набор кодов *и* свои причины. Тут набор причин один
  и тот же (`QUOTA`/`RATE`/`KEY`/`BROKEN`), с одними и теми же константами
  (`limits.py`) и одной и той же строкой `source="kinopoisk"` — разнится
  только код-триггер, который и должен остаться в каждом `_verdict` отдельно.
  Само конструирование `Refusal` дублировать незачем.

  **Что оставить:** дословный код-триггер (`if status == 403` /
  `if status == 402` и т.д.) — в каждом файле свой, это домен зеркала. Тела
  действий — вынести в `limits.py` как `quota_refusal(http) -> Refusal`,
  `rate_refusal(http) -> Refusal`, и, при желании, обе однострочные ветки
  `KEY`/`BROKEN` тоже в мелкие функции. Тогда `_verdict` каждого зеркала
  сведётся к диспетчеру по своим кодам, зовущему общие конструкторы.

### Мелочь

Try/except `BROKEN_BY_PARSING` → `logger.warning(...)` → `return
broken(source, error)` — форма, которая теперь встречается в семи местах
(`tmdb/client.py`, `gog/client.py`, `steam/client.py` ×3, `omdb/client.py`,
`mdblist/client.py`, и оба зеркала Кинопоиска). Не отношу это к находкам
задачи 11: паттерн уже существовал в TMDB/GOG/Steam до неё, и решение оставить
логирование на месте вызова задокументировано в самой `broken()`
(`backend/sources/errors.py:48-51`: «Запись в лог остаётся на месте вызова:
сообщение у каждого своё, и по нему потом ищут причину»). Общий фрагмент —
только `return broken(source, error)`, а он уже вынесен. Дальше выносить
незачем: пришлось бы либо тащить текст сообщения параметром (что уже частично
сделано находкой №1 выше для двух зеркал), либо разбивать try/except ради двух
строк.

## Разобранные пары

- `backend/sources/ratings/kinopoisk/poiskkino.py:PoiskkinoClient._verdict` ≠ `backend/sources/ratings/kinopoisk/unofficial.py:UnofficialClient._verdict` — как функции целиком не сливаются: код-триггеры разные (404/403/401/429 против 402/429/401), и порядок веток разный. Дублируются только тела действий внутри (см. находку 2), не диспетчер
- `backend/sources/ratings/kinopoisk/poiskkino.py:PoiskkinoClient._absent` ≠ ничего в `unofficial.py` — у запасного зеркала нет проблемы «404 без тела от Envoy», аналога нет и не нужен
- `backend/sources/ratings/mdblist/client.py:MdbListClient._verdict` ≠ `backend/sources/ratings/kinopoisk/poiskkino.py:PoiskkinoClient._verdict` / `unofficial.py:UnofficialClient._verdict` — разная стратегия определения «не найдено»: явный код 404 у MDBList против пустоты разобранного тела у обоих зеркал Кинопоиска; коды и структура ответа тоже не пересекаются
- `backend/sources/ratings/omdb/client.py:OmdbClient._answer` / `_denied` ≠ `backend/sources/ratings/kinopoisk/poiskkino.py:PoiskkinoClient._verdict` / `unofficial.py:UnofficialClient._verdict` — у OMDB «не найдено» решается полем `Response` в теле под кодом 200, а не пустотой распарсенного; разбор текста ошибки в `_denied` (`limit`/`key` в строке) аналога в Кинопоиске не имеет вовсе
- `backend/sources/ratings/*/client.py` (try/except `BROKEN_BY_PARSING`, все шесть клиентов) ≠ друг друга — общий фрагмент уже вынесен в `broken()`; оставшееся — задокументированное решение хранить текст лога на месте вызова, не повтор ради разбора

## Вердикт

**С правками.** Ничего не ломает поведение и не путает домены зеркал —
код-триггеры (разные статусы) оставлены раздельно верно. Но между
`PoiskkinoClient` и `UnofficialClient` продублированы дословно: (1) блок
«разобрать → пусто = Missing, иначе Found» (~8 строк, находка 1) и (2) тела
веток `Refusal` для `QUOTA`/`RATE`/`KEY`/`BROKEN` (~13 строк, находка 2). Оба
случая — уже вторая реализация одного и того же зеркала, ровно тот момент,
когда по правилам проекта абстракция должна появиться. До коммита стоит
вынести оба блока в `parse.py` и `limits.py` соответственно.
