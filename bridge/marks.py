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

    def aspects(self, item_id: int, visual: int | None, narrative: int | None,
                gameplay: int | None) -> dict:
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
