# Ревью плана 11: мутации

Измерение — качество тестов. Проверялось одно: падает ли тест именно за то, что
обещает именем и докстрингом.

Дерево — отдельная копия в scratchpad, основной каталог не трогался. Мутаций
внесено **47**, каждая — одна строка, каждая откачена сразу. Молча прошло **13**.
Каждая молчаливая перепроверена на всём наборе `tests/backend` (997 тестов), а не
только на своём файле: ниже помечено, где зелёными остались все 997.

Дерево после работы чисто, набор — 997 зелёных.

## Таблица мутаций

| Что сломал | Файл тестов | Итог |
|---|---|---|
| `library.search`: убран `.distinct()` | `test_credit_search.py`, затем весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `_named`: убран отбор `credit.item_id == item.id` внутри `EXISTS` | `test_credit_search.py` | покраснел |
| `search`: половина людей стала второй половиной студий (`PEOPLE` → `COMPANIES`) | `test_credit_search.py` | покраснел |
| `search`: половина студий стала второй половиной людей (`COMPANIES` → `PEOPLE`) | `test_credit_search.py` | покраснел |
| `search`: `\|` → `&` на условии по людям | `test_credit_search.py` | покраснел |
| `_named`: связь склеена по `credit.item_id`, а не по `entity.link` | `test_credit_search.py`, затем весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `_named`: снят `folded` с имени | `test_credit_search.py` | покраснел |
| `_named`: `contains` → равенство целиком | `test_credit_search.py` | покраснел |
| `_outer`: всегда отдаёт `source_id` | `test_people_search.py`, `test_credits.py` | покраснел |
| `_outer`: всегда отдаёт `None` | `test_people_search.py`, `test_credits.py` | покраснел |
| `_outer`: `!= MANUAL` → `== MANUAL` | `test_people_search.py`, `test_credits.py` | покраснел |
| `identity_of`: вместо имени отдаётся `source_id` | `test_people_search.py`, `test_credits.py` | покраснел |
| `identity_of`: убран отбор `table.id == entity_id` | `test_people_search.py`, `test_credits.py`, затем весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `credits_of`: в `id` берётся `credit.item_id` вместо `table.id` | `test_credit_search.py`, `test_credits.py`, затем весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `views._credits`: в `id` берётся `credit.item_id` вместо `table.id` | весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `to_credit`: `entity_id` всегда `None` | `test_credit_search.py`, `test_views.py` | покраснел |
| `PeopleSearch._outside`: ветви по идентичности обменяны | `test_people_search.py` | покраснел |
| `_works`: отказы не собираются | `test_people_search.py` | покраснел |
| `_own`: возвращает пустой список | `test_people_search.py` | покраснел |
| `by_entity`: `identity is None` → `is not None` | `test_people_search.py` | покраснел |
| `_outside`: отказ `find_people` теряется (`return [], []`) | `test_people_search.py`, затем весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `by_entity`: `merge_results(own, outside)` → наоборот | `test_people_search.py` | покраснел |
| `_works`: спрашивается только первый тёзка | `test_people_search.py` | покраснел |
| `Sources.people_for`: клиент отдаётся и играм | `test_people_search.py`, `test_registry.py`, затем весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `Sources.people_for`: фильмам отдаётся `steam` | весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `parse_credits`: разбирается только `cast` | `test_tmdb_people.py` | покраснел |
| `parse_credits`: разбирается только `crew` | `test_tmdb_people.py` | покраснел |
| `parse_credits`: снят `unique` | `test_tmdb_people.py` | покраснел |
| `_hits`: всегда читает киношные `_KEYS` | `test_tmdb_people.py`, `test_tmdb_search.py` | покраснел |
| `parse_people`: имя и идентификатор обменяны | `test_tmdb_people.py` | покраснел |
| `parse_people`: читается `cast` вместо `results` | `test_tmdb_people.py` | покраснел |
| `credits_of`: `movie_credits` ↔ `tv_credits` | `test_tmdb_people.py` | покраснел |
| `credits_of`: разбор через `parse_search` вместо `parse_credits` | `test_tmdb_people.py` | покраснел |
| `find_people`: имя в запрос не уходит | `test_tmdb_people.py` | покраснел |
| `hits.to_views`: жанры теряются | `test_people_search.py`, `test_search.py` | покраснел |
| `hits.to_views`: оценка источника теряется | `test_people_search.py`, `test_search.py` | покраснел |
| `hits._genres_of`: снят `unique` | `test_people_search.py`, `test_search.py`, `test_genre_resolution.py` | покраснел |
| `hits.to_views`: справочник пространства приезжает пустым | весь `tests/backend` | покраснел |
| `app.build_backend`: `people` и `companies` у `finder` обменяны | весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `app.build_backend`: `finder=None` | весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `PeopleSearch.__init__`: ключи `people`/`companies` обменяны | `test_people_search.py` | покраснел |
| `_own`: `limit=OWN_SIZE` → `limit=1` | `test_people_search.py` | **прошёл молча** |
| `_own`: `offset=0` → `offset=1` | `test_people_search.py` | покраснел |
| `_own`: свои карточки в обратном порядке | `test_people_search.py` | **прошёл молча** |
| `_works`: от каждого тёзки берётся одна работа | `test_people_search.py`, затем весь `tests/backend` | **прошёл молча (997 зелёных)** |
| `by_entity`: `refusals=()` в ответе | `test_people_search.py` | покраснел |
| `search`: снят `.limit(limit)` | `test_credit_search.py`, `test_search_local.py` | покраснел |

