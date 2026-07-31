# План 5. Окно и мост

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** питоновская половина клиента целиком. Окно pywebview с системным
WebView2, бэкенд в своём потоке со своим циклом asyncio, мост из семи доменных
модулей, перевод типов границы в JSON, номер операции с настоящей отменой и
сроком, страница и обложки своим WSGI-обработчиком. После этого плана страница
может спросить у бэкенда что угодно, а показывать это будет план 6.

**Архитектура:** три слоя без обратных связей. `bridge/thread.py` владеет циклом
и списком живых задач — он единственный, кто знает про потоки. `bridge/`
переводит вызов страницы в корутину бэкенда и ответ обратно в JSON: домен на
файл, общее — в `wire.py` (значения) и `answer.py` (оболочка вызова).
`bridge/serve.py` отдаёт страницу и обложки по HTTP, потому что байты через мост
не ходят. `bridge/window.py` поднимает окно, `main.py` собирает всё и настраивает
лог.

Мост тонкий: он **не оркеструет**. Порядок нескольких записей — дело страницы,
и это записанное решение проекта («клиент зовёт репозитории напрямую, сервисный
слой поверх не заводится»). Своего у моста ровно три вещи: перевод значений,
единый формат отказа и память о том, что не пролезает обратно через JSON.

**Стек:** pywebview 6.2.1 (уже в зависимостях), стандартная библиотека. Ни одной
новой зависимости. Фронта в этом плане нет вовсе — ни Vite, ни Svelte, ни npm.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от планов 1–4.** Бэкенд закончен: `build_backend(config, transport)`
  отдаёт `Backend` с семью репозиториями и семью сервисами.
- **`bridge` не импортирует ни `sqlalchemy`, ни `httpx`, ни `aiosqlite`, ни
  `alembic`, ни `PIL`.** Из бэкенда ему открыты только `backend.model` и
  `backend.config`. Это сторожит `tests/backend/test_layers.py`, и на первом же
  файле `bridge/` его вторая половина просыпается.
- **`backend` не импортирует ни `bridge`, ни `webview`, ни `pythonnet`, ни `clr`.**
  Тот же сторож, обратная половина.
- **`build_backend` в `bridge/` не вызывается и не импортируется.** Он приезжает
  готовой функцией из `main.py`: иначе `bridge/thread.py` притащил бы
  `backend.app`, а с ним `sqlalchemy`. Это же и есть вторая причина, по которой
  сборка внедряется, а не берётся по имени.
- **Через мост ходят только простые данные:** числа, строки, списки, словари,
  `None`. Ни датаклассов как есть, ни `datetime`, ни байтов.
- **Байты не ходят через мост вовсе.** Результат вызова pywebview вклеивает в
  текст скрипта; обложка едет HTTP-ручкой. Обратно (заливка своей картинки) —
  base64 в аргументе, там канал другой (`postMessage`).
- **Корутин в `js_api` не бывает.** pywebview зовёт метод синхронно, без
  `await`; корутинный объект уехал бы в `json.dumps` и дал отклонённый промис.
  Любая работа бэкенда идёт через `BackendThread`.
- **Исключений из моста наружу не летит.** Отказ — значение в ответе. Наружу
  уходит либо `{"ok": ...}`, либо `{"fail": ...}`, третьего вида ответа нет.
- **Молча не глотаем ничего.** Пойманное исключение ведёт либо к `fail` в
  ответе, либо к записи в лог — минимум одно из двух, а у непредвиденного и то и
  другое.
- **Время подставляет мост.** Десять операций бэкенда требуют `datetime`
  доводом, но мост подставляет его в семи: `library.refresh_series_counts`,
  `library.link` и `posters.save` — служебные, страница их не зовёт. Часов от
  неё не требуется нигде.
- **В сеть тесты не ходят и окна не поднимают.** Проверяется всё обычным
  `pytest`: бэкенд подменяется двойником, окно в тестах не создаётся ни разу.
- **Байтовые литералы только ASCII.** `b"текст"` с кириллицей — `SyntaxError` на
  сборе, который валит весь прогон.
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ main.py                       сборка, лог, запуск окна
├─ bridge/
│  ├─ thread.py                  поток бэкенда: цикл, живые задачи, отмена
│  ├─ window.py                  окно pywebview и проверка рендерера
│  ├─ serve.py                   WSGI: страница, ресурсы, обложка
│  ├─ api.py                     поверхность моста, собранная из доменов
│  ├─ wire.py                    значения границы в JSON
│  ├─ answer.py                  оболочка вызова: срок, отказ, один формат
│  ├─ kept.py                    то, что не пролезает обратно
│  ├─ library.py                 карточка: заведение, правка, удаление
│  ├─ marks.py                   мои отметки: оценки, теги, закладки
│  ├─ refs.py                    справочники: жанры, люди, студии
│  ├─ feed.py                    лента: страницы и гистограмма
│  ├─ search.py                  поиск: свой, чужой, складывание, заведение
│  ├─ world.py                   внешний мир: привязка, перезапрос, обогащение
│  └─ covers.py                  обложки: заливка и наличие
├─ backend/model/
│  └─ denied.py                  пять отказов операции
└─ tests/bridge/
   ├─ conftest.py                двойники бэкенда и поток на них
   ├─ test_thread.py             граница потоков
   ├─ test_wire.py               перевод значений
   ├─ test_answer.py             один формат ответа
   ├─ test_kept.py               память моста
   ├─ test_bridge_library.py     test_bridge_marks.py
   ├─ test_bridge_refs.py        test_bridge_feed.py
   ├─ test_bridge_search.py      test_bridge_world.py
   ├─ test_bridge_covers.py      test_bridge_surface.py
   ├─ test_serve.py              отдача страницы и обложки
   └─ test_window.py             решение по рендереру
```

Правятся и чужие файлы: `backend/model/__init__.py` (шесть имён отказа),
`backend/storage/repository/{library,tags,credits,external}.py`,
`backend/service/images.py` (объявления отказов уезжают в модель),
`tests/backend/test_layers.py` (половина про клиента переводится на `bridge`),
`client/__init__.py` (удаляется: питона в `client/` больше нет),
`.gitignore` (`client/dist`).

---

## Семь решений, принятых при написании плана

Все семь — следствия того, что видно только с этой стороны границы; поведения
приложения не меняет ни одно. Спека клиента (`docs/specs/2026-07-31-client.md`)
приведена к ним в тот же день, так что расхождения между ней и планом нет.

1. **Доменов моста семь, а не шесть.** Спека сводила ленту и поиск в один домен.
   Описать такой модуль одной фразой без «и» нельзя — это правило 6, — а
   складывание двух выдач требует, чтобы обе половины поиска лежали вместе.
   Отсюда `feed.py` (лента) и `search.py` (поиск).

2. **Номер операции несут поиск, внешний мир и лента** — то, что может быть
   отменено или вытеснено следующим таким же. Решено пользователем 31.07.2026:
   ленте номер нужен по той же причине, что и поиску, — при смене фильтра или
   сортировки старый ответ приезжать не должен. **Оценки, теги и закладки идут
   без номера:** отменять запись нельзя ни при каких обстоятельствах.

   Кто с номером, а кто без — таблица, а не догадка по сигнатурам:

   | Домен | С номером | Без номера |
   |---|---|---|
   | `search` | `local`, `external`, `ensure` | — |
   | `world` | `card_for_link`, `link`, `refresh_series`, `enrich`, `expected` | `parse`, `open` |
   | `feed` | `page`, `views_of`, `histogram` | — |
   | `marks` | — | все |
   | `library`, `refs`, `covers` | — | все |

   **Номер приходит от страницы, а не заводится мостом**, и обёртка страницы
   отдаёт его наружу — иначе второй шаг двухшаговой операции приходит с новым
   номером, `Kept.taken` его не узнаёт, и внешняя выдача поиска не показывается
   никогда. Это же делает возможной отмену: без номера наружу список отменяемых
   наполнить нечем.

3. **«Добавить кандидата» лежит в поиске, а не во внешнем мире.** `loader.ensure`
   принимает `CardView`, а `CardView` обратно через JSON не собрать; кандидата
   мост берёт из выдачи, которую сам же и помнит, а помнит её поиск.

4. **Что не пролезает обратно, мост помнит у себя.** Два места: выдача поиска
   (`CardView` — 17 полей, шесть кортежей датаклассов, `datetime` внутри) и
   карточка привязки (`SourceCard`). Страница называет их по паре «источник +
   идентификатор» и по номеру операции, а не возит содержимое туда и обратно.

5. **Оценки агрегаторов догружаются только тому, что уже в базе.** У кандидата
   нет `imdb_id` — он приходит только в детальном ответе, — и спросить
   агрегаторов о нём нечем. Это не сужение, а то же самое, что записано в
   `search-and-loading.md`: «круг 3 нельзя начать раньше круга 2».

6. **Из семи исключений бэкенда в модель переезжают пять.** `NotOpened` —
   поломка сборки, а не нормальный ход событий: такому место в непредвиденном
   сбое, с логом и плашкой. `ExternalIdTaken` не пересекает границу вовсе: его
   ловит и пишет в лог сам `Enricher`, а у привязки на том же месте поднимается
   `ItemExists`. Оба остались бы в модели классами без сегодняшнего потребителя.

7. **Страницу отдаёт свой WSGI-обработчик, а не файловый сервер pywebview.**
   Иначе не сделать трёх вещей: корень `/` у него отвечает `500` (маршрут зовёт
   обработчик без обязательного аргумента), `.woff2` уезжает как `text/html`, а
   ручки обложки нет вовсе. Сервер pywebview при этом остаётся — он поднимает
   наше приложение как WSGI.

---

### Задача 1: Пять отказов операции переезжают в модель

Мост обязан различать, чем кончилась операция: переименовал тег в занятое имя —
одно сообщение, залил не картинку — другое. Сейчас эти исключения объявлены в
четырёх модулях `storage/` и `service/`, а клиенту открыты только `backend.model`
и `backend.config` — то есть поймать их по типу он не может вовсе.

Ровно так же в своё время переехали `Reason`, `Found`, `Missing` и `Refusal`:
тип, который клиент обязан различать, живёт в модели.

**Два исключения из семи остаются на месте, и оба по одной причине: до клиента
они не долетают.**

- **`NotOpened`** значит «хранилище постеров не открыли при сборке» — это наша
  поломка, и ей место в непредвиденном сбое, а не в списке нормальных исходов.
- **`ExternalIdTaken`** не пересекает границу вовсе. Проверено по коду: его
  бросает `ExternalIdsRepository.put`, а ловит и записывает в лог сам
  `Enricher._keep` (`backend/service/enrich.py:155`). У привязки же занятость
  проверяется до первой записи, и `Linker._check_identifiers`
  (`backend/service/linking.py:87`) поднимает на этом месте `ItemExists`, а не
  его. Перенести его в модель значило бы завести класс без сегодняшнего
  потребителя.

**Файлы:**
- Создать: `backend/model/denied.py`
- Изменить: `backend/model/__init__.py`,
  `backend/storage/repository/library.py:17`,
  `backend/storage/repository/tags.py:14-18`,
  `backend/storage/repository/credits.py:31`,
  `backend/service/images.py:15`
- Изменить: `backend/service/cards.py`, `backend/service/linking.py` — оба берут
  `ItemExists` из `storage/repository/library.py`. После снятия объявления это
  работало бы транзитом, но у двух сервисов осталась бы зависимость от хранилища,
  которой в коде больше нет ни по одному другому поводу.
- Создать: `tests/backend/test_denied.py`
- Изменить: `tests/backend/test_model.py` — сторож поверхности `__all__` обходит
  модель фильтром `is_dataclass`, и шесть новых имён под него не попадают.

**Семь тестовых модулей остаются на старых адресах** (`test_library`,
`test_linking`, `test_manual_cards`, `test_tags`, `test_credits`, `test_images`,
`test_poster_service`) — решение записано в `docs/deferred.md` вместе со списком
мест, потому что довод держится до первой правки старых модулей.

**Интерфейсы:**
- Потребляет: ничего.
- Отдаёт: `Denied`, `ItemExists`, `TagExists`, `WrongTagKind`, `IdentityTaken`,
  `BadImage` — всё импортируется из `backend.model`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/backend/test_denied.py`:

```python
"""Отказ операции — нормальный ход событий, и клиент обязан их различать."""

import pytest

from backend.model import (
    BadImage,
    Denied,
    IdentityTaken,
    ItemExists,
    Kind,
    TagExists,
    WrongTagKind,
)
from backend.storage.posters import NotOpened
from backend.storage.repository.external import ExternalIdTaken
from backend.storage.repository.tags import TagsRepository

FIVE = [ItemExists, TagExists, WrongTagKind, IdentityTaken, BadImage]


@pytest.mark.parametrize("denial", FIVE)
def test_every_denial_is_caught_by_the_common_ancestor(denial):
    """Мост ловит один тип, а не пять: иначе шестой отказ пришлось бы
    дописывать и в бэкенд, и в мост."""
    with pytest.raises(Denied):
        raise denial("занято")


def test_a_closed_poster_store_is_not_a_denial():
    """Хранилище не открыли — это поломка сборки, а не занятое имя тега: она
    обязана долететь до лога, а не стать вежливым отказом на странице."""
    assert not issubclass(NotOpened, Denied)


def test_a_taken_external_id_is_not_a_denial_either():
    """Он не пересекает границу вовсе: его ловит и пишет в лог сам `Enricher`, а
    у привязки на этом месте поднимается `ItemExists`. Класс в модели без
    сегодняшнего потребителя — это «на всякий случай»."""
    assert not issubclass(ExternalIdTaken, Denied)


async def test_a_repository_raises_the_ancestor(sessions, migrated):
    """Следствие, а не объявление: отказ, поднятый настоящей записью в базу,
    ловится общим предком."""
    tags = TagsRepository(sessions)
    await tags.create(Kind.MOVIE, "драма")

    with pytest.raises(Denied):
        await tags.create(Kind.MOVIE, "драма")
```

Фикстуры `sessions` и `migrated` уже есть в `tests/conftest.py`; порядок
аргументов сверить с соседними тестами репозиториев.

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/backend/test_denied.py -v`
Ожидание: FAIL, `ImportError: cannot import name 'Denied' from 'backend.model'`.

- [x] **Шаг 3: Завести модуль отказов**

Создать `backend/model/denied.py`:

```python
"""Отказ операции: занятое имя, занятая идентичность, негодная картинка.

Всё это — нормальный ход событий, а не поломка: человек переименовал тег в уже
существующий, вставил ссылку на карточку, которая в библиотеке есть, выбрал
файлом не картинку. Живут в модели, а не рядом с тем, кто их бросает, потому что
клиенту из бэкенда открыты только `backend.model` и `backend.config`, а
различать эти шесть он обязан: плашка говорит разное.

Общий предок нужен мосту: он ловит один тип и переводит его в род отказа по
имени класса. Без предка седьмой отказ пришлось бы дописывать дважды."""


class Denied(Exception):
    """Операция отклонена, и это ожидаемо."""


class ItemExists(Denied):
    """Карточка с такой парой «источник + идентификатор» уже есть."""


class TagExists(Denied):
    """Тег с таким именем у этого типа содержимого уже заведён."""


class WrongTagKind(Denied):
    """Тег заведён для другого типа содержимого."""


class IdentityTaken(Denied):
    """Человек или студия с такой идентичностью источника уже есть."""


class BadImage(Denied):
    """Залитый файл не разбирается как картинка."""
```

Докстринги шести классов берутся из тех, что стоят у нынешних объявлений, если
те точнее написанных здесь.

- [x] **Шаг 4: Перевести пять модулей на общее объявление**

В каждом файле объявление класса снимается, а имя добавляется **в существующее
перечисление** `from backend.model import (...)`, если оно там уже есть, а не
вторым `from backend.model import`.

| Файл | Снять | Дописать в импорт |
|---|---|---|
| `backend/storage/repository/library.py` | `class ItemExists` | `ItemExists` |
| `backend/storage/repository/tags.py` | `class WrongTagKind`, `class TagExists` | `TagExists`, `WrongTagKind` |
| `backend/storage/repository/credits.py` | `class IdentityTaken` | `IdentityTaken` |
| `backend/service/images.py` | `class BadImage` | `BadImage` |

`backend/storage/repository/external.py` не трогается: `ExternalIdTaken`
остаётся там, где объявлен.

- [x] **Шаг 5: Открыть имена наружу**

В `backend/model/__init__.py` — импорт и шесть имён в `__all__`, по алфавиту, как
там заведено:

```python
from backend.model.denied import (
    BadImage,
    Denied,
    IdentityTaken,
    ItemExists,
    TagExists,
    WrongTagKind,
)
```

- [x] **Шаг 6: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/backend/test_denied.py tests/backend/test_layers.py -v`
Ожидание: PASS. Сторож границы обязан остаться зелёным: `denied.py` не
импортирует ничего, и проверка «модель не зависит ни от чего нашего» это видит.

