# Ревью тестов слайса — `CardWriter` и `resolved_genres`

Прогон: `pytest tests/backend/test_card_writer.py tests/backend/test_genre_resolution.py`
— 24 passed, 3.61 c. Только чтение, мутаций не вносил.

Файлы под ревью: `backend/service/cards.py`, `backend/service/genres.py`.

## Тест — наблюдаемое следствие — что его уронит

### `tests/backend/test_card_writer.py`

| Тест | Следствие | Строка |
|---|---|---|
| `test_a_whole_card_lands_in_the_database` | `title`/`runtime`/`year` карточки доезжают неповреждёнными | `cards.py:53` (`create(card.item)`) — но фактически проверяет `LibraryRepository`, не собственную логику `CardWriter` |
| `test_genres_are_resolved_through_the_reference` | набор имён жанров совпадает с ожидаемым | `cards.py:81` (аргумент `card.genre_ext_ids`/сам вызов `resolved_genres`) |
| `test_people_are_attached_with_their_roles` | роль и позиция привязаны к конкретному имени (`position=0` не теряется) | `cards.py:84` (репозиторий) и `cards.py:99–100` (`credit.role, credit.position`) |
| `test_the_same_person_on_two_cards_is_one_row` | один человек на двух карточках — одна строка, обе привязаны | `cards.py:84` (репозиторий перепутан); дедуп по `source_id` — логика `CreditRepository.ensure`, вне ревизуемых файлов |
| `test_two_namesakes_from_the_source_do_not_merge` | тёзки с разными `source_id` — разные строки | то же — `cards.py:84`, дедуп сам вне файла |
| `test_studios_without_identity_are_merged_by_name` | студии без идентичности клеятся по имени | `cards.py:85` (репозиторий перепутан на `self._people`) |
| `test_companies_are_written_for_a_game` | студия с ролью `DEVELOPER` привязана к игре | `cards.py:85` |
| `test_people_and_studios_do_not_land_in_one_another` | люди и студии не путаются местами ни в одну, ни в другую сторону | `cards.py:84` **и** `cards.py:85` — единственный тест, ловящий перестановку в обе стороны |
| `test_external_identifiers_and_ratings_are_written` | внешний id и оценка агрегатора с `fetched_at == WHEN` пишутся | `cards.py:87–88` (id), `cards.py:89–90` (оценка) |
| `test_the_poster_is_stored` | скачанные байты лежат в хранилище нетронутыми | `cards.py:92–93`; также ловит подмену `self.posters.save` на `self.posters.store_upload` (обрезка) |
| `test_a_prefetched_poster_is_not_downloaded_again` | переданные байты не перекачиваются повторно | `cards.py:45` (`if poster is None:`) |
| `test_a_card_without_a_poster_url_is_still_written` | без `poster_url` карточка всё равно пишется, постера нет | `cards.py:92` (`if poster is not None:`) — без охраны `save` уронит запись на `None` |
| `test_nothing_is_written_when_the_poster_fails` | отказ CDN не даёт карточке попасть в базу, `source == "poster:tmdb"` | `cards.py:48–50` (`if isinstance(poster, Refusal): return poster`) |
| `test_an_unreachable_cdn_keeps_its_reason` | `reason is Reason.NETWORK`, не переобёрнут | `cards.py:50` (`return poster` вместо `return self._refuse(...)`) |
| `test_a_taken_identifier_leaves_nothing_behind` | отказ `("tmdb", Reason.BROKEN)` + карточка убрана целиком | `cards.py:69` (уборка), `70` (refuse вместо item_id), `74–76` (источник/причина отказа) — один тест ловит все четыре |
| `test_the_rollback_takes_the_poster_with_it` | постер снесённой карточки не достаётся следующему номеру | `cards.py:69` (`self.posters.store` в вызове `delete`) |
| `test_a_taken_card_identity_is_a_refusal_not_an_exception` | конфликт по идентичности — `Refusal`, не исключение наружу | `cards.py:54` (`except ItemExists`) |
| `test_an_unknown_genre_does_not_stop_the_card` | незнакомый жанр молча отбрасывается, известный остаётся | нет своей строки в `cards.py`/`genres.py` — фильтрация целиком в `GenresRepository.resolve` (JOIN не находит строку) |
| `test_two_spaces_of_one_card_are_asked_apart` | `9` в двух пространствах даёт два разных жанра | `genres.py:20–22` (ключ `space` в `spaces.setdefault`) |
| `test_one_genre_from_two_tags_is_written_once` | `genres_of` отдаёт `RPG` один раз | **см. дыру ниже** — через базу дедуп на `genres.py:27` не проверяется |

