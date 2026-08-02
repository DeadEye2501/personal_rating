# Источники игр: поток и устройство

Решено пользователем 02.08.2026. Три равноправных источника — Steam, GOG,
old-games.ru.

Ниже — слова пользователя, записанные дословно. Это то, что принято; всё
остальное в этом файле от них производно и на них не влияет.

## Поток, как его видит пользователь

> Как я вижу весь флоу (часть уже реализована).
> 1. Пользователь вводит название игры в поиск.
> 2. Происходит поиск по каждому агрегатору (сейчас уже реализованы 2 из 3 агрегаторов).
> 3. Выдача каждого аграгетора проходит через первичных отсев мусора (убирает DLC, не-игры, оставляет только игры).
> 4. Выдача каждого агрегатора проходит через механизм нормализации (приведение жанров по таблице к внутренним жанрам).
> 5. Нормализованные результаты проходят через шаг дедупликации (если одна игра пришла из нескольких агрегаторов, мы отсеиваем копии по приоритету steam>gog>old-games). (ещё не реализовано).
> 6. Нормализованные дедуплицированные результаты попадают в итоговую выдачу, которая показывается пользователю.
>
> Архитектура.
> 1. Есть независимые модули сбора данных из снешних источников (steam, gog, old-games).
> 2. Если сборщик, который вызывает каждый из этих модулей и собирает ответы от них и передаёт дальше.
> 3. Есть таблица соответствия жанров.
> 4. Есть отдельный модуль дедупликации (ещё не написан).

## Приоритет

> Главный приоритет - это получить максимально широкий список существующих игр.
> Что я мог ввести в поиск любую игру от древней ретро до современной AAA или
> нишевой инди игры, и найти её с обложкой.
>
> Оценки, и всё остальное - вторично.

Язык при этом неважен:

> мне вообще пофигу! пусть в агрегаторе не будет переводом и вообще всё будет на
> английском, вообще не принципиально.

## Выбор трёх источников

> конечно 3 разноправных.

> steam+gog+old-games даст максимальное покрытие.

## Игровые жанры: девятнадцать

Пересмотрены пользователем 02.08.2026. Прежний набор из двадцати двух (решение
29.07.2026) отменён; запись о нём в `CLAUDE.md` устарела.

`Action` · `Shooter` · `Action-RPG` · `RPG` · `Strategy` · `Tactical` ·
`Fighting` · `Platformer` · `Quest` · `Puzzle` · `Survival` · `Tabletop` ·
`Sport` · `Racing` · `Simulator` · `Horror` · `Multiplayer` · `Roguelike` ·
`Arcade`

Имена остаются английскими — решение 29.07.2026 в этой части не менялось.

### Что означает каждый, словами пользователя

> Шутер - это именно классические шутеры от 1го или 3го лица.
> Экшен - это бит-э-мап, шут-э-мап, шутер с видом сверху, сбоку, скролл-шутер, по сути всё со спинномозговым геймплеер, что не попадает в остальные жанры.
> РПГ - классические РПГ с изометрическим видом. Важно, тут упор на ролевой отыгрыш.
> Экшен-РПГ - отдельный от РПГ жанр, тут и дарс соулс, и fallout 4, где экшена и рпг примерно поровну и бои не пошаговые.
> Рейсинг - все гонки, всякие внедорожники и прочее.
> Квест - тут все игры-головоломки с сюжетом, визуальные новеллы, текстовые квесты, поинт и клик и т.д.
> Паззл - тут игры-головоломки без сюжета: три-в-ряд и так далее.
> Платформер - тут все игры про прыжки, 3д, 2д платформеры, многие метроидвании.
> Спорт - тут весь футбол, и спортивные игры.
> Тейлбтоп - карты, шахматы и так далее.
> Аркада - пинбол, ритм.
> Тактика - игры про тактические пошаговые бои типа X-COM.
> Файтинг - ну тут всё просто, файтинги довольно легко отличить.

