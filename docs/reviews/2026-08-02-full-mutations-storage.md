# Ревью мутациями: хранилище и модель

Дата: 02.08.2026. Измерение — мутации по `backend/storage/`, `backend/model/`,
`migrations/`. Работа шла в отдельном рабочем дереве
(`.claude/worktrees/agent-a0969cb3b0074434c`) и в его копии, чтобы гонять два
потока мутаций разом.

**Внесено 136 мутаций, поймано 116, прошло молча 20.**

Набор до мутаций зелёный: `993 passed` на
`tests/backend tests/bridge --ignore=tests/backend/sources` (752 в `tests/backend`
без источников, 241 в `tests/bridge`). Набор после — тот же, дерево чистое.

## Как гонялось

Три круга. Первый — 106 мутаций, каждая против группы тестов, покрывающих её
область (2–25 с на мутацию). Второй и третий — 30 мутаций, нацеленных туда, куда
указал первый, каждая сразу против **полного** набора.

**Каждая молчаливая перепроверена на полном наборе 993 тестов.** Это не
формальность: две мутации, молчавшие на своей группе, полный набор поймал —
`P02` (снятая ветка «хранилище постеров закрыто») краснит
`test_offline.py::test_everything_closes_and_lets_go`, а `D05` (снятый отбор по
пространству меток в `GenresRepository.index`) —
`test_search.py::test_the_spaces_of_genres_do_not_leak_into_each_other`. Обе
живут в модулях, которых в «своей» группе не было. Ложных молчаливых в отчёте
нет.

Три главные находки дополнительно подтверждены **временной пробой**: написан
файл из четырёх тестов, он зелёный на чистом коде и красный под своей мутацией.
Проба удалена, в репозиторий не попала.

## Сильные стороны

- **Ни одна из 136 мутаций не нашла ошибки поведения в боевом коде.** Все двадцать
  молчаливых — либо дыра в тестах, либо свойство без наблюдаемого следствия.
- **Отборы «только эта карточка» сторожатся везде.** Снятый `where(item_id == ...)`
  краснеет и в `clearing`, и в `_has_item`, и в `deletion_summary`, и в
  `unassign`, и в `_named` — пять разных мест, пять разных тестов. Это самый
  дорогой класс ошибок в хранилище, и он закрыт целиком.
- **Подмена ссылки на человека номером карточки поймана трижды**, тремя
  независимыми путями: `_named` (широкий поиск), `_linked` (подсказка и «всё с
  этим человеком»), `_credits` (пачечное чтение). В тестах номера карточки и
  человека нарочно разведены лишними строками — именно это и делает подмену
  наблюдаемой.
- **Сроки годности внешних оценок сторожатся до границы.** `>` → `>=`, обмен
  `VALUE_TTL`/`EMPTY_TTL`, удвоение любого из двух — четыре мутации, четыре
  разных теста, и сроки записаны литералами, а не выведены из тех же констант.
- **Схема сверяется двумя базами целиком.** `test_migration_matches_the_declared_tables`
  ловит и снятый индекс, и суженный ключ уникальности, и переименование
  ограничения — три мутации, которые сверка по именам таблиц пропустила бы.
- **Порядок в титрах, ручной порядок тегов и порядок закладок сторожатся правильно
  устроенными тестами**: данные заводятся в порядке, обратном ожидаемому, поэтому
  потеря `ORDER BY` наблюдается. Там, где это сделано, мутация краснеет мгновенно.

## Находки

### Critical (обязательно чинить)

Нет. Ошибок поведения в боевом коде мутации не нашли.

### Important (чинить)

#### 1. «Когда оценивал» читает время **первой** оценки, и этого не видит ничто

`backend/storage/repository/sections.py:28` — в `_KEYS` заменено
`Sort.RATED_AT: rating.c.updated_at` на `rating.c.created_at`. Молча на полном
наборе (993 passed).

Гонялись: весь `tests/backend` без источников плюс `tests/bridge`.

Свойство без сторожа — **переоценка двигает карточку в начало списка «по времени
оценки»**. Оба теста на этот порядок
(`test_sections.py:105 test_the_freshly_rated_come_first`, и через него
`test_feed.py`) ставят оценку ровно **один раз**, а при первой записи
`created_at == updated_at` — колонки неразличимы по определению.

