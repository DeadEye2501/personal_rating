# Ревью: повторы во всём проекте — задача 6 плана 3 (`backend/service/posters.py`)

Дата: 2026-07-30. Измерение: повторы (весь проект, не дифф).

## Порядок работы

1. Прочитан целиком `docs/module-map.md` и `docs/data-map.md`.
2. Прочитан `docs/not-duplicates.md` — разобранные пары не пересматривались.
3. Собраны кандидаты на повтор для нового кода: `backend/service/posters.py`
   (`PosterService` целиком — `fetch`, `_picture`, `_refuse`, `save`,
   `store_upload`, `aclose`, `_SIGNATURES`), `tests/backend/test_poster_service.py`,
   переехавший в `tests/conftest.py` помощник `picture`, новый параметр
   `content` у `responding` в `tests/backend/sources/conftest.py`.
4. Каждый кандидат проверен чтением обоих мест, с особым вниманием к тому,
   что назвал постановщик: `backend/sources/undocumented.py`,
   `backend/sources/tmdb/client.py:classify`, `backend/sources/registry.py`,
   клиенты источников (`_get`/`card`), `backend/storage/posters.py:PosterStore.put`,
   закрытие клиентов в `Sources.aclose`.

## Находки

Нет ни одной.

## Разобрано и признано разным

- `backend/service/posters.py:PosterService.fetch`/`_picture` ≠
  `backend/sources/undocumented.py:refuse_undocumented` — обе смотрят на код
  ответа и решают, отказ это или нет, но по разным основаниям и с разным
  результатом. `refuse_undocumented` знает только один частный случай (429) и
  взводит предохранитель через `UNDOCUMENTED_BACKOFF`; `_picture` вообще не
  различает коды между собой — любой код, кроме 200, уходит одним и тем же
  `Reason.BROKEN` без взведения предохранителя, и добавляет проверку, которой
  у `refuse_undocumented` нет вовсе — подпись формата картинки в теле. Отказ
  картинки идёт через её собственный `_refuse`, а не через чужую функцию,
  потому что CDN-клиенты (`clients: Mapping[Source, SourceHttp]`) — это не те
  же соединения, что у клиентов источников в `Sources`: `PosterService`
  заводит их отдельно (`SourceHttp(f"cdn:{source}", ...)` в тестах и в плане
  `docs/plans/2026-07-27-card-writing.md:1810`), по одному на CDN, чтобы
  молчание обложек одного магазина не гасило карточки. Слить было бы нечего
  переиспользовать: тело `_picture` короче, чем было бы обращение к чужой
  функции с подгонкой под её контракт.

- `backend/service/posters.py:PosterService._picture` ≠
  `backend/sources/tmdb/client.py:classify` — обе начинаются с «код не 200 —
  разбираемся», но `classify` читает JSON-тело и пять кодов TMDB (404 с
  конкретным `status_code`, 429, 401, иначе `BROKEN`), а `_picture` тело как
  JSON не читает вовсе — оно бинарное, и единственная проверка содержимого
  это первые байты на соответствие подписи формата картинки. Общей логики
  классификации нет: разные входные данные (текст против байт) и разные
  критерии.

- `backend/service/posters.py:PosterService.fetch`/`_picture` ≠
  `backend/sources/gog/client.py:GogClient._catalog`,
  `backend/sources/steam/client.py:SteamClient.search`/`card` — форма запроса
  («получить ответ → если не `httpx.Response`, вернуть как есть → если код не
  200, отказ → иначе разобрать») совпадает, но это уже установленный в
  проекте идиом, зафиксированный в `docs/not-duplicates.md` («идиома
  повторяется в десяти местах восьми файлов, и это осознанно... вынести
  можно было бы только вместе с самим `SourceHttp.get`»). `PosterService`
  добавляет в проект одиннадцатое место того же идиома, а не новый повтор:
  довод не изменился.

- `backend/service/posters.py:PosterService.aclose` ≠
  `backend/sources/registry.py:Sources.aclose` — обе гоняют цикл
  `for x in ...: await x.aclose()`, но над разными коллекциями с разным
  происхождением: `Sources.connections` — все `SourceHttp` клиентов
  источников, поднятые в `build_sources`; `PosterService.clients` — свой,
  отдельно заведённый набор `SourceHttp` для CDN обложек (см. пункт про
  `fetch` выше). Тело — два слова поверх стандартного `for`, короче порога,
  ниже которого вынос ничего не сберегает.

- `backend/service/posters.py:PosterService.save`/`store_upload` ≠
  `backend/storage/posters.py:PosterStore.put` — `save`/`store_upload` не
  переопределяют запись, они делегируют её: `save` вызывает `store.put(...)`
  без изменений, `store_upload` — то же самое, но пропустив данные через
  `crop_to_cover` сперва. Вся SQL-логика (`upserting`, единственный `put`)
  живёт только в `PosterStore.put`; `PosterService` её не повторяет, а
  оборачивает решением «что записывать» — сырые байты или обрезанные.

- `backend/service/posters.py:PosterService._refuse` ≠
  `backend/sources/errors.py:broken` — обе строят `Refusal` с
  `reason=Reason.BROKEN`, но `broken(source, error)` принимает исключение и
  форматирует `detail` через `str(error)`, а `_refuse(self, source, detail)`
  принимает уже готовую строку и добавляет префикс `poster:` к источнику —
  различение отказа обложки от отказа самой карточки того же источника.
  Слить нельзя без искусственной обёртки строки в исключение с одной
  стороны или без потери префикса с другой; тело обеих — одна инструкция
  создания датакласса, ниже порога, где вынос себя оправдывает.

- `tests/backend/sources/conftest.py:responding` (новый параметр `content`)
  ≠ `tests/conftest.py:picture` — не о том же: `responding` строит
  HTTP-транспорт с заданным телом ответа (JSON, текст или байты), `picture`
  рисует настоящую картинку через Pillow. `test_poster_service.py`
  использует оба вместе (`responding(content=POSTER)`, `POSTER = picture(...)`),
  но это композиция двух разных помощников, а не повтор одного в другом.

- `tests/conftest.py:picture` (переехавший помощник) ≠
  `tests/backend/test_images.py:painted`/`size_of`/`red_box` — те остались на
  месте и делают другое: рисуют картинку с цветной полосой для проверки
  границ обрезки и читают размер/цвет результата. Переезд `picture` не
  затронул это разделение, которое уже разобрано в отчёте задачи 5
  (`docs/reviews/2026-07-30-plan-03-task-05-duplicates.md`).

## Вердикт

Коммитить можно как есть. `PosterService` — обёртка над уже существующими
частями (`SourceHttp.get`, `crop_to_cover`, `PosterStore.put`) с собственной,
не повторяющей их классификацией отказа обложки; ни один из шести
подозреваемых из задания (`undocumented.py`, `tmdb/client.py:classify`,
`registry.py`, клиентские `_get`/`card`, `PosterStore.put`, закрытие клиентов
в реестре) не разобран настоящим повтором. Новых записей в
`docs/not-duplicates.md` не требуется: все разобранные пары либо подпадают
под уже установленные в файле основания (идиом «ответ или отказ» в клиентах
источников), либо ниже порога, где машинная проверка вообще смотрит на тело
(конструкция датакласса в одну строку, `for`-цикл закрытия).
