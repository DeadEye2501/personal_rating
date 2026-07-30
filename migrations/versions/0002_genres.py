"""Справочник жанров и соответствия к нему.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29

Наборов два: кино и игры. Имена свои и все с заглавной — TMDB отдаёт киношные
жанры строчными, а сериальные с заглавной, и тащить эту разноголосицу в базу
незачем. Числа рядом с идентификаторами — чужие названия: без них номер
`323922` не значит ничего.

Соответствия здесь поимённо сторожит `tests/backend/test_genre_reference.py`:
он сверяет объявленное ниже с записанным эталоном.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"

FILM = [
    "Боевик", "Вестерн", "Военный", "Детектив", "Детский", "Документальный",
    "Драма", "История", "Комедия", "Криминал", "Мелодрама", "Музыка",
    "Мультфильм", "Мыльная опера", "Новости", "Политика", "Приключения",
    "Реалити-шоу", "Семейный", "Телевизионный фильм", "Ток-шоу", "Триллер",
    "Ужасы", "Фантастика", "Фэнтези",
]

# Пространство идентификаторов у TMDB одно: расходятся наборы, а не номера.
TMDB = {
    "28": ["Боевик"],
    "12": ["Приключения"],
    "16": ["Мультфильм"],
    "35": ["Комедия"],
    "80": ["Криминал"],
    "99": ["Документальный"],
    "18": ["Драма"],
    "10751": ["Семейный"],
    "14": ["Фэнтези"],
    "36": ["История"],
    "27": ["Ужасы"],
    "10402": ["Музыка"],
    "9648": ["Детектив"],
    "10749": ["Мелодрама"],
    "878": ["Фантастика"],
    "10770": ["Телевизионный фильм"],
    "53": ["Триллер"],
    "10752": ["Военный"],
    "37": ["Вестерн"],
    "10762": ["Детский"],
    "10763": ["Новости"],
    "10764": ["Реалити-шоу"],
    "10766": ["Мыльная опера"],
    "10767": ["Ток-шоу"],
    # Сборные: не жанр, а два жанра, сшитых чужим справочником.
    "10759": ["Боевик", "Приключения"],
    "10765": ["Фантастика", "Фэнтези"],
    "10768": ["Военный", "Политика"],
}

# Жанр и тег у обоих магазинов нумеруются порознь: у Steam 9 — это и жанр
# «Гонки», и тег «Стратегия», поэтому источников четыре, а не два.
GAME = [
    "Action", "Quest", "RPG", "JRPG", "Strategy", "Tabletop", "Tactical",
    "Simulator", "Racing", "Sport", "Shooter", "Platformer", "Metroidvania",
    "Puzzle", "Arcade", "Survival", "Horror", "Stealth", "Roguelike",
    "Sandbox", "Fighting", "Multiplayer",
]

STEAM = {
    "1": ["Action"],  # Экшены
    "25": ["Quest"],  # Приключенческие игры
    "3": ["RPG"],  # Ролевые игры
    "2": ["Strategy"],  # Стратегии
    "28": ["Simulator"],  # Симуляторы
    "9": ["Racing"],  # Гонки
    "18": ["Sport"],  # Спорт
    "29": ["Multiplayer"],  # Многопользовательские игры
}

STEAM_TAG = {
    "19": ["Action"],  # Экшен
    "4106": ["Action", "Quest"],  # Приключенческий экшен
    "4231": ["Action", "RPG"],  # Ролевой экшен
    "1646": ["Action"],  # Слэшер
    "4158": ["Action"],  # Beat 'em up
    "323922": ["Action"],  # Мусоу
    "3993": ["Action"],  # Бой
    "4608": ["Action"],  # Сражения на мечах
    "11104": ["Action"],  # Гонки на выживание
    "29482": ["Action", "RPG"],  # Похожа на Dark Souls
    "42804": ["Action", "Roguelike"],  # Экшен-рогалик
    "21": ["Quest"],  # Приключение
    "1698": ["Quest"],  # Point & Click
    "11014": ["Quest"],  # Интерактивная литература
    "3799": ["Quest"],  # Визуальная новелла
    "31579": ["Quest"],  # Отомэ
    "5900": ["Quest"],  # Симулятор ходьбы
    "4486": ["Quest"],  # Выбери себе приключение
    "31275": ["Quest"],  # Текстовая
    "122": ["RPG"],  # Ролевая игра
    "4474": ["RPG"],  # Компьютерная ролевая игра
    "10695": ["RPG"],  # Партийная ролевая игра
    "1754": ["RPG", "Multiplayer"],  # MMORPG
    "1720": ["RPG"],  # Подземелья
    "21725": ["RPG", "Tactical"],  # Тактическая ролевая игра
    "17305": ["RPG", "Strategy"],  # Ролевая стратегия
    "4434": ["JRPG"],  # Японская ролевая игра
    "9": ["Strategy"],  # Стратегия
    "1741": ["Strategy"],  # Пошаговая стратегия
    "1676": ["Strategy"],  # Стратегия в реальном времени
    "4364": ["Strategy"],  # Глобальная стратегия
    "1670": ["Strategy"],  # 4X
    "1645": ["Strategy"],  # Башенная защита
    "1723": ["Strategy"],  # Экшен-RTS
    "12472": ["Strategy"],  # Менеджмент
    "8945": ["Strategy"],  # Управление ресурсами
    "4695": ["Strategy"],  # Экономика
    "4845": ["Strategy"],  # Капитализм
    "6310": ["Strategy"],  # Дипломатия
    "17389": ["Tabletop"],  # Настольная игра
    "1770": ["Tabletop"],  # Настольная с полем
    "1666": ["Tabletop"],  # Карточная игра
    "9271": ["Tabletop"],  # Коллекционная карточная игра
    "32322": ["Tabletop"],  # Построение колоды
    "4184": ["Tabletop"],  # Шахматы
    "13070": ["Tabletop"],  # Пасьянс
    "33572": ["Tabletop"],  # Маджонг
    "7556": ["Tabletop"],  # Игральные кости
    "6835": ["Tabletop"],  # Покер
    "4852": ["Tabletop"],  # Бильярд
    "791774": ["Tabletop"],  # Карточный баттлер
    "1091588": ["Tabletop", "Roguelike"],  # Карточный рогалик
    "1708": ["Tactical"],  # Тактика
    "14139": ["Tactical"],  # Пошаговая тактика
    "3813": ["Tactical"],  # Тактика в реальном времени
    "599": ["Simulator"],  # Симулятор
    "10235": ["Simulator"],  # Симулятор жизни
    "9551": ["Simulator"],  # Симулятор свиданий
    "16598": ["Simulator"],  # Космический симулятор
    "15045": ["Simulator"],  # Полёты
    "1616": ["Simulator"],  # Поезда
    "87918": ["Simulator"],  # Симулятор фермы
    "35079": ["Simulator"],  # Симулятор работы
    "1100688": ["Simulator"],  # Медицинский симулятор
    "1100686": ["Simulator"],  # Симулятор эпидемии
    "9564": ["Simulator"],  # Охота
    "1220528": ["Simulator"],  # Симулятор хобби
    "91114": ["Simulator"],  # Работа в магазине
    "699": ["Racing"],  # Гонки
    "1644": ["Racing"],  # Вождение
    "4102": ["Racing"],  # Боевые гонки
    "1100687": ["Racing"],  # Автосимулятор
    "7622": ["Racing"],  # Бездорожье
    "15868": ["Racing"],  # Мотокросс
    "129761": ["Racing"],  # Квадроциклы
    "198913": ["Racing"],  # Мотоциклы
    "701": ["Sport"],  # Спорт
    "1254546": ["Sport"],  # Футбол
    "1746": ["Sport"],  # Баскетбол
    "324176": ["Sport"],  # Хоккей
    "5727": ["Sport"],  # Бейсбол
    "49213": ["Sport"],  # Регби
    "847164": ["Sport"],  # Волейбол
    "1254552": ["Sport"],  # Американский футбол
    "158638": ["Sport"],  # Крикет
    "7038": ["Sport"],  # Гольф
    "5914": ["Sport"],  # Теннис
    "1753": ["Sport"],  # Скейтбординг
    "12190": ["Sport"],  # Бокс
    "47827": ["Sport"],  # Реслинг
    "7309": ["Sport"],  # Лыжи
    "28444": ["Sport"],  # Сноубординг
    "1774": ["Shooter"],  # Шутер
    "1663": ["Shooter"],  # Шутер от первого лица
    "3814": ["Shooter"],  # Шутер от третьего лица
    "4637": ["Shooter"],  # Шутер с видом сверху
    "5547": ["Shooter"],  # Арена-шутер
    "1023537": ["Shooter"],  # Бумерский шутер
    "353880": ["Shooter"],  # Лутер-шутер
    "620519": ["Shooter"],  # Геройский шутер
    "4758": ["Shooter"],  # Твин-стик шутер
    "56690": ["Shooter"],  # Рельсовый шутер
    "1199779": ["Shooter"],  # Шутер с эвакуацией
    "4255": ["Shooter"],  # Shoot 'em up
    "4885": ["Shooter"],  # Пулевой ад
    "723991": ["Shooter"],  # Пулевой рай
    "7423": ["Shooter"],  # Снайперство
    "1625": ["Platformer"],  # Платформер
    "5379": ["Platformer"],  # 2D-платформер
    "5395": ["Platformer"],  # 3D-платформер
    "3877": ["Platformer"],  # Платформер на точность
    "5537": ["Platformer", "Puzzle"],  # Головоломка-платформер
    "1628": ["Metroidvania"],  # Метроидвания
    "1664": ["Puzzle"],  # Головоломка
    "6129": ["Puzzle"],  # Логика
    "1665": ["Puzzle"],  # Три в ряд
    "1730": ["Puzzle"],  # Сокобан
    "37376": ["Puzzle"],  # Падающие блоки
    "1738": ["Puzzle"],  # Поиск предметов
    "5432": ["Puzzle"],  # Программирование
    "10437": ["Puzzle"],  # Викторина
    "769306": ["Puzzle"],  # Квест-комната
    "1773": ["Arcade"],  # Аркада
    "6621": ["Arcade"],  # Пинбол
    "8666": ["Arcade"],  # Раннер
    "1752": ["Arcade"],  # Ритм-игра
    "5154": ["Arcade"],  # Набор очков
    "1662": ["Survival"],  # Выживание
    "1100689": ["Survival"],  # Симулятор выживания и крафтинга в открытом мире
    "1667": ["Horror"],  # Хоррор
    "3978": ["Horror"],  # Хоррор на выживание
    "1721": ["Horror"],  # Психологический хоррор
    "42089": ["Horror"],  # Скример
    "1659": ["Horror"],  # Зомби
    "7432": ["Horror"],  # Лавкрафт
    "1687": ["Stealth"],  # Стелс
    "97070": ["Stealth"],  # Ассассины
    "1776": ["Stealth"],  # Шпионаж
    "1716": ["Roguelike"],  # Рогалик
    "454187": ["Roguelike"],  # Традиционный рогалик
    "3959": ["Roguelike"],  # Упрощённый рогалик
    "198631": ["Roguelike"],  # Загадочные подземелья
    "3810": ["Sandbox"],  # Песочница
    "1643": ["Sandbox"],  # Строительство
    "4328": ["Sandbox"],  # Градостроение
    "7332": ["Sandbox"],  # Строительство базы
    "220585": ["Sandbox"],  # Симулятор колонии
    "255534": ["Sandbox"],  # Автоматизация
    "5300": ["Sandbox"],  # Симулятор бога
    "5981": ["Sandbox"],  # Горное дело
    "1743": ["Fighting"],  # Файтинг
    "4736": ["Fighting"],  # 2D-файтинг
    "6506": ["Fighting"],  # 3D-файтинг
    "6915": ["Fighting"],  # Боевые искусства
    "128": ["Multiplayer"],  # ММО
    "3859": ["Multiplayer"],  # Для нескольких игроков
    "1685": ["Multiplayer"],  # Кооператив
    "1775": ["Multiplayer"],  # Игрок против игрока
    "176981": ["Multiplayer"],  # Королевская битва
    "1718": ["Multiplayer"],  # MOBA
    "3843": ["Multiplayer"],  # Сетевой кооператив
    "7368": ["Multiplayer"],  # Локальный мультиплеер
    "3841": ["Multiplayer"],  # Локальный кооператив
    "4508": ["Multiplayer"],  # Совместная кампания
    "4840": ["Multiplayer"],  # Локальная игра на четверых
    "10816": ["Multiplayer"],  # Разделение экрана
    "7178": ["Multiplayer"],  # Командная игра
    "17770": ["Multiplayer"],  # Асинхронный мультиплеер
}

GOG = {
    "action": ["Action"],  # Экшн
    "combat": ["Action"],  # Сражения
    "adventure": ["Quest"],  # Приключение
    "pointandclick": ["Quest"],  # Квест
    "visual-novel": ["Quest"],  # Визуальные новеллы
    "rpg": ["RPG"],  # Ролевая игра
    "jrpg": ["RPG", "JRPG"],  # JRPG
    "strategy": ["Strategy"],  # Стратегия
    "managerial": ["Strategy"],  # Менеджмент
    "economic": ["Strategy"],  # Экономика
    "card-game": ["Tabletop"],  # Карточная игра
    "chess": ["Tabletop"],  # Шахматы
    "tactical": ["Tactical"],  # Тактическая
    "simulation": ["Simulator"],  # Симулятор
    "virtuallife": ["Simulator"],  # Виртуальная жизнь
    "racing": ["Racing"],  # Гонки
    "offroad": ["Racing"],  # Внедорожники
    "rally": ["Racing"],  # Ралли
    "touring": ["Racing"],  # Турне
    "sports": ["Sport"],  # Спорт
    "teamsport": ["Sport"],  # Командный спорт
    "soccer": ["Sport"],  # Футбол
    "shooter": ["Shooter"],  # Шутер
    "shoot-em-up": ["Shooter"],  # Shoot 'em Up
    "platformer": ["Platformer"],  # Платформер
    "metroidvania": ["Metroidvania"],  # Metroidvania
    "puzzle": ["Puzzle"],  # Головоломка
    "programming": ["Puzzle"],  # Программирование
    "hidden-object": ["Puzzle"],  # Поиск предметов
    "arcade": ["Arcade"],  # Аркада
    "pinball": ["Arcade"],  # Пинбол
    "survival": ["Survival"],  # Выживание
    "horror": ["Horror"],  # Хоррор
    "stealth": ["Stealth"],  # Стелс
    "espionage": ["Stealth"],  # Шпионаж
    "rougelike": ["Roguelike"],  # Roguelike
    "sandbox": ["Sandbox"],  # Sandbox
    "building": ["Sandbox"],  # Строительство
    "fighting": ["Fighting"],  # Файтинг
}

GOG_TAG = {
    "hack-and-slash": ["Action"],  # Слэшер
    "beat-em-up": ["Action"],  # Beat 'em up
    "combat": ["Action"],  # Сражения
    "souls-like": ["Action", "RPG"],  # Похожа на Dark Souls
    "point-and-click": ["Quest"],  # Point&Click
    "text-based": ["Quest"],  # Текстовая
    "choose-your-own-adventure": ["Quest"],  # Выбери себе приключение
    "walking-simulator": ["Quest"],  # Симулятор ходьбы
    "visual-novel": ["Quest"],  # Визуальная новелла
    "crpg": ["RPG"],  # Компьютерная ролевая игра
    "dungeon-crawler": ["RPG"],  # Подземелья
    "tactical-rpg": ["RPG", "Tactical"],  # Тактическая ролевая игра
    "rts": ["Strategy"],  # Стратегия в реальном времени
    "four-x": ["Strategy"],  # 4X
    "grand-strategy": ["Strategy"],  # Глобальная стратегия
    "tower-defense": ["Strategy"],  # Башенная защита
    "management": ["Strategy"],  # Управление
    "resource-management": ["Strategy"],  # Управление ресурсами
    "trading": ["Strategy"],  # Торговля
    "board-game": ["Tabletop"],  # Настольная с полем
    "tabletop": ["Tabletop"],  # Настольная игра
    "deckbuilding": ["Tabletop"],  # Карточная
    "lifesim": ["Simulator"],  # Симулятор жизни
    "dating-sim": ["Simulator"],  # Симулятор свиданий
    "flight": ["Simulator"],  # Полеты
    "trains": ["Simulator"],  # Поезда
    "farming": ["Simulator"],  # Фермерство
    "football": ["Sport"],  # Футбол
    "martial-arts": ["Fighting"],  # Боевые искусства
    "fishing": ["Sport"],  # Рыбалка
    "team-sport": ["Sport"],  # Командный спорт
    "fps": ["Shooter"],  # Шутер от первого лица
    "bullet-hell": ["Shooter"],  # Скролл-шутер
    "twin-stick-shooter": ["Shooter"],  # Твин-стик шутер
    "looter-shooter": ["Shooter"],  # Лутер-шутер
    "sniper": ["Shooter"],  # Снайпер
    "platformer": ["Platformer"],  # Платформер
    "metroidvania": ["Metroidvania"],  # Метроидвания
    "puzzle-platformer": ["Platformer", "Puzzle"],  # Головоломка-платформер
    "logic": ["Puzzle"],  # Логическая
    "match-three": ["Puzzle"],  # Три в ряд
    "escape-room": ["Puzzle"],  # Побег из комнаты
    "programming": ["Puzzle"],  # Программирование
    "hidden-object": ["Puzzle"],  # Поиск предметов
    "rhythm": ["Arcade"],  # Ритм
    "pinball": ["Arcade"],  # Пинболл
    "arcade": ["Arcade"],  # Аркада
    "crafting": ["Survival"],  # Крафтинг
    "survival": ["Survival"],  # Выживание
    "survival-horror": ["Horror"],  # Хоррор на выживание
    "psychological-horror": ["Horror"],  # Психологический хоррор
    "lovecraftian": ["Horror"],  # Лавкрафт
    "zombies": ["Horror"],  # Зомби
    "vampire": ["Horror"],  # Вампир
    "roguelike": ["Roguelike"],  # Рогалик
    "roguelite": ["Roguelike"],  # Упрощенный рогалик
    "perma-death": ["Roguelike"],  # Перманентная смерть
    "city-builder": ["Sandbox"],  # Градостроение
    "base-building": ["Sandbox"],  # Строительство базы
    "building": ["Sandbox"],  # Строительство
    "sandbox": ["Sandbox"],  # Песочница
    "multiplayer": ["Multiplayer"],  # Многопользовательская игра
    "local-multiplayer": ["Multiplayer"],  # Локальный мультиплеер
    "local-co-op": ["Multiplayer"],  # Локальный кооператив
    "split-screen": ["Multiplayer"],  # Разделение экрана
    "crossplay": ["Multiplayer"],  # Crossplay
    "online-only": ["Multiplayer"],  # Online-only
    "party-game": ["Multiplayer"],  # Партийная игра
}

def upgrade() -> None:
    connection = op.get_bind()

    ids: dict[tuple[str, str], int] = {}
    for kind, names in (("film", FILM), ("game", GAME)):
        for name in names:
            result = connection.execute(
                sa.text("INSERT INTO genre (name, kind) VALUES (:name, :kind)"),
                {"name": name, "kind": kind},
            )
            ids[(kind, name)] = result.lastrowid

    for source, mapping, kind in (
        ("tmdb", TMDB, "film"),
        ("steam", STEAM, "game"),
        ("steam_tag", STEAM_TAG, "game"),
        ("gog", GOG, "game"),
        ("gog_tag", GOG_TAG, "game"),
    ):
        for ext_id, names in mapping.items():
            for name in names:
                connection.execute(
                    sa.text(
                        "INSERT INTO genre_map (source, ext_id, genre_id) "
                        "VALUES (:source, :ext_id, :genre_id)"
                    ),
                    {"source": source, "ext_id": ext_id,
                     "genre_id": ids[(kind, name)]},
                )


def downgrade() -> None:
    # Соответствия уходят каскадом вслед за жанром: внешние ключи в миграциях
    # включены, и отдельное удаление genre_map ничего бы не делало.
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM genre"))