Разделение самих колонок при записи сторожится честно
(`test_ratings.py:74 test_second_write_updates_and_keeps_created_at`), но это
проверка репозитория оценок. Между «в базе лежит верно» и «запрос раздела читает
ту колонку, что лежит верно» сторожа нет ни одного.

Наблюдать: две карточки, оценённые давно в известном порядке, одну переоценить
последней — и потребовать, чтобы при `Order(Sort.RATED_AT)` она встала первой.
Проба написана и проверена: зелёная на чистом коде, красная под мутацией.

#### 2. Порядок жанров на пути страницы не сторожит ничто

`backend/storage/repository/views.py:96` — `.order_by(genre.c.name)` заменено на
`genre.c.id` (мутация V04) и снято целиком (X02). Обе молча на полном наборе.

Единственный сторож — `tests/backend/test_views.py:58
test_genres_come_with_the_card`, и его докстринг прямо обещает обратное: «жанров
два, и по алфавиту они идут не в том порядке, в каком записаны». Пара выбрана
`18` и `28` — в фикстуре `reference` это «Драма» (id 3) и «Боевик» (id 1), то
есть алфавитный порядок совпадает с порядком номеров. Тест не может упасть за то,
ради чего написан.

Соседний тест на том же свойстве сделан правильно и в докстринге объясняет как:
`test_genres.py:75 test_set_and_read_genres_of_a_card` берёт пару 2 и 3
(«Приключения» и «Драма»), где алфавит обратен номерам, и мутация
`genres_of: order_by(name) → order_by(id)` (X03) его роняет. В `test_views.py`
надо сделать то же самое.

#### 3. Порядок студий в `credits_of` не сторожится, и два читателя одной карточки расходятся

`backend/storage/repository/credits.py:166` — для сущности без позиции порядок
`table.c.name` заменён на `table.c.id`. Молча на полном наборе.

Тестов на порядок студий в `credits_of` нет вовсе: `test_credits.py:304
test_companies_work_the_same_way` и `:319 test_companies_have_no_position`
вешают на карточку **одну** студию.

Сверх дыры это ещё и расхождение двух путей чтения одного и того же:
`ViewsRepository._credits` сортирует студии по `entity.table.c.id`
(`views.py:128`, и там сторож на трёх студиях —
`test_studios_come_in_a_stable_order`), а `CreditRepository.credits_of` — по
имени. Одна карточка выдаёт студии в разном порядке в зависимости от того, кто её
прочёл.

При этом у порядка в `credits_of` сегодня нет ни одного боевого потребителя:
единственный вызов, `backend/service/linking.py:108`, проверяет непустоту списка.
То есть выбор один из двух — либо привести порядок к общему с пачечным чтением и
завести на него сторож, либо снять `order_by` как объявление без следствия.
Решать это должен пользователь: это уже не починка теста.

#### 4. `CreditRepository.find_by_name` не зовёт никто, кроме тестов

`backend/storage/repository/credits.py:102`. Мутация Z04 (перевернуть порядок
тёзок) прошла молча — и это лишь следствие: во всём проекте нет ни одного вызова
`find_by_name` из `backend/`, `bridge/` или `client/`. Проверено поиском по всем
`.py`, `.js` и `.svelte`.

Это правило 8 манифеста — объявление без потребителя. Метод публичен, покрыт
четырьмя тестами, документирован («Все тёзки. Выбирает между ними человек») — и
никем не используется. Соседи по задаче используются: `find_anonymous_by_name`
зовёт `ensure`, `find_by_source` зовёт он же.

В `docs/deferred.md` этого нет. Решать, снимать или оставить под будущий экран
выбора тёзки, должен пользователь.

### Minor

#### 5. Правила `ix` и `uq` в `naming_convention` не применяются ни разу

`backend/storage/tables/base.py:15` и `:14`. Мутации X13 и Z01 (испортить оба
шаблона) прошли молча; Z02 и Z03 (`pk` и `fk`) пойманы сразу —
`test_migrations.py::test_migration_matches_the_declared_tables`.

Причина: все девять индексов объявлены с явным именем (`Index("ix_item_kind",
"kind")` и далее), все шесть ключей уникальности — тоже
(`UniqueConstraint(..., name="uq_item_source")`). Шаблоны из соглашения при этом
никогда не подставляются.

