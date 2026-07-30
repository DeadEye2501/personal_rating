# Разобранные пары

Здесь лежат объявления, которые уже сравнивали и признали разными. Проверка
повторов читает этот файл вместе с картами и такие пары пропускает — иначе
каждый проход разбирал бы одно и то же заново.

Строка пишется руками, отпечатки проставляет сборка карт. **Отпечаток — срок
годности вердикта:** изменилось тело любой стороны — отпечаток не сойдётся,
`--check` покраснеет, и пара вернётся в разбор. Вердикт без срока годности хуже
его отсутствия: он глушит проверку ровно там, где она однажды сработала.

Дописывает сюда исполнитель на шаге починки, из отчёта рецензента. Сам рецензент
в репозиторий не пишет.

**Новая пара** пишется без отпечатков — их проставит ближайшая сборка карт.
**Протухшую** продлевают так же: разбирают заново, поправляют причину, если она
изменилась, и **стирают руками разошедшийся отпечаток**. Сборка его не заменит
сама — иначе вердикт воскресал бы молча, на ровной пересборке.

## Разное по существу, совпало по виду

- `backend/storage/posters.py:PosterStore._read` `676202b4` ≠ `backend/storage/repository/base.py:Repository._row` `633db0ec` — разные транспорты: репозиторий работает фабрикой сессий основной базы, `PosterStore` — соединениями собственного движка второго файла. Вынести пришлось бы сам движок, а он у них разный по построению
- `backend/storage/posters.py:PosterStore.has` `55bc608e` ≠ `backend/storage/repository/wishlist.py:WishlistRepository.contains` `6d8f9d7f` — сигнатура одна, тела разные и слить их нельзя: `contains` идёт через `_has_item` основной базы, `has` — через `_read` чужого файла, где ни сессий, ни `Repository` нет. Расхождение остаётся в словаре, а не в коде
- `backend/storage/repository/ratings.py:RatingsRepository._write` `c873639d` ≠ `backend/storage/repository/base.py:Repository._written` `82f22900` — совпадает только корень имени: первый пишет оценку, сохраняя `created_at`, второй переводит `IntegrityError` в своё исключение
- `backend/storage/repository/base.py:Repository._created` `9af10357` ≠ `backend/storage/repository/base.py:Repository._written` `82f22900` — общего три строки `except IntegrityError`. Слить нельзя: `_created` обязан прочитать `scalar_one()` внутри той же сессии и потому не может звать `_run`
- `backend/storage/tables/base.py:item_fk` `4cd3eea9` ≠ `backend/storage/tables/base.py:genre_fk` `9df06746` — сигнатура одна, результат разный: разные имя колонки и целевая таблица. Параметризация удлинила бы двенадцать мест вызова ради экономии пяти строк

- `backend/model/search.py:SearchHit` `41a5effa` ≠ `backend/model/item.py:Item` `6ccf23ff` — половина имён полей общая, и слить их значило бы стереть шов, ради которого они заведены: `Item` — строка базы с `id` и `synced_at`, `SearchHit` — кандидат выдачи, который в базу не попадает никогда. Общий тип потребовал бы необязательного `id`, а с ним и вопроса «эта карточка уже сохранена?» в каждом месте
- `backend/sources/tmdb/client.py:TmdbClient.search` `5149532a` ≠ `backend/sources/tmdb/parse.py:parse_search` `280597d0` — обе ветвятся по `kind is Kind.SERIES`, но ради разного: первая выбирает ручку, вторая — ключи полей в чужом теле. Ветвление общее по виду, а не по делу. Разобрано повторно после задачи 5: у обеих сторон изменилось тело, довод не изменился