### Чего в наборе нет и почему

Решения того же дня, все — пользователя:

- **дробления на два уровня не будет:** «поджанр не нужен. Я не хочу переписывать
  ядро под него». Отсюда требование, которым набор и правился: «давай тогда
  сделаем жанры более высокоуровневыми и уберём излишнее дробление»;
- **`Strategy` не делится** на RTS, пошаговую и экономическую;
- **`Sandbox` не заводится** — Minecraft и Terraria идут в `Survival`;
- **`Stealth` не заводится** — Thief и Dishonored это `Action`;
- **`Metroidvania` не заводится** — уходит в `Platformer`;
- **`Soulslike` не заводится** — уходит в `Action-RPG`;
- **`JRPG` не заводится** — сливается с `RPG`;
- **`Edutainment` не заводится** — жанр есть только у old-games.ru.

## Соответствия GOG

Решено пользователем 02.08.2026.

### Жанры и теги GOG сливаются в один словарь

> сейчас я не вижу разницы между тегами и жанрами у гога. 1. Забираем теги и
> жанры. 2. Смешиваем их в один список, попутно убирая дубликаты (тег экшен и
> жанр экшен сливаются в один). 3. А дальше работаем как с жанрами

Двух пространств `gog` и `gog_tag` больше нет — есть одно.

**Берём не все теги, а только несущие жанр:** «всякие рич и атмисферик - хлам».
Замер: у GOG 55 жанров и 203 тега, после слияния 205 меток, из них жанр несут
106.

**Теги — не повторы жанров, и это замерено на 559 играх:** жанры GOG не дали
ничего вовсе лишь у 5 игр (1%), но теги добавили хотя бы один жанр **378 играм
(68%)**. Больше всего добавили `Survival` (74), `Multiplayer` (73), `Puzzle`
(64), `Quest` (62), `Horror` (57), `Action-RPG` (48), `Tactical` (44). Три
жанра без тегов почти недостижимы: `Multiplayer` — у GOG нет такого жанра
вовсе; `Action-RPG` — тег `souls-like`; `Horror` с `Survival` — жанр проставлен
не у всех.

### Разные написания одного и того же

Вторая таблица соответствия, без неё слияние по слагу не работает. Справа —
что остаётся:

| написание | остаётся |
|---|---|
| `point-and-click` | `pointandclick` |
| `real-time` | `realtime` |
| `sci-fi` | `scifi` |
| `team-sport` | `teamsport` |
| `turn-based` | `turnbased` |
| `virtual-life` | `virtuallife` |
| `roguelike` | `rougelike` — опечатка самого GOG в жанре, проверено живьём |
| `role-playing` | `rpg` |

**Ловушка, о которой надо знать:** слаг `soccer` в жанрах GOG значит футбол, а
в тегах — американский футбол; футбол в тегах зовётся `football`. Совпадение
слага не означает совпадения смысла. Здесь это безвредно — обе метки ведут в
`Sport`, — но при следующем слиянии проверять.

### Форма правила

У правила три поля, и все четыре вида условий выражаются ими:

- **требуется** — набор меток, все обязаны присутствовать;
- **запрещено** — набор меток, ни одной быть не должно; частный случай «любая
  другая метка из таблицы» покрывает `adventure`;
- **гасит части** — снимает ли сработавшее правило те жанры, что дали бы его
  метки поодиночке.

### Колонка GOG

Условия записаны полностью, а не выведены из «гасит части»: спеку читает тот,
кто этого разговора не слышал.