### `tests/backend/test_genre_resolution.py`

| Тест | Следствие | Строка |
|---|---|---|
| `test_spaces_are_asked_apart` | список `[1, 2]` — оба пространства спрошены | `genres.py:21` (ключ `space`) |
| `test_one_genre_from_two_tags_is_returned_once` | `found == [3]`, не `[3, 3]` | `genres.py:27` (`if genre_id not in found:`) |
| `test_one_genre_from_two_spaces_is_returned_once` | повтор между `steam_tag` и `steam` снят | `genres.py:27` — тот же счётчик `found`, теперь через границу пространств |
| `test_nothing_known_gives_an_empty_list` | пустой список, не исключение | `genres.py:25–26` (пустой `ext_ids` не должен падать) — слабо: скорее проверяет `GenresRepository.resolve` на пустом входе |

## Дыры

**Средняя.** `test_one_genre_from_two_tags_is_written_once` (в `test_card_writer.py`) не
доказывает то, что заявляет. `item_genre` имеет
`PrimaryKeyConstraint("item_id", "genre_id")`, а `GenresRepository.set_for_item`
пишет через `.on_conflict_do_nothing()` (`backend/storage/repository/genres.py:54`).
Если убрать дедуп на `genres.py:27` (`if genre_id not in found:`), `resolved_genres`
вернёт `[12, 12]`, `set_for_item` тихо проглотит вторую вставку тем же
конфликтом первичного ключа — и `genres_of(item_id)` всё равно отдаст `RPG`
один раз. Тест через базу пройдёт даже при сломанной строке. Реальная защита —
только `test_one_genre_from_two_tags_is_returned_once` в `test_genre_resolution.py`,
который смотрит на возвращённый список напрямую. Это ровно то, о чём
предупреждает докстринг самого `test_genre_resolution.py` («через базу это не
проверить»), но предупреждение не распространили на одноимённый тест в
`test_card_writer.py` — он выглядит как проверка того же самого, а на деле
дублирует чужую гарантию (константу на схеме), а не строку сервиса.

**Малая.** `test_an_unknown_genre_does_not_stop_the_card` и
`test_nothing_known_gives_an_empty_list` не имеют своей строки в
`cards.py`/`genres.py`: отбрасывание незнакомого id целиком сделано в
`GenresRepository.resolve` (JOIN не находит строку в `genre_map`). Оба теста
полезны как регрессия на границе, но ни один не назовёшь тестом ревизуемого
слайса — это скорее лишний прогон уже проверенной репозиторием логики.

**Малая (не дыра, а слабое звено).** `test_a_whole_card_lands_in_the_database` и
`test_the_same_person_on_two_cards_is_one_row` /
`test_two_namesakes_from_the_source_do_not_merge` привязаны к строке `cards.py`
лишь постольку, поскольку она передаёт данные дальше без изменений; ядро
проверяемого поведения (дедуп по `source_id`, целостность полей `Item`) живёт в
`LibraryRepository`/`CreditRepository`, вне двух файлов этого ревью.

## Непроверенное поведение

- **`synced_at` у постера.** `cards.py:93` пишет
  `self.posters.save(item_id, poster, card.item.synced_at)`. `PosterStore` хранит
  `fetched_at`, но не отдаёт его наружу (`get`/`has` — только данные и факт
  наличия). Ни один тест не может отличить `card.item.synced_at` от
  `datetime.now()`, подставленного по ошибке, — некому спросить об этом поле.
  Подмена аргумента на `datetime.now()` пройдёт все 24 теста молча.
