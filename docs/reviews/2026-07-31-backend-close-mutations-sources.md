# Закрывающее ревью бэкенда: мутации по слою источников

Дата: 2026-07-31. Коммит: `1227049`. Рабочее дерево: отдельное, HEAD не трогался,
кода мутации не оставили — `git status` чист, кроме самого этого отчёта.

Объём: `backend/sources/**` — 21 модуль, 1636 строк. Сторожат их
`tests/backend/sources/**` (13 файлов). Мутаций внесено **103**, каждая — одна
строка, каждая откачена до следующей. Прогон — один файл тестов на мутацию;
пять молчаливых перепроверены на всём `tests/backend` (905 тестов).

Молча прошло **5**.

## Сильные стороны (Strengths)

- **98 мутаций из 103 пойманы**, и пойманы не «упало где-то», а тем самым
  тестом, чьё имя обещает это свойство. Покрыты все шесть клиентов и все общие
  модули: `convert.py`, `errors.py`, `http.py`, `mirror.py`, `undocumented.py`,
  `registry.py`, `build.py`.
- **Сроки — настоящие, а не переписанные из кода.** Пятнадцать секунд сетевого
  отката, минута у TMDB, пять минут у неописанных магазинов, шесть часов у
  Кинопоиска, час запасной у MDBList, «до полуночи» у OMDB — сдвинул любой,
  краснеет тест, и краснеет он на наблюдаемом следствии (ушёл ли второй запрос
  на провод), а не на сверке константы с константой.
- **Отрицательный факт заперт с двух сторон.** «404 И код в теле», превращённое
  в «ИЛИ», ловится сразу; 404 без JSON, 404 с чужим кодом, код отсутствия под
  чужим HTTP-кодом, `success: false` у Steam, каталог GOG, не вернувший
  запрошенный id, — каждый случай сторожит свой тест.
- **Привязка, а не набор, — там, где о ней подумали заранее.** Роли студий
  (`test_convert.py`), жанр против тега у GOG на метках, которые есть только с
  одной стороны, пространства TMDB, номер зеркала Кинопоиска, ключ каждого
  источника в сборке, сверенный с хостом, — всё это перепутать молча нельзя.
  Три теста прямо написаны против этой ловушки, и все три сработали.
- **Причина взвода переживает предохранитель.** Пять разных мутаций, стирающих
  `Reason` при взводе (общий `Breaker`, `undocumented`, `mirror`, TMDB, MDBList),
  пойманы все.
- **`PROVIDES` сверяется с разбором в обе стороны** — и потерянный источник, и
  лишний ловятся на записанном полном ответе.
- **Литералы вместо констант там, где это важно.** Адрес MDBList, двадцать
  секунд таймаута, «2 сезона, 24 серии» — написаны буквой нарочно, и это
  единственное, что делает мутацию по константе наблюдаемой.

## Таблица мутаций

