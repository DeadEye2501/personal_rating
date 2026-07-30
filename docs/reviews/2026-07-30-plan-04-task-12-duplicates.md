# Ревью повторов — план 4, задача 12 (слаг GOG в числовой идентификатор)

Измерение: повторы во всём проекте, не в диффе. Дифф не читался. Карты
(`docs/module-map.md`, `docs/data-map.md`) прочитаны целиком,
`docs/not-duplicates.md` — тоже; пары, уже разобранные там, заново не
поднимались.

## Рассмотренные кандидаты — 6

1. `GogClient.resolve_slug` против `GogClient.card`
   (`backend/sources/gog/client.py`) — оба спрашивают каталог и ищут в нём
   нужную строку.
2. `find_slug` (`backend/sources/gog/parse.py`) против цикла отбора внутри
   `GogClient.card`.
3. `Loader.card_for_link` против `Loader.ensure`
   (`backend/service/loading.py`) — оба ходят к каталожному клиенту за
   карточкой.
4. `FakeCatalog` в `tests/backend/test_link_loading.py` против `FakeCatalog`
   в `tests/backend/test_loading.py` — одно имя, оба наследники `FakeClient`,
   у обоих есть `card`.
5. `source_card` в `tests/backend/test_link_loading.py` против `source_card`
   в `tests/backend/test_loading.py` и в `tests/backend/test_card_writer.py`.
6. Фикстура `tests/fixtures/gog/catalog_by_slug.json` против
   `tests/fixtures/gog/catalog.json` и `tests/fixtures/gog/catalog_nonsense.json`.

Подтверждён один: **п. 3**.

## Разбор по каждому

### 1. `resolve_slug` / `card` — не повтор, разный источник данных и разное «не нашлось»

Прочитано `backend/sources/gog/client.py:62-117` целиком.

`card` идёт через `_catalog(source_id)` — уже разобранный список
`SourceCard`, — и ищет совпадение по `card.item.source_id`. `resolve_slug`
идёт через `_payload(slug…)` — сырое тело ответа, ещё не разобранное, — и
отдаёт его в `find_slug`, которая ищет совпадение по `row["slug"]` в сыром
словаре. Это два разных представления одного и того же ответа, и разделение
намеренное: докстринг `_payload` прямо говорит — «Разбирают его двое и
по-разному: поиску нужны кандидаты, привязке — номер по слагу». Если бы
`resolve_slug` тоже шла через `_catalog`, `find_slug` не на чем было бы
работать — сравнение по слагу требует сырого поля `slug`, которого в
`SourceCard`/`Item` нет вовсе.

Дальше расходится и обработка «не нашлось»: у `card` это `Refusal` с
`Reason.BROKEN` (по контракту `search`/`card` этого клиента `Missing` не
возвращается никогда — так и написано в докстринге класса), у
`resolve_slug` — честный `Missing()` (тоже задокументировано прямо в её
докстринге: «здесь спрашивают не „что похоже на это название“, а „есть ли
ровно такой слаг“, и его отсутствие — честный ответ»). Слитые, эти два
метода потребовали бы флага «это slug-режим», от которого расходились бы и
источник данных, и тип отказа при пустом результате. Не повтор.

### 2. `find_slug` против цикла в `card` — не повтор, разные коллекции и разные поля

Прочитаны `backend/sources/gog/parse.py:67-74` и цикл в
`backend/sources/gog/client.py:88-90`.

```python
# find_slug
for row in payload.get("products") or []:
    if row.get("slug") == slug:
        return str(row["id"])
```

```python
# GogClient.card
for card in cards:
    if card.item.source_id == source_id:
        return Found(card)
```

Общая только форма «цикл, сравнение, возврат при совпадении» — трёх строк,
ниже порога хука (пять инструкций), поэтому кандидат обоснованно всплыл при
ручном проходе. Но предметы разные до полного несовпадения: один перебирает
сырые словари и сравнивает строку `slug`, отдавая идентификатор строкой;
другой перебирает уже собранные `SourceCard` и сравнивает `item.source_id`,
отдавая саму карточку. Общий помощник принял бы предикат и коллекцию как
параметры и сравнялся бы по длине с суммой обоих циклов. Не повтор — тот же
случай, что уже записан в `docs/not-duplicates.md` про `ExternalIdsRepository
.find_item` и `CreditRepository._found_id`: общего один приём, не код.

### 3. `card_for_link` / `ensure` — подтверждённый повтор одного блока «нет клиента»

Прочитан `backend/service/loading.py` целиком (44-98).

