"""Чужие работы человека: спросить о них источник.

Вынесено на втором потребителе: работы одного и того же человека спрашивает и
клик по имени на карточке, и строка поиска — по решению пользователя от
01.08.2026 она ищет по имени всегда. Разойдись эти два пути, одна из двух выдач
молча обеднела бы: у клика внешняя половина осталась бы без работ тёзок, у
строки — без работ вовсе."""

from backend.model import Found, Kind, Refusal, SearchHit
from backend.service.asking import answered, answered_all
from backend.service.hits import once, split
from backend.sources.registry import Sources


class Filmographies:
    """Кто умеет искать по человеку — решает реестр: у игр таких клиентов нет
    вовсе, и замер про магазины лежит там же, в `Sources.people_for`."""

    def __init__(self, sources: Sources) -> None:
        self._sources = sources

    async def of_person(self, source_id: str,
                        kind: Kind) -> tuple[list[list[SearchHit]],
                                             list[Refusal]]:
        """У человека из TMDB идентификатор уже есть, и спрашивать его по имени
        значило бы притащить тёзок туда, где их быть не должно."""
        client = self._sources.people_for(kind)
        if client is None:
            return [], []
        return await self._works(client, [source_id], kind)

    async def of_name(self, name: str,
                      kind: Kind) -> tuple[list[list[SearchHit]],
                                           list[Refusal]]:
        """Именем спрашивают дважды: когда его набрали в строке поиска и когда
        кликнули по человеку, у которого внешней идентичности нет."""
        client = self._sources.people_for(kind)
        if client is None:
            return [], []
        if not name.strip():
            # Пустое имя в базе разрешено, а спрашивать по нему нечего: ушёл бы
            # пустой `query` и вернулся отказ, который не о чем.
            return [], []

        found = await answered(client.find_people(name), client.name)
        if isinstance(found, Refusal):
            return [], [found]
        if not isinstance(found, Found):
            return [], []
        return await self._works(client,
                                 [one.source_id for one in found.value], kind)

    async def _works(self, client, person_ids: list[str],
                     kind: Kind) -> tuple[list[list[SearchHit]],
                                          list[Refusal]]:
        """Фильмографии всех найденных разом: их бывает несколько, и ждать по
        очереди значило бы сложить их сроки ожидания.

        Выдачи остаются по людям, а не сливаются в одну, и складывает их
        вызывающий. Складывать по-разному приходится: у клика по имени порции
        нет — там показываются все работы, и подряд они читаются лучше, — а у
        строки поиска порция двадцать строк, и сложенные подряд работы первого
        тёзки съедают её целиком. Слей их здесь — и одному из двух путей
        досталось бы чужое правило."""
        outcomes = await answered_all(
            (client.credits_of(person_id, kind), client.name)
            for person_id in person_ids
        )

        answers, refusals = split(outcomes)
        return answers, once(refusals)
