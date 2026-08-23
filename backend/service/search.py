"""Что найдётся по запросу."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from backend.model import (
    SEARCH_SIZE,
    CardView,
    ExternalSearch,
    Found,
    IdSource,
    Kind,
    Outcome,
    SearchHit,
)
from backend.service.asking import answered_all
from backend.service.filmography import Filmographies
from backend.service.hits import once, split, to_views, without_removed
from backend.service.merging import merged
from backend.service.relevance import relevant
from backend.sources.registry import Sources
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.removed import RemovedRepository
from backend.storage.repository.views import ViewsRepository
from backend.unique import unique_by

# Слова, которыми вместо выдачи просят список убранного. Список закрытый и
# выбран пользователем 03.08.2026 из двух: широкое правило «всякое слово на
# удал» пересеклось бы с настоящими названиями, и человек, ищущий такую игру,
# получил бы вместо неё список.
#
# `ё` тут уже сведена к `е`: «удалённые» и «удаленные» человек пишет и так,
# и так, а буквы это разные.
COMMANDS = frozenset({"удалено", "удаленное", "удаленный", "удаленные",
                      "deleted", "removed"})


def _asks_for_removed(query: str) -> bool:
    """Спросили ли список убранного.

    Сравнивается **вся строка целиком**, а не вхождение слова: иначе игра, у
    которой в названии стоит `deleted`, перестала бы искаться вовсе — тихо, без
    следа.

    Приведение здесь своё, а не общее `flattened`, и это не небрежность.
    Общее сделано для **названий**: оно выбрасывает артикли где угодно, и через
    него командой становилось `the deleted` — то есть сериал «The Deleted» 2016
    года не находился бы никогда. Команда — не название, ей нужны только регистр,
    края строки и `ё`, которую человек пишет и так, и так."""
    return query.strip().lower().replace("ё", "е") in COMMANDS


def _has_more(clients: list, outcomes: list[Outcome]) -> bool:
    """Есть ли, что догружать.

    Полная порция — единственный признак, который у источников есть: `totalItems`
    у Google всегда `300` и врёт, а у выдачи Steam числа нет вовсе. Считается по
    сырой выдаче, до всякой чистки: из двадцати строк отсев нерелевантного,
    снятие убранного и склейка изданий оставляют меньше, и короткая порция после
    них означает «почистили», а не «кончилось».

    Нелистающий источник «ещё» не обещает никогда, даже отдав полную порцию:
    второй порции у него не бывает, и лента сходила бы за заведомо пустой
    выдачей на каждый поиск игры."""
    return any(client.PAGES and isinstance(outcome, Found)
               and len(outcome.value) >= SEARCH_SIZE
               for client, outcome in zip(clients, outcomes, strict=True))


def _albums(answers: list[list[SearchHit]]) -> list[list[SearchHit]]:
    """Выдачи без синглов — решение пользователя 23.08.2026.

    Приложение оценивает альбомы, и сингл в нём не строка выдачи, а мусор:
    непоказанный, он всё равно доехал бы до заведения карточки. Замерено в тот
    же день: по «дельфин» из двадцати строк семь помечены синглом.

    Здесь, а не в разборе строки: полнота порции считается по сырому ответу
    источника, и укоротивший её отсев объявил бы двадцатую строку последней.
    Обе половины выдачи, а не только каталог: альбомы исполнителя приезжают тем
    же разбором, и синглов у него не меньше."""
    return [[one for one in answer if not one.single] for answer in answers]


def _isbn_of(hit: SearchHit) -> str:
    """ISBN строки, если источник его дал. У сканов и журналов его нет вовсе."""
    return next((one.value for one in hit.external_ids
                 if one.source is IdSource.ISBN), "")


def _weave(answers: list[list[SearchHit]]) -> list[SearchHit]:
    """Несколько выдач — вперемешку, по одному кандидату по кругу.

    Выдач бывает две по двум разным причинам. У игр это два магазина, и склеить
    их подряд нельзя: поиск GOG никогда не отвечает «не найдено» и на
    бессмыслицу отдаёт два десятка несвязанных игр — подряд это значит, что
    вторая половина страницы всегда мусор GOG, а настоящие его находки
    начинаются там, куда никто не доскроллит. У кино источник один, но половины
    у строки две — названия и работы найденных людей, — и подряд фильмография
    одного актёра вытеснила бы за экран всё найденное по названию.

    Порядок внутри каждой выдачи сохраняется: он задан источником."""
    woven = []
    for position in range(max((len(answer) for answer in answers), default=0)):
        for answer in answers:
            if position < len(answer):
                woven.append(answer[position])
    return woven


@dataclass(frozen=True, slots=True)
class SearchParts:
    """Хранилища, которые нужны внешней выдаче.

    Заведено потому, что доводов у сборщика стало шесть: справочник разворачивает
    метки кандидата, память об убранном отсеивает то, что человек уже удалил.

    С `CardParts` записи карточки роднит только повод — предел на число доводов.
    Тот держит общее поведение двух наследников, этот не держит ничего: просто
    два поля, которые нужны обеим сборкам внешней выдачи."""

    genres: GenresRepository
    removed: RemovedRepository


class SearchService:
    """Поиск идёт сразу по двум местам, и метод у каждого свой: своё отдаётся
    первым и работает без сети, внешнее доливается по готовности."""

    def __init__(self, library: LibraryRepository, views: ViewsRepository,
                 sources: Sources, parts: SearchParts,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._library = library
        self._views = views
        self._sources = sources
        self._works = Filmographies(sources)
        self._genres = parts.genres
        self._removed = parts.removed
        # Часы внедряются, как во всех записях проекта: отметка бесплатной оценки
        # кандидата в базу не попадает, но брать время изнутри — путь к тому, что
        # однажды попадёт и проверить это будет нечем.
        self._clock = clock

    async def local(self, kind: Kind, query: str) -> list[CardView]:
        """Своя половина на команду молчит: список убранного показывается один
        раз, и приезжает он второй половиной. Иначе он мелькнул бы сперва
        обычными карточками — кнопки `restore` у них нет."""
        if _asks_for_removed(query):
            return []
        item_ids = await self._library.search(kind, query, limit=SEARCH_SIZE)
        return await self._views.in_order(item_ids)

    async def external(self, kind: Kind, query: str,
                       offset: int = 0) -> ExternalSearch:
        """Строка ищет и по названию, и по имени человека — всегда, а не «если
        названием ничего не нашлось»: решение пользователя 01.08.2026.

        Смещение — вторая и следующие порции, которые просит прокрутка. Со
        смещением спрашиваются только те, кто листать умеет: у остальных второй
        порции не бывает вовсе, и запрос к ним ушёл бы впустую.

        Обе половины уходят разом: сроки ожидания у них свои, и спроси их по
        очереди — выдача ждала бы их сумму. У игр в первой половине два
        магазина, и отказ одного не скрывает ответ другого.

        Команда перехватывает раньше всего: спрашивать магазины про слово
        «удалённые» незачем, а ждать их отказа человек будет секундами."""
        if _asks_for_removed(query):
            gone = await self._removed.listing(kind)
            return ExternalSearch(views=tuple(gone), refusals=(), removed=True)
        clients = [one for one in self._sources.catalog_for(kind)
                   if offset == 0 or one.PAGES]
        outcomes, (works, refused) = await asyncio.gather(
            answered_all((one.search(query, kind, offset), one.name)
                         for one in clients),
            self._namesakes(query, kind, offset),
        )

        answers, refusals = split(outcomes)
        # Порция считается по выдаче, а не по странице: у каталога она стоит
        # одного запроса, у работ — одного на всех найденных тёзок разом, а их
        # бывают сотни, и показанная строка ложится в базу.
        #
        # Работы тёзок переплетаются между собой до того, как порция отрежет
        # лишнее: сложенные подряд, работы первого съедают её целиком, а решение
        # пользователя — «по имени ищутся работы всех людей с таким именем».
        #
        # Близнецы снимаются до среза и по той же паре, что и складывание своей
        # выдачи с чужой: однофамильцы бывают соавторами — Коэны, Руссо,
        # Вачовски, — и общая работа заняла бы по слоту на каждого. Складывание
        # снимает её позже, и до экрана доехала бы половина порции.
        together = unique_by(_weave(works),
                             lambda one: (one.source, one.source_id))
        woven = await self._narrowed(answers, together, query)
        shown = await self._covered(woven, kind)

        return ExternalSearch(
            views=tuple(await to_views(shown, self._genres, self._clock)),
            refusals=tuple(once(refusals + refused)),
            more=_has_more(clients, outcomes),
        )

    async def _covered(self, rows: list[SearchHit], kind: Kind) -> list[SearchHit]:
        """Строки, которым добыта обложка на стороне, — тем, у кого её нет.

        Спрашивается здесь, при поиске, а не при заведении карточки: решение
        пользователя 23.08.2026, обложка нужна человеку в тот миг, когда он
        выбирает из выдачи, а не после.

        Спрашиваются все показанные строки и разом. Порция режется по каждой
        выдаче отдельно, а у книг их две — каталог и работы тёзок, — так что
        строк тут бывает до сорока, и столько же уходит запросов, а на
        нашедшуюся ещё и `HEAD` за крупной картинкой. Очереди под это не
        заведено: замерено 23.08.2026, волна из сорока проходит без единого
        отказа — 0.58 с у поиска издания, 1.22 с у `HEAD`.

        Ищет запасной источник по ISBN и сверяет два признака сразу; у кого
        ISBN нет, тот и не спрашивается. Отказ ничего не ломает: строка
        показывается без обложки, как и раньше.

        Каталогам с обложкой это не стоит ничего: `covers_for` отвечает пустотой
        всем, кроме книг."""
        client = self._sources.covers_for(kind)
        empty = [one for one in rows if not one.poster_url]
        if client is None or not empty:
            return rows

        found = await answered_all(
            (client.cover_for(_isbn_of(one), one.title), client.name)
            for one in empty
        )
        covers = {id(row): answer.value for row, answer in zip(empty, found)
                  if isinstance(answer, Found)}
        return [replace(one, poster_url=covers[id(one)]) if id(one) in covers
                else one for one in rows]

    async def _namesakes(self, query: str, kind: Kind, offset: int):
        """Работы тёзок — только на первой порции.

        Вторая половина выдачи не листается вовсе: фильмография приезжает
        целиком одним запросом на каждого найденного тёзку. Спроси её на каждой
        порции — приехало бы то же самое, на экран не попало бы ничего
        (`merge_results` снимет повторы), а запросы ушли бы все, и у книг они из
        тысячи суточных."""
        if offset:
            return [], []
        return await self._works.of_name(query, kind)

    async def _narrowed(self, answers: list[list[SearchHit]],
                        together: list[SearchHit],
                        query: str) -> list[SearchHit]:
        """Четыре отсева подряд и переплетение. Порядок между ними — решение, а
        не последовательность вызовов.

        **Не относящееся к запросу** уходит первым и **только из выдач
        каталогов**. У работ тёзок запрос — это имя человека, а строки его
        фильмы: общего слова у «Джона Траволты» с «Криминальным чтивом» нет ни
        одного, и общий отсев отменил бы поиск по имени целиком.

        **Синглы** уходят следом и из обеих половин: у альбомов исполнителя
        их не меньше, чем в выдаче поиска.

        **Убранное человеком** — вторым: мусор в базу не ходит, и чем меньше
        строк доживёт до запроса `known`, тем он дешевле.

        Оба стоят **до среза порции**: иначе двадцать негодных строк заняли бы
        двадцать слотов, а добрать двадцать первую неоткуда.

        **Склейка** — последней, и уже после среза. Сливать имеет смысл то, что
        прошло чистку, иначе дополнение склеилось бы с игрой; а склеивать —
        только видимое: победитель с сороковой строки убил бы проигравшего со
        второй, и на экран не попал бы ни один из двух."""
        kept = await without_removed(
            self._removed, _albums([*relevant(answers, query), together]))
        return _weave(merged([one[:SEARCH_SIZE] for one in kept], query))