- [x] **Шаг 7: Прогнать весь набор**

Запустить: `pipenv run pytest`
Ожидание: зелено. Тесты, импортирующие отказы из старых модулей, не правятся:
имя в модуле осталось — оно там теперь импортированное.

- [ ] **Шаг 8: Коммит**

```bash
git add backend/model/denied.py backend/model/__init__.py \
        backend/storage/repository/library.py backend/storage/repository/tags.py \
        backend/storage/repository/credits.py \
        backend/service/images.py tests/backend/test_denied.py
git commit -m "refactor: пять отказов операции переезжают в модель"
```

---

### Задача 2: Поток бэкенда

Единственное место в проекте, которое знает про два потока. Владеет циклом
asyncio, поднимает в нём `Backend`, ведёт список живых задач и отменяет их все
при закрытии — флагов «мы закрываемся» по коду не разбрасываем.

**Почему сборка внедряется, а не зовётся по имени.** Движок SQLAlchemy привязан
к циклу, в котором создан, поэтому `Backend` обязан родиться внутри чужого
потока. А импортировать `backend.app` из `bridge/` нельзя — с ним приедет
`sqlalchemy`, и сторож границы слоёв покраснеет. Оба довода ведут в одно место:
`main.py` передаёт функцию, поток её зовёт.

**Отмена настоящая.** `concurrent.futures.Future.cancel()` отменяет только то,
что не началось, — этого мало. Отменяется `asyncio.Task`, и `CancelledError`
приходит внутрь бэкенда, где его умеют откатывать.

**Файлы:**
- Создать: `bridge/thread.py`
- Создать: `tests/bridge/conftest.py`, `tests/bridge/test_thread.py`

**Интерфейсы:**
- Потребляет: ничего из проекта.
- Отдаёт: `BackendThread`, `Closed`, `BUILD_TIMEOUT`, и методы `start()`,
  `run(factory, op=None) -> concurrent.futures.Future`, `cancel(ops)`,
  `close()`. `factory` — `Callable[[Any], Coroutine]`: получает собранный
  бэкенд, отдаёт корутину.

**`DEADLINE` объявляет не эта задача, а первая из тех, кто ждёт** (правило 8:
константы без сегодняшнего потребителя не пишутся). Дом от этого не меняется —
она встаёт в `bridge/thread.py`, рядом с `BUILD_TIMEOUT`, потому что ждущих
двое, мост и отдача обложек, и срок у них один по одному и тому же доводу:
шестьдесят секунд — сторож от невозвращающегося вызова, а не лимит на операцию.

- [x] **Шаг 1: Написать двойник бэкенда**

Создать `tests/bridge/conftest.py`:

```python
"""Двойники бэкенда и потоки на них.

Настоящий `Backend` здесь не собирается ни разу: у него база, миграции и шесть
клиентов сети, а проверяется тут граница потоков и мост, а не бэкенд."""

import asyncio
import time

import pytest

from bridge.thread import BackendThread


class FakeBackend:
    """Ровно те методы, которые нужны проверкам границы потоков.

    Имена подобраны под свойства, а не под поверхность настоящего бэкенда:
    `together` держит `Event`, потому что «задачи идут разом, а не очередью»
    иначе не наблюдается — при очереди набор просто зависнет."""

    def __init__(self) -> None:
        self.closed = 0
        self.started = 0
        self.finished = 0
        self.gate = asyncio.Event()

    async def echo(self, value):
        return value

    async def where(self):
        return asyncio.get_running_loop()

    async def ident(self):
        import threading
        return threading.get_ident()

    async def boom(self):
        raise RuntimeError("сломалось")

    async def slow(self, seconds=30):
        self.started += 1
        try:
            await asyncio.sleep(seconds)
        finally:
            self.finished += 1
        return "досидел"

    async def together(self, total):
        """Доходит только если все считаются разом."""
        self.started += 1
        if self.started >= total:
            self.gate.set()
        await self.gate.wait()
        return self.started

    async def aclose(self):
        self.closed += 1


async def ready(value):
    """Готовое значение корутиной: сборка бэкенда объявлена асинхронной."""
    return value


def wait_until(condition, timeout=5.0):
    """Ждать события в чужом потоке иначе нечем: своего цикла у теста нет."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.005)
    raise AssertionError("не дождались")


@pytest.fixture
def backend():
    return FakeBackend()


@pytest.fixture
def thread(backend):
    """Поток, поднятый на двойнике. Закрывается всегда — иначе повисший поток
    переживёт тест и утащит за собой соседний."""
    running = BackendThread(lambda: ready(backend))
    running.start()
    yield running
    running.close()
```

- [x] **Шаг 2: Написать падающий тест**

Создать `tests/bridge/test_thread.py`:

```python
"""Граница потоков: что обязано быть правдой у стыка двух циклов."""

import asyncio
import concurrent.futures
import threading

import pytest

from bridge.thread import BackendThread, Closed
from tests.bridge.conftest import FakeBackend, ready, wait_until


def test_work_runs_in_another_thread(thread):
    """Главное свойство: в потоке интерфейса не выполняется ничего бэкендового."""
    other = thread.run(lambda back: back.ident()).result(timeout=5)
    assert other != threading.get_ident()


def test_the_answer_comes_back(thread):
    assert thread.run(lambda back: back.echo(7)).result(timeout=5) == 7


def test_the_backend_is_built_inside_that_thread(backend):
    """Движок SQLAlchemy привязан к циклу, в котором создан, — значит и сборка
    обязана идти внутри, а не снаружи с передачей готового."""
    seen = {}

    async def build():
        seen["thread"] = threading.get_ident()
        seen["loop"] = asyncio.get_running_loop()
        return backend

    running = BackendThread(build)
    running.start()
    try:
        assert seen["thread"] != threading.get_ident()
        assert running.run(lambda back: back.where()).result(timeout=5) is seen["loop"]
    finally:
        running.close()


def test_a_broken_build_reaches_the_caller():
    """Не собрался бэкенд — об этом узнают снаружи, а не по тишине в окне."""
    async def build():
        raise RuntimeError("нет ключа")

    running = BackendThread(build)
    with pytest.raises(RuntimeError, match="нет ключа"):
        running.start()


def test_a_broken_task_does_not_kill_the_thread(thread):
    with pytest.raises(RuntimeError, match="сломалось"):
        thread.run(lambda back: back.boom()).result(timeout=5)

    assert thread.run(lambda back: back.echo("живой")).result(timeout=5) == "живой"


def test_a_cancelled_task_is_really_stopped(thread, backend):
    """Отменяется задача, а не заявка: `CancelledError` обязан прийти внутрь
    бэкенда, иначе откатывать сорванную запись будет нечему."""
    future = thread.run(lambda back: back.slow(), op=1)
    wait_until(lambda: backend.started == 1)

    thread.cancel([1])

    with pytest.raises(concurrent.futures.CancelledError):
        future.result(timeout=5)
    wait_until(lambda: backend.finished == 1)


def test_cancelling_takes_a_list(thread, backend):
    """Страница уходит целиком, и её задачи гасятся одним пересечением границы,
    а не восемнадцатью."""
    futures = [thread.run(lambda back: back.slow(), op=number)
               for number in (1, 2, 3)]
    wait_until(lambda: backend.started == 3)

    thread.cancel([1, 2, 3])

    for future in futures:
        with pytest.raises(concurrent.futures.CancelledError):
            future.result(timeout=5)


def test_cancelling_an_unknown_number_is_quiet(thread):
    """Ответ пришёл раньше, чем страница успела отменить, — это обычное дело."""
    thread.cancel([404])


def test_tasks_run_together_not_in_a_queue(thread):
    """Пять доходят, только если считаются разом: при очереди набор зависнет на
    первой, которая ждёт остальных."""
    futures = [thread.run(lambda back: back.together(5)) for _ in range(5)]
    for future in futures:
        assert future.result(timeout=5) == 5


def test_closing_stops_what_is_still_running(thread, backend):
    thread.run(lambda back: back.slow(), op=1)
    wait_until(lambda: backend.started == 1)

    thread.close()

    wait_until(lambda: backend.finished == 1)
    assert backend.closed == 1


def test_closing_twice_is_quiet(thread):
    thread.close()
    thread.close()


def test_a_call_after_closing_is_refused_not_hung(thread):
    """Окно закрыли, а поздний обработчик страницы всё ещё что-то просит."""
    thread.close()
    with pytest.raises(Closed):
        thread.run(lambda back: back.echo(1))


def test_the_thread_survives_a_backend_that_will_not_close():
    """Закрытие обязано доходить до конца даже так: иначе окно не закроется."""
    class Stubborn(FakeBackend):
        async def aclose(self):
            raise RuntimeError("не закрылся")

    running = BackendThread(lambda: ready(Stubborn()))
    running.start()
    running.close()
```

- [x] **Шаг 3: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_thread.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.thread'`.

- [x] **Шаг 4: Написать поток**

Создать `bridge/thread.py`:

```python
"""Поток бэкенда: свой цикл asyncio, список живых задач, отмена всех разом."""

import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Сколько ждать сборки и закрытия. Сборка поднимает движок, открывает второй файл
# базы и заводит шесть клиентов сети — всё это диск и память, без единого запроса.
BUILD_TIMEOUT = 30.0

# Сколько ждать ответа. Сторож от невозвращающегося вызова, а не лимит на
# операцию: общего лимита у нас нет по решению. Самый долгий законный путь —
# карточка по ссылке в GOG, два запроса подряд по 20 секунд. Шестьдесят — выше
# любого законного с запасом и несравнимо ниже «навсегда».
#
# Объявлен здесь, а не у ждущего: ждут двое — мост и отдача обложек, — и срок у
# них один и тот же по одному и тому же доводу.
DEADLINE = 60.0


class Closed(Exception):
    """Поток закрыт, а его всё ещё о чём-то просят."""


class BackendThread:
    """Сборка внедряется, а не зовётся по имени, по двум причинам сразу:
    движок SQLAlchemy привязан к циклу, в котором создан, — значит бэкенд обязан
    родиться здесь, внутри; а импортировать `backend.app` из `bridge/` нельзя,
    с ним приедет `sqlalchemy` и покраснеет сторож границы слоёв."""

    def __init__(self, build: Callable[[], Coroutine[Any, Any, Any]]) -> None:
        self._build = build
        self._loop: asyncio.AbstractEventLoop | None = None
        self._backend: Any = None
        self._tasks: set[asyncio.Task] = set()
        self._numbered: dict[int, asyncio.Task] = {}
        self._ready: concurrent.futures.Future = concurrent.futures.Future()
        self._thread = threading.Thread(target=self._live, name="backend",
                                        daemon=True)
        self._closed = False

    def start(self) -> None:
        """Ждём сборки здесь: не собрался бэкенд — окно поднимать незачем, и
        узнать об этом надо тем же исключением, а не тишиной."""
        self._thread.start()
        self._ready.result(timeout=BUILD_TIMEOUT)

    def run(self, factory: Callable[[Any], Coroutine],
            op: int | None = None) -> concurrent.futures.Future:
        """Заявка на работу. `factory` получает собранный бэкенд и отдаёт
        корутину — так мост не хранит ссылку на бэкенд у себя."""
        if self._closed:
            raise Closed("поток бэкенда закрыт")

        answer: concurrent.futures.Future = concurrent.futures.Future()
        self._loop.call_soon_threadsafe(self._begin, factory, op, answer)
        return answer

    def cancel(self, ops) -> None:
        """Неизвестный номер — обычное дело: ответ мог прийти раньше отмены."""
        for op in ops:
            task = self._numbered.get(op)
            if task is not None:
                self._loop.call_soon_threadsafe(task.cancel)

    def close(self) -> None:
        """Закрыть могут дважды — окно при закрытии и фикстура теста."""
        if self._closed:
            return
        self._closed = True
        done: concurrent.futures.Future = concurrent.futures.Future()
        self._loop.call_soon_threadsafe(self._finish, done)
        done.result(timeout=BUILD_TIMEOUT)
        self._thread.join(timeout=BUILD_TIMEOUT)

    def _live(self) -> None:
        """Тело потока: цикл живёт ровно столько, сколько живёт бэкенд."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            self._backend = loop.run_until_complete(self._build())
        except Exception as error:
            # Сбой сборки — единственное, что уезжает вызывающему исключением:
            # без бэкенда окно поднимать незачем.
            logger.exception("бэкенд не собрался")
            self._ready.set_exception(error)
            loop.close()
            return
        self._ready.set_result(None)
        loop.run_forever()
        loop.close()

    def _begin(self, factory, op, answer) -> None:
        """Уже в своём потоке: здесь можно заводить задачу."""
        task = self._loop.create_task(factory(self._backend))
        self._tasks.add(task)
        if op is not None:
            self._numbered[op] = task
        task.add_done_callback(lambda ended: self._end(ended, op, answer))

    def _end(self, task, op, answer) -> None:
        self._tasks.discard(task)
        self._numbered.pop(op, None)
        if task.cancelled():
            answer.cancel()
            answer.set_running_or_notify_cancel()
            return
        error = task.exception()
        if error is not None:
            answer.set_exception(error)
            return
        answer.set_result(task.result())

    def _finish(self, done) -> None:
        """Отмена всех разом, потом закрытие бэкенда, потом остановка цикла:
        порядок обратный сборке — сначала гасим то, что ещё ходит в сеть."""
        for task in list(self._tasks):
            task.cancel()
        self._loop.create_task(self._shutdown(done))

    async def _shutdown(self, done) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        try:
            await self._backend.aclose()
        except Exception:
            # Не закрылся начисто — окно всё равно обязано закрыться.
            logger.exception("бэкенд не закрылся начисто")
        finally:
            done.set_result(None)
            self._loop.stop()
```

- [x] **Шаг 5: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/test_thread.py -v`
Ожидание: PASS, 13 тестов.

- [x] **Шаг 6: Завести половину сторожа про мост**

У `tests/backend/test_layers.py` сейчас две проверки вместо четырёх: половины
про сторону интерфейса там нет вовсе, потому что до этого шага не было и
предмета — ни одного `.py` вне `backend/`. Заводить её впрок было нечем:
`python_files` утверждает, что пустой пакет это поломка проверки, а не чистый
код, и оставленный впрок сторож падал бы каждым прогоном. Теперь предмет есть.

Дописать в `tests/backend/test_layers.py`:

```python
BANNED_IN_BRIDGE = {"sqlalchemy", "aiosqlite", "httpx", "alembic", "PIL"}

# Из бэкенда мосту открыты только типы границы и настройки. Всё прочее —
# репозитории, сервисы, клиенты источников — тянет за собой и сессию
# SQLAlchemy, и поход к диску в потоке интерфейса, то есть ровно то, от чего
# граница слоёв и заведена. Список корневых имён этого не ловит: они
# `backend.*`, а не `sqlalchemy`.
ALLOWED_FROM_BACKEND = {"backend.model", "backend.config"}


def test_the_bridge_does_not_import_storage_libraries():
    assert offenders("bridge", BANNED_IN_BRIDGE) == []


def test_the_bridge_takes_only_the_boundary_types_from_the_backend():
    """Мост, импортирующий репозиторий, лежит не там.

    Проверка по корневым именам это пропускает: `backend.storage.repository` —
    такой же `backend`, как и `backend.model`, а тянет за собой сессию
    SQLAlchemy и синхронный поход к базе мимо потока бэкенда."""
    found = []
    for path in python_files("bridge"):
        for module in imported_modules(path):
            if not module.startswith("backend"):
                continue
            if any(module == name or module.startswith(name + ".")
                   for name in ALLOWED_FROM_BACKEND):
                continue
            found.append(f"{path.relative_to(ROOT)} → {module}")

    assert found == []
