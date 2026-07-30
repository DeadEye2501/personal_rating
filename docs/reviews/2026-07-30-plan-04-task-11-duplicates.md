# Ревью повторов — план 4, задача 11 (обложка видимой карточки)

Измерение: повторы во всём проекте, не в диффе. Дифф не читался. Карты
(`docs/module-map.md`, `docs/data-map.md`) прочитаны целиком,
`docs/not-duplicates.md` — тоже; пары, уже разобранные там, заново не
поднимались.

## Рассмотренные кандидаты — 5

1. `PosterService.poster_for` против `.fetch`/`.save` (тот же класс,
   `backend/service/posters.py`) и против `.store_upload` — четыре метода
   вокруг одной картинки.
2. `PosterService.poster_for` против `Loader.ensure` (`backend/service/loading.py`).
3. `PosterService.poster_for` против `Enricher.enrich` (`backend/service/enrich.py`).
4. Фикстура `covers` (`tests/backend/test_cover_reads.py`) против
   `poster_service`/`card_parts` (`tests/conftest.py`) и против фикстуры
   `loader` (`tests/backend/test_loading.py`).
5. Константа `STORED` (`tests/backend/test_cover_reads.py`) против `PICTURE`
   и `picture()` (`tests/conftest.py`).

Подтверждённых повторов: **2** (пп. 1 частично — `store_upload`/`save`, и 4).

## Разбор по каждому

### 1. `poster_for` / `fetch` / `save` / `store_upload` — границы верные, кроме одной пары строк

Прочитаны все четыре тела (`backend/service/posters.py:30-98`).

`poster_for` не повторяет код `fetch`/`save` — она их зовёт:
`data = await self.fetch(source, url)`, затем `await self.save(item_id, data,
now)`. Это композиция, а не дубль: `fetch` отвечает за сеть и подпись формата,
`save` — за запись как есть, `poster_for` — за то, в каком порядке спросить
хранилище и сеть и когда писать. Границы между этими тремя методами верные.

Но `save` и `store_upload` — не так:

```python
async def save(self, item_id: int, data: bytes, now: datetime) -> None:
    await self.store.put(item_id, data, now)

async def store_upload(self, item_id: int, data: bytes,
                       now: datetime) -> None:
    await self.store.put(item_id, crop_to_cover(data), now)
```

Тело `store_upload` — тот же вызов `self.store.put(item_id, ..., now)`, что и
у `save`, с одной разницей: данные пропущены через `crop_to_cover`. Строка
короче порога хука (пять инструкций) и лежит внутри тела метода — ровно тот
повтор, который автоматика не ловит, а ручной проход обязан. Довод такой же,
как у уже подтверждённого повтора `parse_series`/`parse_series_counts` из
задачи 9 (`docs/reviews/2026-07-30-plan-04-task-09-duplicates.md`, п. 5):
разный внешний метод оправдан (загрузка руками — единственное место, где
картинка обрезается), но знание «как записать байты постера» продублировано,
хотя `save` уже есть.

**Что оставить.** `save` — единственное место, вызывающее `store.put`;
`store_upload` вызывает его: `await self.save(item_id, crop_to_cover(data),
now)` вместо повторного `self.store.put(...)`.

### 2. `poster_for` / `Loader.ensure` — не повтор, разные предметы за общей формой

Прочитаны `backend/service/posters.py:72-89` и
`backend/service/loading.py:44-75`. Общая фраза действительно есть: «нет —
сходи и сохрани», но исполняемого кода общего нет. `poster_for` линейна:
проверить хранилище по `item_id` → скачать → записать. `ensure` — это
оркестрация другого уровня: сверka `view.item_id`, поиск по
`find_by_source`, получение клиента, **параллельный** `asyncio.gather` двух
разных запросов (карточка и обложка через `self._posters.fetch`, а не
`poster_for`) и передача результата `CardWriter.save`, которая заводит
строку целиком в нескольких таблицах. `poster_for` работает с байтами одной
картинки и никогда не вызывается изнутри `ensure` — там напрямую зовётся
`fetch`, потому что запись обложки при первом создании карточки идёт вместе
с запись остальных частей, а не сама по себе.

Это тот же довод, что уже записан в `docs/not-duplicates.md` и подтверждён
повторно в задаче 10 для пары `Enricher.enrich` ↔ `Loader.ensure`/`.refresh`:
общая форма «спросить источник, записать» — идиома всего сервисного слоя
(спека прямо описывает три круга загрузки), а не повтор друг друга. Не
повтор.

### 3. `poster_for` / `Enricher.enrich` — не повтор, разное понятие «просрочено»

Прочитаны `backend/service/posters.py:72-89` и
`backend/service/enrich.py:51-78`. Оба читают текущее состояние и решают,
спрашивать ли источник — но критерий «нужно ли спрашивать» у них
принципиально разный. `enrich` определяет протухшее через
`ExternalRatingsRepository.stale_sources(item_id, expected, now)` — по сроку
`fetched_at` по каждому источнику отдельно, и даже когда что-то протухло,
не спрашивает источники, для которых нет `imdb_id`. У `poster_for` понятия
срока годности нет вовсе: `if stored is not None: return stored` — лежащая
обложка не переспрашивается никогда, пока карточка жива. Дальше у `enrich`
харвест по нескольким клиентам разом с правилом первого ответившего и
записью пустого значения для отказавших, а `poster_for` работает с одним
источником и одним результатом. Общего кода нет ни строки — совпадает
только высокоуровневая фраза «недостающее или просроченное — переспроси»,
и то не совпадает: у обложки нет «просроченного». Не повтор.