- `backend/sources/undocumented.py:refuse_undocumented` `ba274616` ≠ `backend/sources/tmdb/client.py:classify` `c47dc07e` — оба переводят код ответа в отказ, но у TMDB кодов пять и один из них означает «такого нет», а у магазинов отсутствие кодом не выражается вовсе: у Steam оно приходит под 200, у GOG его не бывает. Слитые, они потребовали бы таблицу на источник — тот же код, но через параметр
- `backend/sources/undocumented.py:UNDOCUMENTED_BACKOFF` `e8c32704` ≠ `backend/sources/tmdb/client.py:RATE_BACKOFF` `52916657` — одно дело, разные сроки и разные основания: у TMDB минута по её собственной политике, у магазинов пять минут наугад, потому что лимитов они не объявляют вовсе

- `backend/sources/steam/client.py:SteamClient.card` `094bdf08` ≠ `backend/sources/gog/client.py:GogClient._payload` `7a4c1ce6` — обе начинаются с двух строк «пришёл не ответ, а готовый отказ — верни его как есть». Идиома повторяется в десяти местах восьми файлов, и это осознанно: короче она не станет, а вынести её можно было бы только вместе с самим `SourceHttp.get`, поменяв его контракт с «ответ или отказ» на исключение. Разобрано на финальном ревью плана 2 и повторно в задаче 12 плана 4, когда идиома у GOG уехала из `_catalog` в новый `_payload`: довод не изменился

- `backend/storage/repository/credits.py:CreditRepository.find_by_source` `4431e500` ≠ `backend/storage/repository/library.py:LibraryRepository.find_by_source` `91794c3d` — имя и сигнатура совпадают, предметы разные: первый отдаёт номер строки человека или студии, второй — собранную `Item` со всеми полями. Общее уже вынесено в `Repository`
- `backend/storage/repository/credits.py:CreditRepository.attach` `f6ddadb4` ≠ `backend/storage/repository/tags.py:TagsRepository.assign` `964e54df` — общего одно выражение `insert(...).on_conflict_do_nothing()`. `assign` до вставки сверяет тип содержимого тега с типом карточки в одной сессии, `attach` собирает набор значений с необязательной позицией
- `backend/storage/repository/credits.py:IdentityTaken` `2fa82a88` ≠ `backend/storage/repository/library.py:ItemExists` `f94e192e` — пустые наследники `Exception` с разными докстрингами, и в этом смысл: вызывающий различает, какой ключ уникальности занят. Слитые, они это различение стёрли бы
- `backend/storage/repository/credits.py:companies` `447c5757` ≠ `backend/sources/convert.py:companies` `503e3424` — совпало имя: первая отдаёт репозиторий студий, вторая переводит блок чужого ответа в `Credit`. Ни одна о другой не знает
- `backend/model/suggestion.py:Suggestion` `89cf839b` ≠ `backend/model/search.py:SearchHit` `41a5effa` — оба несут строку для показа человеку, и на этом сходство кончается: `SearchHit` — кандидат из чужой базы, который ещё не карточка, `Suggestion` — своя строка людей или студий с названием карточки, по которой её узнают. Общего поля нет ни одного

