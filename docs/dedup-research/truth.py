"""Разметка «одна игра / разные игры» по всем 913 парам-кандидатам, глазами.

Издание одной игры (GOTY, Deluxe, Complete, Remastered, Enhanced) — ОДНА игра.
Переделка с нуля (remake) — РАЗНЫЕ: RE2 2019 и RE2 1998 оценивают порознь.
Сборник из нескольких игр (Bundle, Trilogy, Collection) — РАЗНЫЕ.
Дополнение, DLC, демо, инструмент — РАЗНЫЕ.
"""
import sys
sys.path.insert(0, '.')
from common import all_pairs
from norm import base, strip_edition

# Названия совпадают точно, а игры разные: ремейк против оригинала и тёзки.
EXACT_FALSE = {
    ('S482400', 'O301'), ('G1439637285', 'O301'),        # System Shock 2023 / 1994
    ('S1623070', 'O56'),                                 # Master of Magic 2022 / 1994
    ('S1145360', 'O5117'),                               # Hades 2020 / тёзка
    ('S400', 'O3239'),                                   # Portal 2007 / Portal 1986
    ('S1310410', 'O147'), ('G1177195295', 'O147'),       # Alone in the Dark 2024 / 1992
    ('S883710', 'O353'),                                 # Resident Evil 2 2019 / 1998
    ('S2124490', 'O1521'), ('G2051029707', 'O1521'),     # Silent Hill 2 2024 / 2001
    ('G1207659109', 'O62'),                              # Prince of Persia 2008 / 1989
    ('S203160', 'O98'),                                  # Tomb Raider 2013 / 1996
    ('S2814990', 'O286'),                                # Screamer 2025 / 1995
    ('S2225070', 'O11208'),                              # Trackmania 2020 / 2003
    ('S2300120', 'O8227'),                               # Painkiller 2025 / 2004
    ('S233130', 'O255'),                                 # Shadow Warrior 2013 / 1997
    ('S2099990', 'G1780408621'),                         # «graveyard keeper» строчными
}
# Склеилось снятием слов издания — и склеилось ошибочно.
EDITION_FALSE = {
    ('G1273196341', 'O147'),                             # AitD Deluxe 2024 / 1992
    ('S611670', 'G1801825368'), ('S611670', 'G1711230643'),   # Skyrim VR
    ('S2623190', 'G1242989820'),                         # Oblivion Remastered / Oblivion
    ('S1030840', 'G1595659240'),                         # Mafia Definitive / Mafia 2002
    ('S410710', 'G1439637285'),                          # System Shock EE / SS 2023
    ('G1724969043', 'O98'),                              # Tomb Raider GOTY 2013 / 1996
    ('S3534150', 'G1207658755'),                         # POSTAL 2 VR
}
# Сборники из нескольких игр: не издание, а набор.
EDITION_BUNDLE = {
    ('S6910', 'G1298659718'), ('G1298659718', 'O809'),        # Deus Ex Bundle
    ('S38480', 'G1115629403'), ('G1115629403', 'O109'),       # Earthworm Jim Collection
    ('S244160', 'O683'), ('G2114871440', 'O683'),             # Homeworld Rem. Collection
    ('S1030840', 'G1273195617'),                              # Mafia Trilogy
    ('G1923260625', 'O279'),                                  # Resident Evil Bundle
    ('S46500', 'G1454939961'), ('G1454939961', 'O12492'),     # Syberia Collection
}
# Верные пары, которые нашлись только слагом GOG и вторым названием old-games:
# при первом просмотре кандидатов их не было видно, потому что ни одно из пяти
# правил-кандидатов их не показывало.
EXTRA_TRUE = {
    ('G1207658984', 'O6466'),      # Ultima 7 Complete / The Complete Ultima VII
    ('S2684660', 'G1441199941'),   # The Witcher 3 REDkit / REDkit для «Ведьмак 3»
    ('S1580970', 'O14007'),        # Samorost 1 / Samorost (alt: Samorost 1)
    ('G2006298293', 'O14007'),     # то же со стороны GOG
    ('G1207658912', 'O670'),       # TA: Kingdoms + Iron Plague / TA: Kingdoms
    ('G1207658707', 'O433'),       # Broken Sword 2 Remastered / Smoking Mirror
    ('G1207658715', 'O8227'),      # Painkiller Black Edition / Painkiller 2004
}