| Наш жанр | Метки GOG |
|---|---|
| Action | `action` **без** `rpg` **и без** `jrpg` · `combat` · `hack-and-slash` · `beat-em-up` · `shoot-em-up` · `stealth` · `espionage` · `twin-stick-shooter` |
| Action-RPG | `souls-like` · `action` + `rpg` · `action` + `jrpg` |
| RPG | `rpg` **без** `action` · `jrpg` **без** `action` · `crpg` · `dungeon-crawler` **без** `roguelike`/`roguelite`/`perma-death` |
| Shooter | `shooter` · `fps` · `looter-shooter` · `sniper` |
| Strategy | `strategy` · `rts` · `four-x` · `grand-strategy` · `tower-defense` · `management` · `managerial` · `resource-management` · `trading` · `economic` · `building` · `base-building` · `city-builder` · `auto-battler` |
| Tactical | `tactical` · `tactical-rpg` |
| Quest | `pointandclick` · `visual-novel` · `text-based` · `walking-simulator` · `choose-your-own-adventure` · `fmv` · `adventure` **без любой другой метки из этой таблицы** |
| Platformer | `platformer` · `metroidvania` · `puzzle-platformer` |
| Roguelike | `rougelike` · `roguelite` · `perma-death` |
| Survival | `survival` · `crafting` · `sandbox` |
| Fighting | `fighting` · `martial-arts` |
| Racing | `racing` · `rally` · `offroad` · `touring` |
| Arcade | `arcade` · `pinball` · `rhythm` · `bullet-hell` |
| Puzzle | `puzzle` · `logic` · `match-three` · `escape-room` · `programming` · `hidden-object` · `typing` · `puzzle-platformer` |
| Horror | `horror` · `survival-horror` · `psychological-horror` · `lovecraftian` · `zombies` · `vampire` · `werewolves` |
| Simulator | `simulation` · `lifesim` · `virtuallife` · `dating-sim` · `flight` · `trains` · `farming` · `cooking` |
| Sport | `sports` · `teamsport` · `soccer` · `football` · `fishing` |
| Tabletop | `card-game` · `board-game` · `tabletop` · `deckbuilding` · `chess` |
| Multiplayer | `multiplayer` · `local-multiplayer` · `local-co-op` · `split-screen` · `crossplay` · `online-only` · `party-game` |

**Не разложено намеренно.** `realtime`, `turnbased`, `fpp`, `tpp` — уточнения,
жанра в одиночку не дают, но нужны в сочетаниях. `educational` и `education` —
Edutainment не заводится. `transportation` и `naval` не размещены вовсе.

**Выброшено как хлам — 99 меток.** Список нужен целиком, иначе следующий проход
будет выводить его заново:

`artbook`, `atmospheric`, `cartoony`, `casual`, `cats`, `choices-matter`,
`classic`, `comedy`, `coming-of-age`, `cozy`, `crime`, `cyberpunk`, `dark`,
`dark-comedy`, `demo`, `detective`, `difficult`, `dinosaurs`, `dog`,
`dystopian`, `emotional`, `exploration`, `family-friendly`, `fantasy`,
`female-protagonist`, `first-person`, `freegame`, `funny`, `good-old-game`,
`gore`, `great-soundtrack`, `hentai`, `historical`, `indie`, `investigation`,
`isometric`, `leveleditor`, `lgbtq-plus`, `magic`, `mature`, `medieval`,
`military`, `mod`, `modern`, `movie`, `multiple-endings`, `mystery`,
`mythology`, `narrative`, `nature`, `ninja`, `noir`, `non-violent`, `nsfw`,
`nudity`, `only-on-gog`, `open-world`, `ost`, `parody`, `petting-dogs`,
`philosophical`, `physics`, `pirates`, `pixel-graphics`, `politics`,
`post-apocalyptic`, `procedural-generation`, `psychological`, `realistic`,
`relaxing`, `remake`, `retro`, `robots`, `romance`, `science`, `scifi`,
`sexual-content`, `short`, `space`, `steampunk`, `story-rich`, `superhero`,
`supernatural`, `surreal`, `tanks`, `third-person`, `thriller`,
`time-manipulation`, `top-down`, `two-dimensional`, `underground`,
`underwater`, `vikings`, `violent`, `vr`, `war`, `western`, `world-war-i`,
`world-war-ii`

