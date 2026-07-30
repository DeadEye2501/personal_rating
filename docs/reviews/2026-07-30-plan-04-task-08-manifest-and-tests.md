# Ревью манифеста и тестов — план 4, задача 8 (три круга загрузки)

Измерение: правила манифеста, которых не проверяет машина (2, 6, 7, 8, 10, 11,
13), и качество пятнадцати тестов `test_loading.py`. Только чтение, мутации не
запускались повторно — прослежены логически по коду.

## Прогон

```
tests/backend/test_loading.py tests/backend/sources/test_registry.py
28 passed in 1.90s
```

## Правило 6 — одна ответственность на модуль

`backend/service/loading.py` одной фразой без «и»: **кандидат превращается в
карточку**. Совпадает с докстрокой модуля и записью в `docs/module-map.md`.

Проверено разграничение с `CardWriter` (`backend/service/cards.py`) и
`Linker` (`backend/service/linking.py`) — читаются все три целиком.
`Loader.ensure` трогает `LibraryRepository` только на чтение
(`find_by_source`), запись целиком поручена `writer.save`; от `CardParts` он
не наследует — ему не нужны ни жанры, ни состав, ни внешние идентификаторы
напрямую. Пересечения ответственности нет.

## Правило 2 — место выбрано до первой строки

Новый файл `backend/service/loading.py` обоснован планом (задача 8), а не
дописан в `cards.py`: там другая ответственность (строки базы против
оркестровки трёх кругов). Соответствует.

## Правило 7 — абстракция со второй реализацией

`Sources.client_for` — словарь-константа с `.get`, не класс и не фабрика.
`FakeSources.client_for` в `tests/conftest.py` — вторая реализация того же
контракта для тестов, законная и обязательная (нельзя тестировать сервис на
живом реестре). Новых интерфейсов/базовых классов с одним наследником не
заведено.

## Правило 8 — ничего на всякий случай

- **Параметр `clock` у `Loader` намеренно не написан** — в `ensure` он ни разу
  не используется, и это верно: писать неиспользуемый параметр запрещено
  прямо тем же правилом. Согласен с отклонением от плана.
- **Ветка `if view.item_id is not None: return view.item_id` нужна**, и не
  просто как оптимизация к последующему `find_by_source`: у неё есть
  собственный тест-потребитель. `test_a_view_that_knows_its_identifier_costs_nothing`
  подаёт `CardView(item_id=42, ...)` для карточки, которой в базе нет — без
  этой ветки код упал бы на `find_by_source` (не нашёл), пошёл бы к
  `FakeCatalog`, и `client.asked` перестал бы быть пустым. Ветка обоснована,
  убирать нечего.
- **`Rig` (`tests/backend/test_loading.py:53-61`) — все четыре поля с
  потребителем.** `load` — в каждом тесте; `client` — проверка `.asked` и
  подмена `.card` (broken-тест); `posters` — `.get()` в четырёх тестах и
  монки-патч `.fetch` в тесте на порядок; `requests` — единственный
  потребитель `test_the_cover_is_fetched_once`, но он есть. Ни одного поля
  без сегодняшнего потребителя.

## Правило 9 (смысл) — классификация `BaseException` после `gather`

**Надо ли сужать: да, частично — узкая, но реальная дыра.**

Код не ловит `BaseException` через `except` — он классифицирует уже пойманное
`gather(..., return_exceptions=True)` через `isinstance(outcome, BaseException)`
(`backend/service/loading.py:54`). Это не буквальное нарушение «`BaseException`
не ловится», но по духу правила смысл тот же: любой `CancelledError`,
попавший в `outcome`, превращается в `Refusal(BROKEN)` и логируется как срыв.

Два разных сценария отмены ведут себя по-разному:

- **Отмена самой задачи `ensure` целиком** (обычное закрытие приложения) —
  `asyncio.gather` документированно пробрасывает `CancelledError` через сам
  `await`, а не кладёт её в результаты, даже при `return_exceptions=True`.
  Этот путь не проглатывается — закрытие приложения не превращается в отказ
  источника.
- **Отмена одного из двух дочерних корутин `gather` в отдельности** (например,
  внутренним таймаутом в `client.card` или в `PosterService.fetch`, если такой
  когда-нибудь появится) — по документации `gather`, «if any child is
  cancelled, it is treated as if it raised `CancelledError`», и при
  `return_exceptions=True` это именно попадает в результаты как обычное
  исключение. Нынешний код в этом случае классифицирует `CancelledError` как
  `isinstance(outcome, BaseException)` — то же самое, что и `RuntimeError`, —
  и превращает частную отмену в `Refusal(BROKEN)` с записью в лог, вместо
  того чтобы перебросить её дальше.

Сегодня в проекте нет кода, который бы отменял только один из двух дочерних
корутинов (оба клиента — простые `await`, без вложенных `wait_for`/`timeout`
внутри `ensure`), поэтому наблюдаемого следствия здесь пока нет — это не
Critical. Но правило просит явно: **сузить проверку**, отделив
`asyncio.CancelledError` от остальных `BaseException` и перебрасывая её, а не
классифицируя как отказ:

