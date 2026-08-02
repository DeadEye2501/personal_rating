"""Части карточки и сервис обложек, собранные для теста на подставном транспорте.

Своей сборки здесь нет: набор частей приезжает из `backend/app.py`, а этот модуль
подставляет ему хранилище и транспорт, которых в тесте не бывает настоящих."""

import httpx

from backend.app import card_parts as backend_card_parts
from backend.service.posters import POSTER_SOURCES, PosterService
from backend.service.search import SearchService
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore
from backend.storage.repository.genres import GenresRepository
from backend.storage.repository.library import LibraryRepository
from backend.storage.repository.views import ViewsRepository
from tests.builders import MOMENT
from tests.fakes import FakeSources


def poster_service(store: PosterStore,
                   transport: httpx.MockTransport) -> PosterService:
    """Сервис обложек с одним транспортом на все три источника. Где важно, кого
    именно спросили, тест собирает клиентов сам."""
    clients = {source: SourceHttp(f"cdn:{source}", transport=transport)
               for source in POSTER_SOURCES}
    return PosterService(clients, store)


def card_parts(sessions, store: PosterStore,
               transport: httpx.MockTransport) -> dict:
    """Части карточки, собранные тем же кодом, что и в приложении.

    Своего набора имён здесь нет нарочно: перепутанные местами люди и студии в
    боевой сборке иначе не наблюдаются ничем — тесты писателя и привязки ходили
    бы по собственному набору и мимо ошибки."""
    return backend_card_parts(sessions, poster_service(store, transport))


def search_service(sessions, *clients) -> SearchService:
    """Поиск, собранный на подставных клиентах источников.

    Общий у двух модулей проверок — выдачи и жанров кандидата: разошлись бы они
    настройками, и одна из двух проверяла бы не тот сервис. Часы внедрены теми
    же, что у остальных записей: отметка времени бесплатной оценки иначе была бы
    непроверяемой."""
    return SearchService(LibraryRepository(sessions),
                         ViewsRepository(sessions),
                         FakeSources(*clients),
                         GenresRepository(sessions),
                         clock=lambda: MOMENT)