# Верные пары, до которых не дотягивается ни точное сравнение, ни снятие издания.
FUZZY_TRUE_TITLES = [
    ('Gabriel Knight 2: The Beast Within',
     'Beast Within: A Gabriel Knight Mystery, The'),
    ('Street Racing Syndicate', 'SRS: Street Racing Syndicate'),
    ('Silent Storm', 'Операция Silent Storm'),
    ('Anno 1602 A.D.', '1602 A.D.'),
    ('Little Big Adventure 2', "Twinsen's Little Big Adventure 2 Classic"),
    ('Another World: 20th Anniversary Edition', 'Another World'),
    ('Beneath a Steel Sky (1994)', 'Beneath a Steel Sky'),
    ('Risk of Rain (2013)', 'Risk of Rain'),
    ('DOOM', 'DOOM (2016)'),
    ('Broken Sword 2 - the Smoking Mirror: Remastered (2010)',
     'Broken Sword 2: Remastered (2010)'),
    ('Broken Sword 2 - the Smoking Mirror: Remastered (2010)',
     'Broken Sword II: The Smoking Mirror'),
    ('Broken Sword 3: The Sleeping Dragon (2003)',
     'Broken Sword : The Sleeping Dragon'),
    ('Broken Sword - Shadow of the Templars: Reforged',
     'Broken Sword : The Shadow of the Templars'),
    ('Gabriel Knight - Sins of the Fathers',
     'Gabriel Knight: Sins of the Fathers – 20th Anniversary Edition'),
    ('Gabriel Knight: Sins of the Fathers – 20th Anniversary Edition',
     'Gabriel Knight : Sins of the Fathers'),
    ('The Elder Scrolls IV: Oblivion Game of the Year Edition (2009)',
     'The Elder Scrolls IV: Oblivion - Game of the Year Edition Deluxe'),
    ('Heroes of Might & Magic III - HD Edition',
     "Heroes of Might and Magic III Complete (Collector's Edition)"),
    ('Heroes of Might and Magic® 3: Complete',
     "Heroes of Might and Magic III Complete (Collector's Edition)"),
    ('Master of Orion 1', 'Master of Orion'),
    ('Master of Orion 2', 'Master of Orion II: Battle at Antares'),
    ('POSTAL 2', 'Postal²'),
    ('POSTAL 2 Redux', 'Postal²'),
    ('Simon the Sorcerer: 25th Anniversary Edition', 'Simon the Sorcerer'),
    ('Age of Empires II: Definitive Edition', 'Age of Empires II: The Age of Kings'),
    ('Duke Nukem 3D: 20th Anniversary World Tour', 'Duke Nukem 3D'),
    ('Quake II RTX', 'Quake II'),
    ('Commandos 2 - HD Remaster', 'Commandos 2: Men of Courage'),
    ('Kingdom Come: Deliverance', 'Kingdom Come: Deliverance Royal Edition'),
    ('Kingdom Come: Deliverance II', 'Kingdom Come: Deliverance II Royal Edition'),
    ('Solasta: Crown of the Magister',
     'Solasta: Crown of the Magister - Lightbringers Edition'),
    ('Darkest Dungeon®', 'Darkest Dungeon®: Ancestral Edition'),
    ('Darkest Dungeon® II', 'Darkest Dungeon® II: Resolute Edition'),
    ('Pillars of Eternity II: Deadfire',
     'Pillars of Eternity II: Deadfire - Obsidian Edition'),
    ('Wasteland 2', "Wasteland 2 Director's Cut Digital Classic Edition"),
    ('Wasteland 2', "Wasteland 2 Director's Cut Digital Deluxe Edition"),
    ('Divinity: Original Sin 2', 'Divinity: Original Sin 2 - Divine Edition'),
    ('Divinity: Original Sin 2', 'Divinity: Original Sin 2 - Eternal Edition'),
    ('Hollow Knight: Silksong', 'Hollow Knight: Silksong & Soundtrack Bundle'),
    ('Machinarium', "Machinarium Collector's Edition"),
    ('Wasteland 3', 'Wasteland 3: Colorado Collection'),
    ('The Talos Principle: Reawakened', 'The Talos Principle: Gold Edition'),
    ('Total Annihilation', 'Total Annihilation: Commander Pack'),
    ('Myst Masterpiece Edition', 'Myst'),
    ('Diablo + Hellfire', 'Diablo'),
    ('Disciples 2 Gold', 'Disciples II : Dark Prophecy'),
    ('Rayman® Forever', 'Rayman'),
    ('Казаки', 'Казаки: Европейские войны'),
    ('Resident Evil 3', 'Resident Evil 3: Nemesis'),
    ('Mafia Classic', 'Mafia : The City of Lost Heaven'),
    ('Arcanum', 'Arcanum: Of Steamworks and Magick Obscura'),
    ('Arcanum', 'Arcanum : Of Steamworks & Magick Obscura'),
    ('Cyberpunk 2077', 'Cyberpunk 2077: Полное издание'),
    ('Divine Divinity', 'Divine Divinity. Рождение легенды'),
    ('Divine Divinity. Рождение легенды', 'Divine Divinity'),
    ('Icewind Dale 2 Complete', 'Icewind Dale II'),
    ('Jagged Alliance 2 - Wildfire ', 'Jagged Alliance 2: Wildfire'),
]