**Почему `twin-stick-shooter` в `Action`, а не в `Shooter`:** по определению
пользователя `Shooter` — только классические от первого и третьего лица, а
«шутер с видом сверху, сбоку» и всё спинномозговое — `Action`. По тому же
правилу там же `shoot-em-up` и `bullet-hell` → `Arcade`.

**Почему `dungeon-crawler` остался в `RPG`.** Замер: у GOG 384 игры с этим
тегом, и из 144 просмотренных рогаликом помечены 38%. Остальные — Arx Fatalis,
Avernum 4, Bloodwych, Darkstone, то есть подземельные RPG. Настоящие рогалики
при этом уже несут `roguelike`, `roguelite` или `perma-death`, так что
`Roguelike` от переноса ничего бы не получил, а `RPG` потерял бы две трети.

**Четыре метки размещены на глаз и ждут проверки:** `fishing` → `Sport` (хотя по
правилу «достоверность занятия» это `Simulator`), `cooking` → `Simulator`,
`typing` → `Puzzle`, `auto-battler` → `Strategy` (хотя ближе к `Tabletop`).

## Соответствия Steam

Решено пользователем 02.08.2026. Принцип тот же, что у GOG: жанры и теги
сливаются в один словарь, нежанровое выбрасывается, врущая одиночная метка
разбирается сочетанием.

### Слияние: у Steam номера жанров и тегов сталкиваются

Пространства идентификаторов разные и пересекаются числами — жанр `9` это
«Гонки», а тег `9` это «Стратегия». Зато у каждого полезного жанра есть
тег-двойник с тем же именем, и слияние идёт по нему:

| жанр Steam | тег-двойник |
|---|---|
| `1` Action | `19` Action |
| `2` Strategy | `9` Strategy |
| `3` RPG | `122` RPG |
| `9` Racing | `699` Racing |
| `18` Sports | `701` Sports |
| `25` Adventure | `21` Adventure |
| `28` Simulation | `599` Simulation |
| `29` Massively Multiplayer | `128` Massively Multiplayer |

Всего у Steam **446 тегов** (`IStoreService/GetTagList`), жанр несут около 190.

### Колонка

