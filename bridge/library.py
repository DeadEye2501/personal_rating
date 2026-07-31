"""Мост: карточка целиком — заведение, правка, отвязка, удаление."""

from datetime import date

from backend.model import Kind, new_manual_item
from bridge.answer import Domain


class Library(Domain):
    """Показывать карточку — не его дело: для показа нужен `CardView` с оценкой,
    тегами и закладкой, и собирает его лента. Отсюда наружу уезжают только
    номер новой строки, сводка удаления и найденные тёзки по названию."""

    def create(self, fields: dict) -> dict:
        """Поля формы, а не готовый `Item`: собрать датакласс обратно из JSON
        нечем, а `new_manual_item` уже умеет и `manual`, и свой идентификатор,
        и момент создания.

        Разбор идёт внутри заявки: кривая дата и неизвестный тип содержимого —
        это `ValueError`, и снаружи оболочки он ушёл бы через границу потоков в
        pywebview, где ловить его некому."""
        return self._reply(lambda back: back.library.create(_manual(fields)))

    def replace(self, item_id: int, fields: dict) -> dict:
        """Тот же `_manual`, что и у заведения: свежий `synced_at`, который он
        подставляет, до базы не доезжает — `replace_fields` его не пишет.
        Правка руками не разговор с источником, и объявить карточку только что
        обновлённой значило бы отложить перезапрос сезонов на месяц."""
        return self._reply(
            lambda back: back.library.replace_fields(item_id, _manual(fields)))

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
    доходит, и поле остаётся тем, что объявлено по умолчанию.

    Незаполненным считается `None`, и только он. Пустая строка — это заполненное
    пустым, и она доедет до базы как есть; пустая строка в дате доедет до
    `fromisoformat` и станет отказом. Страница обязана слать `null`, а не `""`."""
    known = {name: value for name, value in fields.items()
             if name not in ("kind", "title") and value is not None}
    if "released_at" in known:
        known["released_at"] = date.fromisoformat(known["released_at"])
    return new_manual_item(Kind(fields["kind"]), fields["title"], **known)
