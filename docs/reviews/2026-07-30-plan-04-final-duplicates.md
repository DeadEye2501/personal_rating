# Ревью плана 4 — повторы во всём проекте по картам

Дата: 2026-07-30. Диапазон: `bc66f2c..fa4782a` (план 4 целиком, чтение читателя —
14 задач). Дифф не читался. Проверка идёт по `docs/module-map.md`,
`docs/data-map.md` и всему коду `backend/`, `tests/`, против уже разобранного в
`docs/not-duplicates.md`. Задача — найти повтор между двумя файлами, которых
один слайсовый рецензент не сопоставлял: слайсовые проходы уже свели найденное
внутри каждой задачи (`rows.py`, `unique.py`, `FakeClient`, `Entity`,
`answered`, `Loader._catalog`, `CreditRepository._linked`).

## Что читал

- `docs/module-map.md` целиком (обе части, 1607 строк).
- `docs/data-map.md` целиком.
- `docs/not-duplicates.md` целиком — больше пятидесяти разобранных пар, взяты
  как данность и заново не оспаривались.
- Код: `backend/service/search.py`, `loading.py`, `enrich.py`, `card_parts.py`,
  `cards.py`, `linking.py`, `library.py`, `posters.py`, `genres.py`,
  `asking.py`; `backend/storage/repository/external.py`, `sections.py`,
  `credits.py`, `wishlist.py`, `library.py`, `ratings.py`, `genres.py`;
  `backend/model/results.py`, `view.py`, `rating.py`; `tests/conftest.py`
  целиком; фрагменты `tests/backend/test_loading.py` и
  `tests/backend/test_card_writer.py`.

## Кандидаты — рассмотрены и отклонены

1. **Три «спросить источник и разобрать исход»: `SearchService.external`,
   `Loader.ensure`, `Enricher.enrich`.** Прочитаны все три целиком. Общее —
   `asyncio.gather` над `answered(...)` и разбор `Found`/`Refusal`/`Missing` —
   уже вынесено в `backend/service/asking.py`. Дальше каждый делает своё:
   `external` переплетает несколько выдач через `_weave` и складывает отказы в
   `ExternalSearch`; `ensure` — это «найди в базе, иначе спроси каталог и
   обложку разом, потом запиши», с ранними выходами по `item_id`/`existing`;
   `enrich` копит найденные значения в `_Harvest`, пишет и находки, и честные
   пустоты по сроку годности. Общей формы после вычета `answered` не осталось.
   Отклонено.

2. **Четыре «отдай порцию номеров»: `SectionsRepository.ids`,
   `CreditRepository.items_of`, `WishlistRepository.list_ids`,
   `LibraryRepository.list_by_kind`.** Прочитаны все четыре. Общий вид —
   `.order_by(...).limit(limit).offset(offset)` — есть, но предметы и результат
   разные: `list_by_kind` отдаёт `list[Item]`, а не номера, три остальных —
   разные таблицы с разными ключами сортировки и разными присоединениями.
   Ровно случай «две функции одной формы над разными таблицами, если предметы
   разные» — уже описан как не-повтор. Отклонено.

3. **`REFRESH_TTL` (`backend/service/loading.py`, 30 дней) и `VALUE_TTL`
   (`backend/storage/repository/external.py`, 30 дней).** Совпадают числом.
   Комментарий у `REFRESH_TTL` — «срок тот же, что у оценок со значением» —
   означает, что совпадение осознанное и уже названо словами в коде, а не
   спрятанный дубль: общая константа связала бы перезапрос сериала (сервис) со
   сроком годности чужой оценки (репозиторий) — два независимых правила.
   Отклонено, довод тот же, что у пары `RATE_BACKOFF`/`RATE_BACKOFF` в
   `not-duplicates.md`.

4. **`merge_fields` и `overwrite_fields`** (`backend/service/linking.py`) —
   одна форма `replace(existing, **{...})` с разным условием фильтра. Оба в
   одном файле одного слайса (план 3), а не между двумя файлами — вне мандата
   этого прохода; при этом слитые под флагом они дали бы функцию с веткой на
   каждой строке, тот же довод, что у `CardWriter`/`Linker` в
   `not-duplicates.md`. Не подтверждено как новая находка.

5. **`tests/backend/test_loading.py:source_card` и
   `tests/backend/test_card_writer.py:source_card`** — совпадает имя приватной
   тестовой фабрики в разных файлах. Прочитаны оба: у `test_loading.py` только
   `item` и `people` — ровно то, что нужно для проверки записи после `ensure`;
   у `test_card_writer.py` вдобавок `genre_ext_ids`, `companies`,
   `external_ids`, `ratings` — полный набор для проверки писателя целиком.
   Тот же приём и тот же довод, что уже разобран для пары
   `test_linking.py:incoming` / `test_card_writer.py:source_card`. Отклонено.

## Подтверждённый повтор

**`tests/conftest.py:an_item`** (строит `Item` в памяти, умолчания — фильм
TMDB) **и `tests/conftest.py:card` (фикстура, вложенная `make`)** — вложенная
`make` заново собирает `Item(id=0, kind=kind, source=Source.TMDB,
source_id=source_id, title=title, synced_at=MOMENT)` и вставляет её через
`LibraryRepository(sessions).create(...)`, хотя `an_item(source_id, title,
kind=kind)` строит буквально тот же объект — совпадают все умолчания:
`Source.TMDB`, `synced_at=MOMENT`. Это не разные предметы (один строит `Item`
в памяти, другой вставляет и отдаёт номер) — второе не повод пересобирать
объект заново, а повод позвать первое перед вставкой. Оба помощника выросли в
одном файле по мере того, как разные слайсы плана 4 добавляли фикстуры, и по
отдельности каждый слайсовый рецензент видел только «новый помощник», а не
пересборку соседнего.

**Оставить:** `an_item` как единственное место, где собирается `Item` в
памяти; тело `card.make` должно звать `an_item(source_id, title, kind=kind)`
вместо повторной сборки полей.

## Вердикт

Один подтверждённый повтор из семи рассмотренных кандидатов.