| Наш жанр | Метки Steam |
|---|---|
| Action | `19` Action **без** `122` RPG, `4434` JRPG **и без** `4231` Action RPG · `1646` Hack and Slash · `4158` Beat 'em up · `323922` Musou · `3993` Combat · `4608` Swordplay · `11104` Vehicular Combat · `3955` Character Action Game · `4777` Spectacle fighter · `4106` Action-Adventure · `4637` Top-Down Shooter · `4758` Twin Stick Shooter · `4255` Shoot 'Em Up · `3954` Rail Shooter · `56690` On-Rails Shooter · `1687` Stealth · `1776` Espionage · `97070` Assassins · `4036` Parkour · `42804` Action Roguelike |
| Action-RPG | `4231` Action RPG — **гасит** `19`, `122` и `4434` · `29482` Souls-like · `19` **+** `122` · `19` **+** `4434` |
| RPG | `122` RPG **без** `19` Action · `4434` JRPG **без** `19` Action · `4474` CRPG · `10695` Party-Based RPG · `1754` MMORPG · `17305` Strategy RPG · `21725` Tactical RPG · `1720` Dungeon Crawler **без** `1716`/`3959`/`454187`/`1759` |
| Shooter | `1774` Shooter · `1663` FPS · `3814` Third-Person Shooter · `5547` Arena Shooter · `1023537` Boomer Shooter · `353880` Looter Shooter · `620519` Hero Shooter · `1199779` Extraction Shooter · `7423` Sniper |
| Strategy | `9` Strategy · `1676` RTS · `1741` Turn-Based Strategy · `4364` Grand Strategy · `1670` 4X · `1645` Tower Defense · `1723` Action RTS · `4684` Wargame · `17305` Strategy RPG · `12472` Management · `8945` Resource Management · `4695` Economy · `4845` Capitalism · `6310` Diplomacy · `4202` Trading · `4328` City Builder · `1643` Building · `7332` Base Building · `220585` Colony Sim · `255534` Automation · `5300` God Game · `5981` Mining · `26921` Political Sim · `16689` Time Management · `10383` Transportation |
| Tactical | `1708` Tactical · `14139` Turn-Based Tactics · `3813` Real Time Tactics · `21725` Tactical RPG |
| Quest | `1698` Point & Click · `11014` Interactive Fiction · `3799` Visual Novel · `31579` Otome · `5900` Walking Simulator · `4486` Choose Your Own Adventure · `31275` Text-Based · `18594` FMV · `21` Adventure **без любой другой метки из этой таблицы** |
| Platformer | `1625` Platformer · `5379` 2D Platformer · `5395` 3D Platformer · `3877` Precision Platformer · `5537` Puzzle Platformer · `1628` Metroidvania |
| Roguelike | `1716` Roguelike · `454187` Traditional Roguelike · `3959` Roguelite · `198631` Mystery Dungeon · `42804` Action Roguelike · `1091588` Roguelike Deckbuilder · `1759` Perma Death |
| Survival | `1662` Survival · `1100689` Open World Survival Craft · `1702` Crafting |
| Fighting | `1743` Fighting · `4736` 2D Fighter · `6506` 3D Fighter · `6915` Martial Arts |
| Racing | `699` Racing · `1644` Driving · `4102` Combat Racing · `1100687` Automobile Sim · `7622` Offroad · `15868` Motocross · `129761` ATV · `198913` Motorbike · `123332` Bikes · `252854` BMX · `19568` Cycling |
| Arcade | `1773` Arcade · `6621` Pinball · `8666` Runner · `1752` Rhythm · `5154` Score Attack · `5390` Time Attack · `4885` Bullet Hell · `723991` Bullet Heaven · `379975` Clicker · `615955` Idler · `560542` Incremental |
| Puzzle | `1664` Puzzle · `6129` Logic · `1665` Match 3 · `1730` Sokoban · `37376` Falling Blocks · `1738` Hidden Object · `5432` Programming · `769306` Escape Room · `24003` Word Game · `71389` Spelling · `5537` Puzzle Platformer |
| Horror | `1667` Horror · `3978` Survival Horror · `1721` Psychological Horror · `42089` Jump Scare · `1659` Zombies · `7432` Lovecraftian · `12686` Vampires · `17015` Werewolves |
| Simulator | `599` Simulation · `10235` Life Sim · `9551` Dating Sim · `16598` Space Sim · `15045` Flight · `37799` Combat Flight Simulator · `1616` Trains · `87918` Farming Sim · `4520` Farming · `22602` Agriculture · `35079` Job Simulator · `1100688` Medical Sim · `1100686` Outbreak Sim · `9564` Hunting · `1220528` Hobby Sim · `91114` Shop Keeper · `3920` Cooking · `23491` Cleaning · `889937` Decorating · `1239876` Organizing · `13577` Sailing · `6910` Naval · `19780` Submarine |
| Sport | `701` Sports · `1254546` Football (Soccer) · `1254552` Football (American) · `1746` Basketball · `324176` Hockey · `5727` Baseball · `49213` Rugby · `847164` Volleyball · `158638` Cricket · `7038` Golf · `22955` Mini Golf · `5914` Tennis · `1753` Skateboarding · `96359` Skating · `12190` Boxing · `47827` Wrestling · `7309` Skiing · `28444` Snowboarding · `7328` Bowling · `13382` Archery · `15564` Fishing · `17927` Pool · `363767` Snooker · `4852` Billiards |
| Tabletop | `17389` Tabletop · `1770` Board Game · `1666` Card Game · `9271` Trading Card Game · `32322` Deckbuilding · `4184` Chess · `13070` Solitaire · `33572` Mahjong · `7556` Dice · `6835` Poker · `16250` Gambling · `791774` Card Battler · `1091588` Roguelike Deckbuilder |
| Multiplayer | `128` Massively Multiplayer · `3859` Multiplayer · `1685` Co-op · `1775` PvP · `176981` Battle Royale · `1718` MOBA · `3843` Online Co-Op · `7368` Local Multiplayer · `3841` Local Co-Op · `4508` Co-op Campaign · `4840` 4 Player Local · `10816` Split Screen · `7178` Party Game · `17770` Asynchronous Multiplayer · `5711` Team-Based · `745697` Social Deduction · `1754` MMORPG · `5055` eSports · `10437` Trivia |

