# Ревью повторов — план 4, задача 8 (три круга загрузки: `Loader.ensure`)

Измерение: повторы во всём проекте, не в диффе. Дифф не читался.

## Рассмотренные кандидаты

1. `Loader.ensure` (`backend/service/loading.py`) против `CardWriter.save`
   (`backend/service/cards.py`) и `Linker.link` (`backend/service/linking.py`)
   — границы и третий повтор общего
2. Разбор исхода `gather` в `Loader.ensure` против `SearchService.external` /
   `_broke` (`backend/service/search.py`) — и против готового помощника
   `broken()` (`backend/sources/errors.py`)
3. `Sources.client_for` против `Sources.catalog_for` и
   `Sources.rating_sources` (`backend/sources/registry.py`)
4. `FakeCatalog` в `tests/backend/test_loading.py` против `FakeCatalog` в
   `tests/backend/test_search.py`
5. `Rig` в `tests/backend/test_loading.py` против `card_parts` и
   `poster_service` в `tests/conftest.py`
6. `candidate` / `source_card` в `tests/backend/test_loading.py` против
   `an_item`, `rated` (`tests/conftest.py`), `hit`, `local_view`
   (`tests/backend/test_search.py`) и `source_card`
   (`tests/backend/test_card_writer.py`)

Итого рассмотрено: **6**. Подтверждённых повторов, требующих действия: **1**
(п. 2, только его часть про `Loader.ensure`).

## Разбор по каждому

### 1. `Loader.ensure` / `CardWriter.save` / `Linker.link` — не повтор, границы держатся

Прочитаны все три целиком: `backend/service/loading.py:27-67`,
`backend/service/cards.py:19-62`, `backend/service/linking.py:55-128`, а
также общий предок `backend/service/card_parts.py`.

Три разные ответственности на одной цепочке «кандидат → строки базы»:

- `Loader.ensure` — вход из ленты и поиска: уже лежит ли карточка (по
  `item_id`, по паре источник+идентификатор), если нет — просит у
  каталожного клиента детальный ответ и обложку разом и передаёт готовое
  писателю. Own state: `library`, `writer`, `sources`, `posters` — репозиторий
  карточек он трогает только на чтение (`find_by_source`), запись поручена
  целиком `CardWriter`.
- `CardWriter.save` — заводит строку с нуля и убирает за собой при срыве.
- `Linker.link` — правит существующую строку, не трогая занятое человеком.

`CardWriter` и `Linker` — оба наследники `CardParts`, и общее у них (сборка
репозиториев, `_attach_credits`, `_write_external`) уже вынесено туда.
`Loader` от `CardParts` нарочно не наследует: ему не нужны ни жанры, ни
состав, ни чужие идентификаторы напрямую — только чтение библиотеки и вызов
`writer.save`. Третьего повтора того же рода (сборка репозиториев, откат,
слияние полей) в `Loader` нет ни одного. Не повтор.

### 2. Разбор исхода `gather` — частично подтверждённый повтор в `Loader.ensure`

Прочитаны `backend/service/loading.py:45-67`,
`backend/service/search.py:70-104`, `backend/service/cards.py:28-46` и
`backend/sources/errors.py:48-51`.

Структура разбора у `Loader.ensure` и `SearchService.external` разная не по
флагу, а по задаче, и здесь повтора нет: `Loader.ensure` ждёт **два разных по
типу** результата (`Outcome` карточки и `bytes | None | Refusal` обложки) и
останавливается на первой же беде; `SearchService.external` ждёт **список
одного и того же типа** от нескольких клиентов и копит успехи и отказы
раздельно, не останавливаясь ни на одном. Слитые, они дали бы метод с веткой
на «один результат или список» в каждой строке.

Но внутри самого `Loader.ensure` нашёлся настоящий повтор — не с
`SearchService`, а с уже существующим в проекте помощником:

```python
# backend/service/loading.py:51-58
for outcome in (card, poster):
    if isinstance(outcome, BaseException):
        logger.exception("загрузка карточки %s сорвалась",
                         view.source_id, exc_info=outcome)
        return Refusal(source=str(view.source), reason=Reason.BROKEN,
                       detail=str(outcome))
```

```python
# backend/sources/errors.py:48-51
def broken(source: str, error: Exception) -> Refusal:
    """Отказ по неразобранному ответу. Запись в лог остаётся на месте вызова:
    сообщение у каждого своё, и по нему потом ищут причину."""
    return Refusal(source=source, reason=Reason.BROKEN, detail=str(error))
```

