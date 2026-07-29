# Ревью: повторы в проекте, второй проход

29.07.2026. Измерение — повторы. Читались `docs/module-map.md`,
`docs/data-map.md` и `docs/not-duplicates.md`; каждый кандидат, оставшийся после
отсева, подтверждался чтением обоих мест в коде.

Прочитано: 53 модуля карты, 201 объявление в карте модулей, 190 записей в карте
данных, 15 разобранных пар в файле вердиктов (пропущены без проверки).

## Подтверждённые повторы

Нет.

## Особое внимание: раздел инструмента карт на три модуля

Проверено первым делом — при переносе кода копия на старом месте не осталась.

`scripts/module_map.py` не объявляет ни одного из одиннадцати имён, которые
берёт у соседа: `DEFINITIONS`, `FUNCTIONS`, `ROOT`, `declarations`,
`depends_on`, `exported`, `implementations`, `modules`, `roots`, `signature`,
`size` импортируются из `scripts/project_ast.py`, а `seal`, `expired` и
`verdict_lines` — из `scripts/not_duplicates.py`. `ROOT` живёт в одном месте,
`MAP`, `DATA_MAP` и `VERDICTS` строятся от него. Обратных импортов нет: разбор
не знает про разметку, вердикты не знают про карты.

## Отвергнутые кандидаты

