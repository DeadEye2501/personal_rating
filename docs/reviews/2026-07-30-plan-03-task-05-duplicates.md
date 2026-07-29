# Ревью: повторы во всём проекте — задача 5 плана 3 (`backend/service/images.py`)

Дата: 2026-07-30. Измерение: повторы (весь проект, не диф).

## Порядок работы

1. Прочитан целиком `docs/module-map.md` и `docs/data-map.md`.
2. Прочитан `docs/not-duplicates.md` — разобранные пары не пересматривались.
3. Собраны кандидаты на повтор для нового кода: `backend/service/images.py`
   (`BadImage`, `_centred_box`, `crop_to_cover`, `TARGET_RATIO`, `TARGET_SIZE`,
   `_QUALITY`) и `tests/backend/test_images.py` (`picture`, `painted`,
   `size_of`, `red_box`).
4. Каждый кандидат проверен чтением обоих мест.

## Находки

Нет ни одной. Ниже — что проверялось и почему не подтвердилось.

## Разобрано и признано разным

- `backend/service/images.py:BadImage` ≠ `backend/storage/repository/library.py:ItemExists`,
  `backend/storage/repository/credits.py:IdentityTaken`,
  `backend/storage/repository/external.py:ExternalIdTaken`,
  `backend/storage/repository/tags.py:WrongTagKind`/`TagExists`,
  `backend/sources/tmdb/parse.py:Incomplete` — все пустые наследники
  `Exception` с разными докстринами. Это уже установленный в проекте идиом
  (три пары этого рода зафиксированы в `docs/not-duplicates.md`), и `BadImage`
  ему следует, а не повторяет конкретный код: тело пустое, различение — в
  докстринге и в том, где ловится исключение. Слить не с чем — общей логики
  нет ни строки.

- `backend/service/images.py:crop_to_cover` (обёртка `except (...) as error:
  raise BadImage(...) from error`) ≠ `backend/sources/errors.py:broken` —
  оба переводят пойманное исключение в свой тип отказа, но `broken` строит
  `Refusal` (датакласс со `source`/`reason`/`detail`) для протокола
  источников (`Outcome`), а `crop_to_cover` поднимает обычное исключение
  `BadImage`, потому что сервис картинок не участвует в протоколе
  «находка / честное отсутствие / отказ» источников — это другой слой с
  другим контрактом ошибок. Общего кода — только сама идиома
  try/except/raise-from, которая короче пяти строк с обеих сторон.

- `backend/service/images.py:crop_to_cover` ≠
  `backend/storage/repository/base.py:Repository._created`/`_written` —
  тоже «поймать и перевести в своё исключение», но `_created`/`_written`
  переводят `IntegrityError` СУБД в доменное исключение репозитория, а
  `crop_to_cover` — ошибку разбора байтов Pillow. Разные исключения, разный
  повод, разные типы результата. Уже разведено между собой в
  `docs/not-duplicates.md`; новый файл добавляет третью сторону того же по
  форме идиома, не более того.

- `backend/service/images.py:TARGET_SIZE` (комментарий ссылается на
  `w500` TMDB) ≠ `backend/sources/tmdb/parse.py:POSTER_BASE` (строка
  `'https://image.tmdb.org/t/p/w500'`) — это не общая константа, а
  объяснение в комментарии, откуда взято число `(500, 750)`. Оба места не
  используют значение друг друга: `POSTER_BASE` — часть URL, `TARGET_SIZE` —
  пиксельный размер результата обрезки. Нечего выносить.

- `tests/backend/test_images.py:picture` (генерирует настоящую картинку через
  `PIL.Image.new(...).save(...)`) ≠ `tests/conftest.py:PICTURE` (константа
  `b"\x89PNG\r\n\x1a\n" + b"0" * 512` — заголовок PNG плюс мусор, не
  декодируется как картинка) — совпадает только то, что оба про «байты
  постера». `PICTURE` нужен тестам хранилища (`test_posters.py`) для
  побайтовой идентичности при записи/чтении, реальное содержимое неважно.
  `picture()` нужен тестам обрезки, где `crop_to_cover` реально открывает
  файл через Pillow и требует валидного изображения. `PICTURE`, пропущенный
  через `crop_to_cover`, упал бы `BadImage`. Слить нельзя — они об одном
  предмете, но с несовместимыми требованиями к содержимому.

- `tests/backend/test_images.py:size_of`/`red_box` — за пределами этого
  файла нигде в тестах не разбирают PNG/JPEG через Pillow, дублировать не с
  чем; это первое появление настоящей работы с изображениями в тестах.

## Вердикт

Коммитить можно как есть. Новый файл — первое появление зависимости от
Pillow в проекте, обособленная ответственность (`backend/service/images.py`
рядом с существующим `backend/service/`… единственным модулем в пакете),
повторов ни с существующим кодом, ни внутри самого слайса не найдено. В
`docs/not-duplicates.md` новых записей не требуется — все проверенные пары
подпадают под уже установленные в файле основания («один глагол/идиом над
разными предметами», «пустые исключения различаются докстрингом»), а не
заводят новый прецедент.
