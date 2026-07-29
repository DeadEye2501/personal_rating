# Ревью задачи 8 плана `sources`: повторы во всём проекте

Измерение: повторы. Дифф не читался — разбор шёл от `docs/module-map.md` и
`docs/data-map.md` против всего кода источников, с подтверждением каждого
кандидата чтением обоих мест.

## Сильные стороны

- Вынос в `backend/sources/convert.py` (`genres`, `year`, `companies`,
  `rating`) сделан по делу: все три разбора (`tmdb/parse.py`, `steam/parse.py`,
  `gog/parse.py`) действительно вызывают одни и те же функции, а не завели
  рядом похожие копии. `_companies` из `steam/parse.py` и `_year` из
  `tmdb/parse.py` в коде больше не встречаются — вынесены до конца, хвостов не
  осталось.
- Оставшиеся тонкие обёртки на местах (`tmdb/parse.py:_genres`,
  `tmdb/parse.py:_own_rating`, `steam/parse.py:_metascore`, `gog/parse.py:_marks`)
  не дублируют друг друга: у каждой свой источник данных внутри чужого ответа
  (вложенный `metacritic.score` у Steam, два разных пространства `genres`/`tags`
  одним слагом у GOG), и это ровно та специфика, ради которой их не слили в
  `convert.py`.
- `gog/parse.py:to_hit` не повторяет существующего превращения карточки в
  кандидата — в `tmdb/parse.py` и `steam/parse.py` `SearchHit` собирается прямо
  из сырого ответа поиска, а не из уже построенного `SourceCard`. У GOG иначе
  просто нет отдельной поисковой ручки, и `to_hit` — единственное место, где
  такое преобразование вообще требуется.
- Различие `year` (в `convert.py`) и `steam/parse.py:_year` осталось
  обоснованным и после выноса: первая режет по префиксу дату вида
  `2014-11-05`/`2023.08.03`, вторая regex’ом вытаскивает год из
  человеческого текста вроде «26 Nov, 2015» — слить их значило бы протащить
  regex туда, где он не нужен.

## Находки

### Важно

**`backend/sources/steam/client.py:SteamClient._fail` (строки 48–58) и
`backend/sources/gog/client.py:GogClient._catalog` (строки 45–53, внутри
20-строчного метода 39–58) — один и тот же перевод HTTP-кода в `Refusal`.**

Steam:
```python
def _fail(self, response: httpx.Response) -> Refusal:
    if response.status_code == 429:
        self._http.breaker.trip(RATE_BACKOFF, Reason.RATE)
        return Refusal(source="steam", reason=Reason.RATE, retry_after=RATE_BACKOFF)
    return Refusal(source="steam", reason=Reason.BROKEN, detail=f"HTTP {response.status_code}")
```

GOG (внутри `_catalog`):
```python
if response.status_code == 429:
    self._http.breaker.trip(RATE_BACKOFF, Reason.RATE)
    return Refusal(source="gog", reason=Reason.RATE, retry_after=RATE_BACKOFF)
if response.status_code != 200:
    return Refusal(source="gog", reason=Reason.BROKEN, detail=f"HTTP {response.status_code}")
```

Логика посимвольно одна: 429 — взвести предохранитель и вернуть `RATE` с тем же
`retry_after`, иначе — `BROKEN` с тем же `detail=f"HTTP {code}"`. Это не то же
сравнение, что уже разобрано в `docs/not-duplicates.md` (там `SteamClient._fail`
сравнивается с `TmdbClient.classify`, и отличие законно: у TMDB пять кодов и
свой `Missing`). Здесь третьей стороны с богатой классификацией нет — GOG такой
же простой двухветочный случай, как Steam.

К этому же плюсуется константа: `backend/sources/steam/client.py:38` и
`backend/sources/gog/client.py:25` — оба `RATE_BACKOFF = timedelta(minutes=5)`,
и обоснование в комментариях у обоих одно и то же по сути: лимиты
недокументированы, откат — своя оценка наугад («Документации у Steam нет
вовсе... Откат свой» / «Лимиты у GOG не документированы вовсе — откат свой»).
Это отличается от `TmdbClient.RATE_BACKOFF` (1 минута, выведена из реальной
политики `Retry-After`), поэтому TMDB трогать не нужно — уже разведено в
`not-duplicates.md`, довод верный и держится.

**Что должно остаться.** Общий перевод «код ответа → `Refusal`, 429 триплит
предохранитель» стоит вынести один раз — например, функцией в
`backend/sources/http.py` рядом с `Breaker` (она уже держит и `Breaker`, и
`Refusal`, и обе стороны её и так импортируют):

```python
def classify_undocumented(
    source: str, response: httpx.Response, breaker: Breaker, backoff: timedelta
) -> Refusal:
    if response.status_code == 429:
        breaker.trip(backoff, Reason.RATE)
        return Refusal(source=source, reason=Reason.RATE, retry_after=backoff)
    return Refusal(source=source, reason=Reason.BROKEN, detail=f"HTTP {response.status_code}")
```

`SteamClient._fail` заменяется вызовом; `GogClient._catalog` зовёт её вместо
своих двух `if`. Общий откат в 5 минут («недокументировано, гадаем») тоже можно
поднять одной константой рядом (например, `UNDOCUMENTED_BACKOFF`) и передавать
её из обоих клиентов — `TmdbClient.RATE_BACKOFF` остаётся своим и отдельным,
как и было решено раньше.

### Мелочь

Не найдено — то, что не подтянулось под «важно», либо уже разведено в
`not-duplicates.md`, либо не подтвердилось чтением (см. ниже).

## Разобранные пары

- `backend/sources/gog/client.py:GogClient._catalog` ≠ `backend/sources/tmdb/client.py:TmdbClient._verdict`/`classify` — тот же довод, что уже записан для Steam против TMDB: у TMDB пять веток и отдельный `Missing` по разобранному телу (`_ABSENT`, коды 401/404), у GOG — только 429 и «не 200». Слитые, они потребовали бы тащить в GOG код для веток, которых у него никогда не будет
- `backend/sources/gog/parse.py:to_hit` ≠ `backend/sources/tmdb/parse.py:parse_search` / `backend/sources/steam/parse.py:parse_search` — оба TMDB и Steam строят `SearchHit` прямо из сырого ответа поисковой ручки; `to_hit` строит его из уже собранного `SourceCard`, потому что у GOG поиск и карточка — один и тот же ответ каталога. Предмет разный: сырой ответ против готовой карточки

## Вердикт

**С правками.** Вынос общего в `convert.py` сделан аккуратно и без хвостов —
это ревью подтверждает целиком. Но у третьей реализации клиента (GOG) не
вынесен общий с двумя другими случай «недокументированный лимит →
`Refusal`»: `SteamClient._fail` и логика внутри `GogClient._catalog` (строки
45–53) совпадают дословно, вместе с константой отката `RATE_BACKOFF = 5 минут`
и её обоснованием. По правилу 7 (абстракция появляется со второй реализацией)
это тот самый момент — стоит вынести общую функцию (например,
`classify_undocumented` в `backend/sources/http.py`) до коммита задачи 8.
