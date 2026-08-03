"""Правила справочника: набор чужих меток на входе, набор наших жанров на выходе.

Проверяется следствие, а не объявление: правила берутся из базы, поднятой
миграциями, и прикладываются к набору меток целиком. Одиночная метка врёт —
ради этого правила и заводились, — и увидеть это можно только на наборе."""

import pytest

from backend.model import GenreSource
from backend.service.genres import matched
from backend.sources.gog.parse import SPELLING, parse_catalog
from backend.sources.steam.parse import GENRE_TWIN, parse_card
from backend.storage.repository.genres import GenresRepository
from backend.storage.session import create_engine, session_factory
from tests.alembic_runner import alembic


@pytest.fixture(scope="module")
def stocked(tmp_path_factory):
    """База со справочником, поднятая миграциями один раз на весь модуль:
    справочник тут и есть предмет проверки, а `alembic` идёт отдельным
    процессом и стоит секунды."""
    db_path = tmp_path_factory.mktemp("reference") / "library.db"
    alembic(db_path, "upgrade", "head")
    return db_path


@pytest.fixture
async def book(stocked):
    """Правила одного пространства из настоящего справочника."""
    engine = create_engine(stocked)
    repository = GenresRepository(session_factory(engine))
    yield repository.rules
    await engine.dispose()


def names(genres) -> list[str]:
    return sorted(genre.name for genre in genres)


async def test_action_and_rpg_together_give_only_action_rpg(book):
    """Пара `19` Action и `122` RPG — это Action-RPG целиком, а не три жанра.

    Сверяется весь набор, а не вхождение: с проверкой «Action-RPG среди
    найденных» рядом молча остались бы и Action, и RPG."""
    assert names(matched(await book(GenreSource.STEAM), {"19", "122"})) == [
        "Action-RPG"
    ]


async def test_action_and_jrpg_behave_the_same_as_action_and_rpg(book):
    """`4434` JRPG отдельным жанром не заводится и в паре ведёт себя как `122`."""
    assert names(matched(await book(GenreSource.STEAM), {"19", "4434"})) == [
        "Action-RPG"
    ]


async def test_rpg_without_action_stays_rpg(book):
    """Запрет односторонний: без `19` ролевая остаётся ролевой."""
    assert names(matched(await book(GenreSource.STEAM), {"122"})) == ["RPG"]


async def test_the_action_rpg_tag_puts_out_its_parts(book):
    """`4231` гасит `19`, `122` и `4434`: игра с этим тегом получает только
    Action-RPG, даже если все три стоят рядом."""
    found = matched(await book(GenreSource.STEAM), {"4231", "19", "122", "4434"})
    assert names(found) == ["Action-RPG"]


async def test_adventure_alone_is_a_quest(book):
    """`21` Adventure в одиночестве — квест."""
    assert names(matched(await book(GenreSource.STEAM), {"21"})) == ["Quest"]


async def test_adventure_next_to_another_mark_gives_nothing(book):
    """Рядом с ролевой `21` не даёт ничего: приключенческого в игре сколько
    угодно, а квестом она от этого не становится."""
    assert names(matched(await book(GenreSource.STEAM), {"21", "122"})) == ["RPG"]


async def test_a_dungeon_crawler_is_an_rpg(book):
    """`1720` Dungeon Crawler — подземельная ролевая, а не рогалик: замерено,
    что рогаликом помечены 38% таких игр, и все они несут свою метку."""
    assert names(matched(await book(GenreSource.STEAM), {"1720"})) == ["RPG"]


async def test_a_dungeon_crawler_next_to_a_roguelite_is_not_an_rpg(book):
    """`3959` Roguelite рядом отменяет ролевую: это те самые 38%."""
    assert names(matched(await book(GenreSource.STEAM), {"1720", "3959"})) == [
        "Roguelike"
    ]


async def test_an_unknown_neighbour_does_not_put_out_a_lonely_rule(book):
    """Соседей правило одиночества считает по справочнику, а не по ответу
    магазина: тегов у Steam 446, а в справочнике 211, и незнакомая соседка
    квеста не отменяет. Считай оно все присланные метки — `21` не сработало бы
    почти никогда."""
    assert names(matched(await book(GenreSource.STEAM), {"21", "99999999"})) == [
        "Quest"
    ]


async def test_a_neighbour_that_is_forbidden_nowhere_still_puts_it_out(book):
    """Соседом считается любая метка справочника, а не только та, что стоит в
    правиле запретом: `4474` CRPG нигде не запрещена, и всё же гасит одинокое
    `21`.

    Метка выбрана нарочно такая: у `122`, которым соседство проверяется в
    остальных тестах, запреты есть, и счёт «известного» по одним лишь запретам
    прошёл бы там молча."""
    assert names(matched(await book(GenreSource.STEAM), {"21", "4474"})) == ["RPG"]


async def test_an_unknown_mark_is_dropped_without_a_word(book, caplog):
    """Незнакомое молча отбрасывается и знакомому не мешает."""
    with caplog.at_level("DEBUG"):
        found = matched(await book(GenreSource.STEAM), {"122", "99999999"})
    assert names(found) == ["RPG"]
    assert [one for one in caplog.records if one.name.startswith("backend")] == []


async def test_nothing_marked_is_nothing_found(book):
    assert matched(await book(GenreSource.STEAM), set()) == []


# Живые наборы: знакомые справочнику метки двух игр, снятые со Steam 03.08.2026.
# Ради них правила и заводились — одиночная метка на таком наборе врёт.
FALLOUT = {"122", "21", "4474"}
STARDEW = {"10235", "122", "15564", "1643", "1702", "22602", "3859", "599",
           "87918", "9551"}


