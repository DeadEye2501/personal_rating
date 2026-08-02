"""Теги Steam: отдельный запрос, три состояния ответа и сверка номера."""

import json

import httpx
import pytest

from backend.model import Found, GenreSource, Kind
from backend.sources.http import SourceHttp
from backend.sources.steam.client import SteamClient
from backend.sources.steam.parse import parse_tags


def test_tags_arrive_in_their_own_space(fixture):
    """Жанр и тег у Steam нумеруются порознь: `9` — это жанр «Гонки» и тег
    «Стратегия». Пространство обязано ехать вместе с номером, иначе стратегия
    молча получит гонки."""
    tags = parse_tags(fixture("steam/store_items.json"), "292030")

    assert tags
    assert all(
        space is GenreSource.STEAM_TAG and ext_id.isdigit() for space, ext_id in tags
    )

def test_a_tag_is_its_number_and_not_its_weight(fixture):
    """Номера тегов сверяются с записанным ответом: рядом с `tagid` в том же
    объекте лежит `weight`, тоже целое, и подмена одного другим проверку «цифры
    и пространство» проходит молча. В базу тогда уедут веса под видом номеров —
    и совпадут с чужими жанрами."""
    payload = fixture("steam/store_items.json")
    recorded = payload["response"]["store_items"][0]["tags"]

    numbers = [ext_id for _, ext_id in parse_tags(payload, "292030")]

    assert numbers == [str(one["tagid"]) for one in recorded]
    assert numbers != [str(one["weight"]) for one in recorded]

def test_an_answer_without_items_is_a_breakage(fixture):
    """Ответ без `store_items` — это «мы спросили неправильно», а не «тегов
    нет». Так Steam отвечает на пустой `ids`.

    Разница не косметическая: на тегах держатся 177 соответствий справочника из
    326, и молчаливое «тегов нет» кладёт в базу обеднённую игру навсегда —
    перезапроса у игр не бывает вовсе.

    Пустой список проверяется рядом с отсутствующим ключом нарочно: это разные
    ответы, а `items[0]` на пустом даёт `IndexError`, которого нет в наборе
    разбора — он ушёл бы из клиента через границу потоков."""
    with pytest.raises(ValueError, match="store_items"):
        parse_tags(fixture("steam/store_items_empty.json"), "292030")

    with pytest.raises(ValueError, match="store_items"):
        parse_tags({"response": {"store_items": []}}, "292030")

def test_a_game_without_tags_is_an_answer_and_not_a_breakage():
    """Обратная сторона: своя игра, `success: 1`, и тегов у неё нет. Это ответ,
    и пустой набор здесь законен.

    Без этой проверки граница наблюдалась бы только со стороны поломки, и
    «нет тегов — тоже промах» прошло бы молча: карточка потеряла бы жанры
    магазина заодно с тегами."""
    payload = {"response": {"store_items": [{"appid": 292030, "success": 1}]}}

    assert parse_tags(payload, "292030") == ()