| № | файл:строка | что сломано | чем прогнано | исход |
|---|---|---|---|---|
| M01 | `convert.py:26` | convert.identifier: пустая строка становится идентификатором | `test_tmdb_card.py` | ПОЙМАНА |
| M02 | `convert.py:37` | convert.genres: жанр без идентификатора проглатывается | `test_convert.py` | ПОЙМАНА |
| M03 | `convert.py:43` | convert.year: год отрезан с конца строки | `test_convert.py` | ПОЙМАНА |
| M04 | `convert.py:53` | convert.companies: разработчик читается из издателей | `test_convert.py` | ПОЙМАНА |
| M05 | `convert.py:83` | convert.rating: ноль пишется как оценка | `test_convert.py` | ПОЙМАНА |
| M06 | `convert.py:65` | convert.FREE_IN_SEARCH: оценка GOG приписана TMDB | `test_convert.py` | ПОЙМАНА |
| M07 | `errors.py:13` | BROKEN_BY_PARSING: TypeError больше не считается поломкой разбора | `test_steam.py` | ПОЙМАНА |
| M08 | `errors.py:38` | is_json: неразобравшееся тело объявлено разобранным | `test_kinopoisk.py` | ПОЙМАНА |
| M09 | `errors.py:26` | refuse_code: неописанный код объявлен бедой с ключом | `test_gog_slug.py` | ПОЙМАНА |
| M10 | `errors.py:58` | parsed: запись в лог больше не называет источник | `test_kinopoisk.py` | ПОЙМАНА |
| M11 | `http.py:37` | Breaker.is_open: ровно срок ещё считается закрытым | `test_http.py` | ПОЙМАНА |
| M12 | `http.py:48` | Breaker.trip: причина взвода забыта, всегда квота | `test_http.py` | ПОЙМАНА |
| M13 | `http.py:22` | NETWORK_BACKOFF: пятнадцать секунд стали пятнадцатью минутами | `test_http.py` | ПОЙМАНА |
| M14 | `http.py:92` | get: сетевой отказ взводит предохранитель как квоту | `test_http.py` | ПОЙМАНА |
| M15 | `http.py:89` | get: ловится всё подряд, а не только сетевое | `test_http.py` | ПОЙМАНА |
| M16 | `http.py:75` | переадресация больше не проходится | `test_http.py` | ПОЙМАНА |
| M17 | `http.py:17` | DEFAULT_TIMEOUT: двадцать секунд стали пятью | `test_http.py` | ПОЙМАНА |
| M18 | `undocumented.py:12` | UNDOCUMENTED_BACKOFF: пять минут стали минутой | `test_http.py` | ПОЙМАНА |
| M19 | `undocumented.py:19` | предохранитель взводится без причины «частота» | `test_http.py` | ПОЙМАНА |
| M20 | `registry.py:38` | catalog_for: магазины поменялись местами | `test_registry.py` | ПОЙМАНА |
| M21 | `registry.py:46` | client_for: карточка Steam уедет к клиенту GOG | `test_registry.py` | ПОЙМАНА |
| M22 | `registry.py:58` | aclose: закрывается только первое соединение | `test_registry.py` | ПОЙМАНА |
| M23 | `build.py:39` | Steam сидит на соединении с именем gog | `test_registry.py` | ПОЙМАНА |
| M24 | `build.py:41` | MDBList получил ключ OMDB | `test_registry.py` | ПОЙМАНА |
| M25 | `build.py:34` | зеркала Кинопоиска обменялись ключами | `test_registry.py` | ПОЙМАНА |
| M26 | `tmdb/client.py:27` | classify: код 6 больше не считается отсутствием | `test_tmdb_failures.py` | ПОЙМАНА |
| M27 | `tmdb/client.py:42` | classify: «404 И код в теле» стало «404 ИЛИ код в теле» | `test_tmdb_failures.py` | ПОЙМАНА |
| M28 | `tmdb/client.py:77` | _verdict: 429 не взводит предохранитель | `test_tmdb_failures.py` | ПОЙМАНА |
| M29 | `tmdb/client.py:24` | RATE_BACKOFF: минута стала часом | `test_tmdb_failures.py` | ПОЙМАНА |
| M30 | `tmdb/client.py:94` | search: сериалы ищутся по киношной ручке | `test_tmdb_search.py` | ПОЙМАНА |
| M31 | `tmdb/client.py:56` | _APPEND: у сериала запрашивается credits вместо aggregate_credits | `test_tmdb_card.py` | ПОЙМАНА |
| M32 | `tmdb/parse.py:91` | _KEYS: сериал читается по ключам фильма | `test_tmdb_search.py` | ПОЙМАНА |
| M33 | `tmdb/parse.py:108` | _item: оригинальное название взято из переведённого поля | `test_tmdb_card.py` | ПОЙМАНА |
| M34 | `tmdb/parse.py:71` | _cast: позиция актёра — номер строки, а не order из ответа | `test_tmdb_card.py` | ПОЙМАНА |
| M35 | `tmdb/parse.py:82` | _required: проверяется только наличие блока, не состав в нём | `test_tmdb_card.py` | ПОЙМАНА |
| M36 | `tmdb/parse.py:46` | _poster: пустой путь склеивается с базой в ссылку в никуда | `test_tmdb_search.py` | ПОЙМАНА |
| M37 | `tmdb/parse.py:148` | parse_movie: режиссёром становится каждый, кроме режиссёра | `test_tmdb_card.py` | ПОЙМАНА |
| M38 | `tmdb/parse.py:187` | parse_series: imdb_id ищется на верхнем уровне, а не в довеске | `test_tmdb_card.py` | ПОЙМАНА |
| M39 | `tmdb/parse.py:167` | parse_series_counts: сезоны считаются из числа серий | `test_tmdb_card.py` | ПОЙМАНА |
| M40 | `tmdb/parse.py:126` | parse_search: source_id уезжает числом, а не строкой | `test_tmdb_search.py` | ПОЙМАНА |
| M41 | `tmdb/parse.py:136` | parse_search: вместо оценки берётся число голосов | `test_tmdb_search.py` | ПОЙМАНА |
| M42 | `tmdb/parse.py:54` | _own_rating: своя оценка TMDB приписана IMDb | `test_tmdb_card.py` | ПОЙМАНА |
| **M43** | **`steam/parse.py:85`** | **parse_tags: номером тега становится его вес** | `test_steam.py` | **МОЛЧА** |
| M44 | `steam/parse.py:85` | parse_tags: теги приезжают в жанровом пространстве | `test_steam.py` | ПОЙМАНА |
| M45 | `steam/parse.py:20` | _year: годы прошлого века больше не ловятся | `test_steam.py` | ПОЙМАНА |
| M46 | `steam/parse.py:26` | poster_url: обложка берётся половинного размера | `test_steam.py` | ПОЙМАНА |
| **M47** | **`steam/parse.py:75`** | **parse_card: жанры читаются из `categories`** | `test_steam.py` | **МОЛЧА** |
| M48 | `steam/parse.py:54` | _metascore: оценка Metacritic приписана Steam | `test_steam.py` | ПОЙМАНА |
| M49 | `steam/client.py:77` | card: берётся любой блок ответа, а не запрошенный appid | `test_steam.py` | ПОЙМАНА |
| M50 | `steam/client.py:89` | card: `success: false` больше не читается как отсутствие | `test_steam.py` | ПОЙМАНА |
| M51 | `steam/client.py:25` | TAGS_CONTEXT: страна US заменена на RU | `test_steam.py` | ПОЙМАНА |
| M52 | `steam/client.py:81` | _tags: отказ на тегах молчит в логе | `test_steam.py` | ПОЙМАНА |
| M53 | `steam/client.py:61` | search: строка поиска не экранируется | `test_steam.py` | ПОЙМАНА |
| M54 | `gog/parse.py:22` | _marks: жанры помечаются теговым пространством | `test_gog.py` | ПОЙМАНА |
| M55 | `gog/parse.py:23` | _marks: теги читаются из жанров | `test_gog.py` | ПОЙМАНА |
| M56 | `gog/parse.py:47` | parse_catalog: оценкой становится возрастной рейтинг | `test_gog.py` | ПОЙМАНА |
| M57 | `gog/parse.py:41` | parse_catalog: обложка берётся горизонтальная | `test_gog.py` | ПОЙМАНА |
| M58 | `gog/parse.py:72` | find_slug: совпадение слага стало нестрогим | `test_gog_slug.py` | ПОЙМАНА |
| M59 | `gog/client.py:77` | card: ненайденный идентификатор объявлен отсутствием | `test_gog.py` | ПОЙМАНА |
| M60 | `gog/client.py:100` | resolve_slug: ненайденный слаг отдаётся находкой | `test_gog_slug.py` | ПОЙМАНА |
| M61 | `gog/client.py:46` | _payload: коды ниже 500 больше не классифицируются | `test_gog.py` | ПОЙМАНА |
| M62 | `gog/client.py:42` | _payload: запрос уходит без `like:` | `test_gog.py` | ПОЙМАНА |
| M63 | `ratings/kinopoisk/mirror.py:49` | answered: «и» заменено на «или» | `test_kinopoisk.py` | ПОЙМАНА |
| M64 | `ratings/kinopoisk/mirror.py:16` | QUOTA_BACKOFF: шесть часов стали часом | `test_kinopoisk.py` | ПОЙМАНА |
| M65 | `ratings/kinopoisk/mirror.py:31` | refuse_rate: взвод без причины «частота» | `test_kinopoisk.py` | ПОЙМАНА |
| M66 | `ratings/kinopoisk/parse.py:11` | _rating: честный ноль слился с отсутствием | `test_kinopoisk.py` | ПОЙМАНА |
| M67 | `ratings/kinopoisk/parse.py:26` | _first_row: берётся последняя строка ответа | `test_kinopoisk.py` | ПОЙМАНА |
| M68 | `ratings/kinopoisk/parse.py:37` | parse_poiskkino: номер Кинопоиска записан как IMDb | `test_kinopoisk.py` | ПОЙМАНА |
| M69 | `ratings/kinopoisk/poiskkino.py:55` | битый ключ объявлен исчерпанной квотой | `test_kinopoisk.py` | ПОЙМАНА |
| M70 | `ratings/kinopoisk/poiskkino.py:68` | _absent: проверка «тело разобралось» перевёрнута | `test_kinopoisk.py` | ПОЙМАНА |
| M71 | `ratings/kinopoisk/poiskkino.py:39` | спрашиваем по идентификатору TMDB вместо IMDb | `test_kinopoisk.py` | ПОЙМАНА |
| M72 | `ratings/kinopoisk/poiskkino.py:24` | FIELDS: оценка не запрашивается явно | `test_kinopoisk.py` | ПОЙМАНА |
| M73 | `ratings/kinopoisk/unofficial.py:44` | 402 классифицирован как частота, а не квота | `test_kinopoisk.py` | ПОЙМАНА |
| M74 | `ratings/kinopoisk/client.py:32` | зеркала поменялись местами | `test_kinopoisk.py` | ПОЙМАНА |
| M75 | `ratings/kinopoisk/client.py:19` | PROVIDES: приписан лишний источник IMDb | `test_rating_provides.py` | ПОЙМАНА |
| M76 | `ratings/mdblist/parse.py:13` | OWNERS: `tomatoes` переведён в Metacritic | `test_mdblist.py` | ПОЙМАНА |
| M77 | `ratings/mdblist/parse.py:31` | parse_ratings: ноль слился с пустым значением | `test_mdblist.py` | ПОЙМАНА |
| M78 | `ratings/mdblist/client.py:25` | _retry_after: `Retry-After` датой роняет клиент | `test_mdblist.py` | ПОЙМАНА |
| M79 | `ratings/mdblist/client.py:83` | _denied: проверка «тело разобралось» перевёрнута | `test_mdblist.py` | ПОЙМАНА |
| M80 | `ratings/mdblist/client.py:20` | QUOTA_FALLBACK: час стал десятью минутами | `test_mdblist.py` | ПОЙМАНА |
| M81 | `ratings/mdblist/client.py:73` | исчерпанная квота не взводит предохранитель | `test_mdblist.py` | ПОЙМАНА |
| M82 | `ratings/mdblist/client.py:49` | сериал спрашивается по киношному пути | `test_mdblist.py` | ПОЙМАНА |
| M83 | `ratings/mdblist/client.py:62` | 404 стал отказом вместо отсутствия | `test_mdblist.py` | ПОЙМАНА |
| M84 | `ratings/mdblist/client.py:33` | PROVIDES: потерян источник TMDB | `test_rating_provides.py` | ПОЙМАНА |
| M85 | `ratings/mdblist/client.py:68` | 202 «кеш строится» объявлен исчерпанной квотой | `test_mdblist.py` | ПОЙМАНА |
| M86 | `ratings/omdb/parse.py:19` | _number: значимая часть отрезается по точке, а не по дроби | `test_omdb.py` | ПОЙМАНА |
| M87 | `ratings/omdb/parse.py:42` | parse_ratings: IMDb записывается дважды | `test_omdb.py` | ПОЙМАНА |
| M88 | `ratings/omdb/parse.py:9` | OWNERS: Rotten Tomatoes переведён в Metacritic | `test_omdb.py` | ПОЙМАНА |
| M89 | `ratings/omdb/client.py:83` | _denied: текст ошибки не приводится к нижнему регистру | `test_omdb.py` | ПОЙМАНА |
| M90 | `ratings/omdb/client.py:91` | _denied: битый ключ закрывает источник до полуночи | `test_omdb.py` | ПОЙМАНА |
| M91 | `ratings/omdb/client.py:22` | until_midnight: срок считается до прошедшей полуночи | `test_omdb.py` | ПОЙМАНА |
| M92 | `ratings/omdb/client.py:74` | _answer: «False» сверяется с другим регистром | `test_omdb.py` | ПОЙМАНА |
| M93 | `ratings/omdb/client.py:64` | любой код кроме 401 разбирается как успех | `test_omdb.py` | ПОЙМАНА |
| M94 | `ratings/omdb/client.py:59` | проверка «тело — объект» ослаблена до «не None» | `test_omdb.py` | ПОЙМАНА |
| M95 | `ratings/omdb/client.py:31` | PROVIDES: потерян источник Rotten | `test_rating_provides.py` | ПОЙМАНА |
| M43b | `steam/parse.py:85` | то же, что M43, но прогнан весь `tests/backend` | `tests/backend` (905) | **МОЛЧА** |
| M47b | `steam/parse.py:75` | то же, что M47, но прогнан весь `tests/backend` | `tests/backend` (905) | **МОЛЧА** |
| M96 | `gog/parse.py:22` | _marks: жанр сопоставляется по названию, а не по слагу | `test_gog.py` | ПОЙМАНА |
| M97 | `build.py:42` | OMDB посажен на соединение MDBList — одно имя у двух источников | `test_registry.py` | ПОЙМАНА |
| M98 | `convert.py:32` | genres: ключ идентификатора по умолчанию стал `name` | `test_tmdb_card.py` | ПОЙМАНА |
| M99 | `steam/client.py:101` | card: жанры теряются, остаются одни теги | `test_steam.py` | ПОЙМАНА |
| **M100** | **`ratings/kinopoisk/client.py:29`** | **KinopoiskClient.name: наружу называется именем зеркала** | `tests/backend` (905) | **МОЛЧА** |
| **M101** | **`ratings/mdblist/client.py:46`** | **MdbListClient.name: наружу называется `omdb`** | `tests/backend` (905) | **МОЛЧА** |
| **M102** | **`tmdb/client.py:67`** | **TmdbClient.name: наружу называется чужим именем** | `tests/backend` (905) | **МОЛЧА** |
| M103 | `steam/parse.py:84` | parse_tags: список тегов берётся из несуществующего ключа | `test_steam.py` | ПОЙМАНА |