```

Докстринг модуля переписать: абзац «второй половины тут нет вовсе, и это не
дыра, а состояние проекта» перестал быть правдой ровно на этом шаге.

**`client/` этим сторожем не проверяется и не будет.** Там нет питона, а границу
его слоёв держит хук на записи файла: `<style>` в компоненте, стиль вне
`styles/`, импорт вверх по слоям, цвет мимо палитры.

Запустить: `pipenv run pytest tests/backend/test_layers.py -v`
Ожидание: PASS, четыре проверки вместо двух.

- [x] **Шаг 7: Коммит**

```bash
git add bridge/thread.py tests/bridge/conftest.py tests/bridge/test_thread.py \
        tests/backend/test_layers.py
git commit -m "feat: поток бэкенда со своим циклом и настоящей отменой"
```

---

### Задача 3: Значения границы в JSON

pywebview сериализует ответ сам, штатным `json.dumps`, без `default=`. Значит
мост обязан вернуть уже пролезающее: словари, списки, числа, строки, `None`.

Что не пролезает — измерено, а не предположено: пять полей модели
(`Item.synced_at`, `Item.released_at`, `ExternalRating.fetched_at`,
`CardView.synced_at`, `Refusal.retry_after`), все 23 датакласса как есть (у всех
`slots=True`, `vars()` не работает), байты и `NaN`.

**Метку типа приклеивает мост.** `Missing` — датакласс без единого поля, после
разбора это `{}`, неотличимое от чего угодно пустого. Поэтому у объединений
`int | Missing | Refusal` форма ответа одна и та же и всегда с меткой.

**Файлы:**
- Создать: `bridge/wire.py`
- Создать: `tests/bridge/test_wire.py`

**Пустой `bridge/__init__.py` не заводится.** Проект живёт на неявных пакетах
(PEP 420): его нет ни у `backend`, ни у `tests`, а корень в пути импорта ставит
`pythonpath = .` из `pytest.ini`. Файл, не делающий ничего, — это правило 8.

**Интерфейсы:**
- Потребляет: ничего из проекта.
- Отдаёт: `to_wire(value) -> Any`.

**`outcome(value)` объявляет не эта задача, а первая, чей домен возвращает исход
источника** — тот же довод, что у `DEADLINE`: у функции нет сегодняшнего
потребителя, а это правило 8. Дом ей всё равно `bridge/wire.py`, и решение,
ради которого она нужна, записано здесь, чтобы не выводить его заново:

> `Missing` — датакласс без единого поля, и после разбора это `{}`, неотличимое
> от чего угодно пустого. Различать исходы по набору ключей нельзя, поэтому у
> объединений `int | Missing | Refusal` форма ответа одна и всегда с меткой:
> `{"outcome": "missing"}`, `{"outcome": "refusal", "refusal": ...}`,
> `{"outcome": "found", "value": ...}`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/bridge/test_wire.py`:

```python
"""Перевод значений границы в то, что переживёт `json.dumps` без своего
кодировщика: его у pywebview нет."""

import json
from datetime import date, datetime, timedelta

import pytest

from backend.model import (
    CardView,
    ExternalRating,
    Genre,
    GenreKind,
    Kind,
    Missing,
    Rating,
    RatingSource,
    Reason,
    Refusal,
    Source,
    Tag,
)
from bridge.wire import outcome, to_wire


def test_a_moment_travels_as_iso_with_a_t():
    """Именно ISO, а не `str(datetime)`: тот даёт пробел вместо «T», и разбор
    на стороне страницы молча получает `Invalid Date`."""
    assert to_wire(datetime(2026, 7, 31, 14, 5, 6)) == "2026-07-31T14:05:06"


def test_a_date_travels_as_iso():
    assert to_wire(date(2014, 11, 5)) == "2014-11-05"


def test_a_delay_travels_as_seconds():
    """`Refusal.retry_after` приезжает при каждом отказе источника."""
    assert to_wire(timedelta(minutes=2, seconds=30)) == 150.0


def test_a_dataclass_travels_as_a_dictionary():
    assert to_wire(Tag(id=3, name="пересмотреть")) == {"id": 3,
                                                       "name": "пересмотреть"}


def test_an_enum_travels_as_a_plain_string():
    assert to_wire(Kind.SERIES) == "series"
    assert type(to_wire(Kind.SERIES)) is str


def test_a_tuple_travels_as_an_array():
    genres = (Genre(id=1, name="Драма", kind=GenreKind.FILM),)
    assert to_wire(genres) == [{"id": 1, "name": "Драма", "kind": "film"}]


def test_the_whole_card_survives_json():
    """Основной тип ленты и самый глубокий: три уровня, шесть кортежей
    датаклассов, `datetime` внутри вложенного."""
    view = CardView(
        kind=Kind.MOVIE,
        source=Source.TMDB,
        source_id="157336",
        title="Интерстеллар",
        item_id=4,
        synced_at=datetime(2026, 7, 31, 12, 0),
        genres=(Genre(id=1, name="Драма", kind=GenreKind.FILM),),
        tags=(Tag(id=2, name="пересмотреть"),),
        external=(ExternalRating(source=RatingSource.IMDB, value=8.7,
                                 fetched_at=datetime(2026, 7, 30, 9, 0)),),
        rating=Rating(item_id=4, score=9.0),
    )

    back = json.loads(json.dumps(to_wire(view), allow_nan=False))

    assert back["title"] == "Интерстеллар"
    assert back["synced_at"] == "2026-07-31T12:00:00"
    assert back["external"][0]["fetched_at"] == "2026-07-30T09:00:00"
    assert back["rating"]["score"] == 9.0
    assert back["genres"][0]["kind"] == "film"


def test_not_a_number_becomes_nothing():
    """`json.dumps` печатает `NaN`, а `JSON.parse` его не принимает — упало бы
    разбором всего ответа, а не одного поля."""
    assert to_wire(float("nan")) is None
    assert to_wire(float("inf")) is None


def test_bytes_are_refused():
    """Байты через мост не ходят вовсе: результат вклеивается в текст скрипта.
    Обложка едет своей ручкой, и молчаливого запасного пути у неё нет."""
    with pytest.raises(TypeError, match="байты"):
        to_wire(b"\x89PNG")


def test_an_unknown_type_is_refused():
    """Отказ громкий, а не `default=str`: подставленная строка вместо объекта
    доедет до страницы и сломается там, где искать её будет некому."""
    with pytest.raises(TypeError):
        to_wire(object())


def test_missing_is_told_apart_from_anything_empty():
    """После разбора `Missing` — это `{}`. Метку приклеивает мост."""
    assert outcome(Missing()) == {"outcome": "missing"}


def test_a_refusal_carries_its_reason():
    refusal = Refusal(source="tmdb", reason=Reason.QUOTA,
                      retry_after=timedelta(seconds=60), detail="квота")
    assert outcome(refusal) == {
        "outcome": "refusal",
        "refusal": {"source": "tmdb", "reason": "quota",
                    "retry_after": 60.0, "detail": "квота"},
    }


def test_a_value_is_wrapped_the_same_way():
    """Форма ответа одна на все три исхода: ветка на стороне страницы одна."""
    assert outcome(7) == {"outcome": "found", "value": 7}
```

Обязательных полей у `CardView` четыре — `kind`, `source`, `source_id`,
`title`; остальные тринадцать со значениями по умолчанию (сверено по
`backend/model/view.py:23-48`).

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_wire.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.wire'`.

- [x] **Шаг 3: Написать перевод**

Создать пустой `bridge/__init__.py` и `bridge/wire.py`:

```python
"""Значения границы в то, что переживёт `json.dumps`.

Своего кодировщика у pywebview нет: результат уходит в `json.dumps` без
`default=`, поэтому перевести всё надо до возврата."""

import dataclasses
import math
from datetime import date, datetime, timedelta
from enum import Enum

from backend.model import Missing, Refusal


def to_wire(value):
    """Отказ громкий, а не `default=str`: неизвестный тип, подставленный
    строкой, доедет до страницы и сломается там, где искать его будет некому."""
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        # `json.dumps` печатает `NaN` и `Infinity`, а `JSON.parse` их не берёт:
        # упало бы разбором всего ответа, а не одного поля.
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, bytes | bytearray):
        raise TypeError("байты через мост не ходят: обложка едет ручкой")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_wire(getattr(value, field.name))
                for field in dataclasses.fields(value)}
    if isinstance(value, list | tuple | set | frozenset):
        return [to_wire(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_wire(item) for key, item in value.items()}
    raise TypeError(f"через мост не проходит: {type(value).__name__}")


def outcome(value) -> dict:
    """Одна форма на три исхода запроса к источнику.

    `Missing` — датакласс без единого поля, и после разбора это `{}`,
    неотличимое от чего угодно пустого. Различать по набору ключей нельзя,
    поэтому метку приклеиваем здесь."""
    if isinstance(value, Missing):
        return {"outcome": "missing"}
    if isinstance(value, Refusal):
        return {"outcome": "refusal", "refusal": to_wire(value)}
    return {"outcome": "found", "value": to_wire(value)}
```

Проверить порядок ветвей: `bool` разбирается раньше `int` (в Python `bool` —
подкласс `int`, и обе ветви ведут в одно), `Enum` — раньше `str`, иначе `StrEnum`
уедет подклассом строки и `type(...) is str` покраснеет.

- [x] **Шаг 4: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/test_wire.py -v`
Ожидание: PASS, 13 тестов.

- [x] **Шаг 5: Коммит**

```bash
git add bridge/__init__.py bridge/wire.py tests/bridge/test_wire.py
git commit -m "feat: значения границы в JSON, с меткой у исхода"
```

---

### Задача 4: Один формат ответа

Оболочка, через которую проходит каждый вызов моста. Делает четыре вещи: ставит
работу в поток бэкенда, ждёт её со сроком, переводит шесть отказов операции в род
отказа и не выпускает наружу ни одного исключения.

**Про срок.** Общего лимита на операцию у нас нет — это решение принято и
записано: «подождём восемь секунд и покажем что успело» выбрасывает ответ,
приехавший на девятой. Здесь другое: у pywebview нет вообще никакого срока, и
зависший вызов оставляет запись в таблице обратных вызовов навсегда, а промис в
JS висит вечно. Это сторож от невозвращающегося вызова, и порог считается от
бэкендовых чисел, а не от терпения человека.

Самый долгий законный путь — карточка по ссылке в GOG: два запроса подряд по
20 секунд, то есть 40. Берём 60: выше любого законного пути с запасом и
несравнимо ниже «навсегда».

**`DEADLINE` объявляет эта задача — она первая, кто ждёт.** Дом ему всё равно
`bridge/thread.py`, рядом с `BUILD_TIMEOUT`: ждущих двое — мост и отдача
обложек, — и срок у них один по одному и тому же доводу. Задача 2 его не
заводила: константа без сегодняшнего потребителя — это правило 8.

```python
# Сколько ждать ответа. Сторож от невозвращающегося вызова, а не лимит на
# операцию: общего лимита у нас нет по решению. Самый долгий законный путь —
# карточка по ссылке в GOG, два запроса подряд по 20 секунд. Шестьдесят — выше
# любого законного с запасом и несравнимо ниже «навсегда».
DEADLINE = 60.0
```

**Файлы:**
- Создать: `bridge/answer.py`
- Изменить: `bridge/thread.py` — объявить `DEADLINE`
- Создать: `tests/bridge/test_answer.py`

**Интерфейсы:**
- Потребляет: `Denied` из `backend.model`, `to_wire` из `bridge.wire`,
  `Closed` и `DEADLINE` из `bridge.thread`.
- Отдаёт: `Domain` с `__init__(thread)` и `_reply(factory, op=None) -> dict`,
  `kebab(name) -> str`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/bridge/test_answer.py`:

```python
"""Один формат ответа на все операции: `{"ok": ...}` либо `{"fail": ...}`."""

import logging
import threading

from backend.model import TagExists
from bridge.answer import Domain, kebab
from tests.bridge.conftest import wait_until


class Probe(Domain):
    """Домен из одного метода: проверяется оболочка, а не чей-то предмет."""

    def ask(self, what, op=None):
        return self._reply(lambda back: getattr(back, what)(), op=op)


def test_a_result_comes_wrapped(thread):
    assert Probe(thread).ask("ident")["ok"] > 0


def test_a_denial_becomes_a_kind_of_failure(thread, backend):
    """Ловим одного предка, а род берём по имени класса: седьмой отказ иначе
    пришлось бы дописывать и в бэкенд, и сюда."""
    async def taken():
        raise TagExists("драма")

    backend.taken = taken
    assert Probe(thread).ask("taken") == {"fail": "tag-exists",
                                          "detail": "драма"}


def test_the_unexpected_becomes_broken_and_is_logged(thread, caplog):
    """Молча не глотаем: непредвиденное даёт и плашку, и запись с трассировкой."""
    with caplog.at_level(logging.ERROR):
        answer = Probe(thread).ask("boom")

    assert answer["fail"] == "broken"
    assert any(record.exc_info for record in caplog.records)


def test_a_cancelled_operation_answers_quietly(thread, backend):
    """Отменённая молчит: плашки за уход со страницы не бывает."""
    answer = {}
    caller = threading.Thread(
        target=lambda: answer.update(value=Probe(thread).ask("slow", op=1)))
    caller.start()
    wait_until(lambda: backend.started == 1)

    thread.cancel([1])
    caller.join(timeout=5)

    assert answer["value"] == {"fail": "cancelled"}


def test_a_hung_call_is_cut_off(thread, backend, monkeypatch):
    """У pywebview срока нет вовсе: зависший вызов оставил бы вечный промис."""
    monkeypatch.setattr("bridge.answer.DEADLINE", 0.05)

    assert Probe(thread).ask("slow", op=2) == {"fail": "timeout"}
    # Срок не только отвечает, но и гасит работу: иначе она досидит все тридцать
    # секунд, тратя квоту источника на ответ, которого никто не ждёт.
    wait_until(lambda: backend.finished == 1)


def test_a_closed_thread_answers_instead_of_raising(thread):
    """Окно закрыли, а поздний обработчик страницы всё ещё что-то просит."""
    thread.close()
    assert Probe(thread).ask("ident") == {"fail": "closed"}


def test_the_kind_of_failure_is_kebab():
    assert kebab("TagExists") == "tag-exists"
    assert kebab("ExternalIdTaken") == "external-id-taken"
    assert kebab("BadImage") == "bad-image"
```

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_answer.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.answer'`.

- [x] **Шаг 3: Написать оболочку**

Создать `bridge/answer.py`:

```python
"""Оболочка вызова моста: срок, отказ, один формат ответа.

Наружу уходит либо `{"ok": <значение>}`, либо `{"fail": <род>, "detail": ...}`.
Третьего вида нет, и исключений наружу не летит: у границы потоков второго
канала доставки не бывает."""

import concurrent.futures
import logging
import re

from backend.model import Denied
from bridge.thread import DEADLINE, Closed
from bridge.wire import to_wire

logger = logging.getLogger(__name__)

_EDGE = re.compile(r"(?<!^)(?=[A-Z])")


def kebab(name: str) -> str:
    """`TagExists` → `tag-exists`. Род отказа берётся из имени класса, а не из
    таблицы: таблица разошлась бы с моделью молча."""
    return _EDGE.sub("-", name).lower()


class Domain:
    """Общее у семи доменов моста.

    Имена с подчёркиванием pywebview на страницу не выносит — поверхностью
    становятся только методы наследников."""

    def __init__(self, thread) -> None:
        self._thread = thread

    def _reply(self, factory, op: int | None = None) -> dict:
        try:
            answer = self._thread.run(factory, op=op)
            return {"ok": to_wire(answer.result(timeout=DEADLINE))}
        except Closed:
            return {"fail": "closed"}
        except concurrent.futures.CancelledError:
            return {"fail": "cancelled"}
        except concurrent.futures.TimeoutError:
            # Срок не только отвечает, но и гасит работу: иначе она досидит своё,
            # тратя квоту источника на ответ, которого уже никто не ждёт.
            self._thread.cancel([op])
            logger.error("операция не уложилась в %s с", DEADLINE)
            return {"fail": "timeout"}
        except Denied as denial:
            return {"fail": kebab(type(denial).__name__), "detail": str(denial)}
        except Exception as error:
            logger.exception("непредвиденный сбой операции")
            return {"fail": "broken", "detail": str(error)}
```