## Находки

### Critical — мутация прошла молча, и это единственный сторож свойства

**1. Сборка `finder` не наблюдается ничем: `finder=None` оставляет 997 зелёных.**

Сломано: в `backend/app.py` поле `finder=PeopleSearch(...)` заменено на
`finder=None`; отдельно — `people=parts["companies"], companies=parts["people"]`,
то есть люди и студии обменяны местами.

Почему не заметил никто: `build_backend` собирается в тестах, но собранный
`finder` не зовёт ни один. `test_people_search.py` строит `PeopleSearch` руками,
своими частями, и до боевой сборки не доходит вовсе.

Это ровно тот дефект, который проект ловил уже дважды — девять молчаливых мутаций
по `backend/app.py` в плане 4 и `loader=None` при 909 зелёных в закрывающем ревью.
Список работ плана 11 запись про это не воспроизвёл.

Чем закрыть: в тесте боевой сборки завести человека со связью и позвать
`backend.finder.by_entity("people", entity_id, Kind.MOVIE)` — ответ обязан
содержать эту карточку. Тот же вызов с `domain="companies"` и студией закрывает
обмен репозиториев: при обмене поиск по человеку пошёл бы в таблицу студий и
вернул бы пусто.

**2. `Sources.people_for` не проверяется ни одним тестом — любой ответ зелёный.**

Сломано: `return None if kind is Kind.GAME else self.tmdb` заменено сначала на
`return self.tmdb` (клиент отдаётся и играм), потом на `... else self.steam`
(фильмам отдаётся магазин). Обе мутации — 997 зелёных.

Почему не заметил никто: в `tests/backend/sources/test_registry.py` про
`people_for` нет ни строки, а `test_people_search.py` работает через
`tests/fakes.py::FakeSources`, где **правило переписано заново**:
`return None if kind is Kind.GAME else self._clients[0]`. Тест
`test_a_game_company_never_goes_outside` с докстрингом «Steam отдаёт разметку,
GOG молча игнорирует параметр» сторожит подделку, а не боевой реестр. Своим
докстрингом фикстура это честно объявляет («настоящий реестр решает это сам, и
проверяется оно в его тестах»), но в тестах реестра этого нет.

Чем закрыть: два прямых теста в `test_registry.py` — `people_for(Kind.GAME) is
None`, `people_for(Kind.MOVIE) is sources.tmdb` и `people_for(Kind.SERIES) is
sources.tmdb`.

**3. Идентичность строки человека держится на совпадении `id`, и три подмены
колонки проходят молча.**

Три отдельные мутации, одна причина:

- `_named` в `library.py`: связь склеена по `credit.item_id == table.id` вместо
  `entity.link == table.id` — 997 зелёных;
- `credits_of` в `credits.py`: в колонку `id` подставлен `credit.item_id` —
  997 зелёных;
- `views._credits`: то же самое — 997 зелёных.

Почему не заметил никто: во всех тестах, где это проверяется, карточка и человек
создаются первыми строками своих таблиц, и `item.id == person.id == 1`.
`test_a_credit_carries_the_row_of_the_person` утверждает
`credit.entity_id == entity_id` — и это правда при любой из двух колонок.
Проверка на отсутствие поля (`entity_id=None`) краснеет, проверка на его смысл —
нет.

Последствие в боевом коде не косметическое: `entity_id` из `views._credits`
уезжает в разметку и им же зовётся `by_entity`. Подмени колонку — клик по актёру
открыл бы работы случайного человека, чей `id` совпал с номером карточки, и
выдача при этом выглядела бы правдоподобно.

