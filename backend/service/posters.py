"""Путь обложки от источника до хранилища."""

import logging
from collections.abc import Mapping
from datetime import datetime

import httpx

from backend.model import Source
from backend.service.images import crop_to_cover
from backend.sources.errors import Reason, Refusal
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore

logger = logging.getLogger(__name__)

# Подписи форматов, которые встречаются у постеров: JPEG, PNG, WebP.
_SIGNATURES = (b"\xff\xd8", b"\x89PNG\r\n\x1a\n", b"RIFF")


class PosterService:
    """Обложка едет от того же источника, что и карточка, и карточка её ждёт:
    не скачалась — не пишем ничего, повторим при следующем показе."""

    def __init__(self, clients: Mapping[Source, SourceHttp],
                 store: PosterStore) -> None:
        self.clients = dict(clients)
        self.store = store

    async def fetch(self, source: Source, url: str) -> bytes | None | Refusal:
        if not url:
            # Обложки нет в самом источнике — ждать нечего.
            return None

        client = self.clients.get(source)
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
                 response: httpx.Response) -> bytes | Refusal:
        if response.status_code != 200:
            logger.warning("постер %s: HTTP %s", url, response.status_code)
            return self._refuse(source, f"HTTP {response.status_code}")

        if not response.content.startswith(_SIGNATURES):
            # Читается подпись формата, а не разбирается картинка. CDN,
            # отдающий под кодом 200 страницу-заглушку или капчу, проходит
            # проверку кода насквозь — и HTML лёг бы в хранилище как обложка, а
            # карточка при этом считалась бы полной. Пустое тело сюда же:
            # подписи у пустоты нет.
            logger.warning("постер %s: тело не изображение, %s байт",
                           url, len(response.content))
            return self._refuse(source, "тело не изображение")

        # Скачанное не трогаем: у всех трёх источников оно уже 2:3.
        return response.content

    def _refuse(self, source: Source, detail: str) -> Refusal:
        """Имя отказа собирается из источника, а не берётся у клиента: клиентов
        зовёт тот, кто их создал, а различать отказы надо по источнику."""
        return Refusal(source=f"poster:{source}", reason=Reason.BROKEN,
                       detail=detail)

    async def save(self, item_id: int, data: bytes, now: datetime) -> None:
        await self.store.put(item_id, data, now)

    async def store_upload(self, item_id: int, data: bytes,
                           now: datetime) -> None:
        """Единственное место, где картинка обрезается: у залитой с диска форма
        произвольная."""
        await self.store.put(item_id, crop_to_cover(data), now)

    async def aclose(self) -> None:
        for client in self.clients.values():
            await client.aclose()
        await self.store.close()