Докстринг модуля этому противоречит прямо: «Имена ограничениям раздаются здесь и
только здесь». Здесь раздаются `pk` и `fk`; `ix` и `uq` раздаются по месту
объявления. Либо снять две мёртвые строки и поправить докстринг, либо снять
явные имена и оставить соглашение работать.

#### 6. Порядок ничьей: третье место того же рода

`sections.py:121` — снят второй ключ `item.c.id` (S09). Молча.

Тест `test_sections.py:166 test_equal_scores_are_ordered_by_identifier` заведён
ровно под это и в своём докстринге сам пишет, что при выборе планировщиком
`ix_item_kind` потеря не видна. То же уже записано в `docs/deferred.md` про
`LibraryRepository.list_by_kind` и в `test_by_credit.py:114` про `items_of`.

Находка не в самом факте — он трижды измерен и трижды объяснён, — а в том, что
объяснения лежат в трёх разных местах и следующий проход разберёт их заново.
Стоит свести в одну запись `docs/deferred.md`.

#### 7. Порядок чужих оценок и идентификаторов: запись есть, но не про то место

`external.py:43` и `:76` — снят `order_by(source)` у `ids_of` и `ratings_of`
(X06, X07). Обе молча.

`docs/deferred.md` уже фиксирует ровно это свойство, но для
`ViewsRepository._by_source`: составной первичный ключ `(item_id, source)`, отбор
идёт по нему, строки приходят упорядоченными сами. На репозиторий чужих значений
запись не распространена, хотя случай тот же и таблицы те же. Дописать в ту же
запись.

#### 8. Новый тег встаёт в конец только благодаря rowid

`tags.py:22` — `func.coalesce(func.max(position), -1) + 1` → без `+ 1` (T01).
Молча. И `:23` — снят `.where(kind == kind)` при счёте конца набора (T02). Тоже
молча.

Причина у обеих одна: ничью в `ORDER BY position` SQLite разрешает по rowid, а у
только что заведённого тега он всегда больше — «в конце набора» получается и без
`+1`, и со сквозной по обоим наборам нумерацией. Три теста, написанные под это
свойство (`test_a_new_tag_goes_to_the_end_of_its_set`,
`..._after_the_reordered_ones`, `..._last_even_after_deletions`), наблюдают
только порядок в списке.

Свойство наблюдаемо, но лишь чтением самой колонки `position` — проба это
подтвердила. Заводить такой тест стоит только вместе с решением, что позиция —
величина, а не порядок; сегодня она наблюдается лишь как порядок.

#### 9. Недостижимые ветки и эквивалентные подмены

Ниже — мутации, прошедшие молча потому, что различаемого ими состояния сегодня не
бывает. Каждая проверена по коду.

- **`credits.py:119`** (C11): `source_id.is_(None)` → `source.is_(None)`.
  Состояние «источник есть, идентификатора нет» не заводит ни один путь: `create`
  кладёт обе колонки или ни одной, `create_manual` — обе. Схема его допускает,
  код — нет.
- **`credits.py:126`** (C12): `and` → `or` в `ensure`. Та же причина —
  половинчатой идентичности в `Credit` не собирает ничто.
- **`tags.py:85`** (T05): снята проверка `row.tag_kind is None`. Она избыточна:
  соседнее `row.kind != row.tag_kind` на несуществующем теге и так истинно
  (`'movie' != None`). Поведение «несуществующий тег не вешается» остаётся верным
  и сторожится (`test_tags.py:243`).
- **`sections.py:57`** (S02): `func.count(func.distinct(key))` → `func.count(key)`.
  Код это сам предсказывает: `distinct` стоит «на случай, если уникальность пары
  не сторожит сама таблица связи», а у `item_tag` и `item_genre` первичный ключ
  как раз `(item_id, tag_id)`.
- **`sections.py:139`** (S16): `func.count()` → `func.count(item.c.id)`.
  Эквивалент: `item.id` не бывает `NULL`.
- **`statements.py:26`** (Q01): снят фильтр `if name not in keyed`, то есть ключ
  переписывается вместе с остальным. Эквивалент: значения ключа в `excluded`
  равны текущим по определению конфликта.
- **`repository/base.py:61`** (X14): `scalar_one()` → `scalar_one_or_none()`.
  `INSERT ... RETURNING` без строки не бывает — либо строка, либо `IntegrityError`.
- **`model/query.py:56`** (Z08): переставлены местами два первых поля `Filters`.
  Эквивалент: единственная сборка, `bridge/feed.py:54`, идёт по именам
  (`Filters(**{...})`).

