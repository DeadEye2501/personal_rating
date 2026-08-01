"""Мост: справочники — жанры, люди, студии.

Люди и студии — один класс с двумя экземплярами: все методы у них общие, и
писать их дважды нельзя. Имя домена приезжает доводом и выбирает репозиторий."""

from backend.model import GenreKind
from bridge.answer import Domain

DOMAINS = ("people", "companies")


class Refs(Domain):
    def genres(self, genre_kind: str) -> dict:
        """Наборов два: кино и игры. Клиенту нужен только список — перевод чужих
        меток в наши жанры это внутренность записи карточки."""
        return self._reply(
            lambda back: back.genres.list_for_kind(GenreKind(genre_kind)))

    def suggest(self, domain: str, name: str, offset: int = 0) -> dict:
        """Строка подсказки несёт название самой высоко оценённой связанной
        карточки — по нему человека и узнают.

        Смещение приходит от страницы: список догружается прокруткой, а сколько
        строк в порции — дело справочника, не её."""
        return self._reply(
            lambda back: _of(back, domain).suggest(name, offset=offset))

    def create_person(self, domain: str, name: str) -> dict:
        """Enter при неподсвеченном списке заводит нового — и человека, и
        студию. Выбранного из подсказки заводить не нужно: `entity_id` уже
        известен."""
        return self._reply(lambda back: _of(back, domain).create_manual(name))


def _of(backend, domain: str):
    """Опечатка на стороне страницы обязана стать отказом, а не вечным промисом:
    `getattr` по неизвестному имени поднял бы `AttributeError`, и его поймала бы
    оболочка — но уже без внятного текста."""
    if domain not in DOMAINS:
        raise ValueError(f"нет такого справочника: {domain}")
    return getattr(backend, domain)
