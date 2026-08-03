"""Ответ `GetItems`: род товара в выдаче и настоящий адрес обложки."""

import json

import httpx

from backend.model import Found, Kind
from backend.sources.http import SourceHttp
from backend.sources.steam.client import SteamClient
from backend.sources.steam.parse import ASSETS, parse_tags, poster_url

FOUND = [
    {"appid": "292030", "name": "The Witcher 3: Wild Hunt"},
    {"appid": "2684660", "name": "The Witcher 3 REDkit"},
    {"appid": "500810", "name": "Arcanum: Of Steamworks and Magick Obscura"},
    {"appid": "4926960", "name": "Arcanum Collegium Playtest"},
]


def two_answers(first: list | dict, items, opens: str = "SearchApps"):
    """Транспорт на два запроса: свой у поиска и у карточки, а второй у обоих
    один — `GetItems`. Он тут не украшение: без него ни выдача не собирается,
    ни адрес обложки не берётся."""
    asked = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request.url)
        if opens in str(request.url):
            return httpx.Response(200, json=first)
        return items(request)

    return httpx.MockTransport(handler), asked


async def searched(transport: httpx.MockTransport, query: str = "arcanum"):
    client = SteamClient(SourceHttp("steam", transport=transport))
    result = await client.search(query, Kind.GAME)
    await client.aclose()
    return result


def assets_of(payload: dict, appid: str) -> dict:
    row = next(one for one in payload["response"]["store_items"]
               if str(one["appid"]) == appid)
    return row["assets"]


async def test_only_what_the_store_called_a_game_stays(fixture):
    """Род товара приезжает числом: `0` игра, `6` инструмент, `12` playtest.
    Ни `SearchApps`, ни `appdetails` его не различают — у REDkit в карточке
    стоит `type: 'game'`, то есть по ней инструмент от игры не отличить.

    Отсев обязан стоять до показа: по решению плана 12 показанная строка
    пишется в базу сама, и мелькнувший playtest успел бы завестись."""
    payload = fixture("steam/store_items_many.json")
    kinds = {str(one["appid"]): one["type"]
             for one in payload["response"]["store_items"]}
    assert kinds == {"292030": 0, "2684660": 6, "500810": 0, "4926960": 12}

    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))
    result = await searched(transport)

    assert isinstance(result, Found)
    assert [hit.source_id for hit in result.value] == ["292030", "500810"]


async def test_the_kind_request_asks_about_every_found_appid(fixture):
    """Спросить про первого и отсеять по нему всех — тихая потеря: остальные
    остались бы неизвестного рода. Номера уходят числами: в выдаче поиска
    `appid` приходит строкой, а `GetItems` на строку отвечает пустотой."""
    payload = fixture("steam/store_items_many.json")
    transport, asked = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))

    await searched(transport)

    wanted = json.loads(asked[1].params["input_json"])
    assert wanted["ids"] == [{"appid": 292030}, {"appid": 2684660},
                             {"appid": 500810}, {"appid": 4926960}]
    assert wanted["data_request"]["include_assets"] is True


async def test_the_search_row_carries_the_year_the_game_came_out(fixture):
    """Год выдачи — тот, когда игра вышла, а не когда попала в магазин.

    Нужен он склейке: годы, разошедшиеся больше чем на люфт, означают разные
    игры, и магазинная дата сделала бы разными игру и её же саму.

    Свидетель нарочно старый: у `Arcanum` даты разные — 2001 против 2016, — и
    подмена одной другой видна. У ровесника Steam они совпадают, и такой
    свидетель ничего бы не сторожил."""
    payload = fixture("steam/store_items_many.json")
    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))

    result = await searched(transport)

    years = {one.source_id: one.year for one in result.value}
    assert years["500810"] == 2001


async def test_a_search_row_born_on_steam_takes_the_store_year(fixture):
    """У игры, вышедшей сразу в Steam, `original_release_date` пуст, и брать
    оттуда нечего — остаётся магазинная дата, и она же верная.

    Без этой половины «берём год выхода» неотличимо от «оставляем без года
    всех, у кого второй даты нет», а без года строка не возражает против
    склейки вовсе."""
    payload = fixture("steam/store_items_many.json")
    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))

    result = await searched(transport)

    years = {one.source_id: one.year for one in result.value}
    assert years["292030"] == 2015


