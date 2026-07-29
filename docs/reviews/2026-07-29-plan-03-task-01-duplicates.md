# Ревью плана 3, задача 1 — повторы по картам

Дата: 29.07.2026. Измерение: **повторы по картам**. Дифф не читался.

Прочитано целиком: `docs/module-map.md`, `docs/data-map.md`,
`docs/not-duplicates.md`. Пары, уже разобранные в `not-duplicates.md`, пропущены.

Подтверждено чтением обоих мест в коде: `backend/storage/repository/credits.py`,
`base.py`, `library.py`, `tags.py`, `genres.py`, `ratings.py`, `wishlist.py`,
`backend/model/item.py`, `backend/storage/posters.py`, `tests/conftest.py`,
`tests/backend/test_credits.py`, `tests/backend/test_delete.py`.

## Подтверждённые повторы

### 1. Своя идентичность ручной сущности объявлена дважды

- `backend/model/item.py:29` — `new_source_id() -> str`, тело `return str(uuid4())`,
  докстринг объясняет, почему идентичность случайная.
- `backend/storage/repository/credits.py:65` — внутри `create_manual`:
  `return await self.create(name, Source.MANUAL, str(uuid4()))`, плюс собственный
  `from uuid import uuid4` в шапке модуля.

Одно дело под двумя видами, и довод у обоих один и тот же — докстринг
`create_manual` прямо говорит «как и ручная карточка». `new_source_id` уже
переиспользуется в двух местах: `backend/model/item.py:45` (`new_manual_item`) и
`backend/storage/repository/library.py:177` (`LibraryRepository.unlink`).
`credits.py` — единственное место, где вместо него написан `uuid4()` руками.

Машинная проверка этого не увидела бы: функция короче пяти инструкций, а повтор
сидит внутри тела чужой функции.

**Остаться должно** `backend/model/item.py:new_source_id`. В `credits.py` —
импорт `new_source_id` из `backend.model` (он уже в `__all__`) и удаление
`from uuid import uuid4`.

### 2. «Снести всё по карточке» написано четырьмя копиями

Одно и то же выражение над разными таблицами, тела совпадают побайтно, кроме
имени таблицы:

- `backend/storage/repository/wishlist.py:21-24` — `remove`;
- `backend/storage/repository/ratings.py:65-69` — `clear`;
- `backend/storage/repository/credits.py:124-129` — `detach_all` (новое в слайсе);
- `backend/storage/repository/genres.py:44-46` — `cleared` внутри `set_for_item`
  (там же нужен не запуск, а сам оператор: удаление и вставка идут одной
  транзакцией).

Все четыре: `delete(T).where(T.c.item_id == item_id)`, первые три обёрнуты в
`await self._run(...)`.

Повтор не новый — три копии из четырёх жили до этого слайса и ни одним ревью не
находились: хук сравнивает записываемый файл с проектом по дереву, а узел с
именем таблицы у этих тел разный, поэтому совпадением он их не считает. Ровно тот
случай, ради которого измерение и заведено.

Прецедент на вынос уже есть в самом проекте: `Repository._has_item(table, item_id)`
(`base.py:31`) заведён именно так — «спрашивают об этом трое, и запрос у всех
троих один и тот же».

**Остаться должно** одно объявление в `Repository` рядом с `_has_item`. Оно
обязано **возвращать оператор, а не выполнять его**, иначе `genres.set_for_item`
им воспользоваться не сможет: там оператор кладётся в общую транзакцию с
вставкой. Три остальных места зовут `self._run(...)` поверх, как сейчас.

`PosterStore.delete` (`posters.py:88`) в вынос не входит: другой транспорт и
другой файл базы — довод тот же, что у уже разобранной пары
`PosterStore._write` ≠ `Repository._run`.

### 3. Повтор внутри `credits.py`

Оба — второе появление, то есть срок выноса по правилу 3 уже наступил:

- предикат имени `func.py_lower(self._entity.table.c.name) == fold(name.strip())`
  написан дословно дважды: строка 80 (`find_by_name`) и строка 91
  (`find_anonymous_by_name`);
- `return row.id if row is not None else None` написано дословно дважды: строка 74
  (`find_by_source`) и строка 97 (`find_anonymous_by_name`).