Метка, дающая два жанра, стоит в обеих строках: `17305` Strategy RPG,
`21725` Tactical RPG, `5537` Puzzle Platformer, `42804` Action Roguelike,
`1091588` Roguelike Deckbuilder, `1754` MMORPG.

### Метки, снятые с проверкой по живым играм

Steam отдаёт список игр по тегу (`store/search/results?tags=`), и три метки на
нём не подтвердились:

| метка | что под ней | решение |
|---|---|---|
| `42329` Coding | пусто | снята |
| `1674` Typing | Typing of the Dead и половина мусора — Homicipher, AI2U | снята |
| `10437` Trivia | одиннадцать Jackbox Party Pack и ничего больше | переехала в `Multiplayer` |

Тем же способом подтверждены три оставшиеся: `5432` Programming — Opus Magnum,
Baba Is You, Turing Complete, то есть настоящие головоломки; `4036` Parkour —
Spider-Man, Dying Light, Titanfall 2, Assassin's Creed, то есть трёхмерные
экшены, а не платформеры; `3955` Character Action Game — Metal Gear Rising,
Ninja Gaiden, NieR:Automata, ULTRAKILL.

### Уточнения: жанра в одиночку не дают, нужны в сочетаниях

`1677` Turn-Based, `4325` Turn-Based Combat, `4161` Real-Time, `7107` Real-Time
with Pause, `3839` First-Person, `1697` Third Person, `4791` Top-Down,
`5851` Isometric, `3798` Side Scroller.

### Выброшено как нежанровое — около 250 меток

Настроение (`4166` Atmospheric, `1742` Story Rich, `1654` Relaxing,
`4026` Difficult), вид (`3964` Pixel Graphics, `3871` 2D, `4191` 3D,
`4975` 2.5D), темы (`3942` Sci-fi, `1684` Fantasy, `3835` Post-apocalyptic,
`4115` Cyberpunk, `4172` Medieval, `1647` Western, `16094` Mythology), софт
(`87` Utilities, `784` Video Production, `872` Animation & Modeling,
`1027` Audio Production, `809` Photo Editing, `1445` Software Training), режим
и способ распространения (`4182` Singleplayer, `492` Indie, `597` Casual,
`493` Early Access, `113` Free to Play), а также животные, страны, эпохи и
`5228` Blood с роднёй.

### Четыре спорные метки, решённые пользователем 02.08.2026

Все четыре — места, где одиночная метка врёт на замеренных играх.

**`4231` Action RPG гасит свои части.** Игра с этим тегом получает только
`Action-RPG`, даже если рядом стоят `19` Action, `122` RPG или `4434` JRPG.
Правило одно на все случаи, без исключений: пара `19`+`122` ведёт себя так же.

**`3810` Sandbox выброшен совсем.** Одиночным он врёт: у Fallout 2 весит 184 из
1328 — последний из двадцати тегов, у Stardew Valley 470, и обе игры стали бы
`Survival`. Сочетания не заводится: `Survival` и без него держится на `1662`
Survival, `1702` Crafting и `1100689` Open World Survival Craft.

