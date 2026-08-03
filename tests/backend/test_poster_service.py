"""Путь обложки от источника до хранилища."""

import io

import pytest
from PIL import Image

from backend.model import Reason, Refusal, Source
from backend.service.images import TARGET_SIZE, BadImage
from backend.service.posters import PosterService
from backend.sources.http import SourceHttp
from backend.storage.posters import PosterStore
from tests.conftest import capture, responding, unreachable
from tests.conftest import MOMENT as WHEN
from tests.conftest import POSTER, POSTER_SOURCES, picture, poster_service


@pytest.fixture
async def service(posters):
    built = poster_service(posters, responding(content=POSTER))
    yield built
    await built.aclose()


async def test_a_downloaded_poster_is_not_re_encoded(service):
    """Скачанный уже 2:3. Перекодировать его — потерять качество и запас под
    высокую плотность экрана, который спека держит сознательно."""
    data = await service.fetch(Source.TMDB, "https://example.com/poster.jpg")

    assert data == POSTER
    assert Image.open(io.BytesIO(data)).size == (600, 900)


async def test_no_url_means_nothing_to_wait_for(service):
    """Обложки нет в самом источнике — он отдал всё, что имел."""
    assert await service.fetch(Source.TMDB, "") is None


async def test_a_missing_picture_is_an_absence_and_not_a_refusal(posters):
    """`404` — это «такой картинки нет», а не «не смогли посмотреть». У Steam
    адрес обложки не приезжает в ответе, а собирается нами по образцу, и у части
    приложений её не существует вовсе: замерено живьём 02.08.2026 — дополнение
    GTA V и служебный клиент Steam отвечают `404`, настоящие игры `200`. Отказом
    это запирало бы игру навсегда: карточка не пишется, а «повторим при
    следующем показе» у постоянного `404` не наступает.

    В теле нарочно настоящая картинка: под `404` CDN отдаёт и заглушку, а
    сохранить её значило бы поселить в карточке чужую обложку насовсем. Здесь
    наблюдается только то, что наружу она не выходит; что она не оседает в
    хранилище — у загрузчика, где под тем же кодом транспорт отдаёт настоящие
    байты, а хранилище остаётся пустым. С телом-текстом проверка сторожила бы
    подпись формата, а не код."""
    service = poster_service(posters, responding(404, content=POSTER))
    result = await service.fetch(Source.TMDB, "https://example.com/missing.jpg")
    await service.aclose()

    assert result is None


async def test_a_server_failure_is_still_a_refusal(posters):
    """Пятисотые от «нет картинки» отличаются тем, что повторить их стоит:
    карточка не пишется, и следующий показ спросит снова."""
    service = poster_service(posters, responding(500, content=POSTER))
    result = await service.fetch(Source.TMDB, "https://example.com/p.jpg")
    await service.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN
    assert result.source == "poster:tmdb"


async def test_an_empty_body_is_a_refusal(posters):
    """Пустоту ловит проверка подписи: подписи у неё нет.

    Причина здесь `BROKEN`, а не `NETWORK`: CDN ответил, просто ответил ничем, —
    и подмена причины заставила бы вызывающего считать это временным обрывом."""
    service = poster_service(posters, responding(content=b""))
    result = await service.fetch(Source.TMDB, "https://example.com/poster.jpg")
    await service.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_page_instead_of_a_picture_is_a_refusal(posters):
    """CDN отдал заглушку или капчу под кодом 200. Проверку кода и непустоты она
    проходит насквозь, и HTML лёг бы в хранилище как обложка — а карточка
    считалась бы при этом полной."""
    service = poster_service(posters, responding(text="<html>404 not found</html>"))
    result = await service.fetch(Source.TMDB, "https://example.com/poster.jpg")
    await service.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.BROKEN


async def test_a_refusal_of_the_client_passes_through_as_it_was(posters):
    """Сеть не отозвалась — это отказ клиента, и подменять его причину нельзя:
    по ней наверху решают, ждать или сказать человеку «нет связи»."""
    service = poster_service(posters, unreachable())
    result = await service.fetch(Source.GOG, "https://example.com/poster.jpg")
    await service.aclose()

    assert isinstance(result, Refusal)
    assert result.reason is Reason.NETWORK
    assert result.source == "cdn:gog"


async def test_png_is_a_picture_too(posters):
    """Форматов у обложек три, и подпись проверяется у всех: у GOG приезжает
    PNG, и отказ на нём означал бы, что карточка не пишется никогда."""
    body = picture(600, 900)
    service = poster_service(posters, responding(content=body))
    result = await service.fetch(Source.GOG, "https://example.com/cover.png")
    await service.aclose()

    assert result == body


async def test_webp_is_a_picture_too(posters):
    """Третий формат из набора подписей. Без проверки его подпись снимается
    безнаказанно, а с ней уходит и весь webp — CDN отдаёт его охотно."""
    body = picture(600, 900, fmt="WEBP")
    service = poster_service(posters, responding(content=body))
    result = await service.fetch(Source.STEAM, "https://example.com/cover.webp")
    await service.aclose()

    assert result == body


