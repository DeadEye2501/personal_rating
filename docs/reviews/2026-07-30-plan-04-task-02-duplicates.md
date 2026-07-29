# Ревью повторов — план 4, задача 2 (пачечное чтение карточек)

Измерение: повторы во всём проекте. Дифф не читался.

## Что читал

- `docs/module-map.md`, `docs/data-map.md` целиком (свежие, собраны скриптом).
- `docs/not-duplicates.md` целиком — пары ниже с ним сверены, повторно
  разобранное не повторяю.
- Код целиком: `backend/storage/repository/views.py`, `backend/storage/rows.py`,
  `backend/storage/repository/library.py`, `backend/storage/repository/credits.py`,
  `backend/storage/repository/external.py`, `backend/storage/repository/ratings.py`,
  `backend/storage/repository/tags.py`, `backend/storage/repository/genres.py`,
  `backend/storage/repository/wishlist.py`, `tests/conftest.py` (фикстуры
  `reference`, `film_genres`), `tests/backend/test_views.py`.
- Поиском проверено: нет ли ещё одной сборки `Item` из `Row` кроме
  `rows.py:to_item` (`grep 'Item('` по `backend/`) — только `rows.py` строит
  `Item` из `Row`; остальные вхождения строят `Item` из словаря источника
  внутри `SourceCard`, это другой предмет.

## Кандидаты, рассмотренные и отклонённые

- **`ViewsRepository._genres` vs `GenresRepository.genres_of`.** Форма запроса
  разная не по флагу, а по необходимости: пачечная версия обязана выбрать
  `item_genre.c.item_id`, чтобы сгруппировать результат по карточкам, и не
  может пройти через `Repository._mapped` (нет группировки по ключу). Разница
  оправданная — «одна карточка против пачки».
- **`ViewsRepository._tags` vs `TagsRepository.tags_of`.** То же основание, плюс
  разные типы на выходе: `tags_of` отдаёт `tuple[int, str]` для управления
  тегами, `_tags` строит датакласс `Tag` для карточки. Конвертера в `Tag` в
  `tags.py` нет вовсе — заводить его в `views.py` не у кого отбирать.
- **`ViewsRepository._wishlist` vs `WishlistRepository.contains`/`list_ids`.**
  `contains` — `EXISTS` на одну карточку через `_has_item`, `list_ids` —
  постраничный список всех закладок по дате. `_wishlist` — пачечная проверка
  принадлежности по набору `item_id`; ни с одним из двух не сливается без
  потери своей формы.
- **`backend/storage/rows.py:to_item`** — второй сборки `Item` из строки базы
  не нашлось нигде. `views.py` зовёт этот же `to_item`, как и было целью
  задачи.
- **Фикстура `reference` (`tests/conftest.py`) vs `film_genres` там же.**
  Наборы разные по составу и происхождению: `reference` — четыре жанра
  (три киножанра плюс игровой), с составным `tmdb:10759`, для тестов
  разрешения идентификаторов и теперь для `test_views.py`; `film_genres` —
  два киножанра `tmdb:878`/`tmdb:12`, ровно то, что нужно карточкам по
  умолчанию в `test_card_writer.py`/`test_linking.py`. Пересекаются только
  форматом заполнения через общий `seed`. Разного назначения, сливать нечего.
- **`_Credits._genres`/`_tags`/`_external` как «один глагол над разными
  предметами».** Форма всех пяти методов `_fetch_all` (запрос по `item_id IN
  (...)`, группировка в `defaultdict`) совпадает по виду, но читает каждый
  свою таблицу под свою задачу — это тот самый случай, который инструкция
  прямо называет не-повтором.

## Подтверждённые повторы

Общая причина у всех пяти: `ViewsRepository` при сборке пачки строит модель из
строки заново вместо вызова уже существующего конвертера того же репозитория —
хотя запрос (пачка против одной карточки) отличается оправданно, перевод
`Row → датакласс` не отличается вовсе.

1. **Жанр.** `backend/storage/repository/genres.py:_to_genre` (14-15) —
   `Genre(id=row.id, name=row.name, kind=GenreKind(row.kind))` — и
   `backend/storage/repository/views.py:ViewsRepository._genres` (119-122)
   строят `Genre` из строки дословно одинаково. Остаться должен `_to_genre`,
   `_genres` обязан звать его на каждой строке вместо инлайна.

2. **Внешний идентификатор.**
   `backend/storage/repository/external.py:_to_external_id` (23-24) и
   `views.py:ViewsRepository._identifiers` (196-198) строят `ExternalId`
   дословно одинаково. Остаться должен `_to_external_id`.

