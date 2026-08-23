"""Повтор запроса к источнику, отговорившемуся занятостью."""

import logging

import httpx

from backend.model import Reason, Refusal
from backend.sources.http import SourceHttp

logger = logging.getLogger(__name__)

# «Занят сейчас», а не отказ. Замерено у обоих владельцев: у old-games.ru волна
# из тридцати даёт два десятка `503`, а следующий одиночный запрос проходит за
# обычные 0.7 с; у Google Books десять запросов подряд дают пять `503`, а повтор
# поднимает удачу с пяти до восьми.
#
# Повтор идёт немедленно: `Retry-After` не шлёт ни один, а пауза не даёт ничего —
# замерено 22.08.2026, выдержка 0.5 с с удвоением дала те же восемь из десяти за
# лишний запрос.
BUSY = 503

# Сколько раз спросить, прежде чем сдаться. Повтор не вечен: при настоящей беде
# клиент отказывает, а не долбится.
ATTEMPTS = 3


async def asked_until_free(http: SourceHttp, url: str,
                           params: dict | None = None) -> httpx.Response | Refusal:
    """Ответ, которым источник не отговорился, — либо отказ, решивший всё.

    Классификации сверх `503` здесь нет, и это не упущение: занятость двое
    понимают одинаково, а остальные коды — по-разному. У old-games не описан ни
    один код, и любой не-200 уходит в `refuse_undocumented`; Google на `429`
    закрывает источник до полуночи, а на `404` с разобранным телом пишет
    отрицательный факт. Пропусти его через чужую классификацию — и суточная
    квота превратилась бы в пятиминутный откат по частоте."""
    for attempt in range(ATTEMPTS):
        response = await http.get(url, params=params)
        if not isinstance(response, httpx.Response):
            return response
        if response.status_code != BUSY:
            return response
        logger.info("%s: занят, попытка %s из %s",
                    http.name, attempt + 1, ATTEMPTS)
    return Refusal(source=http.name, reason=Reason.RATE,
                   detail=f"{ATTEMPTS} ответа подряд с кодом {BUSY}")
