"""Соответствия Steam: жанры и теги магазина одним пространством.

Номера рядом с именами — чужие: без `323922` рядом с «Musou» строка не значит
ничего. Жанр магазина приезжает уже переведённым в номер тега-двойника, это
делает разбор ответа: пространства у Steam разные и сталкиваются числами — жанр
`9` это «Гонки», а тег `9` это «Стратегия».

`4231` Action RPG гасит свои части, и записано это запретами у самих частей:
игра с этим тегом получает только Action-RPG, даже если рядом стоят `19`, `122`
или `4434`."""

from migrations.reference.rule import Rule

STEAM = [
    Rule("Action", "19", without="122, 4434, 4231"),  # Action
    Rule("Action", "1646"),  # Hack and Slash
    Rule("Action", "4158"),  # Beat 'em up
    Rule("Action", "323922"),  # Musou
    Rule("Action", "3993"),  # Combat
    Rule("Action", "4608"),  # Swordplay
    Rule("Action", "11104"),  # Vehicular Combat
    Rule("Action", "3955"),  # Character Action Game
    Rule("Action", "4777"),  # Spectacle fighter
    Rule("Action", "4106"),  # Action-Adventure
    Rule("Action", "4637"),  # Top-Down Shooter
    Rule("Action", "4758"),  # Twin Stick Shooter
    Rule("Action", "4255"),  # Shoot 'Em Up
    Rule("Action", "3954"),  # Rail Shooter
    Rule("Action", "56690"),  # On-Rails Shooter
    Rule("Action", "1687"),  # Stealth
    Rule("Action", "1776"),  # Espionage
    Rule("Action", "97070"),  # Assassins
    Rule("Action", "4036"),  # Parkour
    Rule("Action", "42804"),  # Action Roguelike

    Rule("Action-RPG", "4231"),  # Action RPG
    Rule("Action-RPG", "29482"),  # Souls-like
    Rule("Action-RPG", "19, 122"),  # Action + RPG
    Rule("Action-RPG", "19, 4434"),  # Action + JRPG

    Rule("RPG", "122", without="19, 4231"),  # RPG
    Rule("RPG", "4434", without="19, 4231"),  # JRPG
    Rule("RPG", "4474"),  # CRPG
    Rule("RPG", "10695"),  # Party-Based RPG
    Rule("RPG", "1754"),  # MMORPG
    Rule("RPG", "17305"),  # Strategy RPG
    Rule("RPG", "21725"),  # Tactical RPG
    Rule("RPG", "1720", without="1716, 3959, 454187, 1759"),  # Dungeon Crawler

    Rule("Shooter", "1774"),  # Shooter
    Rule("Shooter", "1663"),  # FPS
    Rule("Shooter", "3814"),  # Third-Person Shooter
    Rule("Shooter", "5547"),  # Arena Shooter
    Rule("Shooter", "1023537"),  # Boomer Shooter
    Rule("Shooter", "353880"),  # Looter Shooter
    Rule("Shooter", "620519"),  # Hero Shooter
    Rule("Shooter", "1199779"),  # Extraction Shooter
    Rule("Shooter", "7423"),  # Sniper

    Rule("Strategy", "9"),  # Strategy
    Rule("Strategy", "1676"),  # RTS
    Rule("Strategy", "1741"),  # Turn-Based Strategy
    Rule("Strategy", "4364"),  # Grand Strategy
    Rule("Strategy", "1670"),  # 4X
    Rule("Strategy", "1645"),  # Tower Defense
    Rule("Strategy", "1723"),  # Action RTS
    Rule("Strategy", "4684"),  # Wargame
    Rule("Strategy", "17305"),  # Strategy RPG
    Rule("Strategy", "12472"),  # Management
    Rule("Strategy", "8945"),  # Resource Management
    Rule("Strategy", "4695"),  # Economy
    Rule("Strategy", "4845"),  # Capitalism
    Rule("Strategy", "6310"),  # Diplomacy
    Rule("Strategy", "4202"),  # Trading
    Rule("Strategy", "4328"),  # City Builder
    Rule("Strategy", "1643"),  # Building
    Rule("Strategy", "7332"),  # Base Building
    Rule("Strategy", "220585"),  # Colony Sim
    Rule("Strategy", "255534"),  # Automation
    Rule("Strategy", "5300"),  # God Game
    Rule("Strategy", "5981"),  # Mining
    Rule("Strategy", "26921"),  # Political Sim
    Rule("Strategy", "16689"),  # Time Management
    Rule("Strategy", "10383"),  # Transportation

    Rule("Tactical", "1708"),  # Tactical
    Rule("Tactical", "14139"),  # Turn-Based Tactics
    Rule("Tactical", "3813"),  # Real Time Tactics
    Rule("Tactical", "21725"),  # Tactical RPG

    Rule("Quest", "1698"),  # Point & Click
    Rule("Quest", "11014"),  # Interactive Fiction
    Rule("Quest", "3799"),  # Visual Novel
    Rule("Quest", "31579"),  # Otome
    Rule("Quest", "5900"),  # Walking Simulator
    Rule("Quest", "4486"),  # Choose Your Own Adventure
    Rule("Quest", "31275"),  # Text-Based
    Rule("Quest", "18594"),  # FMV
    Rule("Quest", "21", alone=True),  # Adventure без любой другой метки

    Rule("Platformer", "1625"),  # Platformer
    Rule("Platformer", "5379"),  # 2D Platformer
    Rule("Platformer", "5395"),  # 3D Platformer
    Rule("Platformer", "3877"),  # Precision Platformer
    Rule("Platformer", "5537"),  # Puzzle Platformer
    Rule("Platformer", "1628"),  # Metroidvania

    Rule("Roguelike", "1716"),  # Roguelike
    Rule("Roguelike", "454187"),  # Traditional Roguelike
    Rule("Roguelike", "3959"),  # Roguelite
    Rule("Roguelike", "198631"),  # Mystery Dungeon
    Rule("Roguelike", "42804"),  # Action Roguelike
    Rule("Roguelike", "1091588"),  # Roguelike Deckbuilder
    Rule("Roguelike", "1759"),  # Perma Death

    Rule("Survival", "1662"),  # Survival
    Rule("Survival", "1100689"),  # Open World Survival Craft
    Rule("Survival", "1702"),  # Crafting

    Rule("Fighting", "1743"),  # Fighting
    Rule("Fighting", "4736"),  # 2D Fighter
    Rule("Fighting", "6506"),  # 3D Fighter
    Rule("Fighting", "6915"),  # Martial Arts

    Rule("Racing", "699"),  # Racing
    Rule("Racing", "1644"),  # Driving
    Rule("Racing", "4102"),  # Combat Racing
    Rule("Racing", "1100687"),  # Automobile Sim
    Rule("Racing", "7622"),  # Offroad
    Rule("Racing", "15868"),  # Motocross
    Rule("Racing", "129761"),  # ATV
    Rule("Racing", "198913"),  # Motorbike
    Rule("Racing", "123332"),  # Bikes
    Rule("Racing", "252854"),  # BMX
    Rule("Racing", "19568"),  # Cycling

    Rule("Arcade", "1773"),  # Arcade
    Rule("Arcade", "6621"),  # Pinball
    Rule("Arcade", "8666"),  # Runner
    Rule("Arcade", "1752"),  # Rhythm
    Rule("Arcade", "5154"),  # Score Attack
    Rule("Arcade", "5390"),  # Time Attack
    Rule("Arcade", "4885"),  # Bullet Hell
    Rule("Arcade", "723991"),  # Bullet Heaven
    Rule("Arcade", "379975"),  # Clicker
    Rule("Arcade", "615955"),  # Idler
    Rule("Arcade", "560542"),  # Incremental

    Rule("Puzzle", "1664"),  # Puzzle
    Rule("Puzzle", "6129"),  # Logic
    Rule("Puzzle", "1665"),  # Match 3
    Rule("Puzzle", "1730"),  # Sokoban
    Rule("Puzzle", "37376"),  # Falling Blocks
    Rule("Puzzle", "1738"),  # Hidden Object
    Rule("Puzzle", "5432"),  # Programming
    Rule("Puzzle", "769306"),  # Escape Room
    Rule("Puzzle", "24003"),  # Word Game
    Rule("Puzzle", "71389"),  # Spelling
    Rule("Puzzle", "5537"),  # Puzzle Platformer

    Rule("Horror", "1667"),  # Horror
    Rule("Horror", "3978"),  # Survival Horror
    Rule("Horror", "1721"),  # Psychological Horror
    Rule("Horror", "42089"),  # Jump Scare
    Rule("Horror", "1659"),  # Zombies
    Rule("Horror", "7432"),  # Lovecraftian
    Rule("Horror", "12686"),  # Vampires
    Rule("Horror", "17015"),  # Werewolves

    Rule("Simulator", "599"),  # Simulation
    Rule("Simulator", "10235"),  # Life Sim
    Rule("Simulator", "9551"),  # Dating Sim
    Rule("Simulator", "16598"),  # Space Sim
    Rule("Simulator", "15045"),  # Flight
    Rule("Simulator", "37799"),  # Combat Flight Simulator
    Rule("Simulator", "1616"),  # Trains
    Rule("Simulator", "87918"),  # Farming Sim
    Rule("Simulator", "4520"),  # Farming
    Rule("Simulator", "22602"),  # Agriculture
    Rule("Simulator", "35079"),  # Job Simulator
    Rule("Simulator", "1100688"),  # Medical Sim
    Rule("Simulator", "1100686"),  # Outbreak Sim
    Rule("Simulator", "9564"),  # Hunting
    Rule("Simulator", "1220528"),  # Hobby Sim
    Rule("Simulator", "91114"),  # Shop Keeper
    Rule("Simulator", "3920"),  # Cooking
    Rule("Simulator", "23491"),  # Cleaning
    Rule("Simulator", "889937"),  # Decorating
    Rule("Simulator", "1239876"),  # Organizing
    Rule("Simulator", "13577"),  # Sailing
    Rule("Simulator", "6910"),  # Naval
    Rule("Simulator", "19780"),  # Submarine

    Rule("Sport", "701"),  # Sports
    Rule("Sport", "1254546"),  # Football (Soccer)
    Rule("Sport", "1254552"),  # Football (American)
    Rule("Sport", "1746"),  # Basketball
    Rule("Sport", "324176"),  # Hockey
    Rule("Sport", "5727"),  # Baseball
    Rule("Sport", "49213"),  # Rugby
    Rule("Sport", "847164"),  # Volleyball
    Rule("Sport", "158638"),  # Cricket
    Rule("Sport", "7038"),  # Golf
    Rule("Sport", "22955"),  # Mini Golf
    Rule("Sport", "5914"),  # Tennis
    Rule("Sport", "1753"),  # Skateboarding
    Rule("Sport", "96359"),  # Skating
    Rule("Sport", "12190"),  # Boxing
    Rule("Sport", "47827"),  # Wrestling
    Rule("Sport", "7309"),  # Skiing
    Rule("Sport", "28444"),  # Snowboarding
    Rule("Sport", "7328"),  # Bowling
    Rule("Sport", "13382"),  # Archery
    Rule("Sport", "15564"),  # Fishing
    Rule("Sport", "17927"),  # Pool
    Rule("Sport", "363767"),  # Snooker
    Rule("Sport", "4852"),  # Billiards

    Rule("Tabletop", "17389"),  # Tabletop
    Rule("Tabletop", "1770"),  # Board Game
    Rule("Tabletop", "1666"),  # Card Game
    Rule("Tabletop", "9271"),  # Trading Card Game
    Rule("Tabletop", "32322"),  # Deckbuilding
    Rule("Tabletop", "4184"),  # Chess
    Rule("Tabletop", "13070"),  # Solitaire
    Rule("Tabletop", "33572"),  # Mahjong
    Rule("Tabletop", "7556"),  # Dice
    Rule("Tabletop", "6835"),  # Poker
    Rule("Tabletop", "16250"),  # Gambling
    Rule("Tabletop", "791774"),  # Card Battler
    Rule("Tabletop", "1091588"),  # Roguelike Deckbuilder

    Rule("Multiplayer", "128"),  # Massively Multiplayer
    Rule("Multiplayer", "3859"),  # Multiplayer
    Rule("Multiplayer", "1685"),  # Co-op
    Rule("Multiplayer", "1775"),  # PvP
    Rule("Multiplayer", "176981"),  # Battle Royale
    Rule("Multiplayer", "1718"),  # MOBA
    Rule("Multiplayer", "3843"),  # Online Co-Op
    Rule("Multiplayer", "7368"),  # Local Multiplayer
    Rule("Multiplayer", "3841"),  # Local Co-Op
    Rule("Multiplayer", "4508"),  # Co-op Campaign
    Rule("Multiplayer", "4840"),  # 4 Player Local
    Rule("Multiplayer", "10816"),  # Split Screen
    Rule("Multiplayer", "7178"),  # Party Game
    Rule("Multiplayer", "17770"),  # Asynchronous Multiplayer
    Rule("Multiplayer", "5711"),  # Team-Based
    Rule("Multiplayer", "745697"),  # Social Deduction
    Rule("Multiplayer", "1754"),  # MMORPG
    Rule("Multiplayer", "5055"),  # eSports
    Rule("Multiplayer", "10437"),  # Trivia
]
