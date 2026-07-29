# Ревью повторов — план 3, задача 8 (`backend/model/link.py`)

Дата 2026-07-30. Изменение: `backend/model/link.py` (`ExternalLink`,
`parse_link`), `tests/backend/test_links.py`, реэкспорт в
`backend/model/__init__.py`. Разобрано против `docs/module-map.md` и
`docs/data-map.md` целиком, диффа не читал.

## Находки

Не найдено ни одной.

## Разобрано и признано разным

- `backend/model/link.py:ExternalLink` ↔ `backend/model/external.py:ExternalId`
  — форма похожа (`source` + идентификатор), но это разные пространства
  источника и разные роли. `ExternalLink.source: Source` — тот же тип, что
  у `Item.source`: чем главный источник карточки её знает (`manual`, `tmdb`,
  `steam`, `gog`), результат вставки ссылки идёт в `LibraryRepository.link`,
  который принимает ровно `(item_id, source: Source, source_id: str, now)`
  (`backend/storage/repository/library.py:154`). `ExternalId.source: IdSource`
  — чем карточку знают источники, которые не являются главным (`imdb`,
  `kinopoisk`, `steam`, `gog`), и пишется через
  `ExternalIdsRepository.put`. Пересечение по членам (`steam`, `gog`) —
  следствие того, что оба перечисления описывают одни магазины, а не признак
  общей сущности: `Source` без `imdb`/`kinopoisk`, `IdSource` без `tmdb`/
  `manual`. Слитый тип потребовал бы объединить два разных перечисления и
  разошёлся бы с сигнатурой `link()`, которая уже принимает `Source`.
- `backend/model/link.py:parse_link` ↔ `backend/sources/*/client.py` (TMDB,
  Steam, GOG) — все шесть клиентов строят или разбирают идентификаторы, но
  `parse_link` — единственное место, где источник текста не структурированный
  ответ API, а произвольная строка, вставленная человеком: URL с хвостами,
  параметрами, необязательными сегментами языка и разным регистром домена.
  Клиенты источников работают с путём запроса и телом JSON и такой разбор не
  делают нигде. Общих регулярных выражений или таблиц «домен → источник» в
  `backend/sources/` нет — проверено `grep` по `steampowered.com`, `gog.com`,
  `themoviedb.org` и по `re.compile` во всём `backend/sources/`.
- `backend/model/link.py:_TMDB_KINDS` (`"movie"/"tv" → Kind`) ↔
  `backend/sources/tmdb/client.py` (`Kind.MOVIE: "credits"`,
  `Kind.SERIES: "aggregate_credits,external_ids"`) — обе таблицы одного вида
  «`Kind` на одной стороне», но направление и содержание противоположны:
  клиент превращает уже известный `Kind` в параметр запроса, `_TMDB_KINDS`
  превращает сегмент чужого URL в `Kind`. Общей таблицы «строка → `Kind`»
  в `backend/sources/tmdb/parse.py` нет: там `Kind.SERIES` — сравнение, а
  не поиск по словарю.
- `backend/model/link.py:_BARE` (`^\d+$`, признак голого TMDB id) ↔
  `backend/sources/convert.py:year` (`head.isdigit()` на первых четырёх
  символах даты) — обе проверяют цифры, но одна проверяет всю строку целиком
  как идентификатор, другая — префикс строки-даты как год; предмет и
  предикат разные, ничего общего вынести не получится без потери смысла.
  Уже описанная в `docs/not-duplicates.md` пара `convert.year` ↔
  `steam/parse.py:_year` этого не покрывает, но довод тот же по духу и
  здесь не задета: `_year` работает с человеческой датой, `_BARE` — с
  идентификатором.

## Вердикт

Повторов не найдено. `parse_link`/`ExternalLink` — новая, единственная в
проекте функциональность разбора вставленной пользователем ссылки; ни один
из шести клиентов источников, ни `ExternalId`/`SearchHit`/`Item` её не
дублируют и не годятся на замену.