## Находки (Issues) — молча прошедшие

Все пять — одного рода: **тест проверяет форму того, что привезли, а не то,
откуда это взято.** Ровно та ловушка, что дала шесть молчаливых мутаций в ревью
плана 2; в Steam её тогда закрыли по пространствам меток, но не по ключам, из
которых метки читаются.

### Important

**1. `backend/sources/steam/parse.py:75` — жанры можно взять из любого блока
ответа, где есть числовые `id`.**

Сломано: `data.get("genres", [])` → `data.get("categories", [])`. Прогон:
`test_steam.py` — 26 зелёных; весь `tests/backend` — **905 зелёных**.

Почему никто не заметил: единственный сторож — `test_genres_arrive_with_identifiers`,
и он утверждает только «набор непуст, пространство `STEAM`, идентификатор
состоит из цифр». `categories` этому подходит целиком: там тоже объекты с
числовым `id`. Ни один тест не сверяет привезённые номера с записанным ответом —
у TMDB такая сверка есть (`["12", "18", "878"]`), у GOG есть (`fantasy`, `rpg`,
`story-rich`), у Steam нет.

Следствие мутации настоящее, а не косметическое: в `0002_genres.py` у
пространства `steam` номер `"2"` — это `Strategy`, а `categories[0].id == 2` —
это «Одиночная игра». То есть каждая одиночная игра молча уезжает в базу
стратегией, и приложение об этом не скажет ничего.