`Refusal(source=str(view.source), reason=Reason.BROKEN, detail=str(outcome))`
— это буквально тело `broken()`, собранное заново на месте вместо вызова.
Помощник для ровно этого случая — «исключение поймано, лог пишется тут же,
отдай `Refusal(BROKEN)`» — уже есть и это установленная идиома всего слоя
источников: `broken()` зовётся в `backend/service/cards.py:32,46` (тем же
порядком — `logger.exception(...)`, затем `return broken(...)`) и во всех
шести клиентах источников (`grep` по `broken(` — 14 мест). `Loader.ensure`
— единственное место в проекте, где тот же исход собирается вручную заново,
хотя строкой ниже по файлу для того же результата подошёл бы готовый
однострочный вызов.

Заодно нашлось то же самое, только раньше — в `SearchService._broke`
(`backend/service/search.py:98-104`):

```python
def _broke(self, client, error: BaseException) -> Refusal:
    logger.exception("поиск в %s сорвался", client.name, exc_info=error)
    return Refusal(source=client.name, reason=Reason.BROKEN, detail=str(error))
```

Это тоже ручная пересборка `broken()`, но код старый (задача 7, уже прошёл
своё ревью повторов и коммит), в этот слайс не входит и правкой этой задачи
не является — упоминаю как наблюдение, не как пункт к действию сейчас.

**Что оставить:** в `Loader.ensure` заменить ручную сборку `Refusal` на
`return broken(str(view.source), outcome)`, оставив `logger.exception(...)`
на месте вызова (это и предписывает докстрока `broken()`). Импорт
`Refusal` из `backend.sources.errors` в `loading.py` тогда меняется на
`broken` (сам тип `Refusal` в файле больше нигде не собирается — стоит
проверить, нужен ли он ещё в сигнатуре `-> int | Missing | Refusal`; нужен,
это тип возврата, импорт остаётся).

### 3. `Sources.client_for` / `catalog_for` / `rating_sources` — не повтор

Прочитаны все три в `backend/sources/registry.py:36-57`. Три разных вопроса:
`catalog_for(kind)` и `rating_sources(kind)` — «каких клиентов спросить для
этого типа содержимого» (список, ветвление по `Kind`), `client_for(source)`
— «какой один клиент отвечает за карточку с этим источником» (словарь,
единственное значение или `None`). Разная арность результата (список против
одного значения или `None`), разный ключ (`Kind` против `Source`) и разная
структура (`if/else` против словаря-константы). Общего кода между ними нет ни
строки. Не повтор.

### 4. `FakeCatalog` в `test_loading.py` / `FakeCatalog` в `test_search.py` — не повтор

Прочитаны `tests/backend/test_loading.py:25-34` и
`tests/backend/test_search.py:20-33` целиком. Имя одно, файлы разные — и это
ровно тот случай, где имя одно, а предмет разный:

- `test_loading.py` подставляет клиент **детального ответа**: единственный
  метод `card(source_id, kind)`, без атрибута `name` (в тестах загрузки
  клиент один, представлять его в отказе не нужно — сам `Loader.ensure`
  берёт имя из `view.source`, а не у клиента), исключение имитируется прямой
  подменой `rig.client.card` в одном тесте, а не веткой внутри метода.
- `test_search.py` подставляет клиент **поиска**: метод `search(query, kind)`,
  обязательный атрибут `name` (нужен `SearchService._broke`, который в
  отказе подписывает клиента по имени, а не по `repr`), и исключение
  встроено в сам метод (`if isinstance(self.outcome, BaseException): raise`),
  потому что тестов на «сорвался один из двух магазинов» здесь много и
  переопределять метод в каждом было бы дороже.

Ни один атрибут, ни одна строка тела не совпадают. Слитые под одним именем,
они дали бы подставной клиент с методом на выбор и мёртвым атрибутом `name`
там, где он не нужен. Не повтор — та же семья решений, что уже описана в
`docs/not-duplicates.md` для пары «одна карточка против страницы»: похоже по
роли (подставной клиент), разное по контракту.

### 5. `Rig` (`test_loading.py`) / `card_parts`, `poster_service` (`conftest.py`) — не повтор