async def test_the_poster_is_asked_at_the_address_it_was_given(posters):
    """На провод уходит переданный адрес, а не собранный по дороге: лишний слэш
    или чужой хост неотличимы от «обложки нет»."""
    transport, seen = capture(content=POSTER)
    service = poster_service(posters, transport)
    await service.fetch(Source.TMDB, "https://cdn.example.com/w500/poster.jpg")
    await service.aclose()

    assert [str(request.url) for request in seen] == [
        "https://cdn.example.com/w500/poster.jpg"
    ]


async def test_each_source_is_asked_through_its_own_client(posters):
    """Молчание одного CDN не должно выключать обложки остальных, а спрашивать
    надо того, у кого карточка: с общим клиентом на всех этого не видно."""
    bodies = {source: picture(600, 900 + number, fmt="JPEG")
              for number, source in enumerate(POSTER_SOURCES)}
    clients = {
        source: SourceHttp(f"cdn:{source}", transport=responding(content=body))
        for source, body in bodies.items()
    }
    service = PosterService(clients, posters)

    for source, body in bodies.items():
        assert await service.fetch(source, "https://example.com/p.jpg") == body
    await service.aclose()


async def test_a_dead_cdn_does_not_close_the_others(posters):
    """Предохранитель у каждого источника свой. Один на всех выключил бы обложки
    целиком из-за одного молчащего CDN — и на пятнадцать секунд, а не на запрос.

    Раздельность проверяется следствием, а не устройством: сравнение `id`
    предохранителей читало бы объекты, которые тест сам же и собрал, и один
    `SourceHttp`, подставленный во все три ключа сборки, осталось бы
    незамеченным."""
    body = picture(600, 900, fmt="JPEG")
    service = PosterService(
        {
            Source.TMDB: SourceHttp("cdn:tmdb", transport=unreachable()),
            Source.STEAM: SourceHttp("cdn:steam",
                                     transport=responding(content=body)),
        },
        posters,
    )

    refused = await service.fetch(Source.TMDB, "https://example.com/p.jpg")
    assert isinstance(refused, Refusal)
    assert refused.reason is Reason.NETWORK

    assert await service.fetch(Source.STEAM, "https://example.com/p.jpg") == body
    await service.aclose()


async def test_an_unknown_source_is_a_refusal(service):
    """Ручная карточка обложку не скачивает: адреса у неё нет, и клиента тоже."""
    result = await service.fetch(Source.MANUAL, "https://example.com/p.jpg")

    assert isinstance(result, Refusal)
    assert result.source == "poster:manual"


async def test_a_downloaded_poster_is_stored_byte_for_byte(service):
    """Обрезается только залитое с диска: скачанное ложится как приехало."""
    data = await service.fetch(Source.TMDB, "https://example.com/poster.jpg")
    await service.save(1, data, now=WHEN)

    assert await service._store.get(1) == data


async def test_an_upload_is_cropped(service):
    """Залитая с диска — единственное, что обрезается."""
    await service.store_upload(1, picture(4000, 1000), now=WHEN)

    stored = await service._store.get(1)
    assert Image.open(io.BytesIO(stored)).size == TARGET_SIZE


async def test_a_bad_upload_is_a_named_error(service):
    with pytest.raises(BadImage):
        await service.store_upload(1, "не картинка".encode(), now=WHEN)

    assert await service._store.get(1) is None, "в хранилище лёг мусор"


async def test_closing_the_service_closes_the_store(tmp_path):
    """Хранилище — второй файл базы, и его тоже закрывает сервис. Проверяется
    удалением файла: открытую базу Windows удалить не даёт, и именно об этот
    отказ спотыкается прогон, если файл кто-то держит."""
    path = tmp_path / "posters.db"
    store = PosterStore(path)
    await store.open()
    service = poster_service(store, responding(content=POSTER))
    await service.save(1, POSTER, now=WHEN)

    await service.aclose()

    path.unlink()


def test_every_source_but_the_manual_one_downloads_posters():
    """Набор источников обложек выводится из перечисления, а не переписывается
    списком.

    Правило простое и записано у самой константы: обложку негде скачивать
    только у ручной карточки — она ниоткуда не приезжала. Всё остальное её
    имеет, и у old-games.ru она есть у 71–82% игр, то есть это одно из двух
    полей, ради которых источник и выбран.

    Сторожа у выпадения источника из набора не было: оба существующих
    **перебирают сам набор**, и укоротившийся на строку он оставлял их
    зелёными, а обложки не скачивались бы вовсе."""
    assert set(POSTER_SOURCES) == set(Source) - {Source.MANUAL}
    assert len(POSTER_SOURCES) == len(set(POSTER_SOURCES)), "повтор в наборе"


async def test_closing_the_service_closes_every_client(posters):
    """Клиентов у сервиса три, и закрыть надо каждого: незакрытый держит
    соединение до конца работы приложения.

    Закрытость видна по отказу: незакрытый клиент отдал бы байты. Исключением
    она наружу не выходит — `fetch` его не выпускает, и это проверено рядом."""
    service = poster_service(posters, responding(content=POSTER))
    await service.aclose()

    for source in POSTER_SOURCES:
        assert isinstance(
            await service.fetch(source, "https://example.com/poster.jpg"),
            Refusal,
        )
