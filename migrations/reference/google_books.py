"""Соответствия Google Books: значение BISAC — наш книжный жанр.

Метка приходит не из выдачи поиска, а из карточки тома: поиск обрезает путь до
верхушки и на «Задаче трёх тел» говорит `Fiction`, а карточка того же тома —
`Fiction / Science Fiction / Hard Science Fiction`.

Берётся второй уровень пути, а где его нет или он `General` — первый. Значения
первого уровня помечены ниже словом «верхний»: попадают они в справочник ровно
потому, что у части книг второго уровня нет вовсе.

Условий тут не бывает, как и у TMDB: метка означает жанр сама по себе, и на
каждое соответствие заведено своё правило — правило требует все свои метки
сразу, поэтому две метки в одном означали бы «обе одновременно».

Одно замеренное значение сюда не взято: `Fairy Tales, Folk Tales, Legends &
Mythology`. Метки в правиле разделяются запятой, а у него запятые внутри — оно
разъехалось бы на три метки, и правило требовало бы все три сразу. Менять
разделитель ради одного значения значит переписать триста шестьдесят три
существующих правила; тот же смысл несёт соседнее `Fairy Tales & Folklore`.
Цена замерена: на 115 книгах это значение встретилось один раз.
"""

from migrations.reference.rule import Rule

GOOGLE_BOOKS = [
    Rule("Фантастика", "Science Fiction"),

    Rule("Фэнтези", "Fantasy"),
    Rule("Фэнтези", "Fairy Tales & Folklore"),

    Rule("Ужасы", "Horror"),

    Rule("Детектив", "Mystery & Detective"),
    Rule("Детектив", "Thrillers"),

    Rule("Приключения", "Action & Adventure"),
    Rule("Приключения", "Sagas"),
    Rule("Приключения", "Military"),

    Rule("Романтика", "Romance"),

    Rule("Классика", "Classics"),
    Rule("Классика", "World Literature"),
    Rule("Классика", "Russian & Soviet"),
    Rule("Классика", "Russian & Former Soviet Union"),

    Rule("Исторический", "Historical"),

    Rule("Юмор", "Humorous"),

    Rule("Драма", "Drama"),                       # верхний

    Rule("Детское", "Juvenile Fiction"),          # верхний
    Rule("Детское", "Children's stories"),

    Rule("Рассказы", "Short Stories"),
    Rule("Рассказы", "Short Stories (single author)"),

    # Верхний, и самый частый запасной: девять книг из ста пятнадцати.
    Rule("Сборник", "Literary Collections"),

    # Верхний. `Fiction`, у которого второго уровня не оказалось.
    Rule("Проза", "Fiction"),

    Rule("Биография", "Biography & Autobiography"),   # верхний
    Rule("Биография", "Personal Memoirs"),

    Rule("История", "History"),                   # верхний
    Rule("История", "History & Surveys"),
    Rule("История", "History & Theory"),

    Rule("Философия", "Philosophy"),              # верхний

    Rule("Психология", "Psychology"),             # верхний
    Rule("Психология", "Clinical Psychology"),
    Rule("Психология", "Mental Health"),
    Rule("Психология", "Social Psychology"),

    Rule("Саморазвитие", "Personal Growth"),
    Rule("Саморазвитие", "Personal Success"),
    Rule("Саморазвитие", "Motivational & Inspirational"),

    Rule("Бизнес", "Business & Economics"),       # верхний
    Rule("Бизнес", "Leadership"),
    Rule("Бизнес", "Organizational Behavior"),
    Rule("Бизнес", "Practice Management"),

    Rule("Наука", "Life Sciences"),
    Rule("Наука", "Anthropology"),
    Rule("Наука", "Social Science"),              # верхний
    Rule("Наука", "Space Science"),
    Rule("Наука", "Political Science"),           # верхний

    Rule("Программирование", "Computers"),        # верхний
    Rule("Программирование", "Software Development & Engineering"),
    Rule("Программирование", "Programming"),
]