- **Уборка жанров/людей/студий/id/оценок при откате.** `test_a_taken_identifier_leaves_nothing_behind`
  и `test_the_rollback_takes_the_poster_with_it` проверяют только исчезновение
  строки `item` и постера. Уход `item_genre`/`person_credit`/`company_credit`/
  `external_id`/`external_rating` целиком держится на `ondelete="CASCADE"` в
  схеме (`backend/storage/tables/base.py`, `catalog.py`) — код `cards.py` тут ни
  при чём, вызывает лишь `self._library.delete(...)`. Это и не должно быть
  предметом теста `CardWriter`, но стоит заметить: в `tests/backend/test_delete.py`
  (совсем другой слайс) каскад тоже проверен только для оценки, тегов и
  закладки — жанры, люди, студии, внешние id и оценки агрегаторов там тоже не
  фигурируют. То есть каскад для этих пяти таблиц не подтверждён нигде в
  тестах, хотя на нём держится ключевая гарантия «частичной карточки не
  бывает».
- **Вторая запись той же карточки.** Не тестируется как «обновление» — и не
  должна: `CardWriter.save` не умеет перезаписывать, только отказывает
  (`test_a_taken_card_identity_is_a_refusal_not_an_exception`). Обновление —
  отдельный путь по спекам, вне этого файла.
- **`seasons_count`/`episodes_count` сериала.** Ни `source_card`, ни `game_card`,
  ни один тест этого слайса не заводит `Kind.SERIES` с этими полями и не
  проверяет их после `save`. Раз `CardWriter` передаёт `card.item` в
  `LibraryRepository.create` без собственной логики для этих полей, дыры в
  `cards.py` тут скорее всего нет, но фактическая проверка отсутствует именно в
  этом слайсе.
- **Пустые наборы по отдельности для «своего» типа.** Пустые `people`, `genre_ext_ids`,
  `external_ids`, `ratings` проверены — но только через `game_card()`, то есть
  все четыре разом и одновременно с игрой. Явного теста «фильм без жанров» или
  «фильм без людей» нет; сейчас отсутствие ошибки на пустом входе подтверждено
  косвенно.

## Помощники и фикстуры

- **`game_card`** подменяет разом шесть полей (`item`, `genre_ext_ids`, `people`,
  `external_ids`, `ratings`, `companies`). Это осознанно и подписано
  докстрингом «жанры и оценки к делу не идут» — но эффект в том, что все тесты
  на `game_card` одновременно ничего не говорят про поведение жанров/оценок/id
  для игр в паре со студиями: взаимодействие этих путей друг с другом (пишутся
  ли жанры одновременно с компанией на одной карточке) нигде не проверено. Не
  дыра относительно заявленного мутациями поведения, но сознательно сузили
  область теста.
- **`source_card`/`another_movie`** делят один и тот же набор `people`
  (Нолан/Макконахи с фиксированными `source_id`) — это то, что и требуется
  тестам на склейку/различение людей, подмены не нашёл.
- **`poster_service`** (в `tests/conftest.py`) собирает клиентов на все три
  источника с одним транспортом — нейтрально, не маскирует логику `cards.py`.
- **`unreachable`** (в `tests/backend/sources/conftest.py`) — простой
  генератор `ConnectError`, ничего специфичного не прячет; используется ровно
  там, где нужно различить «нет связи» от «непонятный ответ».
- **`POSTER = picture(600, 900, fmt="JPEG")`** намеренно отличается форматом
  (JPEG) от `ready = picture(600, 900)` (PNG по умолчанию) в
  `test_a_prefetched_poster_is_not_downloaded_again` — это и позволяет тесту
  различить «переданные байты» от «перекачанных», не читая сетевых вызовов
  напрямую. Работает, не хрупко.
- **`build`/`writer`** ничего не прячут: `writer` — обёртка над `build` с
  дефолтным транспортом, `build` явно принимает `transport` там, где тест
  должен управлять ответом CDN.

## Вердикт

24/24 теста читаемы и по большей части бьют в конкретную строку
`cards.py`/`genres.py`. Одна настоящая дыра — `test_one_genre_from_two_tags_is_written_once`
в `test_card_writer.py` не может поймать поломку дедупа на `genres.py:27`,
потому что `on_conflict_do_nothing()` на `PrimaryKeyConstraint("item_id",
"genre_id")` глушит дубль на уровне записи; страховка есть, но она лежит в
`test_genre_resolution.py`, а не здесь. Отдельно не покрыто: `synced_at` у
постера (никто не может его прочитать через публичный API хранилища) и
каскадная уборка жанров/людей/студий/id/оценок при откате (держится на схеме,
не подтверждена тестами ни в этом слайсе, ни в `test_delete.py`).