async def test_the_search_asks_for_the_release_date(fixture):
    """Дата приезжает только если её попросили, и просит её тот же запрос, что
    уже уходит ради рода товара и обложек.

    Сторожится сам запрос: записанный ответ отдаётся независимо от параметров,
    и снятый флаг оставил бы весь набор зелёным — ровно так же, как однажды на
    пути карточки."""
    payload = fixture("steam/store_items_many.json")
    transport, asked = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))

    await searched(transport)

    wanted = json.loads(asked[1].params["input_json"])
    assert wanted["data_request"]["include_release"] is True


async def test_an_impossible_date_does_not_cancel_the_whole_list(fixture, caplog):
    """Штамп времени вне календаря даёт не `ValueError`, а `OSError`, и это
    замерено: `datetime.fromtimestamp(10**12)` падает `[Errno 22]`.

    До того как год приехал в выдачу, щель была величиной в одну карточку без
    года. Теперь разбор даты стоит внутри отсева, то есть на пути **всей** выдачи
    Steam, и незнакомое исключение унесло бы её целиком — а из клиента наружу не
    должно выйти ни одного."""
    payload = fixture("steam/store_items_many.json")
    for one in payload["response"]["store_items"]:
        one["release"] = {"original_release_date": 10 ** 12}

    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))
    with caplog.at_level("WARNING"):
        result = await searched(transport)

    assert isinstance(result, Found)
    assert len(result.value) == len(FOUND)
    assert "steam" in caplog.text, "неразобранная дата не записана"


async def test_a_refused_kind_request_does_not_cancel_the_results():
    """Потерять настоящую игру хуже, чем показать лишнее дополнение."""
    transport, _ = two_answers(FOUND, lambda _: httpx.Response(429, text="slow down"))

    result = await searched(transport)

    assert isinstance(result, Found)
    assert [hit.source_id for hit in result.value] == [
        one["appid"] for one in FOUND
    ]


async def test_a_kind_answer_that_is_not_json_leaves_the_list_whole(caplog):
    """Код 200, а тело — страница. Так отвечает не сам Steam, а периметр перед
    ним, и разбор на этом падает не `ValueError`, а чем придётся: наружу из
    клиента не должно выйти ни исключения, ни укороченной выдачи."""
    transport, _ = two_answers(
        FOUND, lambda _: httpx.Response(200, text="<html>nope</html>"))

    with caplog.at_level("WARNING"):
        result = await searched(transport)

    assert isinstance(result, Found)
    assert len(result.value) == len(FOUND)
    assert "GetItems" in caplog.text, "неразобранный ответ не записан"


async def test_a_row_without_a_kind_stays(fixture):
    """Ответ про товар, но без рода товара. Молчание о роде — не «род не игра»:
    считать иначе значит терять настоящие игры на форме ответа, которую никто не
    замерял."""
    payload = fixture("steam/store_items_many.json")
    rows = payload["response"]["store_items"]
    payload["response"]["store_items"] = [
        {k: v for k, v in row.items() if k != "type"} for row in rows
    ]
    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))

    result = await searched(transport)

    assert isinstance(result, Found)
    assert [hit.source_id for hit in result.value] == [
        one["appid"] for one in FOUND
    ]


async def test_a_broken_kind_answer_leaves_a_trace(caplog):
    """Ответ 200, а внутри не то. Выдача при этом остаётся целой, и молчать
    нельзя: полная выдача с дополнениями выглядит исправной."""
    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json={"нет": 1}))

    with caplog.at_level("WARNING"):
        result = await searched(transport)

    assert isinstance(result, Found)
    assert len(result.value) == len(FOUND)
    assert "store_items" in caplog.text, "причина несостоявшегося отсева не записана"


async def test_a_row_the_store_kept_silent_about_stays(fixture):
    """Steam ответил не про всех. Молчание — не «это не игра»."""
    payload = fixture("steam/store_items_many.json")
    payload["response"]["store_items"] = [
        one for one in payload["response"]["store_items"]
        if str(one["appid"]) != "500810"
    ]
    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))

    result = await searched(transport)

    assert isinstance(result, Found)
    assert [hit.source_id for hit in result.value] == ["292030", "500810"]
    kept = next(hit for hit in result.value if hit.source_id == "500810")
    assert kept.poster_url == poster_url("500810")


async def test_the_cover_address_is_built_from_the_answer(fixture):
    """Угаданный шаблон неверен у 38% строк: замерено, что у «Arcanum» файла
    `library_600x900_2x.jpg` нет вовсе, а `portrait.png` отвечает.

    Имя файла берётся из ответа, а не собирается по шаблону, и подставляется в
    `asset_url_format` — в нём живёт и номер игры, и метка времени."""
    payload = fixture("steam/store_items_many.json")
    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))

    result = await searched(transport)

    addresses = {hit.source_id: hit.poster_url for hit in result.value}
    for appid in ("292030", "500810"):
        assets = assets_of(payload, appid)
        name = assets.get("library_capsule_2x") or assets["library_capsule"]
        assert addresses[appid].endswith(
            assets["asset_url_format"].replace("${FILENAME}", name)
        )
        assert addresses[appid].startswith("https://")

    assert addresses["500810"] != poster_url("500810"), "адрес остался угаданным"


