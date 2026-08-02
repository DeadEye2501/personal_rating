"""Соответствия old-games.ru: пятнадцать жанров на весь сайт, у игры один.

Сочетаний тут не бывает по построению — тегов у сайта нет вовсе, — поэтому
каждое правило состоит из одной метки, и запретов не нужно ни одного.

`Other` — мусорная корзина самого сайта, не даёт ничего. `Edutainment` не
заводится: такого жанра у нас нет. `Adventure` сведён в `Quest` сознательно, с
известным шумом: туда у них падают Alone in the Dark и Another World."""

from migrations.reference.rule import Rule

OLD_GAMES = [
    Rule("Action", "Action"),
    Rule("RPG", "RPG"),
    Rule("Strategy", "Strategy"),
    Rule("Quest", "Quest"),
    Rule("Quest", "Interactive Fiction"),
    Rule("Quest", "Adventure"),
    Rule("Puzzle", "Puzzle"),
    Rule("Arcade", "Arcade"),
    Rule("Racing", "Racing"),
    Rule("Sport", "Sports"),
    Rule("Simulator", "Simulation"),
    Rule("Fighting", "Fighting"),
    Rule("Tabletop", "Tabletop"),
]