| Кандидат | Почему не повтор |
|---|---|
| `scripts/module_map.py:declared` vs `scripts/project_ast.py:declarations.walk` | Общего две инструкции — обход тела и отбор по `DEFINITIONS`. Дальше расходятся: `declared` пропускает тесты и `__init__`, разбирает псевдонимы типов и рисует разметку с отступом; `walk` не пропускает ничего нарочно — вердикт должен уметь сослаться и на тестовый помощник, — и собирает точечное имя с отпечатком. Общий обходчик потребовал бы передавать и фильтр, и визитёра, то есть больше кода, чем сэкономил бы, и утащил бы вопрос «что показывать» из карты в разбор |
| `scripts/module_map.py:_size` vs `scripts/project_ast.py:size` | Общее слово в имени: первый выдаёт подпись «словарь из 3», второй считает строки узла. Имена стоят рядом в одном пространстве имён, и это читается неудачно, но делают они разное |
| `backend/storage/session.py:create_engine.prepare` vs `migrations/env.py:migrate.prepare` | По две строки, и обе зовут общий `prepare_connection` — то есть общее уже вынесено. Остаток — переходник под подпись слушателя, и вешается он на разные движки: асинхронный `sync_engine` против синхронного алембиковского |
| `backend/storage/posters.py:PosterStore._write` vs `backend/storage/repository/base.py:Repository._run` | Тот же довод, что уже записан в вердиктах для пары `_read` ≠ `_row`: разные транспорты. Слить можно было бы только вместе с движком, а он у них разный по построению |
| `backend/storage/repository/tags.py:_named` vs `backend/storage/repository/genres.py:_to_genre` | По одному преобразователю строки на репозиторий, каждый знает свои колонки; общее уже вынесено в `Repository._mapped` — ровно то основание, по которому в вердиктах разобрана пара `_to_genre` ≠ `_to_item` |
| `backend/storage/repository/library.py:ItemExists` vs `backend/storage/repository/tags.py:TagExists` | Совпадает форма — исключение в две строки, — но не дело: одно говорит «такая карточка уже есть», другое «такой тег уже есть», и слитое перестало бы различать их на стороне интерфейса |
| `backend/model/kinds.py`: `Source`, `GenreSource`, `IdSource`, `RatingSource` | Наборы пересекаются значениями, но ни один не равен другому и не вложен в другой: в `Source` есть `manual` и нет `imdb`, в `GenreSource` — теговые половины `steam_tag` и `gog_tag`, в `RatingSource` — `rotten` и `metacritic`. Общее у них только то, что имена магазинов пишутся одинаково |
| `backend/model/kinds.py:Kind` vs `GenreKind` | `film` в жанрах покрывает и `movie`, и `series`: наборы разного размера и разного смысла |
| `backend/storage/tables/base.py:metadata` vs `backend/storage/posters.py:metadata` | Два файла базы — принятое решение, а не случайность; схемы у них не пересекаются ни одной таблицей |
| `migrations/versions/0002_genres.py:FILM` vs `tests/backend/test_genre_reference.py:FILM_GENRES` (и `GAME` vs `GAME_GENRES`) | Списки совпадают дословно, и в этом смысл: возьми тест набор из миграции — он сойдётся с ней при любой опечатке и не проверит ничего. Поимённо соответствия сторожит третья сторона, `scripts/genre_map.py`, сверкой миграции со спекой |
| `scripts/genre_map.py` vs `tests/backend/test_genre_reference.py` | Разные предметы сверки: скрипт сравнивает текст миграции с таблицами спек, тест — поднятую миграциями базу с ожиданиями, написанными руками. Тест скрипт не повторяет, а запускает — иначе тот не запускается нигде |
| `tests/backend/test_genres.py:reference` vs `tests/conftest.py:migrated` | Фикстура кладёт четыре жанра руками, потому что проверяет разрешение идентификаторов, а не содержимое справочника; `migrated` поднимает базу миграциями целиком |
| `tests/backend/test_delete.py:furnished` vs `tests/backend/test_library.py:in_both_stores` | Первый навешивает на одну карточку всё, что должно уйти вместе с ней; второй заводит две карточки одной игры под одним номером в двух магазинах |
| `tests/scripts/test_module_map.py:shown`, `only` vs `tests/scripts/test_project_ast.py:indexed` | Все три разбирают строку кода в дерево, но каждый зовёт свою проверяемую функцию: `contents`, `assigned` и `declarations`. Общее — одна инструкция `ast.parse` |
| `PICTURE` в `tests/backend/test_delete.py` и `tests/backend/test_posters.py` | Разные размеры под разные проверки; общего — восьмибайтная сигнатура PNG |
| `HEADERS` в `scripts/collect_game_genres.py` и `scripts/record_fixtures.py` | Значение уже общее: оба берут `USER_AGENT` из `backend.sources.http`. Повторён литерал словаря в одну строку |
| `ROOT` в `scripts/genre_map.py`, `scripts/record_fixtures.py`, `tests/alembic_runner.py` | Одна и та же строка-идиома в трёх местах, но вынести её некуда: общий модуль связал бы тестовый помощник с разовым скриптом. `project_ast.ROOT` заведомо другой — он ищет `.git` от текущей папки вверх, а не считает `parents` от своего пути |
| `LibraryRepository.list_by_kind` vs `WishlistRepository.list_ids`; `GenresRepository.set_for_item` vs `TagsRepository.assign`; `get` у `PosterStore`, `LibraryRepository` и `RatingsRepository` | Один глагол над разными предметами: разные таблицы, разные возвраты, у тегов вдобавок проверка типа содержимого и замена целиком против добавления по одному |

## Что стоит записать в вердикты

Чтобы следующий проход не разбирал их заново, в `docs/not-duplicates.md`
просятся пять пар из таблицы выше — те, что видны из карт и будут всплывать
каждый раз: `declared` ≠ `declarations.walk`, `_size` ≠ `size`,
`PosterStore._write` ≠ `Repository._run`, `_named` ≠ `_to_genre`,
`FILM_GENRES` ≠ `FILM` вместе с `GAME_GENRES` ≠ `GAME`.

## Не по измерению, но замечено

В репозитории лежит чужая рабочая копия:
`.claude/worktrees/agent-a45cb97ff213f82a4/` — 4.2 МБ, в ней побайтные копии
всех трёх скриптов карты. Из карт она не видна (папка в `SKIP`), в git не
попадает (`.gitignore`), но на шаге чистки её место — в удалённых.