3. **Внешняя оценка.**
   `backend/storage/repository/external.py:_to_external_rating` (27-30) и
   `views.py:ViewsRepository._external` (180-183) строят `ExternalRating`
   дословно одинаково, включая порядок полей. Остаться должен
   `_to_external_rating`.

4. **Своя оценка.** `backend/storage/repository/ratings.py:_to_rating` (14-24)
   и `views.py:ViewsRepository._ratings` (207-214) строят `Rating` дословно
   одинаково, вплоть до `review=row.review or ""`. Остаться должен
   `_to_rating`.

5. **Титры — конвертер.**
   `backend/storage/repository/credits.py:CreditRepository._to_credit`
   (219-229) и `views.py:ViewsRepository._credits` (159-167) строят `Credit`
   по одинаковому набору полей: имя, роль через `roles(...)`, позиция при
   условии наличия порядка, источник и его идентификатор. Разница только в
   том, откуда берётся условие («есть ли позиция») — `self._entity.position
   is not None` против `kept.ordered`, — то есть в описателе, а не в самой
   сборке (см. пункт 6). Логика конвертации должна остаться одна, доступная
   обеим сторонам.

6. **Титры — описатель.** `backend/storage/repository/credits.py:Entity` +
   `PEOPLE`/`COMPANIES` (365-371 в карте данных) и
   `backend/storage/repository/views.py:_Credits` + `_PEOPLE`/`_STUDIOS`
   (44-60) описывают одну и ту же пару связей (`person`+`person_credit`,
   `company`+`company_credit`) двумя похожими, но не идентичными
   дата-классами:
   - `Entity.position: Column | None` хранит саму колонку позиции (или её
     отсутствие);
   - `_Credits.ordered: bool` хранит только флаг, а колонку `link.c.position`
     код обращается напрямую по имени, дублируя то, что уже несёт `Entity`;
   - `_Credits.key` хранит явной колонкой то, что в `credits.py` уже
     вычисляется свойством `CreditRepository._link` —
     `credit.c[f"{table.name}_id"]` — из тех же `table`/`credit`.

   Это ровно случай «абстракция появляется со второй реализацией»: она уже
   есть (`Entity`), а вторая реализация вместо переиспользования завела
   параллельную. Остаться должен `Entity`/`PEOPLE`/`COMPANIES`; `_Credits`,
   `_PEOPLE`, `_STUDIOS` в `views.py` — убрать, `_credits` — переписать на
   `Entity` (для колонки связи вынести `CreditRepository._link` в
   read-only помощник над `Entity`, которым сможет пользоваться и репозиторий,
   и пачечное чтение).

Практическое следствие пунктов 1–5: сами `_to_*` сейчас модульно-приватные
(`_to_genre`, `_to_external_id`, `_to_external_rating`, `_to_rating`) и метод
`_to_credit` завязан на `self`. Чтобы `views.py` мог их звать без нарушения
принятого в проекте порядка (приватное не импортируется между модулями — так
уже было решено с `to_item`, вынесенным в `rows.py` из `library.py` ровно по
этой причине), конвертеры годится вынести туда же или в соседний общий модуль
и сделать доступными обеим сторонам. Способ выноса — на усмотрение исполнителя,
сам факт дублирования подтверждён.

## Вердикт

Рассмотрено кандидатов: 11 (5 отклонено, 6 подтверждено).

Подтверждённые повторы:
- `genres.py:_to_genre` / `views.py:ViewsRepository._genres` — сборка `Genre`
  из строки; остаться должен `_to_genre`.
- `external.py:_to_external_id` / `views.py:ViewsRepository._identifiers` —
  сборка `ExternalId`; остаться должен `_to_external_id`.
- `external.py:_to_external_rating` / `views.py:ViewsRepository._external` —
  сборка `ExternalRating`; остаться должен `_to_external_rating`.
- `ratings.py:_to_rating` / `views.py:ViewsRepository._ratings` — сборка
  `Rating`; остаться должен `_to_rating`.
- `credits.py:CreditRepository._to_credit` / `views.py:ViewsRepository._credits`
  — сборка `Credit`; логика должна остаться одна и быть доступна обеим
  сторонам.
- `credits.py:Entity`+`PEOPLE`+`COMPANIES` / `views.py:_Credits`+`_PEOPLE`+
  `_STUDIOS` — описатель связи людей и студий с карточкой; остаться должен
  `Entity`/`PEOPLE`/`COMPANIES`.

Готово к коммиту: С правками