- `backend/storage/repository/external.py:ExternalIdTaken` `0b5afcee` ≠ `backend/storage/repository/credits.py:IdentityTaken` `2fa82a88` — пустые наследники `Exception` с разными докстрингами; различение того, какой ключ уникальности занят, и есть их содержание, а слитые они его сотрут
- `backend/storage/repository/external.py:ExternalRatingsRepository.stale_sources` `88516346` ≠ `backend/sources/http.py:Breaker.is_open` `71b93ccd` — общего только арифметика над `datetime`: предохранитель держит один срок в памяти и сбрасывает его, `stale_sources` отбирает из списка источников те, чья строка в базе старше своего срока. Ни строки общего кода
- `backend/storage/repository/external.py:VALUE_TTL` `d5d9d334` ≠ `backend/sources/undocumented.py:UNDOCUMENTED_BACKOFF` `e8c32704` — совпадает тип `timedelta`, дело разное: первое — срок годности записанного в базу, второе — пауза перед следующим запросом. Первое читает хранилище, второе предохранитель
- `backend/sources/ratings/kinopoisk/mirror.py:RATE_BACKOFF` `52916657` ≠ `backend/sources/tmdb/client.py:RATE_BACKOFF` `52916657` — совпали и имя, и значение, но основания разные и записаны рядом с каждым: у TMDB это её объявленная политика, у зеркал Кинопоиска — неописанный частотный ответ. Общая константа связала бы два независимых источника, и правка политики TMDB молча меняла бы Кинопоиск
- `backend/sources/convert.py:year` `3d8f65b9` ≠ `backend/sources/steam/parse.py:_year` `3287d234` — сигнатура одна, разбор разный: первый берёт первые четыре знака машинной даты, второй ищет год регулярным выражением в дате, написанной человеком на языке запроса. Слитые, они вернули бы ту самую ошибку, ради которой `_year` заведён
- `backend/sources/ratings/omdb/parse.py:OWNERS` `7a3dc7e6` ≠ `backend/sources/ratings/mdblist/parse.py:OWNERS` `4584d053` — совпало имя, ключи из разных словарей: у OMDB человеческие названия, у MDBList слаги. Общая таблица позволила бы разобрать чужую метку в разборе соседа
- `backend/sources/ratings/omdb/parse.py:parse_ratings` `34f7d479` ≠ `backend/sources/ratings/mdblist/parse.py:parse_ratings` `8fe3b088` — совпало имя, потому что поверхность разбора у всех источников зовётся одинаково; тела разные: OMDB вытаскивает число из «8.6/10» и «72%» и отсеивает второй приезд IMDb, MDBList берёт готовое число и сохраняет `null` пустым значением
- `backend/service/cards.py:CardWriter` `f74f80c5` ≠ `backend/service/linking.py:Linker` `f82c8b0d` — общее у них вынесено в `CardParts`, а остальное разное по смыслу, а не по флагу: писатель заводит строку и убирает за собой при срыве, привязка правит существующую и не трогает занятое человеком. Слитые под флагом, они дали бы метод, в котором каждая вторая строка — ветка
- `backend/service/linking.py:_FILLABLE` `88cddb34` ≠ `backend/storage/repository/library.py:_FIELDS` `24fa39e5` — второе перечисляет все колонки карточки для записи, первое — подмножество, которое разрешено долить источнику. Разница и есть правило: идентичность, `id`, `synced_at` и тип содержимого источник не трогает
## Один глагол над разными предметами

- `backend/sources/tmdb/client.py:TmdbClient.name` `288035fb` ≠ `backend/sources/steam/client.py:SteamClient.name` `288035fb` ≠ `backend/sources/gog/client.py:GogClient.name` `288035fb` — тело и докстринг совпадают дословно у всех трёх, и это общий интерфейс каталожного клиента, а не повтор: общего предка у клиентов нет намеренно — по решению «добавление седьмого источника не должно требовать правок в существующих». Примесь ради одной инструкции связала бы три независимых модуля крепче, чем стоит сама экономия. Разобрано на ревью задачи 7 плана 4