Какое следствие должен наблюдать тест: **конкретные номера жанров записанного
ответа `steam/appdetails.json`**, а не их форму. Чем закрыть: в
`test_genres_arrive_with_identifiers` заменить проверку «все цифры» на равенство
набора номеров тому, что лежит в `data["genres"]` фикстуры (или выписанному
литералом списку), — как это сделано у TMDB.

**2. `backend/sources/steam/parse.py:85` — номером тега может стать его вес.**

Сломано: `key="tagid"` → `key="weight"`. Прогон: `test_steam.py` — 26 зелёных;
весь `tests/backend` — **905 зелёных**.

Почему никто не заметил: то же самое. `test_tags_arrive_in_their_own_space`
сторожит пространство (`STEAM_TAG`) и «состоит из цифр», а `weight` — тоже
число. Пространство после ревью плана 2 закрыли, ключ — нет.
`test_the_card_carries_both_spaces` смотрит только на множество пространств.

Следствие: теги игры превращаются в случайные числа. Вес, случайно совпавший с
чужим `tagid`, даёт неверный жанр; не совпавший — тихо теряет тег, и карточка
выглядит просто бедной. Именно ради тегов Steam ходит вторым запросом: своих
жанров у него двенадцать на весь магазин.

Какое следствие должен наблюдать тест: **номера из `tags[].tagid` записанного
`steam/store_items.json`**, и что весов среди них нет — в фикстуре они
различимы (1695/1158, 122/976). Чем закрыть: сверить набор разобранных номеров
с `tagid` фикстуры.