async def test_the_fallout_set_is_an_rpg_and_nothing_else(book):
    """Хвостовое «Приключение» (`21`, вес 248 из 1328) не превращает Fallout 2 в
    квест: рядом стоят `122` и `4474`, и правило одиночества не срабатывает.
    Поштучный перевод дал бы ей Quest."""
    assert names(matched(await book(GenreSource.STEAM), FALLOUT)) == ["RPG"]


async def test_the_stardew_set_is_a_simulator_with_role_playing(book):
    """Stardew Valley — симулятор, и `RPG` она получает нарочно: тег `122` весит
    685 из 858, никакой порог по весу его не срежет, а ролевые элементы в игре
    правда есть.

    `Survival` приезжает от `1702` Crafting, а не от песочницы: `3810` Sandbox
    выброшен из справочника совсем — им Fallout 2 и Stardew Valley обе стали бы
    выживанием."""
    assert names(matched(await book(GenreSource.STEAM), STARDEW)) == [
        "Multiplayer", "RPG", "Simulator", "Sport", "Strategy", "Survival"
    ]


async def test_the_gog_book_reads_the_same_rules(book):
    """Форма правила одна на все источники: у GOG `action` с `rpg` тоже дают
    один Action-RPG, хотя метки у него слаги, а не числа."""
    assert names(matched(await book(GenreSource.GOG), {"action", "rpg"})) == [
        "Action-RPG"
    ]


async def test_the_old_games_book_has_no_combinations(book):
    """У old-games.ru жанр у игры ровно один, и правило состоит из одной
    метки: `Adventure` сведён в квест сознательно."""
    assert names(matched(await book(GenreSource.OLD_GAMES), {"Adventure"})) == [
        "Quest"
    ]


async def test_the_books_of_two_sources_do_not_leak_into_each_other(book):
    """`19` у Steam — это Action, а у GOG такой метки нет вовсе."""
    assert matched(await book(GenreSource.GOG), {"19"}) == []


# Что каждый жанр Steam значит у нас. Таблица держится отдельно от боевой
# `GENRE_TWIN` нарочно: та переводит номер жанра в номер тега, и проверить её
# членством значений нельзя — перестановка `9` и `18` оставляет набор тем же.
STEAM_GENRES = {
    "1": "Action",
    "2": "Strategy",
    "3": "RPG",
    "9": "Racing",
    "18": "Sport",
    "25": "Quest",
    "28": "Simulator",
    "29": "Multiplayer",
}


def test_the_table_of_steam_genres_did_not_grow():
    """Проверка выше идёт по рукописной таблице теста, поэтому **добавленную** в
    боевую строку она не увидит вовсе. Комментарий у `GENRE_TWIN` прямо
    утверждает, что жанр несут ровно эти восемь из двенадцати, и не сторожит
    этого ничто: припиши туда «Инди» — и каждая инди-игра получит Action.

    Сверяются ключи, а не значения: значения ловит проверка ниже, привязкой."""
    assert set(GENRE_TWIN) == set(STEAM_GENRES)


@pytest.mark.parametrize(("genre_id", "expected"), sorted(STEAM_GENRES.items()))
async def test_a_steam_genre_leads_to_the_genre_it_names(book, genre_id, expected):
    """Жанр магазина проходит весь путь: разбор ответа переводит его в номер
    тега-двойника, справочник — в наш жанр. Сторожатся обе половины разом, и
    сторожатся **привязкой**, а не набором.

    Ради этого теста и таблица, и проверка стоят порознь. Поменяй в `GENRE_TWIN`
    местами `9` и `18` — набор значений не изменится, а гоночная игра без тегов
    уедет в базу спортивной; перезапроса у игр не бывает вовсе."""
    card = parse_card({"steam_appid": 1, "name": "и", "genres": [{"id": genre_id}]})
    marks = {ext_id for _space, ext_id in card.genre_ext_ids}

    assert names(matched(await book(GenreSource.STEAM), marks)) == [expected]


# Написания GOG поимённо. Проверка ниже идёт по самой `SPELLING`, поэтому
# **удаление** строки для неё незаметно: параметров станет на один меньше, и
# только. А удаление стоит жанра — сотри `role-playing`, и игра, у которой GOG
# отдал ролевую жанром, а не тегом, перестаёт получать `Action-RPG`.
FROZEN_SPELLING = {
    "point-and-click": "pointandclick",
    "team-sport": "teamsport",
    "virtual-life": "virtuallife",
    "roguelike": "rougelike",
    "role-playing": "rpg",
}


def test_the_table_of_gog_spellings_did_not_shrink():
    assert SPELLING == FROZEN_SPELLING


@pytest.mark.parametrize(("written", "canonical"), sorted(SPELLING.items()))
async def test_a_gog_spelling_leads_somewhere(book, written, canonical):
    """Второе написание метки GOG приводится к тому, которое знает справочник, —
    и то, к чему привели, обязано вести в жанр.

    Без второй половины проверки таблица написаний могла бы приводить в никуда:
    опечатка в правой колонке даёт метку, которой нет ни в одном правиле, и игра
    молча теряет жанр. У Steam разъезд таблицы со справочником сторожит
    `test_a_steam_genre_leads_to_the_genre_it_names`, здесь — это."""
    made = parse_catalog({"products": [
        {"id": 1, "title": "и", "genres": [{"slug": written}]}
    ]})
    marks = {ext_id for _space, ext_id in made[0].genre_ext_ids}

    assert marks == {canonical}
    assert matched(await book(GenreSource.GOG), marks), "метка ведёт в никуда"
