# Ревью повторов — план 3, задача 9 (`Linker`)

Дата: 2026-07-30. Измерение: повторы во всём проекте. Только что добавлено:
`backend/service/linking.py` (`merge_fields`, `overwrite_fields`, `Linker`) и
`tests/backend/test_linking.py`.

Прочитаны целиком `docs/module-map.md`, `docs/data-map.md`,
`docs/not-duplicates.md`, `backend/service/cards.py`, `backend/service/linking.py`,
`backend/storage/repository/library.py`, `tests/backend/test_linking.py`,
`tests/backend/test_card_writer.py`.

## Находки

### Серьёзная — конструктор `CardWriter` и `Linker` побайтно совпадает

- `backend/service/cards.py:CardWriter.__init__` (25–41)
- `backend/service/linking.py:Linker.__init__` (60–76)

Семь параметров в одном порядке (`library, genres, people, companies, ids,
ratings, posters`) и тело — семь присваиваний `self._library = library`, …,
`self.posters = posters` — совпадают до символа. Это ровно тот случай, когда
абстракция уже уместна: раньше реализация была одна (`CardWriter`), теперь их
две, и обе несут один и тот же набор из семи зависимостей.

**Решение:** вынести общий `__init__` в базовый класс (например,
`CardRepositories` рядом в `backend/service/`, в отдельном модуле — по
прецеденту `mirror.py`, заведённого на второй реализации). `CardWriter` и
`Linker` наследуют его и своих `__init__` не пишут. Дублирующее объявление —
любое из двух, оставить стоит то, что переедет в базовый класс; какое именно
имя класса выбрать — решение исполнителя на шаге починки.

### Средняя — цикл «привязать состав» повторяется внутри `_attach` и `_fill`

- `backend/service/cards.py:CardWriter._attach` (91–96), тело целиком:
  ```python
  for credit in credits:
      entity_id = await repository.ensure(credit)
      await repository.attach(item_id, entity_id, credit.role, credit.position)
  ```
- `backend/service/linking.py:Linker._fill` (130–144), хвост тела — те же три
  строки, слово в слово, после собственных проверок (`if not credits`,
  `if not overwrite and await repository.credits_of(...)`, `if overwrite:
  await repository.detach_all(...)`).

Сигнатуры совпадают вплоть до имён параметров (`repository, item_id, credits`).
Это не «один глагол над разными предметами» — один и тот же предмет
(`CreditRepository`), тот же порядок вызовов `ensure` → `attach`.

**Решение:** вынести три строки в общий приватный метод базового класса (из
находки выше), например `_write_credits`. `CardWriter._attach` становится этим
методом без обёртки (или прямым вызовом), `Linker._fill` вызывает его после
своих guard-проверок и `detach_all`.

### Средняя — цикл записи внешних идентификаторов и оценок повторяется в `_write_the_rest` и `link`

- `backend/service/cards.py:CardWriter._write_the_rest` (74–89), середина:
  ```python
  for external in card.external_ids:
      await self._ids.put(item_id, external)
  for rating in card.ratings:
      await self._ratings.record(item_id, rating)
  ```
- `backend/service/linking.py:Linker.link` (78–104), середина — те же четыре
  строки, слово в слово.

**Решение:** вынести в общий приватный метод базового класса, например
`_record_external(item_id, card)`. Оба места заменяются вызовом.

### Итог по главному подозреваемому: `CardWriter` и `Linker` — не «один с флагом»

Прочитаны оба целиком, ответ на прямой вопрос: **это два разных дела**, а не
одна операция с переключателем `overwrite`.

- `CardWriter.save` создаёт новую строку (`library.create`), и при любой
  ошибке в `_write_the_rest` откатывает целиком — включая уже скачанный постер
  и уже созданную строку `item`. У `Linker.link` отката нет вовсе: карточка уже
  существует (обычно ручная), откатывать создание нечего, а `_check_identifiers`
  проверяет конфликт **до** первой записи, а не ловит его после.
- `Linker` работает с полями по правилу «внешнее заполняет только пустое»
  (`merge_fields`/`overwrite_fields`, `_fill_genres`, `_fill`) — у `CardWriter`
  этого нет и быть не может: новая карточка целиком приходит от источника,
  мержить не с чем.
- Обложка решается по-разному не по случайности, а по смыслу: `CardWriter.save`
  требует постер до записи и отказывает, если он не скачался (частичной
  карточки не бывает); `Linker._fill_poster` не блокирует привязку неудачным
  постером (дополнительные источники запись не блокируют, обложка уже не
  «источник карточки», а долив). Это не повтор — это две разные точки спеки,
  и сравнивать их дальше как один узел смысла нет.

Вывод: два класса нужны оба, а три находки выше — общий низкоуровневый код
внутри них, который стоит вынести в общего родителя.

