"""Мост: справочники — жанры, люди, студии и шкала оценок.

Люди и студии — один класс с двумя экземплярами: все методы у них общие, и
писать их дважды нельзя. Имя домена приезжает доводом и выбирает репозиторий."""

from backend.model import CompanyRole, GenreKind, PersonRole
from bridge.answer import Domain

DOMAINS = ("people", "companies")

# Роль приходит строкой, а база держит перечисление, и у каждой полки своё:
# режиссёра среди студий не бывает, и отказ на такую пару — это признак, а не
# помеха.
ROLES = {"people": PersonRole, "companies": CompanyRole}


class Refs(Domain):
    def genres(self, genre_kind: str) -> dict:
        """Наборов четыре, и два из них пусты до второго этапа. Клиенту нужен
        только список — перевод чужих меток в наши жанры это внутренность
        записи карточки."""
        return self._reply(
            lambda back: back.genres.list_for_kind(GenreKind(genre_kind)))

    def suggest(self, domain: str, name: str, offset: int = 0) -> dict:
        """Строка подсказки несёт название самой высоко оценённой связанной
        карточки — по нему человека и узнают.

        Смещение приходит от страницы: список догружается прокруткой, а сколько
        строк в порции — дело справочника, не её."""
        return self._reply(
            lambda back: _of(back, domain).suggest(name, offset=offset))

    def set_genres(self, item_id: int, genre_ids: list) -> dict:
        """Жанры приходят снаружи, но у ручной карточки их ставит человек —
        выбором из зашитого набора, а не заведением своих. Набор правится
        целиком: сличать построчно значило бы решать за страницу, что именно
        она поменяла."""
        return self._reply(
            lambda back: back.genres.set_for_item(item_id, genre_ids))

    def detach_all(self, domain: str, item_id: int) -> dict:
        """Состав правится тем же приёмом, что и жанры: снять всё, расставить
        заново. Порядок трёх записей принадлежит странице — мост тонкий и не
        оркеструет."""
        return self._reply(lambda back: _of(back, domain).detach_all(item_id))

    def attach(self, domain: str, item_id: int, entity_id: int, role: str,
               position: int) -> dict:
        """Перевод роли стоит внутри заявки: снаружи оболочки негодная роль
        ушла бы исключением через границу потоков, где ловить его некому."""
        return self._reply(
            lambda back: _of(back, domain).attach(
                item_id, entity_id, _role(domain, role), position))

    def scale(self) -> dict:
        """Ступеней в своей оценке. Спрашивается один раз при загрузке
        страницы: без него ряд звёзд рисовать нечем, а настройка живёт в `.env`.

        Обёрнуто в корутину, как и `world.expected`: поток кладёт фабрику в
        `create_task`, а тот от числа поднимает `TypeError`."""
        return self._reply(lambda back: _scale(back))

    def create_person(self, domain: str, name: str) -> dict:
        """Enter при неподсвеченном списке заводит нового — и человека, и
        студию. Выбранного из подсказки заводить не нужно: `entity_id` уже
        известен."""
        return self._reply(lambda back: _of(back, domain).create_manual(name))


async def _scale(back) -> int:
    return back.scale


def _role(domain: str, role: str):
    """Роль своей полки. Чужая поднимает `ValueError` — тем же путём, что и
    неизвестный домен: отказом, а не вечным промисом."""
    return ROLES[domain](role)


def _of(backend, domain: str):
    """Опечатка на стороне страницы обязана стать отказом, а не вечным промисом:
    `getattr` по неизвестному имени поднял бы `AttributeError`, и его поймала бы
    оболочка — но уже без внятного текста."""
    if domain not in DOMAINS:
        raise ValueError(f"нет такого справочника: {domain}")
    return getattr(backend, domain)
