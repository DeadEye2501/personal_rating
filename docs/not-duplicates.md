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

- `backend/sources/steam/client.py:SteamClient.card` `094bdf08` ≠ `backend/sources/gog/client.py:GogClient._catalog` `2035e450` — обе начинаются с двух строк «пришёл не ответ, а готовый отказ — верни его как есть». Идиома повторяется в десяти местах восьми файлов, и это осознанно: короче она не станет, а вынести её можно было бы только вместе с самим `SourceHttp.get`, поменяв его контракт с «ответ или отказ» на исключение. Разобрано на финальном ревью плана 2

## Один глагол над разными предметами

- `backend/sources/http.py:SourceHttp.get` `495a656f` ≠ `backend/sources/tmdb/client.py:TmdbClient.search` `5149532a` — обе ловят исключение и возвращают `Refusal`, но ловят разное и по разным причинам: первая — сбой провода, вторая — тело, которое не разобралось. Слитые, они назвали бы поломку TMDB пропавшим интернетом
- `backend/storage/repository/tags.py:TagsRepository.list_for_kind` `b0916f5a` ≠ `backend/storage/repository/genres.py:GenresRepository.list_for_kind` `4a9010a7` — разные таблицы и разные наборы значений `kind`; общее уже вынесено в `Repository._mapped`
- `backend/storage/repository/tags.py:TagsRepository.tags_of` `294ca5f1` ≠ `backend/storage/repository/genres.py:GenresRepository.genres_of` `77d87e9a` — одинаковая форма запроса, разные таблицы, соединения и порядок
- `backend/storage/repository/genres.py:_to_genre` `ae074f0e` ≠ `backend/storage/repository/library.py:_to_item` `52c03399` — по одному преобразователю строки на репозиторий, каждый знает свои колонки: ровно тот случай, ради которого заведён `Repository._mapped`
- `backend/storage/repository/library.py:LibraryRepository.refresh_series_counts` `880542f8` ≠ `backend/storage/repository/library.py:LibraryRepository.replace_fields` `a68829f1` — два пути обновления заведены нарочно: первый обновляет единственное, что тянется из источника, второй пишет поля человека и намеренно не трогает привязку

## Похоже в тестах, но проверяет разное

- `tests/backend/test_tables.py:counted` `90eaa387` ≠ `tests/backend/test_genre_reference.py:counted` `e5824e9c` — совпало имя: первый асинхронно считает все строки таблицы в базе из объявлений, второй синхронно — `genre_map` с произвольным `JOIN` в базе из миграций
- `tests/backend/test_tables.py:put` `ee996cab` ≠ `tests/conftest.py:stored.put` `8ffa8012` — фикстура подставляет умолчания и отдаёт ключ, помощник кладёт ровно переданное и ничего не возвращает: ему нужна неполная строка, чтобы проверить отказ ограничения
- `tests/backend/test_library.py:make_item` `a6bef63e` ≠ `tests/conftest.py:card` `acc7b9c8` — `card` отдаёт идентификатор уже вставленной карточки, `make_item` — незаписанный `Item` с богатыми полями, который и есть предмет проверки
- `tests/backend/test_migrations.py:declared` `b2093d76` ≠ `tests/conftest.py:engine` `91ad94d9` — обе поднимают базу из `metadata`, но одна синхронным драйвером (иначе не сравнить через `inspect`), другая асинхронным (иначе с ней не работают репозитории)

## Инструмент карт: похоже внутри одного дела

- `scripts/module_map.py:declared` `0918b161` ≠ `scripts/project_ast.py:declarations.walk` `b6186cbc` — общего две инструкции, обход тела и отбор по `DEFINITIONS`. Дальше расходятся: `declared` пропускает тесты и `__init__`, разбирает псевдонимы и рисует разметку с отступом, а `walk` не пропускает ничего нарочно — вердикт должен уметь сослаться и на тестовый помощник. Общий обходчик потребовал бы передавать и фильтр, и визитёра, то есть больше кода, чем сэкономил бы
- `scripts/module_map.py:_counted` `809febd2` ≠ `scripts/project_ast.py:size` `0c56a09b` — разные дела: первый выдаёт подпись «словарь из 3», второй считает строки узла. Первый и переименован из `_size` ровно потому, что читались они как одно
- `backend/storage/posters.py:PosterStore._write` `630a362e` ≠ `backend/storage/repository/base.py:Repository._run` `0049a4f6` — тот же довод, что у пары `_read` ≠ `_row`: разные транспорты, слить можно было бы только вместе с движком
- `backend/storage/repository/tags.py:_named` `339284af` ≠ `backend/storage/repository/genres.py:_to_genre` `ae074f0e` — по преобразователю строки на репозиторий, каждый знает свои колонки; общее уже вынесено в `Repository._mapped`
- `migrations/versions/0002_genres.py:FILM` `ef100e87` ≠ `tests/backend/test_genre_reference.py:FILM_GENRES` `5bdbe97a` — списки совпадают дословно, и в этом смысл: возьми тест набор из миграции, он сойдётся с ней при любой опечатке и не проверит ничего. То же у `GAME` и `GAME_GENRES`

## Карта — общий файл, и импорт из проекта ей запрещён

- `tests/backend/test_layers.py:imported_modules` `b1644497` ≠ `scripts/project_ast.py:depends_on` `c3734473` — обход дерева за импортами похож, но `project_ast.py` совпадает побайтно с образцом в скилле, и импорт между ним и проектным кодом это свойство ломает
- `tests/backend/test_layers.py:python_files` `82dbcb5b` ≠ `scripts/project_ast.py:modules` `2b28675a` — то же основание плюс разные предметы: пути одного пакета против разобранных деревьев по всем корням