- [x] **Шаг 4: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/test_answer.py -v`
Ожидание: PASS, 7 тестов.

- [x] **Шаг 5: Коммит**

```bash
git add bridge/answer.py tests/bridge/test_answer.py
git commit -m "feat: один формат ответа моста, со сроком и родом отказа"
```

---

### Задача 5: Домены хранилища — карточка и мои отметки

Две небольшие половины одного слайса. Оба домена тонкие: метод моста переводит
аргументы, зовёт бэкенд, возвращает ответ. Своей логики в них нет — порядок
нескольких записей принадлежит странице, и это записанное решение проекта.

**Почему `library` не отдаёт карточку.** `library.get` возвращает `Item`, а
показывать надо `CardView` — с оценкой, тегами и закладкой. Точечное чтение одной
карточки живёт в `feed.views_of`, и второго адреса ему не нужно.

**Файлы:**
- Создать: `bridge/library.py`, `bridge/marks.py`
- Изменить: `tests/bridge/conftest.py` (записывающий двойник)
- Создать: `tests/bridge/test_bridge_library.py`,
  `tests/bridge/test_bridge_marks.py`

**Интерфейсы:**
- Потребляет: `Domain` из `bridge.answer`; `Kind`, `new_manual_item` из
  `backend.model`.
- Отдаёт: `Library` с `create(fields)`, `replace(item_id, fields)`,
  `same_title(kind, title)`, `unlink(item_id)`, `deletion_summary(item_id)`,
  `delete(item_id)`; `Marks` с `score`, `aspects`, `review`, `clear_rating`,
  `create_tag`, `tags`, `reorder_tags`, `rename_tag`, `tag_usage`, `delete_tag`, `assign`,
  `unassign`, `wish`, `unwish`.

- [x] **Шаг 1: Написать записывающий двойник**

Дописать в `tests/bridge/conftest.py`:

```python
class Asked:
    """Записывающий фасад: имя собирается из точек, ответ берётся из словаря.

    Тест не пишет ни одного класса-двойника — весь бэкенд описывается словарём
    `{"tags.create": 7}`, а проверяется потом `log`: и имя, и аргументы, и
    порядок.

    Слабое место у приёма одно: принимается **любое** имя, и опечатка в имени
    метода бэкенда прошла бы молча. Закрывает его отдельная проверка поверхности
    моста — `tests/bridge/test_bridge_surface.py`."""

    def __init__(self, answers: dict, log: list, path: tuple = ()) -> None:
        self._answers = answers
        self._log = log
        self._path = path

    def __getattr__(self, name):
        return Asked(self._answers, self._log, (*self._path, name))

    def __call__(self, *args, **kwargs):
        name = ".".join(self._path)
        self._log.append((name, args, kwargs))
        answer = self._answers.get(name)
        return _raising(answer) if isinstance(answer, Exception) else ready(answer)

    async def aclose(self):
        pass


async def _raising(error):
    raise error


@pytest.fixture
def asked():
    """Пара «чем отвечать» и «о чём спросили»."""
    return {}, []


@pytest.fixture
def spy(asked):
    """Поток на записывающем двойнике. Настоящего бэкенда тут нет."""
    answers, log = asked
    running = BackendThread(lambda: ready(Asked(answers, log)))
    running.start()
    yield running
    running.close()
```

`Asked.aclose` объявлен обычным методом, а не собирается через `__getattr__`:
иначе закрытие потока записалось бы в `log` и сбило проверки порядка.

- [x] **Шаг 2: Написать падающие тесты**

Создать `tests/bridge/test_bridge_library.py`:

```python
"""Мост: карточка целиком — заведение, правка, отвязка, удаление."""

from backend.model import Kind, Source
from bridge.library import Library


def test_a_manual_card_is_built_by_the_bridge(spy, asked):
    """Страница присылает поля формы, а не `Item`: собрать датакласс обратно из
    JSON нечем, а `new_manual_item` уже умеет и источник, и свой идентификатор,
    и момент создания."""
    answers, log = asked
    answers["library.create"] = 12

    assert Library(spy).create({"kind": "movie", "title": "Одиссея",
                                "year": 1997}) == {"ok": 12}

    name, args, _ = log[0]
    assert name == "library.create"
    item = args[0]
    assert item.source is Source.MANUAL
    assert item.source_id
    assert item.kind is Kind.MOVIE
    assert item.title == "Одиссея"
    assert item.year == 1997


def test_an_empty_field_does_not_reach_the_backend(spy, asked):
    """Незаполненное в форме — это «не знаю», а не «пусто»: обязательно только
    название."""
    answers, log = asked
    answers["library.create"] = 12

    Library(spy).create({"kind": "movie", "title": "Одиссея", "year": None})

    _, args, _ = log[0]
    assert args[0].year is None


def test_a_release_date_arrives_as_a_date(spy, asked):
    """Через JSON дата едет строкой, а `Item.released_at` — это `date`."""
    answers, log = asked
    answers["library.create"] = 12

    Library(spy).create({"kind": "movie", "title": "Одиссея",
                         "released_at": "1997-05-18"})

    _, args, _ = log[0]
    assert args[0].released_at.year == 1997


def test_the_same_title_check_stays_inside_one_kind(spy, asked):
    """Фильм «Ведьмак» и игра «Ведьмак» — не дубли."""
    answers, log = asked
    answers["library.find_by_title"] = []

    Library(spy).same_title("movie", "Одиссея")

    name, args, _ = log[0]
    assert name == "library.find_by_title"
    assert args[0] is Kind.MOVIE


def test_deletion_goes_through_the_backend_method(spy, asked):
    """`library.delete` обходит порядок двух файлов базы: обложка обязана
    уходить первой, иначе `id` SQLite выдаст повторно и следующая карточка
    получит чужую обложку."""
    answers, log = asked
    answers["delete_card"] = None

    assert Library(spy).delete(12) == {"ok": None}
    assert [name for name, _, _ in log] == ["delete_card"]


def test_the_summary_travels_as_a_flat_dictionary(spy, asked):
    answers, log = asked
    answers["library.deletion_summary"] = {"tags": 2, "rating": True}

    assert Library(spy).deletion_summary(12) == {"ok": {"tags": 2,
                                                        "rating": True}}
```

Создать `tests/bridge/test_bridge_marks.py`:

```python
"""Мост: свои отметки — оценки, теги, закладки."""

from datetime import datetime

from backend.model import Kind, TagExists
from bridge.marks import Marks


"""Момент везде зажат между двумя замерами вокруг вызова, а не проверен на
`year >= 2026`: тот прошёл бы и для литерала `datetime(2026, 1, 1)`, то есть не
отличил бы взятое время от захардкоженного."""


def test_setting_a_score_carries_the_moment(spy, asked):
    """Часы внутри бэкенда не берутся — это его правило. Страница о них не
    знает, момент подставляет мост."""
    answers, log = asked
    answers["ratings.set_score"] = None

    before = datetime.now()
    Marks(spy).score(12, 9.0)
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "ratings.set_score"
    assert args[:2] == (12, 9.0)
    assert before <= args[2] <= after


def test_aspects_go_to_their_own_scales(spy, asked):
    """Три шкалы у игры разные, и перепутанные местами дают другую карточку —
    а сумма и среднее у них те же. Набор доводов этого не различает, привязка
    различает."""
    answers, log = asked
    answers["ratings.set_aspects"] = 7.0

    before = datetime.now()
    Marks(spy).aspects(12, visual=9, narrative=8, gameplay=4)
    after = datetime.now()

    name, args, kwargs = log[0]
    assert name == "ratings.set_aspects"
    given = args[1:4] if len(args) > 3 else (kwargs["visual"],
                                             kwargs["narrative"],
                                             kwargs["gameplay"])
    assert given == (9, 8, 4)
    assert before <= args[4] <= after


def test_aspects_answer_with_the_derived_score(spy, asked):
    """У игр оценка — среднее трёх шкал, и считает его база: карточке надо
    показать новое число сразу, не перечитывая её целиком."""
    answers, _ = asked
    answers["ratings.set_aspects"] = 7.333333333333333

    assert Marks(spy).aspects(12, 8, 7, 7) == {"ok": 7.333333333333333}


def test_clearing_a_rating_keeps_the_card(spy, asked):
    answers, log = asked
    answers["ratings.clear"] = None

    Marks(spy).clear_rating(12)

    assert [name for name, _, _ in log] == ["ratings.clear"]


def test_a_review_goes_to_the_right_card_with_a_moment(spy, asked):
    answers, log = asked
    answers["ratings.set_review"] = None

    before = datetime.now()
    Marks(spy).review(12, "пересмотрел, всё ещё держит")
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "ratings.set_review"
    assert args[:2] == (12, "пересмотрел, всё ещё держит")
    assert before <= args[2] <= after


def test_tags_come_for_the_asked_kind(spy, asked):
    """Наборы тегов у трёх типов независимы."""
    answers, log = asked
    answers["tags.list_for_kind"] = []

    Marks(spy).tags("game")

    _, args, _ = log[0]
    assert args[0] is Kind.GAME


def test_reordering_survives_as_the_page_sent_it(spy, asked):
    """Ручной порядок обязан пережить перезапуск — за это отвечает `position`, а
    мост обязан не переставить список по дороге."""
    answers, log = asked
    answers["tags.reorder"] = None

    Marks(spy).reorder_tags("movie", [5, 2, 9])

    _, args, _ = log[0]
    assert args[1] == [5, 2, 9]


def test_a_new_tag_belongs_to_one_kind(spy, asked):
    """Наборы тегов у трёх типов независимы, и заведённый не тому типу тег
    оказался бы невидим там, где его завели."""
    answers, log = asked
    answers["tags.create"] = 7

    assert Marks(spy).create_tag("series", "пересмотреть") == {"ok": 7}

    name, args, _ = log[0]
    assert name == "tags.create"
    assert args == (Kind.SERIES, "пересмотреть")


def test_a_taken_tag_name_is_a_kind_of_failure(spy, asked):
    """Переименовал в занятое — нормальный ход событий, а не сбой."""
    answers, _ = asked
    answers["tags.rename"] = TagExists("драма")

    assert Marks(spy).rename_tag(3, "драма")["fail"] == "tag-exists"


def test_deleting_a_tag_names_the_tag_not_the_card(spy, asked):
    """У удаления тега и снятия тега с карточки доводы разного рода, и
    перепутать их — значит стереть тег у всей библиотеки вместо одной строки."""
    answers, log = asked
    answers["tags.delete"] = None

    Marks(spy).delete_tag(3)

    name, args, _ = log[0]
    assert name == "tags.delete"
    assert args == (3,)


def test_assigning_names_the_card_first_then_the_tag(spy, asked):
    """Оба довода — числа, и переставленные местами они молча пройдут до базы.
    Порядок и есть то, что тут сторожится."""
    answers, log = asked
    answers["tags.assign"] = None

    Marks(spy).assign(12, 3)

    name, args, _ = log[0]
    assert name == "tags.assign"
    assert args == (12, 3)


def test_unassigning_goes_the_same_way_round(spy, asked):
    answers, log = asked
    answers["tags.unassign"] = None

    Marks(spy).unassign(12, 3)

    name, args, _ = log[0]
    assert name == "tags.unassign"
    assert args == (12, 3)


def test_wishing_carries_the_moment(spy, asked):
    """Порядок по умолчанию в «Хочу посмотреть» — по дате добавления, и берётся
    она отсюда."""
    answers, log = asked
    answers["wishlist.add"] = None

    before = datetime.now()
    Marks(spy).wish(12)
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "wishlist.add"
    assert args[0] == 12
    assert before <= args[1] <= after


def test_unwishing_needs_no_moment(spy, asked):
    """Снятие закладки момента не требует: строка уходит целиком."""
    answers, log = asked
    answers["wishlist.remove"] = None

    Marks(spy).unwish(12)

    assert log[0] == ("wishlist.remove", (12,), {})
```

- [x] **Шаг 3: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_library.py tests/bridge/test_bridge_marks.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.library'`.

- [x] **Шаг 4: Написать оба домена**

Создать `bridge/library.py`:

```python
"""Мост: карточка целиком — заведение, правка, отвязка, удаление."""

from datetime import date

from backend.model import Kind, new_manual_item
from bridge.answer import Domain


class Library(Domain):
    """Карточку наружу не отдаёт: показывать надо `CardView` с оценкой, тегами
    и закладкой, а это `feed.views_of`."""

    def create(self, fields: dict) -> dict:
        """Поля формы, а не готовый `Item`: собрать датакласс обратно из JSON
        нечем, а `new_manual_item` уже умеет и `manual`, и свой идентификатор,
        и момент создания."""
        item = _manual(fields)
        return self._reply(lambda back: back.library.create(item))

    def replace(self, item_id: int, fields: dict) -> dict:
        """Тот же `_manual`, что и у заведения: свежий `synced_at`, который он
        подставляет, до базы не доезжает — `replace_fields` его не пишет.
        Правка руками не разговор с источником, и объявить карточку только что
        обновлённой значило бы отложить перезапрос сезонов на месяц."""
        item = _manual(fields)
        return self._reply(
            lambda back: back.library.replace_fields(item_id, item))

    def same_title(self, kind: str, title: str) -> dict:
        """Совпадение названия — предупреждение, а не запрет: фильмов с
        одинаковыми названиями много."""
        return self._reply(
            lambda back: back.library.find_by_title(Kind(kind), title))

    def unlink(self, item_id: int) -> dict:
        return self._reply(lambda back: back.library.unlink(item_id))

    def deletion_summary(self, item_id: int) -> dict:
        return self._reply(lambda back: back.library.deletion_summary(item_id))

    def delete(self, item_id: int) -> dict:
        """Только через метод бэкенда: он знает порядок двух файлов базы.
        Обложка уходит первой — `id` SQLite выдаёт повторно, и оставшаяся
        сирота досталась бы следующей карточке."""
        return self._reply(lambda back: back.delete_card(item_id))


def _manual(fields: dict):
    """Незаполненное в форме — это «не знаю», а не «пусто»: до бэкенда оно не
    доходит, и поле остаётся тем, что объявлено по умолчанию."""
    known = {name: value for name, value in fields.items()
             if name not in ("kind", "title") and value is not None}
    if "released_at" in known:
        known["released_at"] = date.fromisoformat(known["released_at"])
    return new_manual_item(Kind(fields["kind"]), fields["title"], **known)
```

Создать `bridge/marks.py`:

```python
"""Мост: свои отметки — оценки, теги, закладки.

Часы подставляет мост: внутри бэкенда они не берутся, а страница о них знать не
должна."""

from datetime import datetime

from backend.model import Kind
from bridge.answer import Domain


class Marks(Domain):
    def score(self, item_id: int, score: float | None) -> dict:
        now = datetime.now()
        return self._reply(
            lambda back: back.ratings.set_score(item_id, score, now))

    def aspects(self, item_id: int, visual, narrative, gameplay) -> dict:
        """Ответ — выведенный балл: у игр оценка это среднее трёх шкал, и
        карточке надо показать новое число, не перечитывая её целиком."""
        now = datetime.now()
        return self._reply(
            lambda back: back.ratings.set_aspects(item_id, visual, narrative,
                                                  gameplay, now))

    def review(self, item_id: int, text: str) -> dict:
        now = datetime.now()
        return self._reply(
            lambda back: back.ratings.set_review(item_id, text, now))

    def clear_rating(self, item_id: int) -> dict:
        return self._reply(lambda back: back.ratings.clear(item_id))

    def create_tag(self, kind: str, name: str) -> dict:
        return self._reply(lambda back: back.tags.create(Kind(kind), name))

    def tags(self, kind: str) -> dict:
        return self._reply(lambda back: back.tags.list_for_kind(Kind(kind)))

    def reorder_tags(self, kind: str, tag_ids: list) -> dict:
        return self._reply(lambda back: back.tags.reorder(Kind(kind), tag_ids))

    def rename_tag(self, tag_id: int, name: str) -> dict:
        return self._reply(lambda back: back.tags.rename(tag_id, name))

    def tag_usage(self, tag_id: int) -> dict:
        """Сколько карточек носит тег. Спрашивается перед удалением: у тега с
        носителями оно подтверждается с их числом, ничей уходит молча."""
        return self._reply(lambda back: back.tags.usage(tag_id))

    def delete_tag(self, tag_id: int) -> dict:
        return self._reply(lambda back: back.tags.delete(tag_id))

    def assign(self, item_id: int, tag_id: int) -> dict:
        return self._reply(lambda back: back.tags.assign(item_id, tag_id))

    def unassign(self, item_id: int, tag_id: int) -> dict:
        return self._reply(lambda back: back.tags.unassign(item_id, tag_id))

    def wish(self, item_id: int) -> dict:
        now = datetime.now()
        return self._reply(lambda back: back.wishlist.add(item_id, now))

    def unwish(self, item_id: int) -> dict:
        return self._reply(lambda back: back.wishlist.remove(item_id))
```

