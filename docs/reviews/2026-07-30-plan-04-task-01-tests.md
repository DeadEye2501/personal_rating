# Ревью качества тестов — план 4, задача 1 («Типы чтения»)

Дата: 2026-07-30. Измерение: качество тестов. Только чтение, мутации не
запускались — использован список из пятнадцати мутаций, уже прогнанных
исполнителем.

## Прогон

```
cd "D:\Projects\Python Scripts\Personal Rating\personal_rating"
"C:\Users\deade\.virtualenvs\personal_rating-nun1_nuE\Scripts\python.exe" -m pytest tests/backend/test_view_types.py -q --no-header
```

Результат: `14 passed in 0.04s`.

## Разбор по тестам

Файл — `tests/backend/test_view_types.py`. Проверяемый код — `backend/model/view.py`
(`CardView`, `Tag`, `view_from_hit`, `view_from_item`) и `backend/model/query.py`
(`Section`, `Sort`, `Order`, `Filters`, `Bucket`, `Histogram`).

### 1. `test_a_candidate_has_no_identifier_in_the_base`
Следствие: `view_from_hit` не проставляет `item_id` — кандидат из поиска ещё не
строка базы. Проверка идёт через вызов функции, это поведение, а не голое чтение
объявления.
Ронка: `view.py:35`, умолчание `item_id: int | None = None` заменить на, скажем,
`= 0`. Не входит в присланный список пятнадцати.

### 2. `test_a_candidate_carries_what_the_search_gave`
Следствие: `view_from_hit` копирует `title`, `year`, `synopsis`, `poster_url` из
`hit` в `CardView`. Настоящее поведение.
Ронка: `view.py:86` (`year=hit.year`), `87` (`synopsis=hit.synopsis`) или `88`
(`poster_url=hit.poster_url`) — любая жёстко заменена на пустое/`None`. Не входит
в список пятнадцати.
**Замечание:** `original_title` в этом тесте не участвует ни во входе, ни в
проверке — см. «Непокрытое» ниже.

### 3. `test_rows_the_search_does_not_fill_are_empty`
Следствие: поля, которых нет в ответе поиска (`runtime`, `people`, `rating`,
`in_wishlist`), после `view_from_hit` остаются на умолчаниях `CardView`, то есть
функция их не выдумывает. Идёт через вызов функции — поведение, хоть и близкое к
чтению умолчания.
Ронка: `view.py:60`, `in_wishlist: bool = False` → `True` — это в точности
мутация №9 из списка.

### 4. `test_genres_are_given_from_outside`
Следствие: аргумент `genres` `view_from_hit` действительно доезжает до
`CardView.genres`.
Ронка: `view.py:89`, `genres=genres,` → `genres=(),` — в точности мутация №4.

### 5. `test_the_free_rating_of_the_source_becomes_an_external_one`
Следствие: собственная оценка TMDB из ответа поиска превращается в одну
`ExternalRating` с `source=RatingSource.TMDB` и тем же числом.
Ронка: `view.py:66`, запись `Source.TMDB: RatingSource.TMDB` в `_OWN_RATING`
подменена (вариант мутации №1), либо `view.py:78`, `value=hit.source_rating`
заменено на константу.

### 6. `test_a_store_rating_belongs_to_its_store`
Следствие: для GOG результирующая `ExternalRating.source` — именно
`RatingSource.GOG`.
Ронка: `view.py:67`, `Source.GOG: RatingSource.GOG` → `Source.GOG:
RatingSource.TMDB` — в точности мутация №1.

### 7. `test_a_source_outside_the_map_brings_no_rating`
Следствие: у Steam, которого нет в `_OWN_RATING`, оценки нет даже при заполненном
`source_rating` в кандидате.
Ронка: добавление `Source.STEAM` в `_OWN_RATING` (`view.py:65-68`) — в точности
мутация №2.

### 8. `test_a_source_in_the_map_without_a_number_brings_no_rating`
Следствие: когда `hit.source_rating is None`, `ExternalRating` не
фабрикуется, даже если источник (TMDB) есть в карте.
Ронка: `view.py:76`, снятие условия `and hit.source_rating is not None` — в
точности мутация №3.

### 9. `test_a_view_is_frozen`
Следствие: попытка присвоить поле после создания `CardView` реально роняет
`FrozenInstanceError` — неизменяемость проверена исполнением, а не чтением
декоратора.
Ронка: `view.py:23`, снятие `frozen=True` из `@dataclass(frozen=True,
slots=True)` над `CardView`. Не входит в список пятнадцати.

### 10. `test_filters_are_empty_by_default`
Следствие: нет — конструируется `Filters()` без аргументов и читаются шесть
кортежей обратно. Никакого преобразования между этим и печатным умолчанием нет.
**Это чтение объявления**, не поведения: по форме совпадает с примером из
правила 13 манифеста.
Ронка: `query.py:47`, `scores: tuple[int, ...] = ()` → `(7,)` (мутация №14) или
`query.py:50`, `excluded_genre_ids` → `(1,)` (мутация №15) — обе уже в списке.

