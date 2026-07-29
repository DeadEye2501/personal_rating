# Ревью повторов — план 2, задача 10 (OMDB)

Измерение: повторы во всём проекте. Дифф не читался — источник разбора:
`docs/module-map.md`, `docs/data-map.md`, `docs/not-duplicates.md`, затем чтение
кода по обеим сторонам каждого кандидата.

## Сильные стороны

- Второй оценочный источник построен по тому же контракту, что и первый:
  `ratings(imdb_id, kind) -> Outcome`, `parse_ratings(payload) -> Ratings`,
  `OWNERS` как единственная точка, где чужой ярлык переводится в
  `RatingSource`. Это не повтор, а последовательное соблюдение уже устоявшейся
  формы — ровно то, что должно совпадать между источниками одного рода.
- Различия там, где они содержательны, не спрятаны: `_denied` у OMDB читает
  текст уже распарсенного JSON, у MDBList — присутствие JSON вообще, и оба
  комментария объясняют, почему код 401/403 сам по себе ничего не говорит.
- Семантика `null` в оценке не смешана: MDBList явно хранит `None` как «спросили
  и не оказалось», OMDB отбрасывает строку целиком, потому что вопрос
  «спрашивали ли Rotten Tomatoes» у него не встаёт — оценка либо есть в списке,
  либо нет.

## Находки

Критично: нет.
Важно: нет.
Мелочь: нет.

Все шесть кандидатов из задания проверены чтением обоих мест целиком
(`backend/sources/ratings/omdb/parse.py`, `backend/sources/ratings/omdb/client.py`,
`backend/sources/ratings/mdblist/parse.py`, `backend/sources/ratings/mdblist/client.py`,
`backend/sources/http.py`) — ни один не подтвердился как код, который нужно
вынести в общее. Обоснование по каждому — в разобранных парах ниже.

## Разобранные пары

- `backend/sources/ratings/omdb/parse.py:parse_ratings` ≠ `backend/sources/ratings/mdblist/parse.py:parse_ratings` — общий каркас («перебрать строки, найти владельца в `OWNERS`, собрать `ExternalRating`, обернуть в `Ratings`») в 3–4 строки, но поведение внутри него не совпадает по смыслу: MDBList обязан сохранить `value=None` как факт «спросили — нет оценки», OMDB обязан пропустить строку целиком при нераспознанном значении и вдобавок держит `seen` для дедупликации против отдельного поля `imdbRating`. Общая функция получила бы четвёртым параметром флаг «выбрасывать ли None», то есть управляющий аргумент вместо общего поведения — именно то, чего манифест просит избегать
- `backend/sources/ratings/omdb/parse.py:OWNERS` ≠ `backend/sources/ratings/mdblist/parse.py:OWNERS` — совпадает только имя и форма (`dict[str, RatingSource]`), это имя по уговору для «таблицы перевода чужого ярлыка», а не общий код: три и четыре записи не пересекаются ни одним ключом (`"Internet Movie Database"` против `"imdb"`, `"Rotten Tomatoes"` против `"tomatoes"`), и набор значений `RatingSource` тоже разный — у MDBList есть `TMDB`, которого OMDB не отдаёт вовсе
- `backend/sources/ratings/omdb/parse.py:_number` ≠ ничего в проекте — искал среди существующих переводов чужого значения в число: `backend/sources/convert.py:year` и `backend/sources/steam/parse.py:_year` берут из строки год (первые четыре цифры / поиск по regex) — другая задача с другими правилами. `mdblist/parse.py` вызывает голый `float(value)` инлайном, отдельной функции для этого там нет. Второй реализации у `_number` в проекте нет — выносить преждевременно
- `backend/sources/ratings/omdb/client.py:OmdbClient._denied` ≠ `backend/sources/ratings/mdblist/client.py:MdbListClient._denied` — разные сигнатуры (`payload: dict` против `response: httpx.Response`) и разная логика классификации: OMDB ищет подстроку `"limit"`/`"key"` в уже распарсенном тексте ошибки, MDBList проверяет, разбирается ли тело вообще как JSON, чтобы отличить отказ по ключу от блокировки Cloudflare на 403. Тот же вид сравнения, что уже записан для `refuse_undocumented` ≠ `classify`: общий повод («код 401/403 сам по себе не говорит, в чём дело»), разные основания решения
- `backend/sources/ratings/omdb/client.py:OmdbClient.ratings` ≠ `backend/sources/ratings/mdblist/client.py:MdbListClient.ratings` — оба вызывают `SourceHttp.get` и классифицируют результат, но это уже общее — оно вынесено в `SourceHttp`. Дальше пути расходятся: OMDB обязан распарсить JSON заранее, потому что текст ошибки нужен уже при коде 401; MDBList часть кодов (`202`, `429`, `404`) разбирает без обращения к телу вовсе и вдобавок взводит `Breaker` через заголовок `Retry-After`, которого у OMDB не существует. Тот же класс сравнения, что уже записан для `SourceHttp.get` ≠ `TmdbClient.search` — один глагол, разные поводы для отказа
- `backend/sources/ratings/omdb/client.py:until_midnight` ≠ `backend/sources/ratings/mdblist/client.py:QUOTA_FALLBACK` ≠ `backend/sources/ratings/mdblist/client.py:_retry_after` — три разных по типу вещи под одной темой «на сколько отложить повтор»: функция от часов (OMDB, суточная квота без заголовков), константа-запасной вариант (MDBList, час, когда сервер не прислал `Retry-After`), парсер заголовка (MDBList, когда прислал). У OMDB заголовка нет вовсе, поэтому `_retry_after` ему не нужен; у MDBList нет полуночной квоты, поэтому `until_midnight` ему не нужен. Тот же вид пары, что уже записан для `UNDOCUMENTED_BACKOFF` ≠ `RATE_BACKOFF` — общий повод, разные основания срока
- `tests/backend/sources/test_omdb.py:responding`/`ask` ≠ `tests/backend/sources/test_mdblist.py:responding`/`ask` — беглая проверка заодно: сигнатуры разные (`responding(status, body)` против `responding(status, *, json=None, text=None, headers=None)`, `ask(transport)` против `ask(transport, kind=Kind.MOVIE)`) — тот же локальный помощник теста под клиента, что уже есть у `test_gog.py:answering` и `test_tmdb_failures.py:responding`; имя по уговору, не код на вынос

## Вердикт

**Да.** Задача 10 не внесла повторов, которые нужно чистить перед коммитом. Все
шесть указанных пар — и попутно проверенные тестовые помощники — разошлись по
существу при чтении кода: общее уже вынесено туда, где оно действительно общее
(`SourceHttp`, `Ratings`, `ExternalRating`, `Outcome`), а то, что похоже по виду
(`OWNERS`, `_denied`, `ratings`, срок отката), несёт разную логику под похожим
именем. Присвоить отпечатки и продлить в `docs/not-duplicates.md` может
исполнитель на шаге починки — новых пар для записи: семь, список выше.
