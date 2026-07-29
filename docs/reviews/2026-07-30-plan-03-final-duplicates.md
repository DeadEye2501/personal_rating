# Итоговое ревью плана 3 — повторы во всём проекте

Измерение: повторы, которые не видит машинная проверка (сравнивает только
записываемый файл) — между двумя файлами, которых один слайс не касался, тела
короче пяти инструкций, повторы внутри одного тела.

Порядок: `docs/module-map.md` и `docs/data-map.md` прочитаны целиком,
`docs/not-duplicates.md` — целиком, с выборочной проверкой части вердиктов.
Кандидаты собирались по новым модулям плана 3 (`backend/service/cards.py`,
`card_parts.py`, `linking.py`, `genres.py`, `images.py`, `posters.py`,
`backend/model/link.py`, `backend/storage/repository/credits.py`,
`external.py`) против всего остального кода — репозиториев и клиентов
источников из планов 1–2, а не только между собой.

## Находки

Ни одной. Кандидатов, прошедших первый отбор по картам, при чтении обоих мест
не подтвердился ни один.

Разобранные и отклонённые кандидаты (не пошли в отчёт, потому что при чтении
кода расхождение оказалось содержательным, а не только именным):

- `backend/service/card_parts.py:CardParts._attach_credits` и
  `backend/service/linking.py:Linker._fill` — общий шаг `_attach_credits` уже
  вынесен в `CardParts` и оба наследника (`CardWriter`, `Linker`) его
  переиспользуют; `_fill` вокруг него — своя логика привязки: guard на «уже
  заполнено», `detach_all` при перезаписи. Не повтор, ровно то переиспользование,
  которое и предполагает `CardParts`.
- `backend/service/cards.py:CardWriter._write_the_rest` и
  `backend/service/linking.py:Linker.link` — уже разобрано и записано в
  `not-duplicates.md` (`CardWriter` ≠ `Linker`), сверено при чтении кода:
  довод держится, оба используют общее из `CardParts` и `resolved_genres`, а
  расходятся по смыслу (запись с нуля и откатом против слияния существующего).
- `backend/service/posters.py:PosterService` и `backend/storage/posters.py:PosterStore` —
  разные уровни: первый ходит в сеть и проверяет магическими байтами, что
  пришла картинка, второй кладёт готовые байты во второй файл базы. Общего
  кода нет, только оба слова «poster» в имени.
- `backend/storage/repository/credits.py:CreditRepository._hint` (три ступени
  подсказки: оценка → закладка → любая карточка) — паттерн «попробовать по
  очереди», внешне похожий на приоритет зеркал Кинопоиска
  (`backend/sources/ratings/kinopoisk/client.py`), но общего кода не делят:
  один строит `Select` по трём таблицам своей базы, другой ходит по сети в два
  разных API. Не повтор, только сходство идеи.
- `backend/model/item.py:new_manual_item`/`new_source_id` и
  `backend/storage/repository/credits.py:CreditRepository.create_manual` —
  второй переиспользует `new_source_id()` напрямую, а не копирует его; общей
  логики за пределами вызова нет.
- Тестовые билдеры-умолчания: `tests/backend/test_card_writer.py:source_card`,
  `game_card`, `another_movie` против `tests/backend/test_linking.py:incoming`,
  `mine` — те же по приёму «умолчания плюс `overrides`», что уже разобраны в
  `not-duplicates.md` для `make_item`/`card`; при чтении кода видно тот же
  повод (разные наборы полей под разные проверки), довод переносится без
  изменений.
- `tests/backend/test_credits.py` и `tests/backend/test_suggestions.py` — оба
  об одном репозитории (`CreditRepository`), но не пересекаются по
  ответственности: первый гоняет `create`/`find_by_*`/`ensure`/`attach`,
  второй — только `suggest`/`_hint` через свой локальный `person_with`.
  Общих тестовых сценариев нет.

## Выборочная проверка старых вердиктов

Три вердикта из `docs/not-duplicates.md`, не относящихся к плану 3 напрямую,
перепроверены чтением обеих сторон заново:

1. `backend/sources/tmdb/client.py:TmdbClient.search` ≠
   `backend/sources/tmdb/parse.py:parse_search` — подтверждено: `search`
   ветвится по `kind is Kind.SERIES`, чтобы выбрать путь запроса (`/search/tv`
   против `/search/movie`), `parse_search` — чтобы выбрать поля в чужом теле
   ответа. Файлы плана 3 не касались, тела не изменились, довод держится.
2. `backend/storage/repository/credits.py:CreditRepository.find_by_source` ≠
   `backend/storage/repository/library.py:LibraryRepository.find_by_source` —
   подтверждено чтением обоих файлов целиком: первый отдаёт `int | None`
   (номер строки), второй — собранный `Item` со всеми тринадцатью полями.
   Общее — только идиома `_maybe`/`_one` из `Repository`.
3. `backend/service/cards.py:CardWriter` ≠ `backend/service/linking.py:Linker` —
   подтверждено, см. выше.

Расхождений не найдено, отпечатки актуальны.

## Вердикт

Дублей, требующих переноса кода, в плане 3 нет. Слой записи (`CardParts` как
общая основа `CardWriter` и `Linker`, `resolved_genres` как общая точка
разрешения жанров) уже вынесен туда, где нужен второй реализации, а внешне
похожие места (постеры сервиса и хранилища, три ступени подсказки и
приоритет зеркал, тестовые билдеры) при чтении кода расходятся по существу.
Мера соблюдена.