`Marks.aspects` берёт четыре довода и `self` — предел правила 5 по параметрам;
пятого сюда добавлять нельзя, и если понадобится, шкалы едут словарём.

- [x] **Шаг 5: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/ -v`
Ожидание: PASS, 24 новых теста — девять про карточку и пятнадцать про отметки.
Плана на четыре больше: он не давал тестов трём объявленным им же методам
(`replace`, `unlink`, `tag_usage`), а четвёртый — про то, что кривое поле формы
становится ответом, а не исключением через границу потоков.

- [x] **Шаг 6: Коммит**

```bash
git add bridge/library.py bridge/marks.py \
        tests/bridge/test_bridge_library.py tests/bridge/test_bridge_marks.py \
        tests/bridge/conftest.py
git commit -m "feat: мост — карточка и свои отметки"
```

---

### Задача 6: Справочники

Жанры, люди и студии. Половина всей поверхности бэкенда — это справочники (27
операций из 76), но странице из них нужны шесть: список жанров для фильтра и для
окна карточки, подсказка при вводе имени, заведение человека двумя жестами и
«показать всё с этим человеком».

**Люди и студии — один класс с двумя экземплярами.** У `CreditRepository` те же
одиннадцать методов на обоих доменах, и мост обязан не написать их дважды: имя
домена приезжает доводом и выбирает репозиторий. Это тот случай, когда общее
выносится сразу — обе реализации есть с первого дня.

**Два жеста различения тёзок.** Выбрал строку в подсказке — существующий
(`entity_id` уже известен, заводить нечего), нажал Enter ни на что не встав —
новый (`create_manual`). Совпадение имени само по себе не решает ничего.

**Файлы:**
- Создать: `bridge/refs.py`
- Создать: `tests/bridge/test_bridge_refs.py`

**Интерфейсы:**
- Потребляет: `Domain` из `bridge.answer`; `GenreKind` из `backend.model`.
- Отдаёт: `Refs` с `genres(genre_kind)`, `suggest(domain, name)`,
  `create_person(domain, name)`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/bridge/test_bridge_refs.py`:

```python
"""Мост: справочники — жанры, люди, студии."""

import pytest

from backend.model import GenreKind
from bridge.refs import Refs


def test_genres_come_for_the_asked_set(spy, asked):
    """Наборов жанров два: кино (фильмы и сериалы делят один) и игры."""
    answers, log = asked
    answers["genres.list_for_kind"] = []

    Refs(spy).genres("game")

    name, args, _ = log[0]
    assert name == "genres.list_for_kind"
    assert args[0] is GenreKind.GAME


@pytest.mark.parametrize(("domain", "asked_name"),
                         [("people", "people.suggest"),
                          ("companies", "companies.suggest")])
def test_the_domain_chooses_the_repository(spy, asked, domain, asked_name):
    """Один класс, два экземпляра: одиннадцать методов писать дважды нельзя, и
    сторожит это привязка, а не набор имён."""
    answers, log = asked
    answers[asked_name] = []

    Refs(spy).suggest(domain, "Нолан")

    assert [name for name, _, _ in log] == [asked_name]


def test_an_unknown_domain_is_a_failure_not_a_crash(spy, asked):
    """Опечатка на стороне страницы не должна становиться вечным промисом."""
    assert Refs(spy).suggest("actors", "Нолан")["fail"] == "broken"


def test_enter_on_nothing_highlighted_creates_a_new_one(spy, asked):
    """Совпадение имени само по себе не решает ничего: полные тёзки существуют,
    и завести второго Василия Пупкина можно."""
    answers, log = asked
    answers["people.create_manual"] = 9

    assert Refs(spy).create_person("people", "Василий Пупкин") == {"ok": 9}
    assert [name for name, _, _ in log] == ["people.create_manual"]
```

**`items_of` мосту не нужен вовсе, и его здесь нет.** Заводился он под «всё с
этим человеком», а этот жест забрал план 11: там `Search.by_person` зовёт
`finder.by_entity` и отдаёт обе половины — свою и внешнюю — уже собранными в
карточки. Отдельная ручка «номера моих карточек с этим человеком» осталась бы
без потребителя, то есть нарушила бы правило 8. Довод записан здесь, потому что
искать его будут в этом плане.

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_refs.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.refs'`.

- [x] **Шаг 3: Написать домен**

Создать `bridge/refs.py`:

```python
"""Мост: справочники — жанры, люди, студии.

Люди и студии — один класс с двумя экземплярами: одиннадцать методов у них общие,
и писать их дважды нельзя. Имя домена приезжает доводом и выбирает репозиторий."""

from backend.model import GenreKind
from bridge.answer import Domain

DOMAINS = ("people", "companies")


class Refs(Domain):
    def genres(self, genre_kind: str) -> dict:
        """Наборов два: кино и игры. Клиенту нужен только список — перевод чужих
        меток в наши жанры это внутренность записи карточки."""
        return self._reply(
            lambda back: back.genres.list_for_kind(GenreKind(genre_kind)))

    def suggest(self, domain: str, name: str) -> dict:
        """Строка подсказки несёт название самой высоко оценённой связанной
        карточки — по нему человека и узнают."""
        return self._reply(lambda back: _of(back, domain).suggest(name))

    def create_person(self, domain: str, name: str) -> dict:
        """Enter при неподсвеченном списке заводит нового — и человека, и
        студию. Выбранного из подсказки заводить не нужно: `entity_id` уже
        известен."""
        return self._reply(lambda back: _of(back, domain).create_manual(name))


def _of(backend, domain: str):
    """Опечатка на стороне страницы обязана стать отказом, а не вечным промисом:
    `getattr` по неизвестному имени поднял бы `AttributeError`, и его поймала бы
    оболочка — но уже без внятного текста."""
    if domain not in DOMAINS:
        raise ValueError(f"нет такого справочника: {domain}")
    return getattr(backend, domain)
```

- [x] **Шаг 4: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_refs.py -v`
Ожидание: PASS, 5 тестов.

- [x] **Шаг 5: Коммит**

```bash
git add bridge/refs.py tests/bridge/test_bridge_refs.py
git commit -m "feat: мост — справочники жанров, людей и студий"
```

---

### Задача 7: Лента

Страницы разделов и гистограмма. Три довода запроса — раздел, тип содержимого,
фильтры и сортировка — приезжают из состояния страницы и складываются здесь в
`Feed`: собирать этот датакласс на стороне JS было бы вторым объявлением того же
набора полей.

**Фильтры трёхпозиционные.** Включённые внутри признака складываются по «или»,
между признаками — по «и», исключённые вычитаются последними. Само сложение
делает база; мост раскладывает три состояния строки на два кортежа —
включённые и исключённые.

**Файлы:**
- Создать: `bridge/feed.py`
- Создать: `tests/bridge/test_bridge_feed.py`

**Интерфейсы:**
- Потребляет: `Domain`; `Feed`, `Filters`, `Kind`, `Order`, `Section`, `Sort`
  из `backend.model`.
- Отдаёт: `FeedBridge` с `page(op, feed, offset, limit)`,
  `views_of(op, item_ids)`, `histogram(op, kind, filters)`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/bridge/test_bridge_feed.py`:

```python
"""Мост: лента — страницы разделов и гистограмма."""

from backend.model import Kind, Section, Sort
from bridge.feed import FeedBridge

WISHED = {
    "section": "wishlist",
    "kind": "game",
    "filters": {"tag_ids": [3], "excluded_genre_ids": [7]},
    "order": {"key": "added_at", "descending": True},
}


def test_the_request_is_assembled_from_what_the_page_holds(spy, asked):
    """Собирать `Feed` на стороне JS значило бы объявить те же поля второй раз."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, WISHED, 0, 50)

    name, args, _ = log[0]
    assert name == "feed.page"
    feed = args[0]
    assert feed.section is Section.WISHLIST
    assert feed.kind is Kind.GAME
    assert feed.order.key is Sort.ADDED_AT
    assert feed.order.descending is True


def test_three_states_of_a_filter_row_become_two_tuples(spy, asked):
    """Не выбран, включён, исключён: исключение сильнее включения, и вычитается
    оно последним — это уже работа базы."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, WISHED, 0, 50)

    filters = log[0][1][0].filters
    assert filters.tag_ids == (3,)
    assert filters.excluded_genre_ids == (7,)
    assert filters.genre_ids == ()


def test_a_missing_filter_means_no_filter(spy, asked):
    """Страница шлёт только то, что человек тронул."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, {"section": "rated", "kind": "movie",
                             "filters": {}, "order": {"key": "score"}}, 0, 50)

    assert log[0][1][0].filters.scores == ()


def test_paging_carries_the_offset(spy, asked):
    """Лента растёт порциями по 50 и своей полной длины не знает."""
    answers, log = asked
    answers["feed.page"] = []

    FeedBridge(spy).page(1, WISHED, 100, 50)

    _, args, kwargs = log[0]
    assert (args[1:], kwargs) in (((100, 50), {}), ((), {"offset": 100,
                                                         "limit": 50}))


def test_one_card_is_reread_by_the_same_door(spy, asked):
    """Точечное обновление после правки — тот же `views_of`, а не второй адрес."""
    answers, log = asked
    answers["feed.views_of"] = []

    FeedBridge(spy).views_of(1, [12])

    assert [name for name, _, _ in log] == ["feed.views_of"]


def test_the_histogram_uses_the_same_filters(spy, asked):
    """Гистограмма строится по тому же отфильтрованному набору, что и разделы с
    карточками, — иначе отфильтрованную её не увидеть никогда."""
    answers, log = asked
    answers["feed.histogram"] = None

    FeedBridge(spy).histogram(1, "game", {"tag_ids": [3]})

    name, args, _ = log[0]
    assert name == "feed.histogram"
    assert args[0] is Kind.GAME
    assert args[1].tag_ids == (3,)
```

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_feed.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.feed'`.

- [x] **Шаг 3: Написать домен**

Создать `bridge/feed.py`:

```python
"""Мост: лента — страницы разделов и гистограмма."""

from backend.model import Feed, Filters, Kind, Order, Section, Sort
from bridge.answer import Domain

# Шесть кортежей `Filters` — по два на признак: включённые и исключённые.
# Перечислены поимённо, потому что имя поля и есть контракт со страницей.
FILTER_FIELDS = ("tag_ids", "genre_ids", "scores",
                 "excluded_tag_ids", "excluded_genre_ids", "excluded_scores")


class FeedBridge(Domain):
    """Имя с хвостом, потому что `Feed` — это тип модели, и второе значение у
    того же слова путало бы обе стороны.

    Номер операции несут все три метода: смена фильтра или сортировки заводит
    новый запрос, и ответ прежнего приезжать не должен — ни страницей карточек,
    ни столбцами гистограммы. Решение и таблица «кто с номером» — в шапке плана."""

    def page(self, op: int, feed: dict, offset: int, limit: int) -> dict:
        request = _feed(feed)
        return self._reply(lambda back: back.feed.page(request, offset, limit),
                           op=op)

    def views_of(self, op: int, item_ids: list) -> dict:
        """Точечное чтение после правки идёт той же дверью, что и лента."""
        return self._reply(lambda back: back.feed.views_of(item_ids), op=op)

    def histogram(self, op: int, kind: str, filters: dict) -> dict:
        """Тот же отфильтрованный набор, что и у разделов с карточками."""
        chosen = _filters(filters)
        return self._reply(
            lambda back: back.feed.histogram(Kind(kind), chosen), op=op)


def _feed(feed: dict) -> Feed:
    order = feed["order"]
    return Feed(
        section=Section(feed["section"]),
        kind=Kind(feed["kind"]),
        filters=_filters(feed["filters"]),
        order=Order(key=Sort(order["key"]),
                    descending=order.get("descending", True)),
    )


def _filters(filters: dict) -> Filters:
    """Страница шлёт только то, что человек тронул: неназванный признак — это
    отсутствие фильтра, а не пустой набор."""
    return Filters(**{name: tuple(filters.get(name, ()))
                      for name in FILTER_FIELDS})
```

- [x] **Шаг 4: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_feed.py -v`
Ожидание: PASS, 6 тестов.

- [x] **Шаг 5: Коммит**

```bash
git add bridge/feed.py tests/bridge/test_bridge_feed.py
git commit -m "feat: мост — лента и гистограмма"
```

---

### Задача 8: Поиск

Своё, чужое, складывание и заведение найденного. Единственный домен моста, у
которого есть своя механика, и вся она — следствие одного: `CardView` через JSON
уезжает, а обратно не собирается.

**Здесь же заводится память моста.** Она понадобится и привязке (задача 9), но
пишется тут, у первого потребителя, а не заранее: вынести общее на втором
появлении можно всегда, а завести его до первого — значит объявить абстракцию в
ожидании реализации.

**Своё показывается сразу, внешнее доливается по готовности.** Два вызова, а не
один: локальная база отвечает за миллисекунды, внешняя — за доли секунды, и
ждать сеть, чтобы показать лежащее на диске, незачем.

**Складывает мост, а не страница.** `merge_results` уже написан и живёт в
модели ровно потому, что складывать приходится клиенту. Переписать его на JS
значило бы объявить второй раз и правило снятия дублей, и правило «своя половина
целиком впереди чужой, а совпавшее чужое вторым разом не показывается — своё
уже стоит выше, и у него есть оценка, теги и закладка».

**Заведение — по паре «источник + идентификатор», а не по номеру строки.**
Кандидата мост берёт из выдачи, которую сам же и помнит; пара переживает
перерисовку и переупорядочивание, номер строки — нет.

**Файлы:**
- Создать: `bridge/kept.py`, `bridge/search.py`
- Создать: `tests/bridge/test_kept.py`,
  `tests/bridge/test_bridge_search.py`

**Интерфейсы:**
- Потребляет: `Domain`; `Kind`, `merge_results` из `backend.model`; `outcome`
  из `bridge.wire`.
- Отдаёт: `Kept` с `put(op, value)`, `taken(op) -> value | None`, `drop()`;
  `Search` с `local(op, kind, query)`, `external(op)`,
  `ensure(op, source, source_id)`.

- [x] **Шаг 1: Написать падающий тест на память**

Создать `tests/bridge/test_kept.py`:

```python
"""То, что не пролезает обратно через JSON, мост помнит у себя."""

from bridge.kept import Kept


def test_what_was_kept_comes_back():
    kept = Kept()
    kept.put(1, ["выдача"])
    assert kept.taken(1) == ["выдача"]


def test_a_stale_number_gets_nothing():
    """Страница набрала новый запрос, пока летел старый: второй шаг старой
    операции обязан уйти ни с чем, а не подставить чужую выдачу."""
    kept = Kept()
    kept.put(1, ["старое"])
    kept.put(2, ["новое"])

    assert kept.taken(1) is None
    assert kept.taken(2) == ["новое"]


def test_only_one_value_is_held():
    """Больше одного помнить незачем — и поиск, и привязка идут по одному за
    раз, — а словарь по номеру протекал бы на каждой брошенной операции."""
    kept = Kept()
    kept.put(1, ["первое"])
    kept.put(2, ["второе"])

    assert kept.taken(1) is None


def test_dropping_forgets_everything():
    kept = Kept()
    kept.put(1, ["выдача"])
    kept.drop()
    assert kept.taken(1) is None


def test_nothing_kept_is_not_a_failure():
    """Второй шаг без первого — обычное дело: операцию отменили."""
    assert Kept().taken(1) is None
```

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_kept.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.kept'`.

- [x] **Шаг 3: Написать память**

Создать `bridge/kept.py`:

```python
"""То, что не пролезает обратно через JSON.

`CardView` и `SourceCard` уезжают на страницу словарями, а обратно нужны
датаклассами. Собирать их из разобранного JSON — это второе объявление тех же
типов, и разошлось бы оно с моделью молча. Мост помнит их у себя, а страница
называет по номеру операции.

Держится ровно одно значение: и поиск, и привязка в интерфейсе идут по одному за
раз, а словарь по номеру протекал бы на каждой брошенной операции."""


class Kept:
    def __init__(self) -> None:
        self._op: int | None = None
        self._value = None

    def put(self, op: int, value) -> None:
        self._op = op
        self._value = value

    def taken(self, op: int):
        """Чужой номер получает `None`: устаревший второй шаг не должен
        подставить выдачу от нового запроса."""
        return self._value if op == self._op else None

    def drop(self) -> None:
        self._op = None
        self._value = None
```

- [x] **Шаг 4: Написать падающий тест на поиск**

Создать `tests/bridge/test_bridge_search.py`:

