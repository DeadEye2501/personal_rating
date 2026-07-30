# Ревью слайса «минорные правки 01»: качество затронутых тестов

Дата: 30.07.2026. Измерение — качество тестов, затронутых слайсом.
Предмет — незакоммиченная правка поверх `9975659`. Только чтение: код, тесты и
git не менялись, мутации не гонялись (шаг исполнителя уже сделан).

## Прогон

```
python -m pytest tests/backend/test_loading.py tests/backend/test_views.py
  tests/backend/test_genres.py tests/backend/test_genre_resolution.py
  tests/backend/sources/test_tmdb_card.py tests/backend/sources/test_tmdb_search.py
  tests/backend/sources/test_tmdb_failures.py tests/backend/test_view_types.py -q
```

**127 passed за 4.08 с.** Ни падений, ни предупреждений, ни пропущенных.

## Что изменилось в тестах

Один помощник в `tests/backend/test_loading.py`: `candidate()` перестал собирать
`CardView` руками и стал звать `view_from_hit(hit(...))`. Тот же путь применён в
`test_a_game_is_asked_about_as_a_game`, где `CardView` собирался по месту.

Правка честная и полезная по мотиву, но **покрытия она не добавляет**: из
кандидата загрузчик читает ровно пять полей — `item_id`, `source`, `source_id`,
`kind`, `poster_url`. Остальное (`year`, `synopsis`, `original_title`, `genres`,
`external`) в этом модуле не наблюдается ничем и наблюдаться не может: в базу
уезжает **детальная** карточка, а не кандидат. Полноту переноса выдачи в
`CardView` сторожит `tests/backend/test_view_types.py::test_a_candidate_carries_what_the_search_gave`,
и после правки он остаётся единственным её сторожем. Это не возражение против
правки — это уточнение того, чего от неё не надо ждать.

## Таблица по тестам `test_loading.py`

Строки в порядке файла. «Следствие» — что видно снаружи после отработки.
«Ломающая строка» — одна правка, которую легко сделать случайно.