async def test_the_card_carries_both_spaces(replay, fixture):
    """Клиент доливает теги к жанрам: без них у игры остаётся один-два общих
    жанра из двенадцати, какие есть у Steam на весь магазин."""
    appid = next(iter(fixture("steam/appdetails.json")))
    client = SteamClient(
        SourceHttp(
            "steam",
            transport=replay("steam/appdetails.json", "steam/store_items.json"),
        )
    )

    result = await client.card(appid, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    spaces = {space for space, _ in result.value.genre_ext_ids}
    assert spaces == {GenreSource.STEAM, GenreSource.STEAM_TAG}

async def test_tags_that_did_not_arrive_do_not_break_the_card(
    replay, fixture, caplog
):
    """Отказ на тегах меняет карточку, а не роняет её: жанры уже собраны.

    Молчать при этом нельзя: карточка с одним жанром вместо двадцати выглядит
    исправной, и без записи в лог причину не найти никогда."""
    appid = next(iter(fixture("steam/appdetails.json")))
    client = SteamClient(
        SourceHttp(
            "steam",
            transport=replay("steam/appdetails.json", "steam/store_items_broken.txt"),
        )
    )

    with caplog.at_level("WARNING"):
        result = await client.card(appid, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert {space for space, _ in result.value.genre_ext_ids} == {GenreSource.STEAM}
    assert "400" in caplog.text, "код отказа на тегах не записан"

async def test_an_empty_tag_answer_leaves_a_trace(replay, fixture, caplog):
    """Карточку это не роняет — жанры магазина уже собраны, — но в логе обязано
    остаться, почему у игры их один-два вместо двадцати. Иначе обеднённая
    карточка выглядит исправной, и причину не найти никогда."""
    appid = next(iter(fixture("steam/appdetails.json")))
    client = SteamClient(
        SourceHttp(
            "steam",
            transport=replay("steam/appdetails.json", "steam/store_items_empty.json"),
        )
    )

    with caplog.at_level("WARNING"):
        result = await client.card(appid, Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert {space for space, _ in result.value.genre_ext_ids} == {GenreSource.STEAM}
    assert "store_items" in caplog.text, "причина обеднённых жанров не записана"

async def test_a_hidden_game_is_a_breakage_and_not_an_absence(fixture):
    """`success: 15` — тоже наш промах, а не ответ «тегов нет». Тем же кодом
    Steam отвечает на **существующую** игру при неверном `country_code`, и
    принять его за пустой набор значит обеднить каждую игру разом и молча.

    Ловушка здесь в том, что `success` у тегов — число: `if item["success"]`
    посчитало бы `15` удачей. Второе значение проверяется рядом с записанным
    пятнадцатым: удача — это ровно единица, а не «не пятнадцать»."""
    with pytest.raises(ValueError, match="15"):
        parse_tags(fixture("steam/store_items_missing.json"), "999999999")

    with pytest.raises(ValueError, match="2"):
        parse_tags({"response": {"store_items": [{"appid": 292030,
                                                  "success": 2}]}}, "292030")

def test_tags_about_another_game_are_refused(fixture):
    """Ответ приходит списком, запрос уходит списком, а берётся из него первый
    попавшийся: подставь Steam чужую строку — и в жанры игры уедут теги соседней.

    Сверяется именно `appid`, а не соседний `id`: в записанном ответе они равны,
    и подмена одного другим прошла бы молча. И сверяется равенство, а не начало
    строки — голое число началом строки этот проект уже принимал."""
    with pytest.raises(ValueError, match="424242"):
        parse_tags(fixture("steam/store_items.json"), "424242")

    tags = {"tags": [{"tagid": 1}]}
    with pytest.raises(ValueError, match="777"):
        parse_tags({"response": {"store_items": [
            {"id": 777, "appid": 999, "success": 1, **tags}]}}, "777")

    with pytest.raises(ValueError, match="29203"):
        parse_tags({"response": {"store_items": [
            {"id": 292030, "appid": 292030, "success": 1, **tags}]}}, "29203")

async def test_the_tag_request_asks_the_way_that_answers(fixture):
    """`country_code: RU` отдаёт пустой ответ с `visible: false` — проверено
    живьём. Подменить его на RU значит молча лишить тегов все игры разом, и
    заметить это можно будет только по обеднённой карточке."""
    asked = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request.url)
        if "appdetails" in str(request.url):
            return httpx.Response(200, json=fixture("steam/appdetails.json"))
        return httpx.Response(200, json=fixture("steam/store_items.json"))

    client = SteamClient(SourceHttp("steam", transport=httpx.MockTransport(handler)))
    await client.card("292030", Kind.GAME)
    await client.aclose()

    card_url, tags_url = asked
    assert "l=russian" in str(card_url), "карточка запрошена не по-русски"
    wanted = json.loads(tags_url.params["input_json"])
    assert wanted["context"]["country_code"] == "US"
    assert wanted["data_request"]["include_tag_count"] > 0
    assert wanted["ids"] == [{"appid": 292030}]

async def test_the_client_checks_the_tags_against_what_it_asked(fixture, caplog):
    """Сверка номера наблюдается через клиент, а не только вызовом разбора с
    чужим номером: в клиенте она держится на том, что он передаёт **свой**
    довод. Литерал вместо него — или сверка ответа с самим собой — прошли бы
    молча, а в жанры игры уехали бы теги соседней.

    Ответ собирается здесь, а не фикстурой: живой Steam на однокарточный запрос
    чужого не отдаёт, и записывать нечего."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "appdetails" in str(request.url):
            return httpx.Response(200, json=fixture("steam/appdetails.json"))
        alien = fixture("steam/store_items.json")
        alien["response"]["store_items"][0]["appid"] = 999999
        return httpx.Response(200, json=alien)

    client = SteamClient(SourceHttp("steam", transport=httpx.MockTransport(handler)))
    with caplog.at_level("WARNING"):
        result = await client.card("292030", Kind.GAME)
    await client.aclose()

    assert isinstance(result, Found)
    assert {space for space, _ in result.value.genre_ext_ids} == {GenreSource.STEAM}
    assert "999999" in caplog.text, "чужой ответ на теги не записан"
