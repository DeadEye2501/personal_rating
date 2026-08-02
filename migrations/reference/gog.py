"""Соответствия GOG: жанры и теги магазина одним пространством.

Метка — слаг, а не число: название у GOG переводится, слаг нет. К общему
написанию слаги приводит разбор ответа — `role-playing` и `rpg` у него одна и та
же метка, иначе сочетание `action` + `rpg` не сработало бы на половине игр.

`rougelike` — опечатка самого GOG в жанре, проверено живьём."""

from migrations.reference.rule import Rule

GOG = [
    Rule("Action", "action", without="rpg, jrpg"),
    Rule("Action", "combat"),
    Rule("Action", "hack-and-slash"),
    Rule("Action", "beat-em-up"),
    Rule("Action", "shoot-em-up"),
    Rule("Action", "stealth"),
    Rule("Action", "espionage"),
    Rule("Action", "twin-stick-shooter"),

    Rule("Action-RPG", "souls-like"),
    Rule("Action-RPG", "action, rpg"),
    Rule("Action-RPG", "action, jrpg"),

    Rule("RPG", "rpg", without="action"),
    Rule("RPG", "jrpg", without="action"),
    Rule("RPG", "crpg"),
    Rule("RPG", "dungeon-crawler", without="rougelike, roguelite, perma-death"),

    Rule("Shooter", "shooter"),
    Rule("Shooter", "fps"),
    Rule("Shooter", "looter-shooter"),
    Rule("Shooter", "sniper"),

    Rule("Strategy", "strategy"),
    Rule("Strategy", "rts"),
    Rule("Strategy", "four-x"),
    Rule("Strategy", "grand-strategy"),
    Rule("Strategy", "tower-defense"),
    Rule("Strategy", "management"),
    Rule("Strategy", "managerial"),
    Rule("Strategy", "resource-management"),
    Rule("Strategy", "trading"),
    Rule("Strategy", "economic"),
    Rule("Strategy", "building"),
    Rule("Strategy", "base-building"),
    Rule("Strategy", "city-builder"),
    Rule("Strategy", "auto-battler"),

    Rule("Tactical", "tactical"),
    Rule("Tactical", "tactical-rpg"),

    Rule("Quest", "pointandclick"),
    Rule("Quest", "visual-novel"),
    Rule("Quest", "text-based"),
    Rule("Quest", "walking-simulator"),
    Rule("Quest", "choose-your-own-adventure"),
    Rule("Quest", "fmv"),
    Rule("Quest", "adventure", alone=True),

    Rule("Platformer", "platformer"),
    Rule("Platformer", "metroidvania"),
    Rule("Platformer", "puzzle-platformer"),

    Rule("Roguelike", "rougelike"),
    Rule("Roguelike", "roguelite"),
    Rule("Roguelike", "perma-death"),

    Rule("Survival", "survival"),
    Rule("Survival", "crafting"),
    Rule("Survival", "sandbox"),

    Rule("Fighting", "fighting"),
    Rule("Fighting", "martial-arts"),

    Rule("Racing", "racing"),
    Rule("Racing", "rally"),
    Rule("Racing", "offroad"),
    Rule("Racing", "touring"),

    Rule("Arcade", "arcade"),
    Rule("Arcade", "pinball"),
    Rule("Arcade", "rhythm"),
    Rule("Arcade", "bullet-hell"),

    Rule("Puzzle", "puzzle"),
    Rule("Puzzle", "logic"),
    Rule("Puzzle", "match-three"),
    Rule("Puzzle", "escape-room"),
    Rule("Puzzle", "programming"),
    Rule("Puzzle", "hidden-object"),
    Rule("Puzzle", "typing"),
    Rule("Puzzle", "puzzle-platformer"),

    Rule("Horror", "horror"),
    Rule("Horror", "survival-horror"),
    Rule("Horror", "psychological-horror"),
    Rule("Horror", "lovecraftian"),
    Rule("Horror", "zombies"),
    Rule("Horror", "vampire"),
    Rule("Horror", "werewolves"),

    Rule("Simulator", "simulation"),
    Rule("Simulator", "lifesim"),
    Rule("Simulator", "virtuallife"),
    Rule("Simulator", "dating-sim"),
    Rule("Simulator", "flight"),
    Rule("Simulator", "trains"),
    Rule("Simulator", "farming"),
    Rule("Simulator", "cooking"),

    # Слаг `soccer` в жанрах GOG значит футбол, а в тегах — американский;
    # футбол в тегах зовётся `football`. Здесь это безвредно, обе метки ведут
    # в один жанр, но при следующем слиянии проверять.
    Rule("Sport", "sports"),
    Rule("Sport", "teamsport"),
    Rule("Sport", "soccer"),
    Rule("Sport", "football"),
    Rule("Sport", "fishing"),

    Rule("Tabletop", "card-game"),
    Rule("Tabletop", "board-game"),
    Rule("Tabletop", "tabletop"),
    Rule("Tabletop", "deckbuilding"),
    Rule("Tabletop", "chess"),

    Rule("Multiplayer", "multiplayer"),
    Rule("Multiplayer", "local-multiplayer"),
    Rule("Multiplayer", "local-co-op"),
    Rule("Multiplayer", "split-screen"),
    Rule("Multiplayer", "crossplay"),
    Rule("Multiplayer", "online-only"),
    Rule("Multiplayer", "party-game"),
]