Методы разные по существу и сливать их не нужно: `ensure` сначала проверяет
`view.item_id` и локальную базу, потом параллельно (`asyncio.gather`) тянет
детальную карточку и обложку и отдаёт результат `CardWriter.save` — то есть
пишет строку в базу. `card_for_link` ничего не пишет, разбирает частный
случай GOG (слаг → номер) и отдаёт голый `SourceCard` — записывать его
предстоит вызывающему через `Linker`, а не через `Loader`. Это два разных
шага пайплайна, и общий метод свёл бы их в одну функцию с длинным
разветвлением на «это привязка или это создание».

Но внутри них есть буквально одинаковый блок — получение клиента и обработка
его отсутствия:

```python
# ensure, строки 54-58
client = self._sources.client_for(view.source)
if client is None:
    logger.warning("нечем загрузить карточку источника %s", view.source)
    return Refusal(source=str(view.source), reason=Reason.BROKEN,
                   detail=f"нет каталожного клиента для {view.source}")
```

```python
# card_for_link, строки 84-88
client = self._sources.client_for(link.source)
if client is None:
    logger.warning("нечем сходить по ссылке на %s", link.source)
    return Refusal(source=str(link.source), reason=Reason.BROKEN,
                   detail=f"нет каталожного клиента для {link.source}")
```

Совпадает всё, кроме текста сообщения в логе и того, что источник читается
с `view.source` в одном случае и `link.source` в другом — оба типа `Source`.
Четыре инструкции, ниже порога хука — тот самый случай, который ловит только
ручной проход. Оба теста (`tests/backend/test_loading.py
:test_an_unknown_source_is_a_refusal_and_a_log` и
`tests/backend/test_link_loading.py
:test_a_link_to_a_source_without_a_client_is_a_refusal`) проверяют этот же
блок дважды, разными путями, но с одним и тем же поведением.

**Что оставить.** Общий блок выносится приватным методом `Loader`, например
`_client_or_refusal(self, source: Source, action: str) -> object | Refusal`,
логирующим `"нечем %s: %s"` (или похожей форматной строкой, сохраняющей два
разных текста через параметр `action`) и строящим тот же `Refusal`. `ensure`
и `card_for_link` зовут его вместо повторной пятистрочной проверки.

### 4. `FakeCatalog` — не повтор, идиома `FakeClient`, а не общий код

Прочитаны `tests/backend/test_link_loading.py:17-32` и
`tests/backend/test_loading.py:31-36`, а также докстринг `FakeClient` в
`tests/conftest.py:94-100`.

```python
# tests/backend/test_loading.py
class FakeCatalog(FakeClient):
    """Спрашивают у него только детальную карточку."""

    async def card(self, source_id: str, kind: Kind):
        self.asked.append((source_id, kind))
        return self.outcome
```

```python
# tests/backend/test_link_loading.py
class FakeCatalog(FakeClient):
    def __init__(self, card_outcome, slug_outcome=None, name: str = "gog") -> None:
        super().__init__(card_outcome, name)
        self.slug_outcome = slug_outcome
        self.slugs_asked = []

    async def card(self, source_id: str, kind: Kind):
        self.asked.append((source_id, kind))
        return self.outcome

    async def resolve_slug(self, slug: str):
        self.slugs_asked.append(slug)
        return self.slug_outcome
```

Тело `card` в обеих версиях действительно дословно совпадает — но это ровно
то поведение, которое `FakeClient` явно оставляет наследникам: «Что у него
спрашивают, дописывают наследники: у каталожного это выдача поиска и
детальная карточка, у перезапроса — сезоны с сериями. Общее у всех трёх
одно: заданный исход, имя источника для отказа и список того, о чём
спросили». По этому же контракту в проекте уже живут `FakeCatalog.search`
в `tests/backend/test_search.py`, `FakeTmdb.series_counts` в
`tests/backend/test_series_refresh.py`, `FakeRatings.ratings` в
`tests/backend/test_enrich.py` — каждый воспроизводит одну и ту же
двухстрочную форму «запомнить аргументы, вернуть готовый исход» под свой
метод интерфейса. Совпадение имени класса и метода здесь не случайность в
смысле «забыли переиспользовать», а следствие того, что оба файла подделывают
один и тот же интерфейс (`card` каталожного клиента) для одного и того же
`Loader`.

Слить их значило бы связать `test_loading.py` и `test_link_loading.py`
общим классом — либо через импорт одного файла в другой, либо через новый
пакетный `conftest.py`, которого сейчас в `tests/backend/` нет ни для чего
другого. Цена — двухстрочный метод, которого сегодняшний хук на дубли не
видит потому, что видеть там нечего: это тот же идиоматический повтор,
что уже отклонён для `TmdbClient.name`/`SteamClient.name`/`GogClient.name`
в `docs/not-duplicates.md` («общий интерфейс… а не повтор»). Не повтор.