| тест | какое следствие наблюдает | одна строка, которая его уронит |
|---|---|---|
| `test_a_candidate_becomes_a_card` | в библиотеке появилась строка, и в ней `title` и `runtime` из **детального** ответа (у кандидата `runtime` нет вовсе) | `LibraryRepository.create`: `runtime` выпал из набора колонок вставки — или `rows.to_item` читает его из чужой колонки |
| `test_the_detail_round_brings_what_the_search_lacked` | `ViewsRepository.views_for` отдаёт карточку с длительностью и составом — то есть части записаны и читаются обратно | `CardWriter._write_the_rest`: `self._attach_credits(self._people, …)` → `self._companies` (роли людей и студий местами); `view.people` опустеет |
| `test_the_detail_round_is_asked_about_the_right_card` | номер, с которым источник спросили (`client.asked`) | `view_from_hit`: `source_id=hit.source_id` потерян (поймана мутациями) |
| `test_a_game_is_asked_about_as_a_game` | тип содержимого, с которым источник спросили | `view_from_hit`: `kind=hit.kind` → `kind=Kind.MOVIE`; или в `Loader.ensure` `client.card(view.source_id, view.kind)` → зашитый `Kind.MOVIE` |
| `test_the_poster_is_stored_with_the_card` | байты достаются из хранилища постеров по `item_id` карточки | `CardWriter._write_the_rest`: снята ветка `if poster is not None: await self.posters.save(...)` — или в `save` уехал не тот `item_id` |
| `test_a_card_already_in_the_base_is_not_asked_for_again` | отдан `id` уже лежавшей карточки, и источнику не задали ни одного вопроса | `Loader.ensure`: снят `if existing is not None: return existing.id` — дальше `ItemExists`, и вместо `id` вернётся `Refusal` |
| `test_a_view_that_knows_its_identifier_costs_nothing` | отдан `item_id` карточки, источнику вопросов нет | `Loader.ensure`: снят `if view.item_id is not None: return view.item_id` |
| `test_a_refusal_of_the_source_writes_nothing` | наружу пришёл **тот самый** объект отказа, и в базе нет строки по паре «источник + номер» | `Loader.ensure`: `if not isinstance(card, Found)` → `if isinstance(card, Missing)`; отказ провалится в писателя |
| `test_a_vanished_card_is_missing_and_not_a_refusal` | тип исхода снаружи: `Missing`, а не `Refusal` | `Loader.ensure`: `return card` → `return broken(...)` в той же ветке; или `asking.answered` начал переводить `Missing` в отказ. Единственный сторож этого различия на пути загрузки |
| `test_a_broken_client_becomes_a_refusal` | исключение клиента превратилось в `Refusal(BROKEN)` с текстом внутри `detail`, наружу не улетело, в базе ничего нет | `Loader.ensure`: `answered(client.card(...), client.name)` → `client.card(...)` прямо в `gather`; `RuntimeError` уйдёт через границу потоков |
| `test_a_poster_that_did_not_arrive_stops_the_writing` | отказ наружу, пустая база **и** пустой ERROR-лог: писателя не позвали вовсе | `Loader.ensure`: проверка `isinstance(poster, Refusal)` переехала **после** `self._writer.save(...)` — база останется пустой (откат), но в логе появится `logger.exception` |
| `test_a_card_without_a_cover_in_the_source_is_still_written` | карточка записана, в хранилище постеров по её `id` пусто | `PosterService._fetched`: `if not url: return None` → `return self._refuse(...)`; загрузка отказала бы на каждой карточке без обложки |
| `test_a_cover_absent_from_the_search_but_present_in_the_detail` | обложка всё-таки легла в хранилище, хотя у кандидата адреса не было | `CardWriter.save`: снята ветка `if poster is None: poster = await self.posters.fetch(...)` — в хранилище будет пусто |
| `test_the_cover_is_fetched_once` | **число** ушедших за обложкой запросов (`rig.requests`) — ровно один | `Loader.ensure`: `self._writer.save(card.value, poster)` → `save(card.value)`; писатель полезет за обложкой сам, запросов станет два. **Кто именно скачал — не наблюдается, см. находку 1** |
| `test_the_two_rounds_go_together` | **порядок** событий: «обложка началась» раньше, чем «карточка приехала» | `Loader.ensure`: `asyncio.gather(...)` разложен на два последовательных `await` (сначала карточка, потом обложка) |
| `test_an_unknown_source_is_a_refusal_and_a_log` | `Refusal("manual", BROKEN)` наружу и запись в логе, называющая **действие**, а не только источник | `Loader._catalog`: `logger.warning("нечем %s: источник %s", action, source)` → сообщение без `action`; оба зовущих станут в логе неразличимы |

Теста, у которого ответа на второй вопрос нет, в модуле не нашлось. Ни один не
снимается.

## Находки

### 1. `test_the_cover_is_fetched_once` не различает, кто скачал обложку

Тест утверждает докстрингом: «обложку скачивает загрузчик и передаёт писателю
готовой». Наблюдает он при этом только длину `rig.requests` и адрес в ней. А
адрес у кандидата и в детальном ответе **один и тот же**: `candidate()` и
`source_card()` умалчивают про `poster` одинаково —
`https://example.com/p.jpg`.

Из этого следует ровно то, что показала мутация. Потеряй `view_from_hit` поле
`poster_url` — у кандидата адреса нет, `PosterService._fetched` на пустом
адресе возвращает `None` **без запроса**, `CardWriter.save` видит `poster is
None` и качает сам, по `card.item.poster_url`, то есть по тому же адресу. Итог —
один запрос по ожидаемому адресу, тест зелёный. Заявленное свойство (круги 2а и
2б идут разом, писатель получает готовое) при этом сломано целиком: обложка
поехала после конца детального ответа.

Наблюдаемое следствие, которое их различает, — **адрес** единственного запроса,
если у кандидата и у детального ответа они разные:

```python
rig = loader(Found(source_card(poster="https://example.com/detail.jpg")))
await rig.load.ensure(candidate(poster="https://example.com/search.jpg"))
assert [str(one.url) for one in rig.requests] == ["https://example.com/search.jpg"]
```

Один assert сторожит тогда оба свойства сразу: запрос один (иначе в списке два)
и сделал его загрузчик по адресу кандидата (иначе в списке `detail.jpg`).
Расхождение адресов не выдумка: TMDB отдаёт в выдаче и в карточке один и тот же
путь, но у Steam и GOG обложка строится из ответа, и совпадение адресов —
свойство источника, а не кода, который тест проверяет.