## Полный список мутаций

| # | Место | Что изменено | Исход | Кто поймал |
|---|---|---|---|---|
| L01 | `repository/library.py` | list_by_kind: главный ключ порядка стал id вместо названия | поймана | test_library.py::test_the_window_moves_and_never_repeats_a_card |
| L02 | `repository/library.py` | list_by_kind: limit и offset переставлены местами | поймана | test_library.py::test_creating_the_same_identity_twice_is_refused |
| L03 | `repository/library.py` | find_by_title: «или» между названиями стало «и» | поймана | test_library.py::test_a_null_title_does_not_break_the_search_for_duplicates |
| L04 | `repository/library.py` | find_by_title: снят отбор по типу содержимого | поймана | test_library.py::test_find_by_title_matches_original_title_within_one_kind |
| L05 | `repository/library.py` | search: снят отбор по типу содержимого | поймана | test_search_local.py::test_the_type_of_content_never_mixes |
| L06 | `repository/library.py` | search: снята ветка студий | поймана | test_credit_search.py::test_finds_by_the_name_of_a_company |
| L07 | `repository/library.py` | _named: снят отбор по item_id — найдётся любая карточка | поймана | test_credit_search.py::test_a_person_of_another_card_does_not_bring_this_one |
| L08 | `repository/library.py` | _named: соединение по item_id вместо ссылки на человека | поймана | test_credit_search.py::test_finds_by_the_name_of_a_person |
| L09 | `repository/library.py` | replace_fields: правка руками снова пишет synced_at | поймана | test_library.py::test_replace_fields_rewrites_everything_the_human_gave |
| L10 | `repository/library.py` | link: привязка не обновляет synced_at | поймана | test_manual_cards.py::test_link_refreshes_synced_at |
| L11 | `repository/library.py` | unlink: снятая привязка оставляет пустую идентичность | поймана | test_manual_cards.py::test_unlink_returns_the_card_to_manual_and_keeps_the_data |
| L12 | `repository/library.py` | refresh_series_counts: сезоны и серии переставлены местами | поймана | test_library.py::test_refresh_touches_only_seasons_and_episodes |
| L13 | `repository/library.py` | deletion_summary: оценка и закладка переставлены местами | поймана | test_delete.py::test_summary_tells_the_three_apart |
| S01 | `repository/sections.py` | _carrying_all: «все выбранные» стало «хоть одна» | поймана | test_filters.py::test_two_tags_are_joined_by_and |
| S02 | `repository/sections.py` | _carrying_all: снят distinct в счёте | **молча** | недостижимо по схеме |
| S03 | `repository/sections.py` | _included: отбор по оценке стал исключением | поймана | test_filters.py::test_a_score_filter_takes_whole_columns |
| S04 | `repository/sections.py` | _excluded: снята ветка NULL | поймана | test_filters.py::test_an_excluded_score_does_not_empty_the_wishlist |
| S05 | `repository/sections.py` | _excluded: исключение тегов читает включённые | поймана | test_filters.py::test_an_excluded_tag_wins_over_an_included_genre |
| S06 | `repository/sections.py` | _KEYS: порядок по названию мимо своего приведения регистра | поймана | test_sections.py::test_the_alphabet_ignores_case |
| S07 | `repository/sections.py` | _KEYS: «когда оценивал» читает время первой оценки | **молча** | дыра, находка 1 |
| S08 | `repository/sections.py` | ids: сторона порядка перевёрнута | поймана | test_sections.py::test_the_high_scores_come_first |
| S09 | `repository/sections.py` | ids: снят второй ключ порядка | **молча** | известно, находка 6 |
| S10 | `repository/sections.py` | _narrow: условия двух разделов переставлены местами | поймана | test_sections.py::test_the_rated_section_shows_only_what_has_a_score |
| S11 | `repository/sections.py` | _narrow: закладка присоединена внутренним соединением | поймана | test_sections.py::test_the_rated_section_shows_only_what_has_a_score |
| S12 | `repository/sections.py` | _narrow: снят отбор по типу содержимого | поймана | test_sections.py::test_the_type_of_content_never_mixes |
| S13 | `repository/sections.py` | histogram: средняя считается по другому разделу | поймана | test_histogram.py::test_the_footer_counts_the_same_set_the_columns_do |
| S14 | `repository/sections.py` | histogram: средняя по округлённым вниз оценкам | поймана | test_histogram.py::test_the_average_is_not_collected_from_the_columns |
| S15 | `repository/sections.py` | _COLUMN: снято округление вниз | поймана | test_filters.py::test_a_score_filter_takes_whole_columns |
| S16 | `repository/sections.py` | histogram: счёт по колонке вместо звёздочки | **молча** | эквивалент |
| C01 | `repository/credits.py` | attach: снят ON CONFLICT DO NOTHING | поймана | test_credits.py::test_attaching_the_same_role_twice_is_quiet |
| C02 | `repository/credits.py` | attach: позиция пишется тем, у кого её нет | поймана | test_credits.py::test_roles_are_stored_as_their_plain_values |
| C03 | `repository/credits.py` | credits_of: порядок в титрах заменён алфавитным | поймана | test_credits.py::test_attach_keeps_the_order_from_the_credits |
| C04 | `repository/credits.py` | items_of: снят distinct | поймана | test_by_credit.py::test_both_roles_of_one_person_give_one_card |
| C05 | `repository/credits.py` | items_of: снят отбор по вкладке | поймана | test_by_credit.py::test_the_kind_narrows_and_nothing_else_does |
| C06 | `repository/credits.py` | items_of: порядок по оценке перевёрнут | поймана | test_by_credit.py::test_the_highest_rated_comes_first |
| C07 | `repository/credits.py` | items_of: неоценённые выпадают из выдачи | поймана | test_by_credit.py::test_the_unrated_follow_the_rated |
| C08 | `repository/credits.py` | _linked: связь склеена по номеру карточки | поймана | test_suggestions.py::test_hint_is_the_highest_rated_film |
| C09 | `repository/credits.py` | _hint: ступени подсказки переставлены | поймана | test_suggestions.py::test_a_rated_film_beats_a_wished_one |
| C10 | `repository/credits.py` | _hint: узнаётся по самому низко оценённому | поймана | test_suggestions.py::test_hint_is_the_highest_rated_film |
| C11 | `repository/credits.py` | find_anonymous_by_name: пустота проверяется у источника | **молча** | недостижимо |
| C12 | `repository/credits.py` | ensure: «и» заменено на «или» | **молча** | недостижимо |
| C13 | `repository/credits.py` | _name_starts_with: подсказка ищет подстроку | поймана | test_suggestions.py::test_suggest_matches_the_beginning_of_the_name |
| C14 | `repository/credits.py` | suggest: limit и offset переставлены местами | поймана | test_suggestions.py::test_hint_is_the_highest_rated_film |
| C15 | `repository/credits.py` | _outer: ручная идентичность выдаётся за внешнюю | поймана | test_credits.py::test_the_identity_goes_out_only_when_someone_can_be_asked |
| T01 | `repository/tags.py` | create: новый тег встаёт на позицию последнего | **молча** | находка 8 |
| T02 | `repository/tags.py` | create: конец набора считается по всем наборам сразу | **молча** | находка 8 |
| T03 | `repository/tags.py` | reorder: снят отбор по набору | поймана | test_tags.py::test_reorder_does_not_touch_tags_of_another_set |
| T04 | `repository/tags.py` | list_for_kind: порядок по номеру вместо ручной позиции | поймана | test_tags.py::test_a_new_tag_goes_after_the_reordered_ones |
| T05 | `repository/tags.py` | assign: снята проверка на несуществующий тег | **молча** | избыточная ветка |
| T06 | `repository/tags.py` | usage: счёт носителей идёт по колонке карточки | поймана | test_tags.py::test_a_tag_knows_how_many_cards_wear_it |
| T07 | `repository/tags.py` | tags_of: метки карточки в порядке номеров | поймана | test_tags.py::test_tags_of_a_card_keep_the_manual_order |
| T08 | `repository/tags.py` | unassign: тег снимается со всех карточек сразу | поймана | test_tags.py::test_unassign_takes_only_the_asked_pair |
| R01 | `repository/ratings.py` | _write: повторная оценка переписывает время первой | поймана | test_ratings.py::test_second_write_updates_and_keeps_created_at |
| R02 | `model/rating.py` | average_score: делится на число шкал | поймана | test_ratings.py::test_unset_aspect_does_not_drag_the_score_down |
| R03 | `model/rating.py` | average_score: пустая оценка стала нулём | поймана | test_ratings.py::test_clearing_all_aspects_leaves_no_score |
| E01 | `repository/external.py` | stale_sources: граница срока стала включающей | поймана | test_external_ratings.py::test_exactly_at_the_deadline_is_still_fresh |
| E02 | `repository/external.py` | stale_sources: сроки значения и пустоты переставлены | поймана | test_external_ratings.py::test_a_value_lives_a_month |
| E03 | `repository/external.py` | VALUE_TTL: срок годности значения удвоен | поймана | test_external_ratings.py::test_a_value_lives_a_month |
| E04 | `repository/external.py` | EMPTY_TTL: пустой ответ живёт как значение | поймана | test_external_ratings.py::test_an_empty_answer_lives_a_week |
| E05 | `repository/external.py` | find_item: снят отбор по источнику | поймана | test_external_ids.py::test_find_item_by_identifier |
| E06 | `repository/external.py` | put: разрешение конфликта мимо составного ключа | поймана | test_external_ids.py::test_put_and_read_back |
| E07 | `repository/external.py` | record: «у источника нет» пишется нулём | поймана | test_external_ratings.py::test_three_states_are_told_apart |
| W01 | `repository/wishlist.py` | list_ids: старые сверху вместо новых | поймана | test_wishlist.py::test_order_is_newest_first |
| W02 | `repository/wishlist.py` | add: снят ON CONFLICT | поймана | test_wishlist.py::test_adding_twice_keeps_the_first_date |
| V01 | `repository/views.py` | _credits: соединение по номеру карточки | поймана | test_views.py::test_people_come_in_the_order_of_the_credits |
| V02 | `repository/views.py` | _credits: порядок в титрах заменён номером строки | поймана | test_views.py::test_people_come_in_the_order_of_the_credits |
| V03 | `repository/views.py` | _tags: метки в порядке номеров вместо ручного | поймана | test_views.py::test_tags_come_in_their_manual_order |
| V04 | `repository/views.py` | _genres: жанры в порядке номеров вместо алфавитного | **молча** | дыра, находка 2 |
| V05 | `repository/views.py` | in_order: порядок спрошенных номеров потерян | поймана | test_feed.py::test_a_page_keeps_the_order_of_the_section |
| V06 | `repository/views.py` | _fetch_all: люди и студии переставлены местами | поймана | test_views.py::test_people_come_in_the_order_of_the_credits |
| V07 | `repository/views.py` | _fetch_all: признак закладки перевёрнут | поймана | test_views.py::test_a_bare_card_comes_back |
| V08 | `repository/views.py` | _fetch_all: своя оценка не доезжает до карточки | поймана | test_views.py::test_my_own_rating_comes_with_the_card |
| P01 | `posters.py` | open: повторное открытие не закрывает прежний движок | поймана | test_posters.py::test_opening_twice_does_not_lose_the_first_engine |
| P02 | `posters.py` | _opened: снята ветка «хранилище закрыто» | поймана | test_offline.py::test_everything_closes_and_lets_go |
| P03 | `posters.py` | has: пустые байты неотличимы от отсутствия обложки | поймана | test_posters.py::test_an_empty_picture_is_still_there |
| P04 | `posters.py` | put: ключ конфликта — время, а не карточка | поймана | test_posters.py::test_put_and_get |
| Q01 | `statements.py` | upserting: ключ переписывается вместе с остальным | **молча** | эквивалент |
| Q02 | `statements.py` | clearing: снят отбор по карточке | поймана | test_genres.py::test_genres_come_back_with_their_set |
| N01 | `session.py` | folded: своё приведение регистра заменено встроенным | поймана | test_offline.py::test_the_local_search_still_finds |
| N02 | `session.py` | prepare_connection: внешние ключи выключены | поймана | test_session.py::test_foreign_keys_are_enabled_on_every_connection |
| N03 | `session.py` | session_factory: expire_on_commit включён | поймана | test_session.py::test_sessions_do_not_expire_objects_on_commit |
| N04 | `session.py` | fold: приведение к верхнему регистру на обеих сторонах | поймана | test_session.py::test_case_folding_is_registered_on_every_connection |
| Y01 | `entity.py` | Entity.link: имя колонки берётся у таблицы связи | поймана | test_credits.py::test_roles_are_stored_as_their_plain_values |
| Y02 | `entity.py` | PEOPLE/COMPANIES: наборы ролей переставлены местами | поймана | test_credits.py::test_a_credit_carries_the_row_of_the_person |
| O01 | `rows.py` | to_item: пустое оригинальное название отдаётся None | поймана | test_library.py::test_texts_written_past_the_repository_come_back_empty |
| O02 | `rows.py` | to_rating: пустая рецензия отдаётся None | поймана | test_ratings.py::test_score_of_a_film_is_what_was_set |
| O03 | `rows.py` | to_credit: роль отдаётся сырой строкой | поймана | test_views.py::test_people_come_in_the_order_of_the_credits |
| O04 | `rows.py` | to_credit: порядок в титрах не доезжает наружу | поймана | test_views.py::test_people_come_in_the_order_of_the_credits |
| O05 | `rows.py` | grouped: каждая следующая строка вытесняет прежние | поймана | test_views.py::test_genres_come_with_the_card |
| O06 | `rows.py` | to_credit: источник строки состава не доезжает наружу | поймана | test_views.py::test_the_identity_of_a_credit_survives_the_page |
| D01 | `repository/genres.py` | resolve: снято снятие повторов | поймана | test_genres.py::test_overlapping_identifiers_do_not_duplicate |
| D02 | `repository/genres.py` | resolve: снят отбор по пространству меток | поймана | test_genres.py::test_sources_do_not_leak_into_each_other |
| D03 | `repository/genres.py` | set_for_item: пустой набор не очищает прежние жанры | поймана | test_genres.py::test_an_empty_set_clears_the_genres |
| D04 | `repository/genres.py` | list_for_kind: снят отбор по набору жанров | поймана | test_genres.py::test_list_for_kind_keeps_the_two_sets_apart |
| D05 | `repository/genres.py` | index: снят отбор по пространству меток | поймана | test_search.py::test_the_spaces_of_genres_do_not_leak_into_each_other |
| A01 | `repository/base.py` | _has_item: снят отбор по карточке | поймана | test_delete.py::test_summary_counts_only_the_asked_card |
| A02 | `repository/base.py` | _run: транзакция на оператор вместо одной на все | поймана | test_genres.py::test_a_failed_replacement_keeps_the_old_set |
| M01 | `model/link.py` | parse_link: слаг GOG не приводится к нижнему регистру | поймана | test_links.py::test_the_case_of_the_address_does_not_matter |
| M02 | `model/link.py` | parse_link: голое число принимается и для игр | поймана | test_links.py::test_a_bare_identifier_is_refused_for_games |
| M03 | `model/link.py` | parse_link: сериальная ссылка объявляется фильмом | поймана | test_links.py::test_addresses_are_understood |
| M04 | `model/item.py` | new_manual_item: переданное synced_at перебивается | поймана | test_manual_cards.py::test_a_given_moment_is_not_overwritten |
| M05 | `model/view.py` | view_from_item: названия переставлены местами | поймана | test_by_credit.py::test_the_cards_come_back_whole |
| M06 | `model/view.py` | view_from_hit: жанры кандидата теряются | поймана | test_people_search.py::test_the_works_carry_genres_and_the_free_rating |
| G01 | `migrations/0002_genres.py` | сборный жанр TMDB разворачивается в один вместо двух | поймана | test_genre_reference.py::test_tmdb_map_has_thirty_rows_over_twenty_seven_ids |
| G02 | `migrations/0002_genres.py` | теги Steam записаны в пространство жанров | поймана | test_genre_reference.py::test_game_map_covers_both_stores |
| G03 | `migrations/0001_schema.py` | ключ уникальности карточки расширен названием | поймана | test_migrations.py::test_migration_matches_the_declared_tables |
| X01 | `repository/credits.py` | credits_of: студии в порядке номеров, а не по имени | **молча** | дыра, находка 3 |
| X02 | `repository/views.py` | _genres: сортировка снята вовсе | **молча** | дыра, находка 2 |
| X03 | `repository/genres.py` | genres_of: жанры в порядке номеров (контроль) | поймана | test_genres.py::test_set_and_read_genres_of_a_card |
| X04 | `repository/library.py` | search: снят порядок выдачи широкого поиска | поймана | test_search_local.py::test_the_alphabet_orders_the_found |
| X05 | `repository/credits.py` | suggest: подсказка в порядке номеров | поймана | test_suggestions.py::test_suggest_respects_the_limit_and_keeps_the_order |
| X06 | `repository/external.py` | ids_of: снят порядок чужих идентификаторов | **молча** | известно, находка 7 |
| X07 | `repository/external.py` | ratings_of: снят порядок чужих оценок | **молча** | известно, находка 7 |
| X08 | `rows.py` | to_item: пустой адрес обложки отдаётся None | поймана | test_library.py::test_texts_written_past_the_repository_come_back_empty |
| X09 | `rows.py` | to_item: пустой синопсис отдаётся None | поймана | test_library.py::test_texts_written_past_the_repository_come_back_empty |
| X10 | `session.py` | create_engine: папка под базу больше не создаётся | поймана | test_offline.py::test_the_data_folder_is_made_if_it_is_not_there |
| X11 | `tables/catalog.py` | item: снят составной индекс по типу и году | поймана | test_migrations.py::test_migration_matches_the_declared_tables |
| X12 | `tables/mine.py` | tag: ключ уникальности потерял набор | поймана | test_migrations.py::test_migration_matches_the_declared_tables |
| X13 | `tables/base.py` | naming_convention: шаблон `ix` испорчен | **молча** | находка 5 |
| X14 | `repository/base.py` | _created: scalar_one → scalar_one_or_none | **молча** | недостижимо |
| X15 | `model/query.py` | Order: сторона по умолчанию перевёрнута | поймана | test_feed.py::test_a_page_keeps_the_order_of_the_section |
| X16 | `model/view.py` | CardView: закладка по умолчанию включена | поймана | test_view_types.py::test_rows_the_search_does_not_fill_are_empty |
| X17 | `model/item.py` | new_source_id: идентичность перестала быть уникальной | поймана | test_credit_search.py::test_finds_by_the_name_of_a_person |
| X18 | `repository/credits.py` | _hint: «карточки нет» стало нулевым номером | поймана | test_suggestions.py::test_a_person_without_any_card_has_an_empty_hint |
| X19 | `repository/library.py` | deletion_summary: счёт меток идёт по колонке тега | поймана | test_delete.py::test_summary_counts_every_tag |
| X20 | `repository/views.py` | _fetch_all: снят отбор карточек по спрошенным номерам | поймана | test_views.py::test_nothing_comes_back_when_none_of_the_asked_exists |
| X21 | `repository/genres.py` | index: раскладка по нашему номеру, а не по чужому | поймана | test_people_search.py::test_the_works_carry_genres_and_the_free_rating |
| X22 | `statements.py` | upserting: вставка с заменой вместо разрешения конфликта | поймана | test_card_writer.py::test_a_taken_identifier_leaves_nothing_behind |
| Z01 | `tables/base.py` | naming_convention: шаблон `uq` испорчен | **молча** | находка 5 |
| Z02 | `tables/base.py` | naming_convention: шаблон `pk` испорчен | поймана | test_migrations.py::test_migration_matches_the_declared_tables |
| Z03 | `tables/base.py` | naming_convention: шаблон `fk` испорчен | поймана | test_migrations.py::test_migration_matches_the_declared_tables |
| Z04 | `repository/credits.py` | find_by_name: тёзки в обратном порядке номеров | **молча** | находка 4 |
| Z05 | `repository/views.py` | in_order: порядок спрошенных заменён порядком номеров | поймана | test_by_credit.py::test_the_cards_come_back_whole |
| Z06 | `repository/sections.py` | _KEYS: порядок по оценке читает шкалу «картинка» | поймана | test_feed.py::test_a_page_keeps_the_order_of_the_section |
| Z07 | `repository/tags.py` | reorder: порядок переставляется задом наперёд | поймана | test_tags.py::test_a_new_tag_goes_after_the_reordered_ones |
| Z08 | `model/query.py` | Filters: два первых поля переставлены местами | **молча** | эквивалент |

## Вердикт

**Готово к продолжению работы?** Да

**Обоснование:** 136 мутаций не нашли в хранилище и модели ни одной ошибки
поведения — все двадцать молчаливых либо не имеют наблюдаемого следствия, либо
указывают на дыру в тестах, а не в коде. Три дыры (`RATED_AT` по `created_at`,
порядок жанров на пути страницы, порядок студий в `credits_of`) стоит закрыть
тестами по образцу соседних, правильно устроенных; два вопроса — мёртвый
`find_by_name` и расхождение двух читателей по порядку студий — решает
пользователь, потому что это уже не починка теста.