### Minor

**3. `name` у клиентов источников не наблюдается ничем.**
`ratings/kinopoisk/client.py:29`, `ratings/mdblist/client.py:46`,
`tmdb/client.py:67` — проверены поимённо, все три молчат на всём наборе (905
тестов). У Steam, GOG и OMDB свойство устроено так же (`return self._http.name`),
и сторожа у него нет тоже.

Почему никто не заметил: единственное упоминание — `test_registry.py`,
`assert isinstance(client.name, str) and client.name`, то есть проверка формы.
Все тесты про имя источника в отказах смотрят на `Refusal.source`, а его клиенты
подставляют литералом — своим, отдельно от `name`.

Следствие: `name` уходит только в `answered(..., client.name)` из
`backend/service/*`, то есть называет источник в двух местах — в отказе
**сорвавшегося** клиента и в записи `logger.exception`. Разойдись оно с тем
именем, которым источник называется во всех остальных отказах, — человек увидит
в плашке «omdb» там, где сломался MDBList, и пойдёт править не тот ключ. Проект
эту беду однажды уже чинил (имя брали из `PROVIDES[0]`, а там у MDBList и OMDB
одно и то же `imdb`); починка ввела `name`, но следствия починки не сторожит
никто.

Какое следствие должен наблюдать тест: **имя, которым клиент называется наружу,
совпадает с именем в его отказе.** Чем закрыть: в `test_registry.py` для каждого
клиента взвести предохранитель его соединения и сравнить `Refusal.source`
пришедшего отказа с `client.name` — одна проверка на всех, включая Кинопоиск, у
которого `name` берётся не у транспорта, а из `mirror.SOURCE`.

