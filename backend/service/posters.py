"""Путь обложки от источника до хранилища."""

import logging
from collections.abc import Mapping
from datetime import datetime
from urllib.parse import urlsplit

import httpx

from backend.model import BadImage, Kind, Reason, Refusal, Source
from backend.service.asking import answered
from backend.service.images import already_shaped, crop_to_cover
from backend.sources.errors import refuse_code
from backend.sources.fantlab.client import ORIGINAL
from backend.sources.fantlab.client import SOURCE as FANTLAB
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
                  Source.GOOGLE_BOOKS, Source.DEEZER)

# Чей адрес качается не соединением источника карточки. Обложку книге ищет
# FantLab, а карточка приезжает от Google — и в самой карточке от чужого
# каталога не остаётся ни следа, так что различить их можно только по хозяину
# адреса.
#
# Своё соединение ему нужно по двум причинам сразу: одна сетевая беда на
# fantlab.ru иначе закрывала бы на пятнадцать секунд все книжные обложки,
# включая гугловые, — а без обложки книга не заводится вовсе, — и плашка
# называла бы человеку не тот источник. Предохранитель у него при этом свой:
# соединений к сайту два, и то, которым ищут издание, живёт у самого клиента.
#
# Хост берётся из адреса самого клиента, а не пишется здесь строкой: разойдись
# они — и починка отменилась бы молча, адрес поехал бы прежним чужим
# соединением при зелёном наборе. Второго заимодавца заводить так же: сверку
# имени держит тест боевой сборки, а сверку хоста — только это правило.

LENDERS = {urlsplit(ORIGINAL).hostname: FANTLAB}


def _owner_of(url: str, source: Source) -> str:
    """Чьё соединение качает этот адрес: обычно источника карточки, а у
    одолженной обложки — того, на чьём сайте она лежит."""
    return LENDERS.get(urlsplit(url).hostname or "", str(source))


class PosterService:
    """Обложка едет от того же источника, что и карточка, и карточка её ждёт:
    не скачалась — не пишем ничего, повторим при следующем показе."""

    def __init__(self, clients: Mapping[str, SourceHttp],
                 store: PosterStore) -> None:
        # Ключ — имя источника строкой, а не значение `Source`: у заимодавца
        # обложек своего значения там нет и быть не может — карточек он не
        # приносит. `Source` при этом строка и сама, так что зовущие передают
        # его как есть.
        self._clients = {str(name): one for name, one in clients.items()}
        self._store = store

    async def fetch(self, source: Source, url: str,
                    kind: Kind) -> bytes | None | Refusal:
        """Обложка байтами, и исключения из этого пути не вылетает.

        Тип нужен форме: чужую по форме обложку тут обрезает та же функция, что
        и залитую руками, а у альбома обложка квадратная.

        Защита стоит здесь, а не у зовущих: их трое — загрузчик, писатель
        карточки и привязка, — и двое последних публичные, то есть за границей
        потоков, где второго канала для исключения нет."""
        return await answered(self._fetched(source, url, kind),
                              self._name(_owner_of(url, source)))

    async def _fetched(self, source: Source, url: str,
                       kind: Kind) -> bytes | None | Refusal:
        if not url:
            # Обложки нет в самом источнике — ждать нечего.
            return None

        owner = _owner_of(url, source)
        client = self._clients.get(owner)
        if client is None:
            logger.warning("постер: нет клиента для источника %s", owner)
            return self._refuse(owner, f"нет клиента для {owner}")

        response = await client.get(url)
        if not isinstance(response, httpx.Response):
            # Отказ клиента уходит наверх своей причиной: сеть, квота и частота
            # решаются там по-разному.
            return response
        return self._picture(owner, url, response, kind)

    def _picture(self, owner: str, url: str, response: httpx.Response,
                 kind: Kind) -> bytes | None | Refusal:
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
            return refuse_code(self._name(owner), response.status_code)

        if not response.content.startswith(_SIGNATURES):
            # Читается подпись формата, а не разбирается картинка. CDN,
            # отдающий под кодом 200 страницу-заглушку или капчу, проходит
            # проверку кода насквозь — и HTML лёг бы в хранилище как обложка, а
            # карточка при этом считалась бы полной. Пустое тело сюда же:
            # подписи у пустоты нет.
            logger.warning("постер %s: тело не изображение, %s байт",
                           url, len(response.content))
            return self._refuse(owner, "тело не изображение")

        if already_shaped(response.content, kind):
            # Пришло в нашей форме — не трогаем: перекодировать значит потерять
            # качество и запас под высокую плотность экрана. Так приходит
            # большинство: у TMDB, Steam, GOG и Deezer обложка ровно 2:3 или
            # ровно квадрат.
            return response.content

        # Чужая форма идёт через ту же обрезку, что и залитая руками картинка.
        # Таких источников два: у Google Books обложки бывают и 1808×2552, и
        # 128×194, у old-games.ru коробочный скан — 120×146, замерено 23.08.2026.
        # Без обрезки рамка карточки срезала бы им бока или верх с низом, а в
        # хранилище легло бы то, что каждый раз режется заново.
        try:
            return crop_to_cover(response.content, kind)
        except BadImage as error:
            # Заголовок картинки прочитался, а тело нет: обрезанный на середине
            # файл. Отказ, а не пустота: «обложки нет» отменило бы повтор при
            # следующем показе.
            logger.warning("постер %s: не обрезалась, %s", url, error)
            return self._refuse(owner, "картинка не разобралась")

    @staticmethod
    def _name(owner: str) -> str:
        """Имя отказа собирается из источника, а не берётся у клиента: клиентов
        зовёт тот, кто их создал, а различать отказы надо по источнику."""
        return f"poster:{owner}"

    def _refuse(self, owner: str, detail: str) -> Refusal:
        """Отказ по причине, которую кодом не выразить. Отказ по коду собирает
        общий `refuse_code` — фраза `HTTP <код>` лежит там одним местом на всех,
        кто её пишет."""
        return Refusal(source=self._name(owner), reason=Reason.BROKEN,
                       detail=detail)

    async def poster_for(self, item_id: int | None, source: Source, url: str,
                         now: datetime,
                         kind: Kind) -> bytes | None | Refusal:
        """Обложка видимой карточки. Лежащая в хранилище отдаётся сразу.

        У кандидата `item_id` пуст: обложку показываем, но класть её некуда —
        сохранит её загрузчик вместе с карточкой."""
        if item_id is None:
            return await self.fetch(source, url, kind)

        stored = await self._store.get(item_id)
        if stored is not None:
            return stored

        data = await self.fetch(source, url, kind)
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

    async def store_upload(self, item_id: int, data: bytes, kind: Kind,
                           now: datetime) -> None:
        """У залитой с диска картинки форма произвольная, и обрезается она
        всегда — в отличие от скачанной, которой обрезка достаётся, только если
        источник прислал чужую форму.

        Тип нужен самой обрезке: у альбома обложка квадратная, у остальных
        афиша 2:3."""
        await self.save(item_id, crop_to_cover(data, kind), now)

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()
        await self._store.close()