Чем закрыть: развести идентификаторы в фикстуре — завести две-три лишние
карточки до человека (или наоборот), чтобы `item.id != person.id`. Одна строка
в `test_credit_search.py` и одна в тесте `views` закрывают все три места.
Отдельно нужен тест на `entity_id` в составе `CardView`: сейчас путь
`views._credits` не сторожит ничто, а именно он кормит клик.

**4. `identity_of` может не смотреть, чью строку спросили.**

Сломано: `where(table.c.id == entity_id)` → `where(table.c.id != None)`. 997
зелёных.

Почему не заметил никто: во всех тестах сервиса в таблице ровно один человек, а
в единственном тесте про несуществующую строку (`by_entity("people", 404, ...)`)
таблица пуста — `None` возвращается и без отбора.

Чем закрыть: в `test_an_unknown_entity_has_nothing_to_show` завести перед вызовом
одного настоящего человека, а спрашивать чужой `entity_id`. Тогда без отбора
`identity_of` вернул бы чужую пару и внешняя половина ушла бы в сеть за чужим
человеком.

**5. Отказ `find_people` теряется бесследно.**

Сломано: в `_outside` ветка `if not isinstance(found, Found): return [], [found]`
заменена на `return [], []`. 997 зелёных.

Почему не заметил никто: единственный тест про отказ
(`test_own_cards_come_even_when_the_source_refuses`) идёт по ветке с внешней
идентичностью — отказывает `credits_of`, а не `find_people`. Путь заведённого
руками человека при отказе источника не проверяется вовсе: у пользователя вместо
плашки «источник недоступен» была бы тихая выдача только из своей базы, то есть
ровно та ложь, ради которой отказы и заведены значением.

Чем закрыть: тест с `people_outcome=Refusal(...)` — своя половина приезжает,
`found.refusals` непусто.

**6. `.distinct()` в `search` не наблюдается, а тест утверждает обратное.**

Сломано: `.distinct()` убран. 997 зелёных.

Почему не заметил никто: и не мог. Состав подмешивается в `WHERE` через
`EXISTS`, а не соединением, и строк карточки это не размножает ни при какой
раскладке связей. Тест `test_a_card_is_returned_once_even_with_two_roles`
привязывает человека двумя ролями и утверждает в докстринге «Без `distinct` она
заняла бы два места в выдаче» — это неправда для написанного запроса. Докстринг
самой `search` («`distinct` обязателен») утверждает то же самое.

Это тот же класс, что уже разбирался проектом на втором ключе сортировки
библиотеки: свойство не наблюдается, и сторож его не сторожит.

Чем закрыть — решением, а не тестом. Либо `distinct` снимается как мёртвый, либо
остаётся с честной записью на месте: «страховка на случай перехода с `EXISTS` на
соединение; на нынешнем запросе не наблюдается — замерено». Тест и оба докстринга
надо привести к тому, что правда: сейчас код о себе врёт в двух местах.

### Important — прошла молча, но свойство сторожит что-то ещё

**7. `_works` может отдать по одной работе от каждого тёзки.**

Сломано: `hits.extend(outcome.value)` → `hits.extend(outcome.value[:1])`. 997
зелёных.

Почему не заметил никто: в `test_every_namesake_brings_their_work` у каждого
тёзки ровно один хит, и обрезка до одного ничего не меняет. Сам разбор
фильмографии (`parse_credits`) сторожится отдельно и полно, поэтому это Important,
а не Critical: полнота приезжающего проверена, теряется она уже в сервисе.

Чем закрыть: дать одному из тёзок два хита и проверить, что приехали оба.

### Minor

**8. `OWN_SIZE` не сторожит ничто.** `limit=OWN_SIZE` → `limit=1` проходит молча:
ни в одном тесте у человека нет двух карточек. Закрывается тем же приёмом — две
связанные карточки и проверка, что приехали обе.

**9. Порядок своей половины не сторожит ничто.** `in_order(item_ids[::-1])`
проходит молча по той же причине. Порядок при этом нигде и не обещан — если он
безразличен, это стоит записать там, где он живёт, а не заводить тест.

## Вердикт

**Готово к коммиту?** С правками.

**Довод:** поведение плана 11 в целом сторожится хорошо — 34 из 47 мутаций
поймано сразу, включая все подмены в разборе TMDB, все ветвления сервиса и почти
все условия запроса. Но две дыры повторяют то, на чём проект уже обжигался
дважды (боевая сборка не зовётся вовсе; правило реестра проверяется у подделки), а
третья делает три подмены колонки `entity_id` неразличимыми — и именно этим полем
работает новый жест. Правки дешёвые: два теста на реестр, один вызов
`backend.finder` в тесте сборки, разведённые идентификаторы в фикстурах и тест на
отказ `find_people`.