### 4. `covers` — подтверждённый повтор транспорта, отслеживающего запросы

Прочитаны `tests/backend/test_cover_reads.py:13-23` и
`tests/backend/test_loading.py:66-90`, а также `capture` в
`tests/backend/sources/conftest.py:63-76`.

`covers`:

```python
asked = []

def answer(request: httpx.Request) -> httpx.Response:
    asked.append(str(request.url))
    return httpx.Response(200, content=PICTURE)

return poster_service(posters, httpx.MockTransport(answer)), asked
```

`loader.build`:

```python
asked = []

def answer(request: httpx.Request) -> httpx.Response:
    asked.append(str(request.url))
    return httpx.Response(poster_status, content=PICTURE)

parts = card_parts(sessions, posters, httpx.MockTransport(answer))
```

Замыкания совпадают дословно с точностью до источника кода ответа
(`200` против параметра `poster_status`). Но это не только повтор друг
друга — это ещё и переизобретение уже существующего `capture()`:

```python
def capture(*, content: bytes | None = None):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if content is None:
            return httpx.Response(200, json={})
        return httpx.Response(200, content=content)

    return httpx.MockTransport(handler), seen
```

`capture()` уже используется ровно для этой задачи в соседнем файле того же
пакета — `tests/backend/test_poster_service.py:112` (`transport, seen =
capture(content=POSTER)`), с тем же паттерном вызова `poster_service(posters,
transport)`, что и в `covers`. То есть `covers` — это третий по счёту
инструмент «транспорт + список ушедших запросов» на уровне сервиса обложек,
и не единственный до неё: `loader` завёл свой раньше. Со стороны `covers`
переиспользовать `capture()` было можно сразу — она рядом, в том же пакете
`tests.backend.sources.conftest`, уже импортируется файлами `tests/backend/`
(например, `test_card_writer.py`, `test_poster_service.py`).

Разница с уже принятой в `docs/not-duplicates.md` парой
`tests/backend/sources/conftest.py:capture` (там не фигурирует, но по духу
похоже на `responding`/`unreachable` — оснастка транспорта, разная по
поведению): здесь `covers` и `loader.build` не отличаются по поведению от
`capture()` вовсе, кроме одной детали — `capture()` кладёт в список сам
`httpx.Request`, а не готовую строку `str(request.url)`; это не отличие по
существу, обе стороны сразу берут `str(request.url)` в проверках
(`test_cover_reads.py`) либо используют `str(request.url)` при построении
`Rig.requests`.

**Что оставить.** `capture()` из `tests/backend/sources/conftest.py` — уже
существующий и уже используемый в том же пакете инструмент. `covers`
переписывается на `transport, asked = capture(content=PICTURE)` (с адаптацией
на `str(request.url)` там, где сейчас сравнивается `asked` напрямую).
`loader.build` в `tests/backend/test_loading.py` — тем же приёмом:
`transport, requests = capture(content=PICTURE)`; поле `Rig.requests`
собирается из `[str(r.url) for r in requests]`, либо `Rig` хранит сам список
`Request` и сравнение на месте использования берёт `.url`. Отдельных
рукописных замыканий `answer(request)` в обоих файлах не остаётся.

### 5. `STORED` / `PICTURE` — не повтор, третий случай уже разобранного расхождения

Прочитаны `tests/backend/test_cover_reads.py:10` и `tests/conftest.py:49`
(`PICTURE`), а также докстринг `picture()` там же. `docs/not-duplicates.md`
уже отличает `picture()` (настоящая картинка через Pillow, нужна там, где
предмет проверки — размер) от `PICTURE` (руками набранные байты с подписью,
нужны там, где проверяется побайтовая сохранность). `STORED` — тот же
приём, что `PICTURE`: подпись формата плюс набивка нулями, руками. Разница
в значении — не случайность, а единственная причина, по которой константа
вообще существует: комментарий рядом прямо это объясняет — «Вторая картинка
нужна, чтобы отличить «отдали лежащее» от «скачали заново»: с одинаковыми
байтами эти два случая неразличимы. Подпись JPEG, а не PNG». Слить `STORED`
с `PICTURE` в одно значение — значит стереть ровно то различие, ради
которого весь файл `test_cover_reads.py` может проверить, что кешированный
постер не идёт по сети за новым. Как и `picture()` против `PICTURE`, это не
повтор, а третий случай того же обоснованного расхождения: одна картинка на
роль, а не одна на все нужды теста. Не повтор.

## Вердикт

Из пяти кандидатов подтверждены два:

- где / где / что оставить: `backend/service/posters.py:PosterService.save`
  / `backend/service/posters.py:PosterService.store_upload` — `store_upload`
  зовёт `self.save(item_id, crop_to_cover(data), now)` вместо повторного
  `self.store.put(...)`.
- где / где / что оставить: `tests/backend/test_cover_reads.py:covers` /
  `tests/backend/test_loading.py:loader.build` — обе стороны используют уже
  существующий `tests/backend/sources/conftest.py:capture`; рукописные
  замыкания `answer(request)` убираются из обоих файлов.

Остальные три при чтении обоих мест разошлись по существу: `poster_for`
против `fetch`/`save` — верная композиция без повтора; `poster_for` против
`Loader.ensure` — общая идиома слоя, а не общий код (тот же довод, что для
`Enricher.enrich` ↔ `Loader.ensure` в задаче 10); `poster_for` против
`Enricher.enrich` — разное понятие протухания, общего кода нет; `STORED`
против `PICTURE` — третий случай уже разобранного расхождения
«руками набранные байты с подписью для проверки сохранности» против
«настоящая картинка для проверки размера».

**Готово к коммиту: С правками**
