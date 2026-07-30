# Ревью повторов — план 4, задача 14

Измерение: повторы во всём проекте. Дифф не читался.

## Рассмотренные кандидаты

### 1. `CreditRepository.items_of` против `CreditRepository.credits_of` — не повтор

Прочитаны оба тела (`backend/storage/repository/credits.py:179-218`).

`credits_of(item_id)` отвечает на «кто снят в этой карточке»: соединяет
`credit` с таблицей сущности (`person`/`company`), берёт `entity.position`
только если он есть, порядок — по позиции в титрах или по имени. `items_of`
отвечает на обратный вопрос — «в чём снят этот человек»: соединяет `credit` с
`item`, довешивает `outerjoin` на `rating`, снимает повтор `distinct()` (одна
роль на две записи связи) и режет порцию `limit/offset` с порядком по своей
оценке. Общих таблиц нет ни одной — разные направления одной и той же связи.
Не повтор.

### 2. `CreditRepository.items_of` против `SectionsRepository.ids` — не повтор

Прочитаны оба тела (`credits.py:194-218`, `backend/storage/repository/sections.py:90-101`).

`SectionsRepository.ids` — универсальный запрос по разделу: пять ключей
сортировки (`_KEYS`), включение и исключение по тегам/жанрам/оценкам через
`Filters`, отбор по разделу («Оценённые»/«Хочу посмотреть») и типу
содержимого — всё через общий `_narrow`, который не знает ничего про людей и
студий. `items_of` — узкий запрос с одним зашитым порядком (по своей оценке)
и единственным условием — связь через `credit.<link> == entity_id`; жанров,
тегов и разделов не касается вовсе.

Слить их значило бы протащить фильтр «связан с этим человеком» в `Filters`
или `Feed`, привязав `SectionsRepository` (который ничего не знает про
`person`/`company`) к домену `CreditRepository`. Общего у них — только форма
ответа «порция номеров с лимитом и смещением», которая уже используется как
общий приём в нескольких репозиториях (`WishlistRepository.list_ids`,
`LibraryRepository.search`) и не считается поводом для абстракции сама по
себе. Не повтор — вопросы разные, наборы таблиц разные.

### 3. `items_of` против `WishlistRepository.list_ids` — не повтор

`list_ids` читает только таблицу `wishlist`, без `distinct`, без сущности,
порядок — по `added_at`. Общей таблицы с `items_of` нет, кроме `item`, к
которой `list_ids` вообще не обращается (отдаёт `item_id` из `wishlist`
напрямую). Не повтор.

### 4. `items_of` против `LibraryRepository.list_by_kind` — не повтор

`list_by_kind` отдаёт полные `Item` (через `to_item`), фильтр только по
`kind`, порядок по названию, без связи с сущностями. Другой набор колонок,
другой тип на выходе, другой набор условий. Не повтор.

### 5. `CreditRepository.items_of` против `CreditRepository._linked` — подтверждённый повтор

Прочитаны оба тела (`credits.py:194-218` и `credits.py:236-245`). Обе строят
один и тот же фрагмент: `item` соединяется с `self._entity.credit` по
`self._entity.credit.c.item_id == item.c.id` и фильтруется тем же условием
`self._link == entity_id`. Проверено `grep` по всему `backend/` — это ровно
два места, где встречается `self._entity.credit.c.item_id == item.c.id`, и
оба в этом файле:

```
credits.py:210:  self._entity.credit.c.item_id == item.c.id)   # items_of
credits.py:243:  self._entity.credit.c.item_id == item.c.id)   # _linked
```

Дальше они расходятся по назначению: `_linked` — общая основа для трёх
ступеней `_hint` (проверено — `_hint` использует именно `_linked`, довешивая
`join` на `rating`/`wishlist` с разными `order_by`/`limit(1)`), `items_of`
довешивает `outerjoin` на `rating`, `distinct()`, свой порядок и
`limit/offset`. Но само соединение «карточка — связь с этой сущностью» и
фильтр по `entity_id` — общий инвариант, который сейчас поддерживается в двух
местах одного класса вручную. Это ровно тот случай, который автоматическая
проверка дублей не ловит («не видит повторов короче пяти инструкций» —
здесь два выражения, `join` и `where`), а правило «общее выносится сразу, а
не при третьем дубле» уже нарушено: второе появление — `items_of` из этой
задачи — совпадающий фрагмент не вынесло.

**Что оставить.** Канонической должна остаться связка `_linked` — она уже
несёт объяснение, почему фильтр по сущности нельзя терять. `items_of`
предлагается строить поверх неё, например:

```python
self._linked(entity_id).with_only_columns(item.c.id).distinct()
    .outerjoin(rating, rating.c.item_id == item.c.id)
    .order_by(rating.c.score.desc(), item.c.id)
    .limit(limit).offset(offset)
```

либо вынести сам `join+where` в отдельный приватный метод, которым пользуются
оба. Разбирать заново на следующем ревью, если тела разойдутся.

## Тесты

Прочитаны `tests/backend/test_by_credit.py` (9 тестов), `tests/backend/test_credits.py`
(24 теста), `tests/backend/test_suggestions.py` (14 тестов). Пересечения по
предмету проверки нет: `test_by_credit.py` целиком про `items_of` (порядок по
оценке, неоценённые следом, `distinct` при двух ролях, порция по
`limit/offset`, разделение людей и студий, сборка через `ViewsRepository`);
`test_credits.py` — про идентичность (`ensure`, `find_by_source`,
`find_anonymous_by_name`, тёзки) и про `credits_of`/`attach`/`detach_all`;
`test_suggestions.py` — про `suggest`/`_hint`. Общих сценариев не найдено, не
повтор.

## Вопрос про `LibraryService.views_of`

Не согласен с решением не заводить метод. `Backend.views: ViewsRepository`
(`backend/app.py:50`) отдаёт клиенту репозиторий целиком — не тип границы
слоёв, а объект с асинхронными методами поверх сессии SQLAlchemy. Это прямо
противоречит собственному комментарию в `backend/service/library.py:19`:
«через границу слоёв клиент репозитории не видит вовсе» — сказанному именно
про `ViewsRepository`, который `LibraryService` не оборачивает по этой самой
причине.

Хуже то, что автоматическая проверка границы (`tests/backend/test_layers.py`,
`test_client_takes_only_the_boundary_types_from_the_backend`) ловит только
`import` вида `from backend.storage... import ...`. Обращение вида
`self._backend.views.in_order(ids)` — это доступ к атрибуту уже полученного
объекта `Backend`, без единого `import` репозитория в клиентском файле, и
этот тест его не заметит никогда, даже когда `client/` перестанет быть
пустым. Граница держится сейчас только на том, что клиента ещё не написали.

`LibraryService` уже хранит `self._views` для `page`. Однострочный метод
`async def cards(self, item_ids: list[int]) -> list[CardView]: return await
self._views.in_order(item_ids)` в нём стоит меньше, чем поле `views` в
публичной поверхности `Backend`, и не требует новой абстракции — использует
существующую зависимость того же сервиса. Предлагаю завести такой метод и
убрать `views` из полей `Backend`.