- `backend/sources/http.py:SourceHttp.get` `495a656f` ≠ `backend/sources/tmdb/client.py:TmdbClient.search` `5149532a` — обе ловят исключение и возвращают `Refusal`, но ловят разное и по разным причинам: первая — сбой провода, вторая — тело, которое не разобралось. Слитые, они назвали бы поломку TMDB пропавшим интернетом
- `backend/storage/repository/tags.py:TagsRepository.list_for_kind` `b0916f5a` ≠ `backend/storage/repository/genres.py:GenresRepository.list_for_kind` `8ee53ef7` — разные таблицы и разные наборы значений `kind`; общее уже вынесено в `Repository._mapped`. Разобрано повторно в задаче 2 плана 4: сборка строки уехала в `rows.py`, довод не изменился
- `backend/storage/repository/tags.py:TagsRepository.tags_of` `294ca5f1` ≠ `backend/storage/repository/genres.py:GenresRepository.genres_of` `bb731b6d` — одинаковая форма запроса, разные таблицы, соединения и порядок. Разобрано повторно там же и по той же причине
- `backend/storage/repository/credits.py:CreditRepository.credits_of` `6ccfc2d3` ≠ `backend/storage/repository/tags.py:TagsRepository.tags_of` `294ca5f1` — та же семья, что парой выше, плюс своё: у `credits_of` и набор колонок, и порядок зависят от `Entity.position`, которого у тегов нет. Разобрано повторно: сборка `Credit` стала функцией и зовётся лямбдой, довод не изменился
- `backend/storage/repository/credits.py:CreditRepository.find_by_name` `cd684aa5` ≠ `backend/storage/repository/library.py:LibraryRepository.find_by_title` `11004f6f` — общей была идиома сравнения регистра, и её больше нет: она вынесена в `session.folded`. Осталось разное — у названия сравниваются две колонки через `|` и добавлен фильтр по типу содержимого, у имени одна колонка с порядком по номеру. Разобрано повторно: у `find_by_title` сменилось имя сборщика строки
- `backend/storage/repository/credits.py:to_credit` `af7d9738` ≠ `backend/storage/rows.py:to_genre` `9d72e4e8` — по сборщику на таблицу, и `to_credit` лежит отдельно от остальных нарочно: ему нужен `Entity`, объявленный в `credits.py`, а `rows.py` пришлось бы импортировать из репозитория, который сам импортирует его. Пара разобрана заново в задаче 2 плана 4, когда обе стороны переехали
- `backend/storage/rows.py:to_genre` `9d72e4e8` ≠ `backend/storage/rows.py:to_item` `3a967d51` — два сборщика в одном модуле, каждый знает свои колонки: у первого три поля, у второго тринадцать с пустыми строками вместо `NULL`. Слить их можно было бы только через таблицу колонок на каждый тип, то есть переписав то же самое данными
- `backend/storage/repository/library.py:LibraryRepository.refresh_series_counts` `880542f8` ≠ `backend/storage/repository/library.py:LibraryRepository.replace_fields` `a68829f1` — два пути обновления заведены нарочно: первый обновляет единственное, что тянется из источника, второй пишет поля человека и намеренно не трогает привязку

- `backend/storage/repository/external.py:ExternalIdsRepository.ids_of` `086500a6` ≠ `backend/storage/repository/external.py:ExternalRatingsRepository.ratings_of` `d4af5efb` — одинаковая форма запроса, разные таблицы и разные типы на выходе; таблиц две, потому что чужой идентификатор и чужая оценка живут по разным правилам. Разобрано повторно в задаче 2 плана 4: сборка строк уехала в `rows.py`, довод не изменился
- `backend/storage/rows.py:to_external_id` `bee0fea7` ≠ `backend/storage/rows.py:to_external_rating` `f0f9fb2b` — по сборщику на таблицу, каждый знает свои колонки: у идентификатора их два, у оценки три, и пустое значение оценки означает «спрашивали, у источника нет»
- `backend/storage/repository/external.py:ExternalIdsRepository.find_item` `9c373710` ≠ `backend/storage/repository/library.py:LibraryRepository.find_by_source` `91794c3d` — форма отбора по двум колонкам общая, предметы разные: номер карточки по чужому идентификатору против собранной `Item` по своему источнику
- `backend/storage/repository/external.py:ExternalIdsRepository.find_item` `9c373710` ≠ `backend/storage/repository/credits.py:CreditRepository._found_id` `9b43e59d` — общего один вызов `_maybe`: `_found_id` — обёртка без запроса, читающая `row.id`, `find_item` строит отбор по паре и читает `row.item_id`

## Одна карточка против страницы: восемь пар одного довода