### 5. `source_card` в трёх файлах — не повтор, разный состав под разную проверку

Прочитаны все три: `tests/backend/test_link_loading.py:10-14`,
`tests/backend/test_loading.py:44-52`, `tests/backend/test_card_writer.py
:35-52`.

```python
# test_link_loading.py — общий для TMDB и GOG, минимальная карточка
def source_card(source: Source, source_id: str) -> SourceCard:
    return SourceCard(
        item=Item(id=0, kind=Kind.GAME, source=source, source_id=source_id,
                  title="Arcanum", synced_at=MOMENT)
    )
```

```python
# test_loading.py — жёстко TMDB/фильм, с людьми и длительностью
def source_card(source_id="157336",
                poster="https://example.com/p.jpg") -> SourceCard:
    return SourceCard(
        item=Item(..., runtime=169, poster_url=poster),
        people=(Credit("Кристофер Нолан", PersonRole.DIRECTOR, …),),
    )
```

```python
# test_card_writer.py — полный набор через умолчания и замены
def source_card(**overrides) -> SourceCard:
    fields = dict(item=…, genre_ext_ids=…, people=(…, …), companies=(),
                  external_ids=(…,), ratings=(…,))
    fields.update(overrides)
    return SourceCard(**fields)
```

Три версии обслуживают три разных предмета проверки. `test_link_loading.py`
проверяет маршрутизацию (TMDB напрямую, GOG через слаг) — ей всё равно, что
внутри карточки, важно только, что `source`/`source_id` можно передать для
любого из двух источников, поэтому сигнатура позиционная и минимальная.
`test_loading.py` проверяет, что второй круг загрузки донёс длительность и
состав — ей нужны именно `runtime` и `people`. `test_card_writer.py`
проверяет запись в базу по всем таблицам — ей нужны жанры, оценки и внешние
идентификаторы. Это тот же приём, что уже разобран в `docs/not-duplicates.md`
для пары `test_linking.py:incoming` / `test_card_writer.py:source_card` —
«карточки разные по назначению… слитые, они потянули бы замены в каждый
вызов». Слить эти три значило бы отдать самому скупому вызывающему
(`test_link_loading.py`) все поля, которые нужны только двум другим. Не
повтор.

### 6. Фикстуры GOG — не повтор, три разных записанных сценария

`tests/fixtures/gog/catalog_by_slug.json` — 14 строк, два продукта с тремя
полями (`id`, `slug`, `title`), один из них — почти совпадающий по слагу
сосед (`arcanum_soundtrack` рядом с `arcanum_of_steamworks_and_magick_
obscura`), нужный ровно для проверки строгого совпадения в `find_slug`.
`tests/fixtures/gog/catalog.json` — 3357 строк, полный «боевой» ответ
каталога на осмысленный запрос, с фичами, скриншотами и остальными полями,
которые `find_slug` не читает вовсе. `tests/fixtures/gog/catalog_nonsense.
json` — 7861 строка, ответ на бессмысленный запрос: используется там, где
предмет проверки — то, что GOG не умеет говорить «не найдено» и на любую
бессмыслицу отвечает десятками несвязанных игр. Размер, состав полей и цель
не совпадают ни у одной пары — это три разных живых снятия по правилу
проекта «живых ответов источников записывают в `tests/fixtures/`», а не один
файл, продублированный трижды. Не повтор.

## Вердикт

Из шести кандидатов подтверждён один:

- где / где / что оставить: `backend/service/loading.py:Loader.ensure`
  (строки 54-58) / `backend/service/loading.py:Loader.card_for_link`
  (строки 84-88) — блок «нет клиента → `Refusal`» выносится приватным
  методом `Loader`, оба вызывают его вместо повторной пятистрочной проверки.

Остальные пять при чтении обоих мест разошлись по существу: `resolve_slug`
против `card` — разный источник данных (`_payload` против `_catalog`) и
разное «не нашлось» (`Missing` против `Refusal`), обе стороны задокументированы
докстрингами; `find_slug` против цикла в `card` — разные коллекции и поля
сравнения; `FakeCatalog` в двух файлах — идиома `FakeClient`, где каждый
наследник сам определяет, что спрашивает, и это уже отклонённый тип повтора
(«общий интерфейс, а не повтор» — как у `.name` трёх клиентов); `source_card`
в трёх файлах — тот же приём «умолчания плюс замены» под разный состав полей,
что и уже принятая пара `incoming`/`source_card`; фикстуры GOG — три разных
живых снятия под три разные проверки.

**Готово к коммиту: С правками**
