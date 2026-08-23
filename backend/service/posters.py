"""Путь обложки от источника до хранилища."""

import logging
from collections.abc import Mapping
from datetime import datetime

import httpx

from backend.model import Reason, Refusal, Source
from backend.service.asking import answered
from backend.service.images import crop_to_cover
from backend.sources.errors import refuse_code
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore

logger = logging.getLogger(__name__)

# Подписи форматов, которые встречаются у постеров: JPEG, PNG, WebP.
_SIGNATURES = (b"\xff\xd8", b"\x89PNG\r\n\x1a\n", b"RIFF")

# Код, под которым CDN говорит «такой картинки у меня нет». От прочих неудач
# отличается тем, что повторять запрос бессмысленно: ни завтра, ни через месяц
# она не появится. Один, а не набор: `410` сюда просился по смыслу, но замерен
# не был, а вписанный вперёд он молча решал бы судьбу карточки.
_ABSENT = 404

# Источники, у которых бывает обложка: у ручной карточки её скачивать негде.
# Набор объявлен здесь, а не у сборки: клиентов под него заводят двое — боевая
# сборка и тесты, — и разойдись они, четвёртый источник молча остался бы без
# обложек в одной из двух.
POSTER_SOURCES = (Source.TMDB, Source.STEAM, Source.GOG, Source.OLD_GAMES,
                  Source.GOOGLE_BOOKS)


class PosterService:
    """Обложка едет от того же источника, что и карточка, и карточка её ждёт:
    не скачалась — не пишем ничего, повторим при следующем показе."""

    def __init__(self, clients: Mapping[Source, SourceHttp],
                 store: PosterStore) -> None:
        self._clients = dict(clients)
        self._store = store

    async def fetch(self, source: Source, url: str) -> bytes | None | Refusal:
        """Обложка байтами, и исключения из этого пути не вылетает.

        Защита стоит здесь, а не у зовущих: их трое — загрузчик, писатель
        карточки и привязка, — и двое последних публичные, то есть за границей
        потоков, где второго канала для исключения нет."""
        return await answered(self._fetched(source, url), self._name(source))

    async def _fetched(self, source: Source, url: str) -> bytes | None | Refusal:
        if not url:
            # Обложки нет в самом источнике — ждать нечего.
            return None

        client = self._clients.get(source)
        if client is None:
            logger.warning("постер: нет клиента для источника %s", source)
            return self._refuse(source, f"нет клиента для {source}")

        response = await client.get(url)
        if not isinstance(response, httpx.Response):
            # Отказ клиента уходит наверх своей причиной: сеть, квота и частота
            # решаются там по-разному.
            return response
        return self._picture(source, url, response)

    def _picture(self, source: Source, url: str,
                 response: httpx.Response) -> bytes | None | Refusal:
        if response.status_code == _ABSENT:
            # Обложки по этому адресу нет, и не будет: карточка живёт без неё,
            # как и та, у которой адрес пуст. Отказом это быть не может — у
            # Steam адрес не приезжает в ответе, а собирается нами по образцу, и
            # у части приложений такой картинки не существует вовсе (замерено
            # живьём 02.08.2026 на дополнении и на служебном клиенте). Отказ
            # запретил бы записать карточку, а «повторим при следующем показе» у
            # постоянного `404` не наступает никогда.
            logger.info("постер %s: обложки нет, HTTP %s",
                        url, response.status_code)
            return None

        if response.status_code != 200:
            logger.warning("постер %s: HTTP %s", url, response.status_code)
            return refuse_code(self._name(source), response.status_code)

        if not response.content.startswith(_SIGNATURES):
            # Читается подпись формата, а не разбирается картинка. CDN,
            # отдающий под кодом 200 страницу-заглушку или капчу, проходит
            # проверку кода насквозь — и HTML лёг бы в хранилище как обложка, а
            # карточка при этом считалась бы полной. Пустое тело сюда же:
            # подписи у пустоты нет.
            logger.warning("постер %s: тело не изображение, %s байт",
                           url, len(response.content))
            return self._refuse(source, "тело не изображение")

        # Скачанное не трогаем: обрезка есть только у залитого руками.
        # У киношных и игровых источников пропорция и так 2:3, у книжного она
        # своя — замерено, `zoom=3` отдаёт 575×883, — и подгонять её нечем:
        # обрезать пришлось бы название с обложки.
        return response.content

    @staticmethod
    def _name(source: Source) -> str:
        """Имя отказа собирается из источника, а не берётся у клиента: клиентов
        зовёт тот, кто их создал, а различать отказы надо по источнику."""
        return f"poster:{source}"

    def _refuse(self, source: Source, detail: str) -> Refusal:
        """Отказ по причине, которую кодом не выразить. Отказ по коду собирает
        общий `refuse_code` — фраза `HTTP <код>` лежит там одним местом на всех,
        кто её пишет."""
        return Refusal(source=self._name(source), reason=Reason.BROKEN,
                       detail=detail)

    async def poster_for(self, item_id: int | None, source: Source, url: str,
                         now: datetime) -> bytes | None | Refusal:
        """Обложка видимой карточки. Лежащая в хранилище отдаётся сразу.

        У кандидата `item_id` пуст: обложку показываем, но класть её некуда —
        сохранит её загрузчик вместе с карточкой."""
        if item_id is None:
            return await self.fetch(source, url)

        stored = await self._store.get(item_id)
        if stored is not None:
            return stored

        data = await self.fetch(source, url)
        if data is None or isinstance(data, Refusal):
            return data

        await self.save(item_id, data, now)
        return data

    async def save(self, item_id: int, data: bytes, now: datetime) -> None:
        await self._store.put(item_id, data, now)

    async def delete(self, item_id: int) -> None:
        """Обложку убирает владелец хранилища, а не тот, кто удаляет карточку:
        второй файл базы наружу не показывается вовсе."""
        await self._store.delete(item_id)

    async def has(self, item_id: int) -> bool:
        """Лежит ли обложка. Нужно привязке: заливший картинку руками не должен
        получить поверх неё чужую."""
        return await self._store.has(item_id)

    async def store_upload(self, item_id: int, data: bytes,
                           now: datetime) -> None:
        """Единственное место, где картинка обрезается: у залитой с диска форма
        произвольная."""
        await self.save(item_id, crop_to_cover(data), now)

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()
        await self._store.close()