Сборка строки в тип у них общая и вынесена в `rows.py`; различаются они тем, на
какой вопрос отвечают. Репозиторий признака отвечает про **одну** карточку — по
номеру, своей сессией, готовым списком. `ViewsRepository` отвечает про
**страницу** — набором номеров, в общей сессии на все девять запросов, и
раскладывает найденное по карточкам, для чего тащит в выборку лишнюю колонку
`item_id`. Слитые, они дали бы метод, у которого от «одной карточки» остался бы
только список из одного номера, а вызывающему пришлось бы разбирать словарь
там, где он ждёт список.

- `backend/storage/repository/views.py:ViewsRepository._genres` `bacadf2f` ≠ `backend/storage/repository/genres.py:GenresRepository.genres_of` `bb731b6d` — довод раздела: набор номеров против одного, общая сессия против своей, словарь по карточкам против списка
- `backend/storage/repository/views.py:ViewsRepository._tags` `6042c858` ≠ `backend/storage/repository/tags.py:TagsRepository.tags_of` `294ca5f1` — довод раздела; вторая к тому же отдаёт пары чисел и строк, а не `Tag`
- `backend/storage/repository/views.py:ViewsRepository._credits` `aba98e4f` ≠ `backend/storage/repository/credits.py:CreditRepository.credits_of` `6ccfc2d3` — довод раздела; сборка `Credit` и описатель `Entity` у них уже общие
- `backend/storage/repository/views.py:ViewsRepository._external` `d5abf46a` ≠ `backend/storage/repository/external.py:ExternalRatingsRepository.ratings_of` `d4af5efb` — довод раздела; сборка строки общая, в `rows.py` 
- `backend/storage/repository/views.py:ViewsRepository._identifiers` `cdd22dad` ≠ `backend/storage/repository/external.py:ExternalIdsRepository.ids_of` `086500a6` — довод раздела; сборка строки общая, в `rows.py` 
- `backend/storage/repository/views.py:ViewsRepository._ratings` `65853a60` ≠ `backend/storage/repository/ratings.py:RatingsRepository.get` `5409417b` — довод раздела; вторая отдаёт одну оценку или `None`, первая словарь по карточкам
- `backend/storage/repository/views.py:ViewsRepository._wishlist` `ee85ac38` ≠ `backend/storage/repository/wishlist.py:WishlistRepository.list_ids` `3fb14d9d` — вторая ещё и отвечает на свой вопрос: не «кто из этих отложен», а «что лежит в списке», с порядком и порцией
- `backend/storage/repository/views.py:ViewsRepository._read` `b1bb1380` ≠ `backend/storage/repository/base.py:Repository._rows` `8d58057c` — тела в одну инструкцию совпадают дословно, и разница ровно в том, кто владеет сессией: `_rows` открывает свою на каждый запрос, `_read` работает в переданной. Слить нельзя, не потеряв то, ради чего репозиторий заведён: девять запросов одной сессией

- `tests/conftest.py:reference` `45d5643d` ≠ `tests/conftest.py:film_genres` `5c190561` — оба сеют справочник жанров руками, наборы разные и подобраны под свои проверки: `reference` включает сборный `10759`, который разворачивается в два жанра, и чужое пространство Steam; `film_genres` — ровно два киножанра, чтобы проверить, что чужой жанр не затирает выбранный руками
## Похоже в тестах, но проверяет разное

- `tests/backend/test_tables.py:counted` `90eaa387` ≠ `tests/backend/test_genre_reference.py:counted` `e5824e9c` — совпало имя: первый асинхронно считает все строки таблицы в базе из объявлений, второй синхронно — `genre_map` с произвольным `JOIN` в базе из миграций
- `tests/backend/test_tables.py:put` `ee996cab` ≠ `tests/conftest.py:stored.put` `8ffa8012` — фикстура подставляет умолчания и отдаёт ключ, помощник кладёт ровно переданное и ничего не возвращает: ему нужна неполная строка, чтобы проверить отказ ограничения
- `tests/backend/test_library.py:make_item` `a6bef63e` ≠ `tests/conftest.py:card` `586388f2` — `card` отдаёт идентификатор уже вставленной карточки, `make_item` — незаписанный `Item` с богатыми полями, который и есть предмет проверки. Разобрано повторно: у `card` появился параметр `title`, довод не изменился
- `tests/conftest.py:picture` `e489ff95` ≠ `tests/conftest.py:PICTURE` `e75cdc7d` — оба про байты постера, но общая только эта фраза: константа набрана вручную и картинкой не разбирается вовсе — она нужна там, где проверяется побайтовая сохранность в хранилище; помощник рисует настоящую картинку заданного размера, потому что размер и есть предмет проверки. Пропусти константу через `crop_to_cover` — получишь `BadImage`
- `tests/backend/test_migrations.py:declared` `b2093d76` ≠ `tests/conftest.py:engine` `91ad94d9` — обе поднимают базу из `metadata`, но одна синхронным драйвером (иначе не сравнить через `inspect`), другая асинхронным (иначе с ней не работают репозитории)