Слить сами методы нельзя — `find_anonymous_by_name` спрашивает лишнюю колонку и
берёт одного, — но **остаться должно по одному объявлению каждого**: приватный
предикат `_same_name(name)` в `CreditRepository` и одно чтение идентификатора
(годится и приватный `_id(statement) -> int | None` в `Repository`, если он
понадобится второму репозиторию; пока хватит и локального).

Мелочь, но обе строки — ровно те, где ошибка проходит молча: `strip()`, забытый
в одной из двух копий, тесты не поймают.

## Разобрано и повтором не является

Ни одна из пар ниже в отчёт как находка не идёт — они подтверждены как разные, и
их место в `docs/not-duplicates.md`, если исполнитель сочтёт нужным закрыть их от
следующего прохода.

- `CreditRepository.find_by_source` ≠ `LibraryRepository.find_by_source` — имя и
  сигнатура совпадают, предметы разные: первый отдаёт номер строки человека или
  студии, второй — собранную `Item`. Общее (`_row`, `_mapped`) уже в `Repository`.
- `CreditRepository.find_by_name` ≠ `LibraryRepository.find_by_title` — общая
  только идиома `func.py_lower(...) == fold(...)`: у названия сравниваются две
  колонки через `|` и фильтр по типу содержимого, у имени — одна колонка с
  порядком по номеру.
- `CreditRepository.credits_of` ≠ `TagsRepository.tags_of` ≠
  `GenresRepository.genres_of` — та же семья, что уже разобрана в
  `not-duplicates.md`: разные таблицы, соединения и порядок. У `credits_of`
  вдобавок и набор колонок, и порядок зависят от `Entity.position`.
- `CreditRepository._to_credit` ≠ `_to_genre` ≠ `_named` ≠ `_to_item` — по
  преобразователю строки на репозиторий, ровно тот случай, ради которого заведён
  `Repository._mapped`. `_to_credit` сделан методом, а не функцией модуля,
  обоснованно: ему нужен `self._entity.roles`.
- `CreditRepository.attach` ≠ `TagsRepository.assign` — общего одно выражение
  `insert(...).on_conflict_do_nothing()`; `assign` перед вставкой проверяет
  совпадение типов содержимого в одной сессии, `attach` собирает набор значений с
  необязательной позицией.
- `CreditExists` ≠ `ItemExists` ≠ `TagExists` — три пустых наследника `Exception`
  с разными докстрингами. В том и смысл, что вызывающий различает, какой ключ
  уникальности занят; слитые, они это различение стёрли бы.
- `CreditRepository` **ничего из `Repository` не переписывает** — проверено
  поимённо: `create` → `_created`, `find_*` → `_row`/`_rows`, `attach`,
  `detach_all` → `_run`, `credits_of` → `_mapped`. Своего доступа к сессии в
  модуле нет ни одного.
- `Entity`, `PEOPLE`, `COMPANIES` — в карте данных ничего похожего по составу
  нет: единственный сосед-контейнер `Sources` (`registry.py`) держит клиентов
  источников, а не описания таблиц.
- `people()` / `companies()` ≠ `build_sources` ≠ `session_factory` — общее только
  слово «фабрика» в разговоре, дела разные.

## Тесты

- `tests/backend/test_credits.py` **не заводит ни одного своего помощника,
  фикстуры или константы** — карта модулей это подтверждает, чтение файла тоже.
  Всё берётся из `tests/conftest.py`: `sessions`, `card`, `posters`. Дублирования
  с `conftest.py` нет.
- `test_deleting_the_card_takes_the_credits_but_not_the_person` не повторяет
  `tests/backend/test_delete.py`: тамошний помощник `furnished` вешает оценку,
  тег, закладку и постер и про `person_credit` / `company_credit` не знает вовсе.
  Проверяемый факт новый.

## Вердикт

**Три подтверждённых повтора, ни одного блокирующего.**

Порядок починки по цене: (1) — одна строка и один импорт, чинится сразу; (3) —
внутри одного файла, тоже дёшево; (2) — трогает четыре модуля и один из них
чужой слайсу, но именно он и есть находка этого измерения, а тянуть его дальше
значит писать пятую копию в следующей задаче.