```python
"""Мост: поиск — своё, чужое, складывание, заведение найденного."""

from backend.model import CardView, ExternalSearch, Kind, Missing, Source
from bridge.search import Search


def a_view(source_id, item_id=None, title="Одиссея"):
    return CardView(kind=Kind.MOVIE, source=Source.TMDB, source_id=source_id,
                    title=title, item_id=item_id)


def test_local_comes_first_and_alone(spy, asked):
    """Ждать сеть, чтобы показать лежащее на диске, незачем."""
    answers, log = asked
    answers["search.local"] = [a_view("1", item_id=5)]

    answer = Search(spy).local(1, "movie", "одиссея")

    assert [name for name, _, _ in log] == ["search.local"]
    assert answer["ok"][0]["item_id"] == 5


def test_external_is_merged_with_what_was_shown(spy, asked):
    """Свой близнец чужого кандидата показывается один раз, и показывается
    именно свой: у него есть оценка, теги и закладка."""
    answers, _ = asked
    answers["search.local"] = [a_view("1", item_id=5)]
    answers["search.external"] = ExternalSearch(
        views=(a_view("1"), a_view("2")), refusals=())

    search = Search(spy)
    search.local(1, "movie", "одиссея")
    answer = search.external(1)

    ids = [view["source_id"] for view in answer["ok"]["views"]]
    assert ids == ["1", "2"]
    assert answer["ok"]["views"][0]["item_id"] == 5


def test_the_local_half_comes_first(spy, asked):
    """Сначала своя половина целиком, потом чужая — правило одно на всю выдачу
    поиска, и живёт оно в `merge_results`."""
    answers, _ = asked
    answers["search.local"] = [a_view("9", item_id=5, title="Только своё")]
    answers["search.external"] = ExternalSearch(views=(a_view("1"),),
                                                refusals=())

    search = Search(spy)
    search.local(1, "movie", "одиссея")

    ids = [view["source_id"]
           for view in search.external(1)["ok"]["views"]]
    assert ids == ["9", "1"]


def test_the_query_is_asked_once(spy, asked):
    """Второй шаг не переспрашивает запрос: разъехаться им было бы нечему —
    мост помнит и тип, и строку."""
    answers, log = asked
    answers["search.local"] = []
    answers["search.external"] = ExternalSearch(views=(), refusals=())

    search = Search(spy)
    search.local(1, "game", "ведьмак")
    search.external(1)

    _, args, _ = log[1]
    assert args[0] is Kind.GAME
    assert args[1] == "ведьмак"


def test_a_stale_number_gets_nothing(spy, asked):
    """Набрал новый запрос, пока летел старый: старые результаты не затирают
    новые, и второй шаг старой операции обязан уйти ни с чем."""
    answers, _ = asked
    answers["search.local"] = []

    search = Search(spy)
    search.local(1, "movie", "старое")
    search.local(2, "movie", "новое")

    assert search.external(1) == {"fail": "stale"}


def test_a_refusal_of_the_outer_base_travels_as_a_field(spy, asked):
    """Отказ источника — не исключение, а поле в ответе: второго канала у
    границы потоков нет."""
    from datetime import timedelta

    from backend.model import Reason, Refusal
    answers, _ = asked
    answers["search.local"] = []
    answers["search.external"] = ExternalSearch(
        views=(),
        refusals=(Refusal(source="tmdb", reason=Reason.NETWORK,
                          retry_after=timedelta(seconds=15)),))

    search = Search(spy)
    search.local(1, "movie", "одиссея")
    answer = search.external(1)

    assert answer["ok"]["refusals"][0]["reason"] == "network"
    assert answer["ok"]["refusals"][0]["retry_after"] == 15.0


def test_a_candidate_is_added_by_its_pair(spy, asked):
    """Пара «источник + идентификатор» переживает перерисовку выдачи, а номер
    строки — нет."""
    answers, log = asked
    answers["search.local"] = [a_view("157336")]
    answers["loader.ensure"] = 12

    search = Search(spy)
    search.local(1, "movie", "интерстеллар")
    answer = search.ensure(1, "tmdb", "157336")

    assert answer == {"ok": {"outcome": "found", "value": 12}}
    name, args, _ = log[1]
    assert name == "loader.ensure"
    assert args[0].source_id == "157336"


def test_adding_something_that_is_not_in_the_list_is_stale(spy, asked):
    answers, _ = asked
    answers["search.local"] = []

    search = Search(spy)
    search.local(1, "movie", "одиссея")

    assert search.ensure(1, "tmdb", "404") == {"fail": "stale"}


def test_a_source_that_lost_the_card_says_so(spy, asked):
    """Исход запроса к источнику — один из трёх, и `Missing` обязан отличаться
    от чего угодно пустого."""
    answers, _ = asked
    answers["search.local"] = [a_view("157336")]
    answers["loader.ensure"] = Missing()

    search = Search(spy)
    search.local(1, "movie", "интерстеллар")

    assert search.ensure(1, "tmdb", "157336") == {
        "ok": {"outcome": "missing"}}
```

- [x] **Шаг 5: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_search.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.search'`.

- [x] **Шаг 6: Написать домен**

Создать `bridge/search.py`:

```python
"""Мост: поиск — своё, чужое, складывание, заведение найденного.

Единственный домен со своей механикой, и вся она из одного: `CardView` уезжает на
страницу словарём, а обратно не собирается. Поэтому выдачу мост помнит, а
страница называет кандидата парой «источник + идентификатор»."""

from backend.model import Kind, merge_results
from bridge.answer import Domain
from bridge.kept import Kept
from bridge.wire import outcome


class Search(Domain):
    def __init__(self, thread) -> None:
        super().__init__(thread)
        self._kept = Kept()
        self._asked: tuple[Kind, str] | None = None

    def local(self, op: int, kind: str, query: str) -> dict:
        """Своё показывается сразу: локальная база отвечает за миллисекунды."""
        self._asked = (Kind(kind), query)
        return self._reply(lambda back: self._own(back, op), op=op)

    def external(self, op: int) -> dict:
        """Внешнее доливается по готовности и складывается со своим здесь:
        `merge_results` живёт в модели ровно потому, что складывать приходится
        клиенту, и второго его объявления быть не должно."""
        if self._kept.taken(op) is None:
            return {"fail": "stale"}
        return self._reply(lambda back: self._outer(back, op), op=op)

    def ensure(self, op: int, source: str, source_id: str) -> dict:
        """Кандидат берётся из помнимой выдачи: `CardView` собрать из JSON
        нечем, а пара переживает перерисовку списка."""
        candidate = _found(self._kept.taken(op), source, source_id)
        if candidate is None:
            return {"fail": "stale"}
        return self._reply(
            lambda back: self._added(back, candidate), op=op)

    async def _own(self, back, op):
        """Перевод в JSON делает оболочка, и делает его один раз: отсюда наружу
        уходят датаклассы. Довод зовётся `back` не для красоты — по этому имени
        сторож поверхности и собирает вызовы."""
        kind, query = self._asked
        views = list(await back.search.local(kind, query))
        self._kept.put(op, views)
        return views

    async def _outer(self, back, op):
        kind, query = self._asked
        found = await back.search.external(kind, query)
        merged = merge_results(self._kept.taken(op) or [], list(found.views))
        self._kept.put(op, merged)
        return {"views": merged, "refusals": found.refusals}

    async def _added(self, back, candidate):
        return outcome(await back.loader.ensure(candidate))


def _found(views, source: str, source_id: str):
    if not views:
        return None
    for view in views:
        if view.source == source and view.source_id == source_id:
            return view
    return None
```

`_added` — единственное место домена, где перевод идёт своими руками: у исхода
запроса форма особая, с меткой, и собрать её может только `outcome`. `to_wire`
поверх готового словаря отработает вторым проходом и ничего не испортит.

- [x] **Шаг 7: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/test_kept.py tests/bridge/test_bridge_search.py -v`
Ожидание: PASS, 14 тестов.

- [x] **Шаг 8: Коммит**

```bash
git add bridge/kept.py bridge/search.py \
        tests/bridge/test_kept.py tests/bridge/test_bridge_search.py
git commit -m "feat: мост — поиск со складыванием выдач и памятью"
```

---

### Задача 9: Внешний мир

Всё, что ходит в сеть помимо поиска: перезапрос сериала, оценки агрегаторов,
разбор вставленной ссылки, карточка по ссылке и привязка.

**Разбор ссылки зовётся мостом, а не переписывается на JS.** `parse_link` уже
написан и лежит в модели; вторая регулярка на тот же адрес разошлась бы с первой
молча. Вызов идёт на каждое нажатие клавиши в одном поле — это без сети и без
диска, чистая функция.

**Карточка привязки помнится, как и выдача поиска.** `SourceCard` уезжает на
страницу словарём, а `linker.link` требует датакласс. Страница его и не
показывает: ей нужно только «нашлось» или «нет».

**Оценки агрегаторов — только тому, что уже в базе.** У кандидата нет `imdb_id`,
он приходит только в детальном ответе: круг 3 нельзя начать раньше круга 2.

**Файлы:**
- Создать: `bridge/world.py`
- Создать: `tests/bridge/test_bridge_world.py`

**Интерфейсы:**
- Потребляет: `Domain`, `Kept`; `Kind`, `parse_link` из `backend.model`;
  `outcome`, `to_wire` из `bridge.wire`.
- Отдаёт: `World` с `parse(raw, kind)`, `card_for_link(op, raw, kind)`,
  `link(op, item_id, overwrite)`, `refresh_series(op, item_id)`,
  `enrich(op, item_id, kind)`, `expected(op, kind)`, `open(url)`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/bridge/test_bridge_world.py`:

```python
"""Мост: внешний мир — привязка, перезапрос, оценки агрегаторов."""

from datetime import datetime

from backend.model import ItemExists, Kind, Missing, RatingSource
from bridge.world import World


def test_a_pasted_link_is_parsed_without_the_network(spy, asked):
    """Галочка появляется, когда адрес похож на разобранный, — это чистая
    функция, и второй регулярки на тот же адрес быть не должно."""
    answers, log = asked

    answer = World(spy).parse("https://www.themoviedb.org/movie/157336-inter",
                              None)

    assert answer["ok"]["source"] == "tmdb"
    assert answer["ok"]["source_id"] == "157336"
    assert answer["ok"]["kind"] == "movie"
    assert log == []


def test_something_that_is_not_a_link_is_not_a_failure(spy, asked):
    """Человек ещё печатает: непохожее на адрес — это «пока нет», а не отказ."""
    assert World(spy).parse("одис", None) == {"ok": None}


def test_the_card_for_a_link_is_kept_not_sent_back(spy, asked):
    """`SourceCard` уезжает словарём, а `linker.link` требует датакласс:
    возить его туда и обратно значило бы объявить те же поля второй раз."""
    answers, log = asked
    answers["loader.card_for_link"] = "карточка"
    answers["linker.link"] = None

    world = World(spy)
    assert world.card_for_link(1, "themoviedb.org/movie/157336", None) == {
        "ok": {"outcome": "found", "value": "карточка"}}

    before = datetime.now()
    world.link(1, 12, False)
    after = datetime.now()

    name, args, kwargs = log[1]
    assert name == "linker.link"
    assert args[0] == 12
    assert args[1] == "карточка"
    assert before <= args[2] <= after
    assert kwargs == {"overwrite": False}


def test_linking_without_a_kept_card_is_stale(spy, asked):
    assert World(spy).link(1, 12, False) == {"fail": "stale"}


def test_a_taken_identity_is_a_kind_of_failure(spy, asked):
    """Ссылка ведёт на карточку, которая в библиотеке уже есть: дубль завести не
    даём, и говорим об этом.

    Род отказа именно `item-exists`: занятость проверяется до первой записи, и
    `Linker._check_identifiers` поднимает там `ItemExists`
    (`backend/service/linking.py:87`). `ExternalIdTaken` до клиента не долетает
    вовсе — его ловит и пишет в лог сам `Enricher`."""
    answers, _ = asked
    answers["loader.card_for_link"] = "карточка"
    answers["linker.link"] = ItemExists("imdb:tt0816692 уже за карточкой 4")

    world = World(spy)
    world.card_for_link(1, "themoviedb.org/movie/157336", None)

    assert world.link(1, 12, False)["fail"] == "item-exists"


def test_a_source_without_that_card_says_missing(spy, asked):
    answers, _ = asked
    answers["loader.card_for_link"] = Missing()

    assert World(spy).card_for_link(1, "themoviedb.org/movie/1", None) == {
        "ok": {"outcome": "missing"}}


def test_an_unparsable_link_never_reaches_the_network(spy, asked):
    answers, log = asked

    assert World(spy).card_for_link(1, "одис", None)["fail"] == "bad-link"
    assert log == []


def test_refreshing_a_series_is_silent_when_nothing_was_needed(spy, asked):
    """Клиент не может отличить «перезапросили» от «не понадобилось», и не
    должен: перезапрос идёт по сроку, а решает его бэкенд."""
    answers, log = asked
    answers["series.refresh"] = None

    assert World(spy).refresh_series(1, 12) == {"ok": None}
    assert [name for name, _, _ in log] == ["series.refresh"]


def test_enriching_answers_with_what_arrived(spy, asked):
    answers, log = asked
    answers["enricher.enrich"] = []

    World(spy).enrich(1, 12, "movie")

    name, args, _ = log[0]
    assert name == "enricher.enrich"
    assert args == (12, Kind.MOVIE)


def test_expected_sources_are_known_before_the_network(spy, asked):
    """Под неприехавшую оценку рисуется кружок, и сколько их будет, надо знать
    до ответа сети."""
    answers, _ = asked
    answers["enricher.expected"] = [RatingSource.IMDB, RatingSource.KINOPOISK]

    assert World(spy).expected(1, "movie") == {"ok": ["imdb", "kinopoisk"]}


def test_a_synchronous_backend_method_still_answers(thread, backend):
    """`Enricher.expected` — обычный `def`, а поток кладёт фабрику в
    `create_task`, и тот от не-корутины падает **внутри колбэка цикла**, мимо
    `try` в `_reply`: заявка не разрешилась бы вовсе, и вызов досидел бы весь
    срок, ответив «не уложились».

    Идёт через настоящий поток, а не через двойника: `Asked.__call__` отдаёт
    корутину на любой вызов, и у него синхронный метод бэкенда выглядит так же,
    как асинхронный."""
    backend.enricher = SimpleNamespace(
        expected=lambda kind: [RatingSource.IMDB])

    assert World(thread).expected(1, "movie") == {"ok": ["imdb"]}
```

Этот тест — единственный в модуле, кто берёт настоящий `BackendThread`:
проверяемое свойство лежит ровно на стыке «фабрика → `create_task`», а двойник
этот стык и подменяет.

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_world.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.world'`.

- [x] **Шаг 3: Написать домен**

Создать `bridge/world.py`:

