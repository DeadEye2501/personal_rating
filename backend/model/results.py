"""Своя выдача и чужая, сложенные в одну.

Лежит в модели, а не в сервисе поиска: складывать приходится и клиенту — своё он
уже показал, внешнее приехало потом."""

from backend.model.kinds import Source
from backend.model.view import CardView


def merge_results(local: list[CardView],
                  external: list[CardView]) -> list[CardView]:
    """Порядок задан источником: у него есть данные о популярности и совпадении
    с запросом, которых у нас нет.

    Дубли снимаются по паре «источник + идентификатор». Одна и та же игра из
    Steam и из GOG под эту пару не попадает и показывается дважды."""
    mine = {(view.source, view.source_id): view for view in local}

    merged: list[CardView] = []
    seen: set[tuple[Source, str]] = set()
    for view in external:
        key = (view.source, view.source_id)
        if key in seen:
            continue
        seen.add(key)
        # Своё стоит на своём месте и ничем не выделено — но показываем именно
        # его: у него есть оценка, теги и закладка.
        merged.append(mine.get(key, view))

    merged.extend(view for view in local
                  if (view.source, view.source_id) not in seen)
    return merged