async def test_the_double_size_cover_wins_over_the_single(fixture):
    """У «Ведьмака 3» в ответе лежат обе: `library_600x900_russian.jpg` и
    `..._2x.jpg`. Без `_2x` приезжает 300×450 — вдвое меньше своего имени."""
    payload = fixture("steam/store_items_many.json")
    assets = assets_of(payload, "292030")
    assert assets["library_capsule"] != assets["library_capsule_2x"]
    transport, _ = two_answers(FOUND, lambda _: httpx.Response(200, json=payload))

    result = await searched(transport)

    address = next(hit.poster_url for hit in result.value
                   if hit.source_id == "292030")
    assert address.endswith(assets["library_capsule_2x"] + "?t=1768303991")


async def test_a_game_without_assets_keeps_the_guessed_address():
    """Не приехал блок картинок — остаётся угаданный адрес: он верен в 62%
    случаев, и это лучше, чем карточка без обложки вовсе.

    Рядом стоит дополнение, и оно обязано уйти: без него тот же угаданный адрес
    остался бы и при отсеве, развалившемся целиком, — а разницы не видно."""
    bare = {"response": {"store_items": [
        {"appid": 292030, "success": 1, "type": 0},
        {"appid": 2684660, "success": 1, "type": 4},
    ]}}
    transport, _ = two_answers(FOUND[:2], lambda _: httpx.Response(200, json=bare))

    result = await searched(transport)

    assert isinstance(result, Found)
    assert [hit.source_id for hit in result.value] == ["292030"]
    assert result.value[0].poster_url == poster_url("292030")


async def test_a_game_the_store_would_not_talk_about_stays(fixture):
    """Отговорка — не «это не игра». Замерено 03.08.2026: на живую «Ведьмак 3»
    при `country_code: RU` приезжает `success: 15`, `visible: false` и **без
    поля `type`**; та же форма записана в фикстуре про несуществующий appid.

    Считать её родом «не игра» значит выбросить настоящую игру, снятую с витрины
    или недоступную в стране запроса, — а при неверном контексте сразу все, и
    игровой поиск опустел бы целиком при зелёном наборе."""
    row = fixture("steam/store_items_missing.json")["response"]["store_items"][0]
    assert row["success"] != 1 and "type" not in row

    hidden = {"response": {"store_items": [{**row, "appid": 292030}]}}
    transport, _ = two_answers(FOUND[:1],
                               lambda _: httpx.Response(200, json=hidden))

    result = await searched(transport)

    assert isinstance(result, Found)
    assert [hit.source_id for hit in result.value] == ["292030"]