Прочитаны `tests/backend/test_loading.py:53-88` и
`tests/conftest.py:62-74,149-155`. `card_parts` и `poster_service` — общие
фабрики production-объектов (репозитории, `PosterService`), и `Rig` их не
пересобирает, а зовёт как есть внутри `build()`:

```python
parts = card_parts(sessions, posters, httpx.MockTransport(answer))
...
return Rig(load=Loader(..., writer=CardWriter(**parts), ...), ...)
```

`Rig` — датакласс-обвязка вокруг результата этого вызова: то, за чем
наблюдает тест (`load`, `client`, `posters`, `requests`), и не описывает
ничего из того, что уже описывают `card_parts`/`poster_service`. Общего кода
нет. Не повтор.

### 6. `candidate` / `source_card` (`test_loading.py`) против прочих строителей — не повтор

Прочитаны `tests/backend/test_loading.py:37-50`, `tests/conftest.py:77-91,
113-124` (`an_item`, `rated`), `tests/backend/test_search.py:36-47` (`hit`,
`local_view`), `tests/backend/test_card_writer.py:35-52` (`source_card`).

- `candidate()` строит `CardView` без `item_id` — кандидат, ещё не карточка,
  ровно то, что подаётся на вход `Loader.ensure`. `local_view()`
  (`test_search.py`) строит `CardView`, но **с** `item_id=7` — уже
  сохранённую карточку для проверки `merge_results`. Разница в одном поле —
  и это ровно то поле, которым проверка каждого файла и живёт: «есть ли
  идентификатор» решает, идёт ли карточка в `Loader.ensure` за детальным
  ответом или уже готова к показу. Слитые, они стёрли бы это различие или
  потребовали бы необязательного `item_id` с проверкой на каждый вызов — тот
  же довод, что уже записан для пары `SearchHit`/`Item` в
  `docs/not-duplicates.md`.
- `an_item`/`rated` строят `Item` — их место ниже по стеку, где карточка уже
  разложена по колонкам; `candidate` работает на границе поиска и загрузки,
  где сохранённости ещё нет. Разные типы, разные слои.
- `hit()` строит `SearchHit` — сырую находку внешнего источника, ещё без
  перевода в `CardView`. `candidate()` начинается на шаг позже: вход
  `Loader.ensure` — это уже `CardView`, прошедший `view_from_hit`. Общих
  полей формально несколько (`source_id`, `title`), но предмет и место в
  конвейере разные.
- `source_card()` в `test_loading.py` (два позиционных параметра —
  `source_id`, `poster`, только `item` и один `people`) и `source_card()` в
  `test_card_writer.py` (`**overrides` поверх богатого умолчания с жанрами,
  студиями, внешними идентификаторами и оценкой) совпадают именем и одной
  парой значений («Интерстеллар», Нолан с `source_id="525"`), но это
  тот же приём, что уже разобран в `docs/not-duplicates.md` для пары
  `test_linking.py:incoming` / `test_card_writer.py:source_card`:
  «карточки разные по назначению». Здесь тестам `Loader.ensure` не нужны ни
  жанры, ни студии, ни внешние идентификаторы, ни оценки — предмет проверки
  «кандидат стал карточкой», а не разбор этих полей (это уже проверяет
  `test_card_writer.py`), и двухпараметровая сигнатура удобнее для
  дюжины вызовов, где меняется только `source_id` или `poster`. Переиспользуй
  тест загрузки богатый `source_card(**overrides)` — пришлось бы на каждый
  вызов гасить пять полей, которые к делу не идут (`genre_ext_ids=()`,
  `companies=()`, `external_ids=()`, `ratings=()`), либо чинить `item` целиком
  ради смены одного `poster_url`. Не повтор, тот же прецедентный довод.

## Вердикт

Из шести кандидатов подтверждён один — `Loader.ensure` вручную пересобирает
`Refusal(BROKEN)` вместо вызова уже существующего в проекте `broken()`,
идиомы, использованной 14 раз в шести клиентах источников и в
`CardWriter.save`. Остальные пять при чтении обоих мест разошлись по
существу: либо разный слой и тип данных, либо принятый в проекте прецедент
«похожие по роли, разные по контракту» строители в тестах.

- где / где / что оставить: `backend/service/loading.py:54-58` (ручная сборка
  `Refusal`) / `backend/sources/errors.py:48-51` (`broken()`) — оставить
  вызов `broken(str(view.source), outcome)`, убрать ручную сборку в
  `loading.py`.

**Готово к коммиту: С правками**
