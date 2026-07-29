# Ревью починки — итоги финального ревью плана 2

Дата: 2026-07-29. Ревьюируются два коммита `7a8a412..HEAD`
(`81f26e5` — сама починка, `8289d97` — обновление `CLAUDE.md`).

## Что проверено и как

**1. Шесть мутаций.** Рабочее дерево:
`git worktree add /c/Users/deade/AppData/Local/Temp/review-fixes HEAD`
(POSIX-путь — Windows-путь с обратными слэшами git worktree в bash-инструменте
ломает). Прогон: `python -m pytest tests/backend/sources -q --no-header` из
основного окружения (`personal_rating-nun1_nuE`). Базовый прогон — 233 зелёных.
Каждая мутация внесена точечной правкой одного файла, прогнана, откачена
(`git checkout -- <файл>`); дерево удалено по завершении
(`git worktree remove --force`).

**2. Перенос классификации в `undocumented.py`.** Прочитан весь диф
`http.py`/`undocumented.py`/`gog/client.py`/`steam/client.py`, сверен с
докстрингом `SourceHttp` («Классификацию ответов не делает») и с
`docs/reviews/2026-07-29-plan-02-final-manifest.md` (находка «Важно 1»,
которая и вызвала перенос). Проверено, что смена сигнатуры
`refuse_undocumented(http, response) → refuse_undocumented(http, status)`
не теряет данных — оба места вызова используют только `status_code`.

**3. Спеки.** `docs/specs/2026-07-27-sources.md` и
`-data-model.md` сверены построчно с `backend/sources/steam/parse.py`,
`backend/sources/steam/client.py`, `backend/sources/gog/parse.py` и с
`migrations/versions/0002_genres.py` (через `scripts/genre_map.py`, чтобы
получить точные числа, а не глазами).

**4. План.** Все четыре дописанных куска `docs/plans/2026-07-27-sources.md`
сверены с текущим кодом (`backend/sources/registry.py`,
`backend/sources/ratings/kinopoisk/`, `backend/sources/gog/parse.py`).

**5. Карты.** `python scripts/module_map.py --check` — прошёл, карты не
отстали.

## Находки

### Важно

- `docs/plans/2026-07-27-sources.md:43` — новый абзац «Общее у клиентов
  вынесено по ходу...» называет местом `refuse_undocumented`
  **`backend/sources/http.py`**, хотя в этом же коммите (`81f26e5`) функция
  переехала в `backend/sources/undocumented.py`. Оба изменения — часть одной
  правки, но не согласованы друг с другом: доку про перенос дописали, а
  соседний абзац про то же самое не поправили. Грозит небольшим — читающий план
  пойдёт искать функцию не туда, — но именно такого рода нестыковка и была
  предметом задания. Чинить: заменить `backend/sources/http.py` на
  `backend/sources/undocumented.py` в этой строке.

### Мелочь

- `CLAUDE.md:50` — «Весь набор — 479 тестов» относится к прогону из
  `docs/reviews/2026-07-29-plan-02-final-build.md` (479 прошло), который
  состоялся **до** починки шести дыр. Починка добавила 14 новых тестов
  (`test_convert.py` целиком — 11, плюс по одному в `test_gog.py`,
  `test_mdblist.py`, `test_steam.py`); сейчас в дереве 493 теста. Абзац в
  `CLAUDE.md` описывает план 2 как «сделан целиком» уже после починки, поэтому
  число рядом с ним читается как актуальное, а на деле досчитано раньше. Не
  искажает работоспособность кода, только цифру в прозе.

### Придирка к найденному, не находка

- Тест на битый жанр (`test_a_genre_without_its_identifier_is_a_broken_answer`)
  ловит именно `KeyError`, а не любое исключение — целится точно, мутация
  «проглотить недостающий ключ» ловится, а не маскируется широким
  `pytest.raises(Exception)`. Слабости не нашёл.

## Проверка шести мутаций

| Мутация | Файл | Покраснело |
|---|---|---|
| Перестановка ролей `developer`/`publisher` в `companies()` | `backend/sources/convert.py` | Да — `test_the_developer_is_not_the_publisher` |
| Обмен пространств жанра/тега у GOG в `_marks()` | `backend/sources/gog/parse.py` | Да — `test_a_genre_is_not_labelled_as_a_tag` |
| Битый жанр проглатывается (`genres()` не бросает `KeyError`) | `backend/sources/convert.py` | Да — `test_a_genre_without_its_identifier_is_a_broken_answer` |
| Ноль слился с пустотой у MDBList (`not value` вместо `value is None`) | `backend/sources/ratings/mdblist/parse.py` | Да — `test_an_honest_zero_is_not_an_empty_value` |
| Год у Steam только XXI века (`YEAR` без `19`) | `backend/sources/steam/parse.py` | Да — `test_a_game_from_the_last_century_keeps_its_year` |
| Зеркало Кинопоиска под своим именем | `backend/sources/registry.py` | Да — `test_every_source_has_its_own_breaker` |

Все шесть мутаций после починки красные, все шесть тестов бьют по привязке
метки к источнику, а не по набору меток — заявленная цель достигнута.

## Вердикт

**Правки приняты: Да, с доработкой.** Единственная строка правки —
`docs/plans/2026-07-27-sources.md:43`, где нужно заменить `http.py` на
`undocumented.py`. Код, тесты и спеки — без замечаний; перенос
`refuse_undocumented` в отдельный модуль оправдан манифестом (правило 6:
`SourceHttp` перестал держать классификацию, которую сам отрицает), сужение
сигнатуры до `status: int` корректно и не теряет данных.