Переименовывать тест не нужно — нужно дать ему то, чем он сможет упасть.

### 2. Оба теста на `candidate(poster="")` кругов не наблюдают

Вопрос из задания: наблюдается ли разница между «адрес пришёл с выдачей» и
«адрес приехал только в детальном ответе»? **Ни одним из двух.**

`test_a_cover_absent_from_the_search_but_present_in_the_detail` смотрит только
`posters.get(item_id) == PICTURE`. Тот же самый `PICTURE` окажется в хранилище и
на пути «адрес пришёл с выдачей»: следствие у двух путей совпадает дословно, и
докстринг про «обложка едет вторым запросом уже внутри писателя» тест не
проверяет ничем.

Здесь, в отличие от находки 1, достроить дешевле: у кандидата адрес пуст, значит
загрузчик запроса не делает вовсе, и **единственный** запрос в списке
физически может быть только запросом писателя.

```python
assert [str(one.url) for one in rig.requests] == ["https://example.com/p.jpg"]
```

С ним тест начинает различать три вещи, которых сейчас не различает: что запрос
был ровно один (писатель не продублировал), что он ушёл по адресу из детального
ответа, и что загрузчик на пустом адресе в сеть не полез.

`test_a_card_without_a_cover_in_the_source_is_still_written` про круги ничего и
не обещает, и его докстринг честно объясняет, почему пусто у обоих: иначе
писатель скачал бы обложку вторым запросом и тест проверял бы не то. Претензий
нет; можно усилить одной строкой `assert rig.requests == []` — «нет адреса, нет
и запроса», — и это тоже наблюдаемое следствие, сейчас не сторожимое ничем.

### 3. Помощник `candidate()` обещает докстрингом больше, чем даёт

«Появись у `CardView` поле, которое переносит поиск, тринадцать проверок пошли
бы на карточке, которой не бывает» — верно, но у нового поля в этом модуле не
будет ни одного наблюдателя: загрузчик читает из кандидата пять полей и
записывает в базу детальную карточку. Расхождение поймает не `test_loading.py`,
а `test_view_types.py`. Формулировку стоит сузить до того, что правда: кандидат
собирается тем же путём, каким приезжает в работе, — чтобы модуль не описывал
себя как сторожа полноты `view_from_hit`.

## Догадки (для итогового ревью, здесь не проверялись)

- `Loader.ensure`: `self._posters.fetch(view.source, view.poster_url)` →
  `fetch(card.item.source, ...)` невозможно (карточки ещё нет), но подмена
  `view.source` на зашитый `Source.TMDB` пройдёт молча по всему
  `test_loading.py`: транспорт в оснастке один на все три источника, а
  `test_a_game_is_asked_about_as_a_game` до обложки не доходит (`source_card()`
  отдаёт карточку TMDB и её `poster_url`, но проверяется только `client.asked`).
- `CardWriter.save`: `if poster is None` → `if not poster` пройдёт молча — пустых
  байтов обложки в этом модуле нет ни в одном тесте (пустоту постера сторожит
  ревью плана 4, но в другом модуле).
- `Repository._grouped`: `defaultdict(list)` → `{}` ловится только через
  `ViewsRepository._by_card`. У второго зова, `GenresRepository.index`,
  результат тут же сплющивается в обычный словарь, так что объявленный в
  докстринге `_grouped` контракт («карточка без признака обязана дать пустой
  список») наблюдаем ровно у одного из двух зовущих. Совпадает с таблицей
  мутаций исполнителя; проверить стоит, не появится ли третий зов, который на
  этот контракт положится, не имея своего теста.
- `TmdbClient._asked`: подмена `self._params(**extra)` на `self._params()`
  ловится (мутации это показали), но подмена **порядка** — отдать `verdict`
  раньше проверки `isinstance` — вряд ли: на не-`Response` `_verdict` упал бы
  атрибутом, и тест увидел бы исключение вместо отказа. Стоит проверить, что
  где-то наблюдается именно `Refusal`, а не «тест упал как-нибудь».