```python
"""Мост: внешний мир — привязка, перезапрос сериала, оценки агрегаторов и
открытие страницы источника."""

import webbrowser
from datetime import datetime

from backend.model import Denied, Kind, parse_link
from bridge.answer import Domain
from bridge.kept import Kept
from bridge.wire import outcome, to_wire


class World(Domain):
    def __init__(self, thread) -> None:
        super().__init__(thread)
        self._kept = Kept()

    def parse(self, raw: str, kind: str | None) -> dict:
        """Зовётся на каждое нажатие клавиши, но не ходит ни в сеть, ни на диск.
        Переписывать разбор на JS нельзя: вторая регулярка на тот же адрес
        разошлась бы с первой молча.

        Идёт через `_reply`, как и всё остальное, хотя бэкенд ей не нужен:
        отдельный путь наружу означал бы, что исключение из `parse_link` летит
        через границу потоков мимо оболочки. Цена — переброс в поток без
        единого обращения к диску или сети."""
        return self._reply(lambda _back: self._parsed(raw, kind))

    async def _parsed(self, raw: str, kind: str | None):
        return parse_link(raw, _kind(kind))

    def card_for_link(self, op: int, raw: str, kind: str | None) -> dict:
        """Карточка помнится здесь: страница её не показывает, ей нужно только
        «нашлось» или «нет»."""
        link = parse_link(raw, _kind(kind))
        if link is None:
            return {"fail": "bad-link"}
        return self._reply(lambda back: self._asked(back, op, link), op=op)

    def link(self, op: int, item_id: int, overwrite: bool) -> dict:
        """Внешнее заполняет только пустое; галочка «перезаписать данные» — на
        случай, когда карточка заводилась на скорую руку."""
        card = self._kept.taken(op)
        if card is None:
            return {"fail": "stale"}
        now = datetime.now()
        return self._reply(
            lambda back: back.linker.link(item_id, card, now,
                                          overwrite=overwrite), op=op)

    def refresh_series(self, op: int, item_id: int) -> dict:
        """Тихо ничего не делает в трёх случаях — не сериал, не TMDB, не
        просрочено, — и различать их странице незачем."""
        return self._reply(lambda back: back.series.refresh(item_id), op=op)

    def enrich(self, op: int, item_id: int, kind: str) -> dict:
        """Только тому, что уже в базе: у кандидата нет `imdb_id`, он приходит
        лишь в детальном ответе."""
        return self._reply(
            lambda back: back.enricher.enrich(item_id, Kind(kind)), op=op)

    def expected(self, op: int, kind: str) -> dict:
        """Под неприехавшую оценку рисуется кружок, и сколько их будет, надо
        знать до ответа сети.

        Обёрнуто в корутину, а не отдано как есть: `Enricher.expected` —
        синхронный метод, а `_begin` кладёт фабрику в `create_task`, и тот от
        списка падает **внутри колбэка цикла** — мимо `try` в `_reply`. Заявка
        не разрешилась бы вовсе, и вызов досидел бы весь срок."""
        return self._reply(lambda back: self._expected(back, kind), op=op)

    async def _expected(self, back, kind: str):
        return back.enricher.expected(Kind(kind))

    def open(self, url: str) -> dict:
        """Страница источника открывается системным браузером.

        Обычная ссылка увела бы саму страницу приложения: окно — это Chromium
        без адресной строки и без кнопки «назад», и вернуться было бы нечем.
        Мимо потока бэкенда намеренно — к базе и сети это отношения не имеет."""
        return self._reply(lambda _back: self._opened(url))

    async def _opened(self, url: str) -> None:
        # Только свои адреса: `webbrowser` отдаёт строку системе как есть, а
        # схема оттуда приходит с чужой страницы карточки.
        if not url.startswith("https://"):
            raise Denied(f"чужая схема адреса: {url}")
        webbrowser.open(url)

    async def _asked(self, back, op, link):
        card = await back.loader.card_for_link(link)
        self._kept.put(op, card)
        return outcome(card)


def _kind(kind: str | None) -> Kind | None:
    """Тип берётся из адреса, а подсказка тумблера нужна там, где его в адресе
    нет, — у голого идентификатора."""
    return Kind(kind) if kind else None
```

`_asked` кладёт в память и `Missing`, и `Refusal` — а `link` на них упал бы. Так
не выйдет: `link` берёт помнимое только после того, как страница увидела
`{"outcome": "found"}`, и другой ветки у неё нет. Если это перестанет быть
правдой, память обязана держать только найденное.

- [x] **Шаг 4: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_world.py -v`
Ожидание: PASS, 11 тестов.

- [x] **Шаг 5: Коммит**

```bash
git add bridge/world.py tests/bridge/test_bridge_world.py
git commit -m "feat: мост — внешний мир, привязка и обогащение"
```

---

### Задача 10: Обложки, сборка моста и сторож поверхности

Последний домен и первое место, где мост собирается целиком. Здесь же —
проверка, закрывающая слабое место всех предыдущих: записывающий двойник
принимает любое имя, и опечатка в имени метода бэкенда прошла бы молча.

**Заливка едет base64, а показ — нет.** Направления у моста разные: аргументы
уходят `postMessage`-ом с JSON-строкой, а результат вклеивается в текст скрипта.
Поэтому картинка внутрь идёт base64, а наружу — HTTP-ручкой из задачи 11.

**Файлы:**
- Создать: `bridge/covers.py`, `bridge/api.py`
- Создать: `tests/bridge/test_bridge_covers.py`,
  `tests/bridge/test_bridge_surface.py`

**Интерфейсы:**
- Потребляет: все семь доменов.
- Отдаёт: `Covers` с `store_upload(item_id, data)`, `has(item_id)`;
  `Api` с полями `library`, `marks`, `refs`, `feed`, `search`, `world`,
  `covers` и методом `cancel(ops)`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/bridge/test_bridge_covers.py`:

```python
"""Мост: обложки — заливка своей картинки и наличие."""

import base64
from datetime import datetime

from backend.model import BadImage
from bridge.covers import Covers

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()


def test_an_uploaded_picture_arrives_as_bytes(spy, asked):
    """Внутрь картинка идёт base64: аргументы уезжают `postMessage`-ом, и этот
    канал бинарным тоже не бывает."""
    answers, log = asked
    answers["posters.store_upload"] = None

    before = datetime.now()
    Covers(spy).store_upload(12, PNG)
    after = datetime.now()

    name, args, _ = log[0]
    assert name == "posters.store_upload"
    assert args[0] == 12
    assert args[1] == b"\x89PNG\r\n\x1a\n"
    assert before <= args[2] <= after


def test_not_a_picture_is_a_kind_of_failure(spy, asked):
    """Обрезка до 2:3 идёт на бэкенде, и негодный файл он же и распознаёт."""
    answers, _ = asked
    answers["posters.store_upload"] = BadImage("не картинка")

    assert Covers(spy).store_upload(12, PNG)["fail"] == "bad-image"


def test_broken_base64_does_not_reach_the_backend(spy, asked):
    answers, log = asked

    assert Covers(spy).store_upload(12, "не base64!")["fail"] == "bad-image"
    assert log == []


def test_having_a_cover_is_a_plain_answer(spy, asked):
    answers, _ = asked
    answers["posters.has"] = True

    assert Covers(spy).has(12) == {"ok": True}
```

Создать `tests/bridge/test_bridge_surface.py`:

```python
"""Каждый вызов, который мост делает бэкенду, обязан ему подходить.

Записывающий двойник принимает любое имя с любыми доводами — переименованный
метод и лишний довод прошли бы молча на всём наборе. Этой проверкой закрывается
ровно та дыра, и закрывается она **обеими половинами**: имя должно
существовать, а доводы — сходиться с сигнатурой. Половины имён мало: расхождение
`items_of(entity_id, limit, offset)` с настоящим `items_of(entity_id, kind)` —
это верное имя и неверный вызов, и до живого запуска его не видит никто.

Вызовы собираются разбором исходников, а не переписываются сюда руками: список,
набранный вручную, разошёлся бы с кодом молча — и это была бы та же дыра, только
на этаж выше."""

import ast
import inspect
from pathlib import Path

import pytest

from backend.app import Backend
from bridge.api import Api

ROOT = Path(__file__).resolve().parents[2]
# Всё, что зовёт бэкенд по имени `back`: семь доменов моста и отдача обложек.
SOURCES = sorted((ROOT / "bridge").glob("*.py"))

DOMAINS = {"library", "marks", "refs", "feed", "search", "world", "covers"}


def chain(node):
    """`back.tags.create(...)` → `("tags", "create")`; чужой корень → `None`."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name) and node.id == "back":
        return tuple(reversed(parts))
    return None


def asked() -> dict[str, int]:
    """Что мост зовёт у бэкенда и со сколькими позиционными доводами.

    Доводы считаются, а не только имена: расхождение сигнатуры — ровно тот род
    поломки, который у этого проекта дважды доезжал до живого запуска
    (`items_of` с пределом, которого у репозитория нет). `hasattr` его не видит,
    а число доводов видит."""
    found = {}
    for path in SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                parts = chain(node.func)
                if parts:
                    # Звёздочка в вызове означает «сколько угодно»: считать
                    # нечего, и проверка сигнатуры для этого места снимается.
                    starred = any(isinstance(one, ast.Starred) for one in node.args)
                    found[".".join(parts)] = -1 if starred else len(node.args)
    return found


def surface(api) -> set[str]:
    """Поверхность моста так же, как её собирает pywebview: `dir()` без имён с
    подчёркиванием, с рекурсией в не-вызываемые объекты."""
    found = set()
    for name in dir(api):
        if name.startswith("_"):
            continue
        value = getattr(api, name)
        if callable(value):
            found.add(name)
        else:
            found.update(f"{name}.{inner}" for inner in surface(value))
    return found


def test_the_bridge_shows_seven_domains_and_cancelling(spy):
    """Семь доменов, а не шесть: поиск отделён от ленты — описать их одной
    фразой без «и» нельзя."""
    shown = surface(Api(spy))

    assert {name.split(".")[0] for name in shown} == DOMAINS | {"cancel"}
    assert "cancel" in shown


def test_something_is_actually_collected():
    """Пустой набор — это поломка сбора, а не чистый мост: сломанная маска и
    переименованный довод отдают ту же пустоту, что и отсутствие вызовов."""
    assert len(asked()) > 30


@pytest.mark.parametrize(("path", "count"), sorted(asked().items()))
def test_every_call_the_bridge_makes_fits_the_backend(path, count):
    where = Backend
    for step in path.split("."):
        assert hasattr(where, step), f"{path}: нет {step}"
        where = _behind(where, step)

    if count < 0:
        return
    # `bind` проверяет не только число, но и обязательные без умолчания: вызов
    # без `kind` у метода, который его требует, покраснеет здесь, а не в окне.
    inspect.signature(where).bind(None, *range(count))


def _behind(where, step):
    """У `Backend` поля объявлены аннотациями, и значения у класса нет — за
    именем стоит тип из `__annotations__`. У сервисов и репозиториев дальше идут
    обычные методы класса."""
    annotations = getattr(where, "__annotations__", {})
    return annotations.get(step) or getattr(where, step)
```

Отсюда условие, без которого сторож слепнет: **довод с бэкендом во всех этих
файлах зовётся `back`.** Это не стиль — по этому имени и собираются вызовы, и
переименованный довод молча выключил бы проверку. Держит его проверка
«что-то вообще собралось».

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_bridge_covers.py tests/bridge/test_bridge_surface.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.covers'`.

- [x] **Шаг 3: Написать домен обложек**

Создать `bridge/covers.py`:

```python
"""Мост: обложки — заливка своей картинки и наличие.

Показ идёт не отсюда: байты вклеиваются в текст скрипта, поэтому обложка едет
HTTP-ручкой (`bridge/serve.py`). Внутрь картинка идёт base64 — там канал другой,
`postMessage` с JSON-строкой."""

import binascii
import base64
from datetime import datetime

from backend.model import BadImage
from bridge.answer import Domain


class Covers(Domain):
    def store_upload(self, item_id: int, data: str) -> dict:
        """Обрезка по центру до 2:3 идёт на бэкенде, там же, где картинка и
        хранится: в потоке интерфейса ей делать нечего."""
        now = datetime.now()
        return self._reply(
            lambda back: back.posters.store_upload(item_id, _picture(data),
                                                   now))

    def has(self, item_id: int) -> dict:
        return self._reply(lambda back: back.posters.has(item_id))


def _picture(data: str) -> bytes:
    """Разбор идёт внутри заявки, а не до неё: брошенный снаружи `BadImage`
    прошёл бы мимо оболочки и уехал исключением через границу потоков.

    Род отказа у обеих бед один: человеку разница между «не base64» и «не
    картинка» ничего не даёт."""
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise BadImage("картинка не разобралась") from error
```

`_picture` зовётся внутри лямбды, то есть уже в потоке бэкенда, и его исключение
приезжает оболочке тем же путём, что и отказ репозитория.

- [x] **Шаг 4: Собрать мост**

Создать `bridge/api.py`:

```python
"""Поверхность моста: семь доменов и отмена.

pywebview собирает её рефлексией — `dir()` без имён с подчёркиванием, с
рекурсией в объекты, — и имена с точкой на стороне страницы разворачиваются в
дерево: `pywebview.api.feed.page(...)`."""

from bridge.covers import Covers
from bridge.feed import FeedBridge
from bridge.library import Library
from bridge.marks import Marks
from bridge.refs import Refs
from bridge.search import Search
from bridge.world import World


class Api:
    """Отмена лежит на корне, а не в домене: страница уходит целиком и гасит всё,
    что начала, одним пересечением границы."""

    def __init__(self, thread) -> None:
        self._thread = thread
        self.library = Library(thread)
        self.marks = Marks(thread)
        self.refs = Refs(thread)
        self.feed = FeedBridge(thread)
        self.search = Search(thread)
        self.world = World(thread)
        self.covers = Covers(thread)

    def cancel(self, ops: list) -> dict:
        """Неизвестный номер — обычное дело: ответ мог прийти раньше отмены."""
        self._thread.cancel(ops)
        return {"ok": None}
```

- [x] **Шаг 5: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/ -v`
Ожидание: PASS. Сторож поверхности обязан пройти по всем вызовам, которые делают
семь доменов; расхождение здесь — это опечатка, и правится код моста, а не тест.

- [x] **Шаг 6: Коммит**

```bash
git add bridge/covers.py bridge/api.py \
        tests/bridge/test_bridge_covers.py tests/bridge/test_bridge_surface.py
git commit -m "feat: мост собран целиком, со сторожем поверхности"
```

---

### Задача 11: Отдача страницы и обложек

Страница едет по HTTP, а не со схемы `file://`: Chromium блокирует `type="module"`
по CORS, а Vite выпускает именно модули. Сервер pywebview при этом поднимается
сам — достаточно отдать окну не путь, а WSGI-приложение.

**Почему своё, а не файловый сервер библиотеки.** У него корень `/` отвечает
`500` (оба маршрута висят на одной функции с обязательным доводом, и на `/` она
зовётся без него — замерено), `.woff2` уезжает как `text/html` (в `mimetypes`
машины его нет — замерено), а ручки обложки нет вовсе.

**Обложка мимо моста.** Результат вызова pywebview вклеивает в текст скрипта:
на каждый постер это сериализация, экранирование, склейка исходника и разбор
движком. Через `<img src="/poster?item=12">` браузер берёт картинку сам,
кеширует по `Cache-Control` и **сам же обрывает запрос**, когда карточка ушла из
разметки, — та самая отмена начатой загрузки, только без единой строки на
стороне страницы.

**Файлы:**
- Создать: `bridge/serve.py`
- Изменить: `.gitignore`
- Создать: `tests/bridge/test_serve.py`

**Интерфейсы:**
- Потребляет: `DEADLINE` из `bridge.thread`; `Source` из `backend.model`.
- Отдаёт: `Page(thread, root)` — WSGI-приложение (`__call__(environ,
  start_response)`), `WEB_ROOT`, `TYPES`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/bridge/test_serve.py`:

```python
"""Отдача страницы, ресурсов и обложек.

WSGI зовётся напрямую: сервер здесь не поднимается, окно не создаётся."""

from bridge.serve import Page

PNG = b"\x89PNG\r\n\x1a\nостальное"
JPEG = b"\xff\xd8\xff\xe0остальное"


def call(page, path, query=""):
    seen = {}

    def start(status, headers):
        seen["status"] = status
        seen["headers"] = dict(headers)

    body = b"".join(page({"PATH_INFO": path, "QUERY_STRING": query,
                          "REQUEST_METHOD": "GET"}, start))
    return seen["status"], seen["headers"], body


def test_the_root_gives_the_page(tmp_path, spy):
    """У сервера pywebview корень отвечает `500` — замерено. Свой обязан
    отдавать страницу."""
    (tmp_path / "index.html").write_bytes(b"<h1>тут</h1>")

    status, headers, body = call(Page(spy, tmp_path), "/")

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("text/html")
    assert body == b"<h1>тут</h1>"


def test_a_font_gets_its_own_type(tmp_path, spy):
    """В `mimetypes` этой машины `.woff2` нет, и файловый сервер библиотеки
    отдаёт его как `text/html` — замерено."""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "roboto.woff2").write_bytes(b"wOF2")

    _, headers, _ = call(Page(spy, tmp_path), "/assets/roboto.woff2")

    assert headers["Content-Type"] == "font/woff2"


def test_a_module_gets_the_script_type(tmp_path, spy):
    """Chromium не исполнит модуль с неверным типом, и страница останется
    пустой без единой ошибки."""
    (tmp_path / "app.js").write_bytes(b"export {}")

    _, headers, _ = call(Page(spy, tmp_path), "/app.js")

    assert headers["Content-Type"].startswith("text/javascript")


def test_a_way_out_of_the_root_is_refused(tmp_path, spy):
    """Отдаём только своё дерево, и проверка идёт по разрешённому пути, а не по
    строке: `..` внутри имени файла — законный символ."""
    (tmp_path.parent / "чужое.txt").write_bytes(b"секрет")

    status, _, _ = call(Page(spy, tmp_path), "/../чужое.txt")

    assert status.startswith("403")