# Одна игра, названия на разных языках: строкой не сходятся ни при какой мере.
# Найдено отдельным проходом по парам «кириллица против латиницы».
CROSS_LANGUAGE_TITLES = [
    ('The Witcher 3: Wild Hunt', 'Ведьмак 3: Дикая Охота'),
    ('The Witcher 3: Wild Hunt', 'Ведьмак 3: Дикая Охота - Издание Игра Года'),
    ('The Witcher: Enhanced Edition', 'Ведьмак'),
    ('The Witcher 2: Assassins of Kings Enhanced Edition', 'Ведьмак 2: Убийцы королей'),
    ('Gothic II: Gold Classic', 'Готика 2 Золотое Издание'),
    ('Готика 2 Золотое Издание', 'Gothic II'),
    ('Готика 2 Золотое Издание', 'Gothic II : Gold Edition'),
    ('Amnesia: The Dark Descent', 'Амнезия: Призрак прошлого'),
    ('Space Rangers HD: A War Apart', 'Космические Рейнджеры HD: Революция'),
    ('Perimeter', 'Периметр'),
    ('PERIMETER: Legate Edition', 'Периметр'),
    ("Perimeter: Emperor's Testament", 'Периметр: Завет Императора'),
    ('Cossacks: Back to War', 'Казаки: Снова война'),
    ('Cossacks 3', 'Казаки 3'),
    ('Blitzkrieg Anthology', 'Антология Блицкриг'),
    ('Blitzkrieg 2 Anthology', 'Антология Блицкриг 2'),
    ('Антология Блицкриг', 'Blitzkrieg'),
    ('IL-2 Sturmovik: 1946', 'Ил-2 Штурмовик. Платиновая коллекция'),
]


def _flat(title):
    return title.replace('> ', '').strip().lower()


def build():
    info = all_pairs()
    want = {(_flat(x), _flat(y)) for x, y in FUZZY_TRUE_TITLES + CROSS_LANGUAGE_TITLES}
    fuzzy_true = set()
    for key, (a, b, _) in info.items():
        if (_flat(a[2]), _flat(b[2])) in want or (_flat(b[2]), _flat(a[2])) in want:
            fuzzy_true.add(key)
    labels = {}
    for key, (a, b, _) in info.items():
        ids = (f'{a[0]}{a[1]}', f'{b[0]}{b[1]}')
        rid = (ids[1], ids[0])
        if base(a[2]) == base(b[2]):
            labels[key] = 'no' if ids in EXACT_FALSE or rid in EXACT_FALSE else 'yes'
        elif strip_edition(a[2]) == strip_edition(b[2]):
            bad = EDITION_FALSE | EDITION_BUNDLE
            labels[key] = 'no' if ids in bad or rid in bad else 'yes'
        else:
            labels[key] = 'yes' if key in fuzzy_true else 'no'
        if ids in EXTRA_TRUE or rid in EXTRA_TRUE:
            labels[key] = 'yes'
    return info, labels, fuzzy_true


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    info, labels, fz = build()
    print('пар всего', len(info), '| одна игра', sum(1 for v in labels.values() if v == 'yes'))
    print('верных сверх точного найдено', len(fz), 'из', len(FUZZY_TRUE_TITLES)+len(CROSS_LANGUAGE_TITLES))
    seen = set()
    for key, (a, b, _) in info.items():
        if key in fz:
            seen.add(frozenset((_flat(a[2]), _flat(b[2]))))
    for x, y in FUZZY_TRUE_TITLES + CROSS_LANGUAGE_TITLES:
        if frozenset((_flat(x), _flat(y))) not in seen:
            print('   НЕ НАЙДЕНО:', x, '||', y)