**`122` RPG остаётся одиночным.** Да, Stardew Valley от этого получает `RPG`
вдобавок к `Simulator` — там тег весит 685 из 858, то есть никакой порог по
весу его бы не срезал. Принято: ролевые элементы в игре действительно есть.

**`1680` Heist выброшен.** Замер показал тему, а не жанр: PAYDAY и Dishonored —
экшены, Persona 5 — JRPG, Crime Scene Cleaner — симулятор, Teardown —
песочница. Ни одна игра жанра не теряет: PAYDAY остаётся экшеном по другим
меткам.

## Соответствия old-games.ru

Решено пользователем 02.08.2026.

**Справочник у них крошечный и плоский: пятнадцать жанров на весь сайт, тегов
нет, у игры ровно один жанр** — проверено на пятнадцати играх. Отсюда главное
для реализации: **сочетаний в этой колонке не бывает по построению**, каждое
правило состоит из одной метки, и «запрещено» тоже не понадобится.

### Колонка

| Наш жанр | old-games.ru |
|---|---|
| Action | `Action` |
| RPG | `RPG` |
| Strategy | `Strategy` |
| Quest | `Quest` · `Interactive Fiction` · `Adventure` |
| Puzzle | `Puzzle` |
| Arcade | `Arcade` |
| Racing | `Racing` |
| Sport | `Sports` |
| Simulator | `Simulation` |
| Fighting | `Fighting` |
| Tabletop | `Tabletop` |

`Other` — мусорная корзина самого сайта, не даёт ничего. `Edutainment` не
заводится: Edutainment у нас нет.

**`Adventure` сведён в `Quest` сознательно, с известным шумом.** У old-games.ru
это отдельный от `Quest` жанр, и падают туда не поинт-энд-клики, а Alone in the
Dark и Another World — хоррор и кинематографичный платформер. Myst при этом
лежит в `Quest`. Решение пользователя: «Адверчера всё-таки в квест».

### Восемь наших жанров old-games.ru не наполнит никогда

`Action-RPG`, `Shooter`, `Platformer`, `Roguelike`, `Survival`, `Horror`,
`Tactical`, `Multiplayer`. Принято: «Да, шутера нет, ну и хуй с ним».

Замер показывает, куда они утекают, и это пригодится, когда дойдёт до
дедупликации:

| игра | у них | у нас было бы |
|---|---|---|
| DOOM II: Hell on Earth | `Action` | Shooter |
| Prince of Persia 2 | `Arcade` | Platformer |
| Beyond Castle Wolfenstein | `Arcade` | Platformer |
| X-COM: UFO Defense | `Strategy` | Tactical |
| Rogue | `RPG` | Roguelike |
| Alone in the Dark | `Adventure` | Horror |

Прочее из того же замера, где расхождения нет: Diablo → `RPG`, Myst → `Quest`,
Dune II, Worms 2, Heroes of Might and Magic, SimCity, Civilization →
`Strategy`, Mortal Kombat → `Fighting`, Tetris и Lemmings → `Puzzle`,
737 Flight Simulator → `Simulation`.

### Замеры, на которые набор опирается

- **`Action-RPG` умеет назвать один источник из трёх.** У Steam это тег `4231`
  «Ролевой экшен». У GOG в полном справочнике — 64 жанра и 203 тега — такой
  метки нет вовсе, только `action` и `rpg` по отдельности плюс `souls-like`,
  `crpg`, `tactical-rpg`. У old-games.ru ближайшее — просто `RPG`.
- **У old-games.ru пятнадцать жанров на весь сайт, тегов нет, у игры один
  жанр** — проверено на пятнадцати играх. Его `Strategy` не уточняет ни вида, ни
  темпа: это и был довод против деления стратегии.
- **Из словаря GOG наша таблица берёт меньше половины:** 39 жанров из 64 и 68
  тегов из 203.