def test_a_missing_file_is_not_found(tmp_path, spy):
    status, _, _ = call(Page(spy, tmp_path), "/нет.js")
    assert status.startswith("404")


def test_a_cover_of_a_library_card_is_taken_by_its_number(tmp_path, spy, asked):
    """Источник и адрес берёт сам обработчик: страница знает только `item_id`,
    и подсказке при вводе имени больше и не из чего исходить."""
    from backend.model import Item, Kind, Source
    from datetime import datetime
    answers, log = asked
    answers["library.get"] = Item(id=12, kind=Kind.MOVIE, source=Source.TMDB,
                                  source_id="1", title="Одиссея",
                                  synced_at=datetime(2026, 7, 31),
                                  poster_url="https://image/1.jpg")
    answers["posters.poster_for"] = PNG

    status, headers, body = call(Page(spy, tmp_path), "/poster", "item=12")

    assert status.startswith("200")
    assert headers["Content-Type"] == "image/png"
    assert body == PNG
    assert [name for name, _, _ in log] == ["library.get", "posters.poster_for"]


def test_a_cover_of_a_candidate_is_taken_by_its_address(tmp_path, spy, asked):
    """У кандидата нет `item_id` — он ещё не в базе, и сохранять обложку
    некуда."""
    answers, log = asked
    answers["posters.poster_for"] = JPEG

    status, headers, body = call(Page(spy, tmp_path), "/poster",
                                 "source=tmdb&url=https%3A%2F%2Fimage%2F1.jpg")

    assert status.startswith("200")
    assert headers["Content-Type"] == "image/jpeg"
    assert body == JPEG
    assert [name for name, _, _ in log] == ["posters.poster_for"]
    _, args, _ = log[0]
    assert args[0] is None


def test_a_cover_that_did_not_arrive_is_not_found(tmp_path, spy, asked):
    """Не приехала — на её месте заглушка, и делает её `onerror` у картинки, а
    не пустой ответ с кодом 200."""
    answers, _ = asked
    answers["posters.poster_for"] = None

    status, _, _ = call(Page(spy, tmp_path), "/poster",
                        "source=tmdb&url=https%3A%2F%2Fimage%2F1.jpg")

    assert status.startswith("404")


def test_a_refused_source_does_not_pretend_to_be_a_picture(tmp_path, spy, asked):
    """Отказ источника — не картинка: отдать его байтами значило бы нарисовать
    в карточке битый файл."""
    from backend.model import Reason, Refusal
    answers, _ = asked
    answers["posters.poster_for"] = Refusal(source="tmdb",
                                            reason=Reason.NETWORK)

    status, _, _ = call(Page(spy, tmp_path), "/poster",
                        "source=tmdb&url=https%3A%2F%2Fimage%2F1.jpg")

    assert status.startswith("404")


def test_a_cover_asked_without_anything_is_refused(tmp_path, spy, asked):
    status, _, _ = call(Page(spy, tmp_path), "/poster")
    assert status.startswith("400")
```

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_serve.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.serve'`.

- [x] **Шаг 3: Написать отдачу**

Создать `bridge/serve.py`:

```python
"""Страница, ресурсы и обложки по HTTP.

Своё, а не файловый сервер pywebview, по трём замеренным причинам: корень `/` у
него отвечает `500`, `.woff2` уезжает как `text/html`, а ручки обложки нет
вовсе. Сам сервер при этом поднимает pywebview: окну отдаётся WSGI-приложение,
и оно оказывается нашим."""

import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs

from backend.model import Source
from bridge.thread import DEADLINE

logger = logging.getLogger(__name__)

# `bridge/serve.py` лежит в `bridge/`, а собирает фронт Vite в `client/dist` —
# отсюда шаг наверх. План 10 заменит константу функцией: под `sys._MEIPASS`
# корень другой, но появляется он только при заморозке.
WEB_ROOT = Path(__file__).resolve().parent.parent / "client" / "dist"

# Тип объявляем сами: у `mimetypes` этой машины `.woff2` нет, и браузер получил
# бы `text/html`. Модуль с неверным типом Chromium не исполнит вовсе.
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
}

# Тип картинки берётся из первых байтов: хранилище держит только байты, а
# `Pillow` в клиент не пускает граница слоёв.
MAGIC = ((b"\x89PNG\r\n\x1a\n", "image/png"),
         (b"\xff\xd8\xff", "image/jpeg"),
         (b"RIFF", "image/webp"))


class Page:
    """Дерево отдаётся одно и целиком; всё, что не `/poster`, — это файл."""

    def __init__(self, thread, root: Path = WEB_ROOT) -> None:
        self._thread = thread
        self._root = Path(root).resolve()

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        if path == "/poster":
            return self._poster(parse_qs(environ.get("QUERY_STRING", "")),
                                start_response)
        return self._file(path, start_response)

    def _file(self, path: str, start_response):
        wanted = "index.html" if path == "/" else path.lstrip("/")
        # Проверка по разрешённому пути, а не по строке: `..` внутри имени файла
        # — законный символ, а вот выход за корень отдавать нельзя.
        resolved = (self._root / wanted).resolve()
        if not resolved.is_relative_to(self._root):
            return _answer(start_response, "403 Forbidden", "text/plain", b"")
        if not resolved.is_file():
            return _answer(start_response, "404 Not Found", "text/plain", b"")
        kind = TYPES.get(resolved.suffix, "application/octet-stream")
        return _answer(start_response, "200 OK", kind, resolved.read_bytes())

    def _poster(self, query: dict, start_response):
        item = _single(query, "item")
        source = _single(query, "source")
        url = _single(query, "url")
        if item is None and not (source and url):
            return _answer(start_response, "400 Bad Request", "text/plain", b"")

        try:
            picture = self._thread.run(
                lambda back: _fetched(back, item, source, url)).result(DEADLINE)
        except Exception:
            logger.exception("обложка не доехала")
            return _answer(start_response, "404 Not Found", "text/plain", b"")
        if not isinstance(picture, bytes | bytearray) or not picture:
            # Не приехала, отказал источник, пустые байты — на месте обложки
            # заглушка, и делает её `onerror` у картинки.
            return _answer(start_response, "404 Not Found", "text/plain", b"")
        # Обложка не меняется, пока карточку не перезалили, а прокрутка ленты
        # спрашивает одну и ту же по многу раз. Без этого каждая перерисовка
        # тащила бы все постеры заново — по потоку моста и чтению второго файла
        # базы на карточку.
        return _answer(start_response, "200 OK", _looks_like(picture), picture,
                       cache="max-age=86400")


async def _fetched(back, item, source, url):
    """У своей карточки источник и адрес берутся из неё самой: страница знает
    только номер, а подсказке при вводе имени больше и не из чего исходить.
    У кандидата номера нет вовсе — обложку тогда не сохраняем."""
    if item is None:
        return await back.posters.poster_for(None, Source(source), url,
                                             datetime.now())
    card = await back.library.get(int(item))
    if card is None:
        return None
    return await back.posters.poster_for(card.id, card.source,
                                         card.poster_url, datetime.now())


def _looks_like(picture: bytes) -> str:
    for magic, kind in MAGIC:
        if picture.startswith(magic):
            return kind
    return "application/octet-stream"


def _single(query: dict, name: str) -> str | None:
    values = query.get(name)
    return values[0] if values else None


def _answer(start_response, status: str, kind: str, body: bytes,
            cache: str | None = None):
    headers = [("Content-Type", kind), ("Content-Length", str(len(body)))]
    if cache:
        headers.append(("Cache-Control", cache))
    start_response(status, headers)
    return [body]
```

- [x] **Шаг 4: Закрыть сборку фронта от git**

Проверить `.gitignore`: строка `dist/` там уже есть и закрывает `client/dist`
на любой глубине — дописывать нечего. Убедиться заодно, что `*.spec` не
помешает плану 10: файл сборки PyInstaller туда попадает.

- [x] **Шаг 5: Прогнать и увидеть зелёное**

Запустить: `pipenv run pytest tests/bridge/test_serve.py -v`
Ожидание: PASS, 10 тестов.

- [x] **Шаг 6: Коммит**

```bash
git add bridge/serve.py tests/bridge/test_serve.py .gitignore
git commit -m "feat: своя отдача страницы, ресурсов и обложек"
```

---

### Задача 12: Окно и сборка приложения

Последняя задача плана: окно поднимается, мост в нём работает, лог пишется рядом
с программой.

**Рендерер проверяется после старта.** Отсутствие среды WebView2 роняет окно не в
ошибку, а в тихий откат на MSHTML, где половина оформления не работает вовсе.
Молчание тут хуже отказа — ровно та беда, из-за которой отброшен Qt.

**Проверка отделена от показа.** Решение «этот рендерер годится» — чистая
функция от имени, и проверяется она обычным тестом; поднимать окно ради этого не
нужно и нельзя.

**Файлы:**
- Создать: `bridge/window.py`, `main.py`
- Создать: `tests/bridge/test_window.py`

**Интерфейсы:**
- Потребляет: `Api`, `Page`, `BackendThread`.
- Отдаёт: `open_window(thread, debug=False)`, `supported(renderer) -> bool`,
  `RENDERER`, `MIN_WIDTH`.

- [x] **Шаг 1: Написать падающий тест**

Создать `tests/bridge/test_window.py`:

```python
"""Решение по рендереру. Окно здесь не поднимается ни разу."""

from bridge.window import supported


def test_the_system_chromium_is_what_we_drew_the_mockup_in():
    assert supported("edgechromium")


def test_the_old_engine_is_not_silently_accepted():
    """Нет среды WebView2 — pywebview молча уезжает на MSHTML, и приложение
    просто выглядит сломанным. Молчание тут хуже отказа."""
    assert not supported("mshtml")


def test_an_unknown_engine_is_not_accepted():
    """Список разрешённого, а не список запрещённого: седьмой движок обязан
    упереться в проверку, а не проскочить."""
    assert not supported("qtwebengine")
    assert not supported(None)
```

- [x] **Шаг 2: Прогнать и увидеть красное**

Запустить: `pipenv run pytest tests/bridge/test_window.py -v`
Ожидание: FAIL, `ModuleNotFoundError: No module named 'bridge.window'`.

- [x] **Шаг 3: Написать окно**

Создать `bridge/window.py`:

```python
"""Окно приложения и проверка того, чем оно рисует."""

import logging

import webview

from bridge.api import Api
from bridge.serve import Page

logger = logging.getLogger(__name__)

TITLE = "Personal Rating"

# Системный WebView2 — тот самый Chromium, в котором рисовался макет. Список
# разрешённого, а не запрещённого: седьмой движок обязан упереться в проверку.
RENDERER = "edgechromium"

# Ширина шапки — минимум окна; максимум не ограничен. Число уточняется в плане 6,
# когда шапка появится и её ширину станет чем замерить.
MIN_WIDTH = 900
MIN_HEIGHT = 600

# Стартовый размер задан явно: умолчание `create_window` — 800×600, то есть
# меньше собственного минимума, и окно открывалось бы уже подтянутым.
WIDTH = 1280
HEIGHT = 820


def supported(renderer: str | None) -> bool:
    return renderer == RENDERER


def open_window(thread, debug: bool = False) -> None:
    """Возвращается только после закрытия окна: `webview.start` блокирует."""
    window = webview.create_window(
        TITLE,
        url=Page(thread),
        js_api=Api(thread),
        width=WIDTH,
        height=HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        background_color="#0d0d0d",
    )
    webview.start(func=_check_renderer, debug=debug)
    # Окно закрыли — гасим начатое и закрываем бэкенд. Отдельного флага
    # «мы закрываемся» не заводим: список живых задач ведёт поток.
    thread.close()
    del window


def _check_renderer() -> None:
    """Зовётся фоновой функцией: к этому моменту библиотека уже выбрала движок."""
    if not supported(webview.renderer):
        logger.critical(
            "окно рисует %s вместо %s: среда WebView2 не установлена, и "
            "оформление работать не будет", webview.renderer, RENDERER)
```

Цвет фона `#0d0d0d` — это цвет до отрисовки страницы, и он обязан совпасть с
`--bg` из палитры, когда та появится в плане 6. Пока стоит значение из макета;
сверить и поправить там же.

- [x] **Шаг 4: Написать сборку**

Создать `main.py`:

```python
"""Собирает зависимости, настраивает лог и поднимает окно."""

import logging
import logging.handlers
import os
from pathlib import Path

from dotenv import load_dotenv

from backend.app import build_backend
from backend.config import load_config
from bridge.thread import BackendThread
from bridge.window import open_window

BASE_DIR = Path(__file__).resolve().parent

# Лог лежит рядом с программой и не растёт бесконечно.
LOG_BYTES = 5 * 1024 * 1024
LOG_FILES = 3


def setup_logging(config) -> None:
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.handlers.RotatingFileHandler(
                config.log_file, maxBytes=LOG_BYTES, backupCount=LOG_FILES,
                encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    load_dotenv()
    config = load_config(os.environ, BASE_DIR)
    setup_logging(config)

    # Сборка уезжает функцией: бэкенд обязан родиться внутри чужого потока —
    # движок SQLAlchemy привязан к циклу, в котором создан, — а импортировать
    # `backend.app` из `bridge/` нельзя: там стоит сторож границы слоёв, и с
    # ним приехали бы и SQLAlchemy, и httpx в поток интерфейса.
    thread = BackendThread(lambda: build_backend(config))
    thread.start()
    open_window(thread, debug=bool(os.environ.get("PR_DEBUG")))


if __name__ == "__main__":
    main()
```

- [x] **Шаг 5: Прогнать весь набор**

Запустить: `pipenv run pytest`
Ожидание: зелено. `tests/backend/test_layers.py` обязан пройти: `main.py` не
входит ни в `backend`, ни в `bridge`, и именно поэтому он и есть то место, где
две половины встречаются.

- [x] **Шаг 6: Проверить руками**

Заглушка страницы кладётся в `client/dist/index.html` и в репозиторий не
попадает (папка закрыта `.gitignore`); план 6 заменит её сборкой Vite.

```html
<h1>Personal Rating</h1>
<pre id="out">жду мост…</pre>
<script>
  window.addEventListener('pywebviewready', async () => {
    const answer = await window.pywebview.api.refs.genres('film')
    document.getElementById('out').textContent = JSON.stringify(answer, null, 2)
  })
</script>
```

Запустить:

```powershell
pipenv run alembic upgrade head
pipenv run python main.py
```

Ожидание: окно открывается, в нём список жанров кино из базы. В `data/app.log`
нет записи про рендерер — значит рисует `edgechromium`. Закрытие окна не оставляет
висящего процесса.

Заглушку после проверки удалить.

- [x] **Шаг 7: Коммит**

```bash
git add bridge/window.py main.py tests/bridge/test_window.py
git commit -m "feat: окно приложения, сборка и лог"
```

---

## Самопроверка плана

Пройдено по спекам после написания.

**Покрытие спеки клиента.** Раздел «Мост» — задачи 3–10 целиком: шесть доменов
разложены по семи модулям (решение 1), одна дверь, только запрос-ответ,
номер операции (решение 2), пять родов непролезающих значений, время от
моста, один формат отказа операции, отказ источника полем. Раздел «Обложки мимо
моста» — задача 11, вместе с типом для `.woff2`. Раздел «Что проверяется» —
питоновская половина здесь вся; состояние и компоненты живут в плане 6.
Раздел «Сборка и поставка» — здесь только отдача по HTTP и окно с системной
рамкой; `sys._MEIPASS` и один `.exe` — план 10, и раньше времени они были бы
веткой без сегодняшнего потребителя.

**Что этот план сознательно не делает.** Нет ни одной строки фронта. Нет
`sys._MEIPASS`. Нет ширины окна по замеру шапки — замерять пока нечего. Нет
`enricher.enrich` для кандидатов (расхождение 5) и нет `genres.set_for_item`,
`people.attach`, `people.ensure`: состав ручной карточки пишется в плане 9, и
операции моста под него заводятся там же, с потребителем на том же слайсе.

Нет `Search.by_person` и нет `Refs.items_of`. Первый заводит план 11 вместе со
своим потребителем — щелчком по имени в карточке; второй не заводится вовсе,
потому что после этого у него не осталось бы потребителя ни одного.

**Чем измеряется готовность.** Весь набор зелёный; окно открывается и показывает
ответ бэкенда; сторож поверхности моста сходится с бэкендом именами и
сигнатурами; сторож границы
слоёв зелёный обеими половинами впервые с 31.07.2026.