- `tests/backend/test_linking.py:incoming` `c7be1644` ≠ `tests/backend/test_card_writer.py:source_card` `673152f0` — тот же приём «умолчания плюс замены», что у `make_item` и `card`, но карточки разные по назначению: у привязки она с синопсисом и без внешних идентификаторов, у записи — с ними и с двумя жанрами. Слитые, они потянули бы замены в каждый вызов
- `tests/backend/test_linking.py:mine` `3182384d` ≠ `tests/conftest.py:card` `586388f2` — `mine` собирает `Item` в памяти для проверок слияния без базы, `card` вставляет строку и отдаёт номер
## Инструмент карт: похоже внутри одного дела

- `scripts/module_map.py:declared` `0918b161` ≠ `scripts/project_ast.py:declarations.walk` `b6186cbc` — общего две инструкции, обход тела и отбор по `DEFINITIONS`. Дальше расходятся: `declared` пропускает тесты и `__init__`, разбирает псевдонимы и рисует разметку с отступом, а `walk` не пропускает ничего нарочно — вердикт должен уметь сослаться и на тестовый помощник. Общий обходчик потребовал бы передавать и фильтр, и визитёра, то есть больше кода, чем сэкономил бы
- `scripts/module_map.py:_counted` `809febd2` ≠ `scripts/project_ast.py:size` `0c56a09b` — разные дела: первый выдаёт подпись «словарь из 3», второй считает строки узла. Первый и переименован из `_size` ровно потому, что читались они как одно
- `backend/storage/posters.py:PosterStore._write` `630a362e` ≠ `backend/storage/repository/base.py:Repository._run` `0049a4f6` — тот же довод, что у пары `_read` ≠ `_row`: разные транспорты, слить можно было бы только вместе с движком
- `backend/storage/repository/tags.py:_named` `339284af` ≠ `backend/storage/rows.py:to_genre` `9d72e4e8` — оба читают номер и имя, но `_named` отдаёт пару чисел и строк, а не тип границы слоёв: репозиторий тегов старше типа `Tag` и наружу отдаёт кортежи. Разобрано повторно в задаче 2 плана 4, когда вторая сторона переехала в `rows.py`
- `migrations/versions/0002_genres.py:FILM` `ef100e87` ≠ `tests/backend/test_genre_reference.py:FILM_GENRES` `5bdbe97a` — списки совпадают дословно, и в этом смысл: возьми тест набор из миграции, он сойдётся с ней при любой опечатке и не проверит ничего. То же у `GAME` и `GAME_GENRES`

## Карта — общий файл, и импорт из проекта ей запрещён

- `tests/backend/test_layers.py:imported_modules` `b1644497` ≠ `scripts/project_ast.py:depends_on` `c3734473` — обход дерева за импортами похож, но `project_ast.py` совпадает побайтно с образцом в скилле, и импорт между ним и проектным кодом это свойство ломает
- `tests/backend/test_layers.py:python_files` `82dbcb5b` ≠ `scripts/project_ast.py:modules` `2b28675a` — то же основание плюс разные предметы: пути одного пакета против разобранных деревьев по всем корням
