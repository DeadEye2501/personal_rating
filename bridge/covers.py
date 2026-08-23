"""Мост: обложки — заливка своей картинки и наличие.

Показ идёт не отсюда: байты вклеиваются в текст скрипта, поэтому обложка едет
HTTP-ручкой. Внутрь картинка идёт base64 — там канал другой, `postMessage` с
JSON-строкой."""

import base64
from datetime import datetime

from backend.model import BadImage, Kind
from bridge.answer import Domain


class Covers(Domain):
    def store_upload(self, item_id: int, data: str, kind: str) -> dict:
        """Обрезка идёт на бэкенде, там же, где картинка и хранится: в потоке
        интерфейса ей делать нечего.

        Тип приезжает строкой и переводится внутри заявки — как и везде на этой
        границе: перевод снаружи оболочки ушёл бы исключением через границу
        потоков. Нужен он самой обрезке: у альбома обложка квадратная."""
        now = datetime.now()
        return self._reply(
            lambda back: back.posters.store_upload(item_id, _picture(data),
                                                   Kind(kind), now))

    def has(self, item_id: int) -> dict:
        return self._reply(lambda back: back.posters.has(item_id))


def _picture(data: str) -> bytes:
    """Разбор идёт внутри заявки, а не до неё: брошенный снаружи `BadImage`
    прошёл бы мимо оболочки и уехал исключением через границу потоков.

    Род отказа у обеих бед один: человеку разница между «не base64» и «не
    картинка» ничего не даёт."""
    try:
        return base64.b64decode(data, validate=True)
    # `binascii.Error` наследует `ValueError`, и второй ловит обоих.
    except ValueError as error:
        raise BadImage("картинка не разобралась") from error
