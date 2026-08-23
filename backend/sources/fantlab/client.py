"""Разговор с FantLab по сети: обложка книги, которой нет у основного источника."""

import logging

import httpx

from backend.model import Found, Missing, Outcome, Refusal
from backend.sources.errors import parsed
from backend.sources.fantlab.parse import edition_of
from backend.sources.http import SourceHttp
from backend.sources.undocumented import asked

logger = logging.getLogger(__name__)

SOURCE = "fantlab"
SEARCH = "https://api.fantlab.ru/search-editions"

# Два размера картинки. `orig` — настоящая обложка, от 600×861 до 3129×4874; у
# части изданий её нет вовсе и адрес отвечает 404 — замерено 23.08.2026, три
# издания из тринадцати. `big` есть всегда, но он около 200 пикселей по ширине.
ORIGINAL = "https://fantlab.ru/images/editions/orig/{edition}"
SMALL = "https://fantlab.ru/images/editions/big/{edition}"

# Чем отвечает настоящая обложка. Перечислены поимённо, а не проверкой на
# `image/`: заглушка «обложки нет» приезжает как `image/svg+xml`, то есть тоже
# картинкой — 56 КБ векторной надписи под кодом `200`. Замерено 23.08.2026 и
# разведкой, и повторно при написании.
_PICTURES = ("image/jpeg", "image/jpg", "image/png", "image/webp")


class FantLabClient:
    """Обложки, и только они: карточек, поиска и людей у этого источника мы не
    берём вовсе.

    Каталог его — фантастика, фэнтези и смежное, и это принятое ограничение:
    обычная проза и нон-фикшн там не найдутся. Замерено разведкой 23.08.2026."""

    def __init__(self, http: SourceHttp) -> None:
        self._http = http

    @property
    def name(self) -> str:
        """Под этим именем источник назовётся в отказе — им подписывает ответы
        `answered_all`, который зовёт обложки разом."""
        return self._http.name

    async def cover_for(self, isbn: str, title: str) -> Outcome:
        """Адрес обложки того самого издания — или «нет такого».

        Сверяются оба признака сразу, ISBN и название: поиск у FantLab
        полнотекстовый, а ISBN у Google местами чужой. Подробности — в
        `edition_of`."""
        if not isbn.strip():
            # Искать нечем: без номера сверять будет нечего, и полнотекстовый
            # поиск по названию привёл бы чужое издание.
            return Missing()

        answer = await asked(self._http, SEARCH, {"q": isbn, "page": 1})
        if not isinstance(answer, httpx.Response):
            return answer

        edition = parsed(logger, SOURCE, f"выдача по {isbn} не разобралась",
                         lambda: edition_of(answer.json(), isbn, title))
        if isinstance(edition, Refusal):
            return edition
        if edition is None:
            return Missing()
        return await self._picture(edition)

    async def _picture(self, edition: int) -> Outcome:
        """Крупная обложка, а если её нет — маленькая.

        Наличие спрашивается `HEAD`-ом: у `orig` бывает 404, а качать 350 КБ
        ради проверки незачем — замерено 23.08.2026, `HEAD` источник понимает и
        отвечает типом содержимого."""
        original = ORIGINAL.format(edition=edition)
        answer = await self._http.head(original)
        if isinstance(answer, httpx.Response) and _is_picture(answer):
            return Found(original)
        return Found(SMALL.format(edition=edition))

    async def aclose(self) -> None:
        await self._http.aclose()


def _is_picture(answer: httpx.Response) -> bool:
    """Картинка ли по ту сторону адреса. Тип содержимого, а не код: заглушка
    «обложки нет» приезжает под кодом 200."""
    kind = answer.headers.get("content-type", "").split(";")[0].strip().lower()
    return answer.status_code == 200 and kind in _PICTURES