### `_FILLABLE` (`linking.py`) против `_FIELDS` (`library.py`) — разное по существу

- `backend/service/linking.py:_FILLABLE` — 9 полей.
- `backend/storage/repository/library.py:_FIELDS` — 13 полей.

`_FIELDS` — это всё, что идёт в INSERT/UPDATE строки `item`, включая
идентичность (`kind, source, source_id`) и `synced_at`. `_FILLABLE` — подмножество
без них, и это осознанно: комментарий в `linking.py` (строки 21–23) прямо
объясняет, почему идентичность и отметка синхронизации туда не входят — их
ставит сама привязка, а не слияние полей. Отношение «13 против 9, одно —
надмножество другого с документированной причиной» — не повтор, а именно тот
случай, что уже описан в `docs/not-duplicates.md` про `SearchHit` и `Item`:
общего имени мало, чтобы считать данные одним и тем же набором.

### `_EMPTY` — не повтор идиомы `value or ""`

`_EMPTY = (None, "")` в `linking.py` используется для проверки «поле пустое,
можно заполнить» (`getattr(existing, name) in _EMPTY`). В остальном коде
(`library.py:_to_item`, разборы источников) `or ""` — это нормализация чтения
из базы/API (None → пустая строка при выдаче наружу), а не проверка условия.
Разные задачи: одна решает, писать ли поле, другая приводит значение к
показываемому виду. Именованной константы `_EMPTY` или тождественного ей
условия больше нигде в проекте нет — сравнивать не с чем.

### Тестовая — SQL-затравка справочника жанров дублирована между двумя тестовыми файлами

- `tests/backend/test_card_writer.py:reference` (79–88), тело — две строки
  `INSERT INTO genre ...` и `INSERT INTO genre_map ...` с жанрами
  «фантастика»/«приключения» и `ext_id` `878`/`12`.
- `tests/backend/test_linking.py:linker` (95–116), внутри фикстуры — те же две
  строки `INSERT`, побайтно совпадающие.

Совпадение не поймал бы автоматический поиск дублей: `reference` — отдельная
функция, а в `test_linking.py` та же затравка вписана прямо в тело фикстуры
`linker` вместе с построением `Linker` — тела двух функций целиком не совпадают,
хотя эти четыре строки внутри — да.

**Решение:** вынести затравку в общий помощник тестов (например,
`tests/conftest.py`, рядом с `seed`), и вызвать его из `test_card_writer.py` и
из фикстуры `linker` в `test_linking.py`. Какая из двух копий останется как
источник текста — решение исполнителя, разница в них только в докстринге на
одной стороне.

## Разобрано и признано разным

- `tests/backend/test_card_writer.py:source_card` ≠ `tests/backend/test_linking.py:incoming`
  — обе строят `SourceCard` по шаблону «словарь умолчаний + `.update(overrides)`»,
  и это тот же общий приём, что уже узаконен для `make_item`/`card`/`game_card`
  в `docs/not-duplicates.md`. Наборы умолчаний разные не только по значениям,
  но и по составу (`incoming` без `companies`/`external_ids`/`ratings` по
  умолчанию, с одним жанром вместо двух) — под разные тестируемые классы.
  Общий фильм («Interstellar», `tmdb:157336`, Нолан) — сквозная фикстура данных
  проекта, а не повтор кода.
- `_FILLABLE` (`linking.py`) ≠ `_FIELDS` (`library.py`) — см. находку выше,
  надмножество с документированной причиной, не повтор.
- `_EMPTY` (`linking.py`) ≠ идиома `value or ""` в разборах источников и
  `library.py:_to_item` — разные задачи (решение писать/не писать против
  нормализации для показа), совпадения кода нет.
- Вызов `resolved_genres(self._genres, card.genre_ext_ids)` в
  `CardWriter._write_the_rest` и в `Linker._fill_genres` — общий уже вынесен
  (`backend/service/genres.py:resolved_genres`), вокруг него в каждом месте своя
  логика (`Linker` проверяет `overwrite`/`genres_of`, `CardWriter` — нет).

## Вердикт

Найдено четыре повтора: один серьёзный (конструктор `CardWriter`/`Linker`
совпадает побайтно) и два средних (цикл привязки состава, цикл записи внешних
идентификаторов и оценок) — все три в паре `CardWriter`/`Linker`, оправданы
второй реализацией и требуют вынесения в общего родителя, а не отказа от
абстракции. Ещё один — в тестах: SQL-затравка справочника жанров дословно
повторена между `test_card_writer.py` и `test_linking.py`, стоит вынести в
общий помощник. Сами классы `CardWriter` и `Linker` — не «один с флагом»:
у отката, слияния полей и решения по обложке разный смысл, и разделение
оправдано спекой. `_FILLABLE`/`_FIELDS` и `_EMPTY` повторами не являются.