async def test_the_card_takes_cover_and_tags_from_one_answer(replay, fixture):
    """Адрес обложки уезжает в базу навсегда: перезапроса у игр не бывает, а
    хранилище качает недостающую картинку именно по нему. Угаданный, неверный у
    38% игр, оставил бы там мёртвую ссылку — и привязка по вставленной ссылке
    качала бы по ней же.

    Записан ответ на **парный** запрос, а не два половинчатых: на пару Steam мог
    бы ответить иначе, и проверка на половинках проверяла бы не тот путь.
    Обложка и теги смотрятся вместе по той же причине — запрос-то один, и
    потерять любую половину можно, не тронув другую."""
    appid = next(iter(fixture("steam/appdetails.json")))
    assets = assets_of(fixture("steam/store_items_card.json"), appid)
    client = SteamClient(SourceHttp("steam", transport=replay(
        "steam/appdetails.json", "steam/store_items_card.json")))

    result = await client.card(appid, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.poster_url != poster_url(appid)
    assert result.value.item.poster_url.startswith(ASSETS)
    assert result.value.item.poster_url.endswith(assets["library_capsule_2x"]
                                                 + "?t=1768303991")
    tagged = parse_tags(fixture("steam/store_items_card.json"), appid)
    assert tagged, "фикстура без тегов — проверять нечего"
    assert set(tagged) <= set(result.value.genre_ext_ids), \
        "теги потерялись из общего с обложкой ответа"


async def test_the_card_asks_for_covers_and_tags_at_once(fixture):
    """Один запрос на двоих — решение, а не совпадение, и держится оно на том,
    что в нём просят обе вещи.

    Наблюдается по запросу: записанный ответ несёт `assets` независимо от того,
    просили их, — снимешь `include_assets`, и на фикстуре ничего не изменится, а
    на живом Steam у каждой заводимой игры уедет в базу угаданный адрес."""
    payload = fixture("steam/store_items_card.json")
    transport, asked = two_answers(fixture("steam/appdetails.json"),
                                   lambda _: httpx.Response(200, json=payload),
                                   opens="appdetails")
    client = SteamClient(SourceHttp("steam", transport=transport))

    await client.card("292030", Kind.GAME)
    await client.aclose()

    wanted = json.loads(asked[1].params["input_json"])["data_request"]
    assert wanted["include_assets"] is True
    assert wanted["include_tag_count"] > 0


async def test_a_card_the_store_kept_quiet_about_keeps_the_guessed_cover(replay):
    """Обратная сторона: `GetItems` не ответил — адрес остаётся тем, что собрала
    карточка. Пустая строка вместо него оставила бы игру без обложки вовсе."""
    client = SteamClient(SourceHttp("steam", transport=replay(
        "steam/appdetails.json", "steam/store_items_empty.json")))

    result = await client.card("292030", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.poster_url == poster_url("292030")


async def test_an_empty_search_asks_nobody_about_kinds():
    """Пустой `ids` Steam понимает как «спросили неправильно» и отвечает без
    `store_items` — то есть запись в лог о поломке на каждый ненайденный
    запрос."""
    transport, asked = two_answers([], lambda _: httpx.Response(200, json={}))

    result = await searched(transport, "zzqqxxnotagame123")

    assert isinstance(result, Found)
    assert result.value == []
    assert len(asked) == 1, "за родом товара сходили, не найдя ни одной строки"


async def test_the_card_takes_the_year_the_game_came_out(replay):
    """Год выхода игры, а не год её появления в Steam.

    `appdetails` отдаёт магазинную дату, и у старых игр она врёт на десятилетия.
    Замерено на живом API 03.08.2026: `Fallout` — 2015 против 1997, `Fallout 2`
    — 2009 против 1998, `Arcanum` — 2016 против 2001, `DOOM + DOOM II` — 2007
    против 1995.

    Верная дата лежит в том же ответе `GetItems`, который карточка уже
    спрашивает ради тегов и обложки. Пишется год навсегда: перезапроса у игр не
    бывает.

    Свидетель нарочно старый: у игры, вышедшей сразу в Steam, обе даты совпадают
    и подмена одной другой прошла бы незамеченной. У «Ведьмака 3»
    `original_release_date` вовсе пуст — на этом и держится вторая половина
    проверки ниже."""
    client = SteamClient(SourceHttp("steam", transport=replay(
        "steam/appdetails_old_game.json", "steam/store_items_release.json")))

    result = await client.card("38400", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.year == 1997


async def test_a_game_born_on_steam_keeps_the_store_year(replay):
    """У игры, вышедшей сразу в Steam, `original_release_date` приходит нулём —
    не отсутствует, а именно `0`, замерено, — и берётся магазинная дата.

    Без этой половины «берём год выхода» неотличимо от «обнуляем год всем, у
    кого второй даты нет».

    **Чего эта проверка не различает:** пришёл ли 2015-й от `appdetails` или от
    магазинной даты `GetItems`. У одной и той же игры это всегда один год, и
    свидетеля, где они разошлись бы, не существует. Замерено, что переход на
    запас поведение карточки не изменил; сам запас наблюдается на пути выдачи,
    где года у строки не было вовсе."""
    client = SteamClient(SourceHttp("steam", transport=replay(
        "steam/appdetails.json", "steam/store_items_card.json")))

    result = await client.card("292030", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert result.value.item.year == 2015


async def test_the_card_asks_for_the_release_date(fixture):
    """Дата выхода приезжает только если её попросили: `include_release` в
    запросе `GetItems`.

    Сторожится сам запрос, потому что записанные ответы отдаются по порядку и
    параметров не смотрят — без этой проверки снятый флаг оставлял весь набор
    зелёным, а в базу каждой заводимой игры уезжал магазинный год. Навсегда:
    перезапроса у игр не бывает."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params.get("input_json"))
        name = ("steam/appdetails_old_game.json" if len(seen) == 1
                else "steam/store_items_release.json")
        return httpx.Response(200, json=fixture(name))

    client = SteamClient(SourceHttp("steam", transport=httpx.MockTransport(handler)))
    await client.card("38400", Kind.GAME)
    await client.aclose()

    asked = json.loads(seen[1])
    assert asked["data_request"]["include_release"] is True