## Рекомендации (Recommendations)

1. Закрыть две дыры по Steam правкой двух уже существующих тестов
   (`test_genres_arrive_with_identifiers`, `test_tags_arrive_in_their_own_space`):
   сверять номера с записанным ответом, а не их форму. Это ровно то, что у TMDB
   и GOG уже сделано, — Steam просто пропустили.
2. Правило на будущее, годное всему проекту: **«все элементы такой-то формы» —
   не проверка привязки.** Если в фикстуре рядом лежит второй блок такой же
   формы (`genres` и `categories`, `tagid` и `weight`), тест обязан называть
   значения, а не их вид.
3. Имя источника (`name`) — либо один общий тест на совпадение с
   `Refusal.source`, либо запись в `docs/deferred.md` с доводом: следствие видно
   только в тексте плашки и лога.
4. Ничего из найденного не требует правки боевого кода: все пять мутаций — дыры
   в тестах, сам слой источников ведёт себя так, как обещает.

## Вердикт (Assessment)

**Бэкенд можно закрывать?** С правками

**Обоснование:** 98 мутаций из 103 пойманы, и пойманы именно теми тестами,
которые это обещают, — слой источников проверен всерьёз. Перед закрытием стоит
дописать две проверки по Steam (жанры и теги сверяются с номерами записанного
ответа, а не с их формой): без них молча проходит запись неверных жанров каждой
игре, и 905 зелёных тестов об этом не скажут. Третья находка — про имя клиента —
тянет на запись в отложенное, а не на задержку закрытия.