```python
for outcome in (card, poster):
    if isinstance(outcome, asyncio.CancelledError):
        raise outcome
    if isinstance(outcome, Exception):
        logger.exception(...)
        return broken(str(view.source), outcome)
```

## Правило 10 — логика не в интерфейсе

Не применимо к этому слайсу: `Loader` — часть `backend/`, обработчиков
интерфейса здесь нет.

## Правило 11 — комментарии

Прочитан каждый комментарий и докстрока в диффе (`loading.py`,
`test_loading.py`, `registry.py`, `conftest.py`). Все объясняют неочевидное
решение, а не пересказывают код рядом, ссылок на чужие файлы или рамок нет:

- `loading.py:43-44` — почему круги 2а/2б идут `gather`, а не подряд (адрес
  обложки уже пришёл с выдачей).
- `loading.py:52-53` — почему исключение превращается в `Refusal`, а не летит
  наружу (у границы потоков второго канала доставки нет).
- `loading.py:60-62` — почему «не скачалась» останавливает запись целиком, а
  не считается частным случаем.
- `test_loading.py:189-196` (`test_a_poster_that_did_not_arrive_stops_the_writing`)
  — доказательство от противного прямо в докстроке: что случилось бы без
  проверки. Ценный комментарий, не пересказ.
- `test_loading.py:213-216`, `228-230` — почему `poster=""` стоит именно там,
  где стоит (иначе тест проверял бы не то, что заявляет).
- `test_loading.py:239-242` — то же для «скачана один раз».
- `registry.py:41-42`, `conftest.py:108-109` — почему у ручной карточки нет
  клиента и почему подставной клиент игнорирует источник.

Замечаний нет.

## Правило 13 — тест проверяет поведение, а не объявление

Все 15 тестов `test_loading.py` дергают `ensure()` и проверяют внешне видимое
следствие (возврат, строку в базе, файл в `PosterStore`, содержимое лога,
список запросов/обращений), а не поле или константу. По каждому — что он
ловит и на какой строке `loading.py` он покраснеет, если её сломать:

| Тест | Следствие | Ронящая строка |
|---|---|---|
| `test_a_candidate_becomes_a_card` | кандидат становится строкой библиотеки с деталями | `return await self._writer.save(...)` |
| `test_the_detail_round_brings_what_the_search_lacked` | деталь (runtime, состав) доезжает до вида карточки | тот же `return`, плюс передача `card.value` |
| `test_the_detail_round_is_asked_about_the_right_card` | детальный запрос идёт с `source_id`/`kind` кандидата, не с чужими | `client.card(view.source_id, view.kind)` внутри `gather(...)` |
| `test_the_poster_is_stored_with_the_card` | обложка сохраняется вместе с карточкой | `self._posters.fetch(...)` + передача `poster` в `save` |
| `test_a_card_already_in_the_base_is_not_asked_for_again` | известная пара источник+id не идёт к клиенту повторно | `existing = await self._library.find_by_source(...)` / `if existing is not None: return existing.id` |
| `test_a_view_that_knows_its_identifier_costs_nothing` | известный `item_id` не идёт даже в `find_by_source` | `if view.item_id is not None: return view.item_id` |
| `test_a_refusal_of_the_source_writes_nothing` | `Refusal` от клиента не пишется в базу | `if not isinstance(card, Found): return card` |
| `test_a_vanished_card_is_missing_and_not_a_refusal` | `Missing` возвращается как есть, не путается с `Refusal` | та же строка |
| `test_a_broken_client_becomes_a_refusal` | исключение клиента не улетает наружу, ловится и логируется | цикл `for outcome in (card, poster): if isinstance(outcome, BaseException): ...` |
| `test_a_poster_that_did_not_arrive_stops_the_writing` | несостоявшаяся обложка останавливает запись целиком, без записи в лог о срыве | `if isinstance(poster, Refusal): return poster` |
| `test_a_card_without_a_cover_in_the_source_is_still_written` | отсутствие обложки у самого источника не блокирует запись | ветка `poster is None`, дошедшая до `writer.save` |
| `test_a_cover_absent_from_the_search_but_present_in_the_detail` | пустой адрес в выдаче не мешает — обложка доедет вторым запросом внутри писателя | передача `poster=None` в `writer.save(card.value, poster)` |
| `test_the_cover_is_fetched_once` | обложка, уже скачанная `Loader`, не качается писателем повторно | передача уже скачанных байт, а не `None`, в `writer.save` |
| `test_the_two_rounds_go_together` | деталь и обложка идут параллельно, не подряд | `await asyncio.gather(client.card(...), self._posters.fetch(...), ...)` |
| `test_an_unknown_source_is_a_refusal_and_a_log` | источник без каталожного клиента — предсказуемый отказ с логом, а не падение | `client = self._sources.client_for(view.source); if client is None: ...` |

Ни один тест не читает поле/константу вместо следствия. Замечаний по
правилу 13 нет.

## Два довода про обложку из брифа — оба подтверждаются