### 11. `test_sections_and_sorts_are_named_not_numbered`
Следствие: нет — перечисляются значения `Section`/`Sort` и сравниваются список с
литералом. Учебный пример чтения объявления (почти дословно совпадает с
примером из скилла).
Ронка: `query.py:11`, `RATED = "1"` (мутация №12) или `query.py:23`, удаление
`TITLE = "title"` (мутация №13).

### 12. `test_the_default_side_is_the_one_with_more_on_top`
Первая проверка (`Order(key=Sort.SCORE).descending is True`) читает умолчание —
та же форма, что в тестах 10 и 11. Вторая (`descending=False` явно передан)
подтверждает лишь то, что конструктор датакласса хранит переданное значение —
верно для любого поля датакласса по определению, правдоподобной поломкой одной
строки не ловится ничего сверх этого.
Ронка: `query.py:33`, `descending: bool = True` → `False` — в точности
мутация №11.

### 13. `test_a_histogram_carries_its_footer`
Конструирует `Histogram(...)` напрямую и тут же читает `total`/`average` —
функции под проверкой нет, это хранение значений конструктором, а не поведение.
Ронка: только удаление поля целиком — `query.py:71` (`total: int`) или `72`
(`average: float | None`) — тогда `Histogram(...)` упадёт `TypeError` на
неизвестном ключевом аргументе. Правдоподобной поломкой одной строки внутри уже
существующих полей этот тест не роняется вовсе.

### 14. `test_a_view_of_an_item_carries_every_field`
Следствие: `view_from_item` копирует все тринадцать полей `Item` в `CardView`
верно, включая то, что счётчики сезонов и серий не перепутаны местами. Полное
сравнение объектов ловит дрейф в любом поле — настоящее поведение.
Ронка: любая строка `view.py:98-110`, например `107`/`108` со свапом
(`seasons_count=item.episodes_count`, мутация №7), `98` → `item_id=None`
(мутация №8), `110` → `synced_at=None` (мутация №6), `107` → `runtime=None`
(мутация №5).

## Тесты, которые читают объявление, а не поведение

- `test_filters_are_empty_by_default` (10)
- `test_sections_and_sorts_are_named_not_numbered` (11)
- `test_the_default_side_is_the_one_with_more_on_top` (12, частично — первая
  проверка)
- `test_a_histogram_carries_its_footer` (13)

Все четыре ловят реальные мутации из присланного списка (№9, 11–15 в разных
сочетаниях), так что вреда сейчас нет — но альтернативы «через следствие» в
границах этого модуля нет: `Filters`, `Order`, `Section`, `Sort`, `Histogram` —
чистые контейнеры данных без логики, поведение проверять не на чем. Единственный
способ проверить их поведенчески — тест на стороне, которая их использует
(фильтрация по умолчанию, сборка гистограммы в репозитории), а это уже другая
задача плана. Здесь эти тесты — не ошибка, а неизбежность формы задачи; стоит
иметь в виду при полном ревью, что настоящую проверку умолчаний унаследует
задача, которая их реально использует.

## Непокрытое

Правдоподобные поломки, которые не поймает ни один из 14 тестов:

1. **`view_from_hit` не копирует `original_title`.** Строка `view.py:85`,
   `original_title=hit.original_title` → `original_title=""`. Ни `hit()` в
   `tests/backend/test_view_types.py`, ни один тест `view_from_hit` не задаёт
   непустой `original_title` и не сверяет его в результате — проверяется только
   для `view_from_item` (тест 14, где мутация №10, судя по всему, и ловилась).
   Пройдёт молча.

2. **`view_from_hit` подставляет `kind`/`source`/`source_id` не из `hit`.**
   Строки `view.py:81-83`. Тесты 5–8 меняют `hit.source`/`hit.kind`, но только
   чтобы направить код в нужную ветку `_OWN_RATING` — ни `view.kind`, ни
   `view.source`, ни `view.source_id` ни разу не сравниваются с исходным `hit` в
   каком-либо тесте `view_from_hit`. Жёсткая подстановка вроде `source=Source.TMDB`
   независимо от `hit.source` пройдёт молча.

## Вердикт

Прогон: `14 passed`. Тесты в целом честные — 10 из 14 наблюдают следствие вызова
функции и ловят конкретную мутацию из списка. Найдены два реальных пробела
(`original_title` и identity-поля в `view_from_hit`) — оба про один и тот же
путь конвертации, оба воспроизводимы одной строкой правки теста (расширить
`test_a_candidate_carries_what_the_search_gave` или завести отдельный тест).

**Готово к коммиту: С правками** — стоит долить проверку `original_title` и
`kind`/`source`/`source_id` в тест на `view_from_hit`, прежде чем закрывать
слайс; остальное (декларативные тесты умолчаний) — осознанный предел формы
задачи, не блокер.
