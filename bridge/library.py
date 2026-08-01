"""Мост: карточка целиком — заведение, правка, отвязка, удаление."""

from dataclasses import replace
from datetime import date

from backend.model import Denied, Kind, new_manual_item
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
        """Правка ложится **поверх** существующей строки, а не вместо неё:
        `replace_fields` пишет все колонки разом, а окно карточки знает не все
        поля — даты выхода в нём нет вовсе, адрес обложки приходит от источника.
        Без наложения правка названия стирала бы и то, и другое молча.

        Свежий `synced_at` до базы не доезжает — `replace_fields` его не пишет.
        Правка руками не разговор с источником, и объявить карточку только что
        обновлённой значило бы отложить перезапрос сезонов на месяц."""
        return self._reply(lambda back: _over(back, item_id, fields))

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


async def _over(back, item_id: int, fields: dict) -> None:
    """Карточку могли удалить из другого окна, пока форма была открыта. Писать
    поверх нечего, и молчать нельзя: человек решил бы, что правка сохранилась."""
    current = await back.library.get(item_id)
    if current is None:
        raise Denied("такой карточки больше нет")

    await back.library.replace_fields(
        item_id, replace(current, title=fields["title"], **_known(fields)))


def _known(fields: dict) -> dict:
    """Незаполненное в форме — это «не знаю», а не «пусто»: до бэкенда оно не
    доходит, и поле остаётся тем, что было.

    Незаполненным считается `None`, и только он. Пустая строка — это заполненное
    пустым, и она доедет до базы как есть; пустая строка в дате доедет до
    `fromisoformat` и станет отказом. Страница обязана слать `null`, а не `""`.

    Тип содержимого и название сюда не попадают: у заведения они обязательные
    доводы сборщика, у правки — название кладётся отдельно, а тип карточка не
    меняет вовсе."""
    known = {name: value for name, value in fields.items()
             if name not in ("kind", "title") and value is not None}
    if "released_at" in known:
        known["released_at"] = date.fromisoformat(known["released_at"])
    return known


def _manual(fields: dict):
    """Поля формы в новую ручную карточку: `new_manual_item` уже умеет и
    `manual`, и свой идентификатор, и момент создания."""
    return new_manual_item(Kind(fields["kind"]), fields["title"],
                           **_known(fields))