1. **Без проверки `isinstance(poster, Refusal)` писатель пытается сохранить
   отказ вместо байтов.** Прослежено по коду: без этой проверки `Loader`
   передал бы `poster` (объект `Refusal`) в `CardWriter.save`. Там
   `poster is None` — ложь (это `Refusal`, не `None`), поэтому свой повторный
   `fetch` писатель не вызывает; строка `item` создаётся; на шаге
   `_write_the_rest` → `self.posters.save(item_id, poster, ...)` →
   `PosterStore.put` пытается записать объект `Refusal` в колонку `BLOB` —
   драйвер SQLite не свяжет параметр такого типа и бросит исключение.
   `CardWriter.save` ловит его в `except Exception`, откатывает уже созданную
   строку (`self._library.delete(...)`) и пишет `logger.exception("откатываю
   карточку %s", ...)`. Итог совпадает с текущим (карточки в базе нет), но
   появляется ERROR-запись в логе от `backend.service.cards` — и именно её
   ловит `assert [... r.levelname == "ERROR"] == []` в
   `test_a_poster_that_did_not_arrive_stops_the_writing`. Довод верен.
2. **Без передачи готовой обложки писатель качает её вторым разом.** Если
   `Loader` всегда передавал бы `poster=None` вместо скачанных байт,
   `CardWriter.save` увидел бы `poster is None` и вызвал бы свой `fetch` с
   `card.item.poster_url` — тем же адресом, что уже скачал `Loader`. Второй
   `httpx`-запрос лёг бы в `rig.requests`, и
   `assert rig.requests == ["https://example.com/p.jpg"]` в
   `test_the_cover_is_fetched_once` покраснел бы (список из двух одинаковых
   URL вместо одного). Довод верен.

## Чего не хватает — непокрытая поломка

**`view.kind`, ушедший в детальный запрос, можно захардкодить на `Kind.MOVIE`
— ни один из 15 тестов не покраснеет.**

`candidate()` (`tests/backend/test_loading.py:37-39`) всегда строит
`CardView(kind=Kind.MOVIE, ...)` — параметризуется только `source_id` и
`poster`. Единственная проверка переданного клиенту типа —
`test_the_detail_round_is_asked_about_the_right_card`
(`assert rig.client.asked == [("27205", Kind.MOVIE)]`) — тоже ожидает
`Kind.MOVIE`, потому что кандидат в тесте не может быть никаким другим. Замени
строку

```python
client.card(view.source_id, view.kind)
```

на

```python
client.card(view.source_id, Kind.MOVIE)
```

— и все 15 тестов останутся зелёными, хотя в приложении карточка игры
(`Kind.GAME`) при загрузке из Steam/GOG молча получала бы детальный запрос не
того типа. Не хватает варианта `candidate(kind=Kind.GAME, source=Source.STEAM)`
с проверкой `rig.client.asked == [(..., Kind.GAME)]`.

(Отдельно проверены остальные наводки из брифа: гонка «карточка появилась в
базе между проверкой и записью» действительно не тестируется в
`test_loading.py`, но обработана на уровне `CardWriter.save`/`ItemExists` —
это её ветка и её тесты, не этого слайса. `PosterService.fetch` физически не
может вернуть `None` при непустом адресе — `if not url: return None` это
единственный источник `None` в методе, ветвление проверено целиком. Отмена
задачи внутри `gather` разобрана отдельно в правиле 9.)

## Вердикт по находкам

**Important**
- Правило 9 — `backend/service/loading.py:54` —
  `isinstance(outcome, BaseException)` классифицирует `CancelledError` дочерней
  корутины наравне с обычным исключением и превращает её в `Refusal(BROKEN)`.
  Сегодня в проекте нет кода, отменяющего один из двух дочерних `gather`
  по отдельности, поэтому следствия нет, но правило и общий довод про
  `CancelledError` требуют явно выделить и перебросить её, не классифицировать.
- Тестовый пробел — `tests/backend/test_loading.py` — нет теста на `Kind.GAME`
  в `candidate()`; хардкод `Kind.MOVIE` в вызове клиента прошёл бы все 15
  тестов молча. Добавить один тест с `kind=Kind.GAME`.

**Minor**
- (Не моё измерение, но подтверждаю согласованность с параллельным ревью
  повторов: `backend/service/loading.py:54-58` вручную пересобирает
  `Refusal(BROKEN)` вместо вызова `broken()` из `backend/sources/errors.py`
  — см. `docs/reviews/2026-07-30-plan-04-task-08-duplicates.md`. Здесь не
  переоцениваю, только подтверждаю, что чинить стоит вместе.)

**Critical**
- Нет.

Правила 2, 6, 7, 8, 10, 11 — без замечаний. Разделение `Loader`/`CardWriter`
чистое, комментарии по делу, `Rig` и ветка `item_id` обоснованы тестами.

**Готово к коммиту: С правками** (сузить `BaseException`/`CancelledError` в
`loading.py:54`, добавить тест на `Kind.GAME`; заодно — правку из ревью
повторов про `broken()`, раз оба замечания в одном файле).
