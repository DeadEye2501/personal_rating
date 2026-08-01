"""Складывание своей выдачи с чужой: порядок половин и снятие близнецов.

Отдельно от `test_search.py`: складывает не сервис, а `merge_results` из модели,
и зовут его с обеих сторон границы — сервис клика по человеку и мост."""

from backend.model import (
    CardView,
    Kind,
    Source,
    merge_results,
    view_from_hit,
)
from tests.conftest import hit


def local_view(source_id="157336", title="Интерстеллар") -> CardView:
    return CardView(item_id=7, kind=Kind.MOVIE, source=Source.TMDB,
                    source_id=source_id, title=title)


def test_a_local_card_comes_first_and_its_twin_does_not_repeat():
    """Своё идёт впереди всего чужого, а чужой близнец вторым разом не
    показывается: карточка одна, и показать надо ту, у которой есть оценка."""
    external = [view_from_hit(hit("1", "Первый")), view_from_hit(hit("157336"))]
    merged = merge_results([local_view()], external)

    assert [v.source_id for v in merged] == ["157336", "1"]
    assert merged[0].item_id == 7


def test_what_is_found_only_locally_comes_first_too():
    external = [view_from_hit(hit("1", "Первый"))]
    merged = merge_results([local_view("999", "Только у меня")], external)

    assert [v.source_id for v in merged] == ["999", "1"]


def test_the_order_of_the_local_half_is_kept():
    """Своя половина приходит уже упорядоченной — по оценке у клика, по
    названию у строки, — и склейка этого порядка не трогает."""
    mine = [local_view("999", "Своё первое"), local_view("998", "Своё второе")]
    merged = merge_results(mine, [view_from_hit(hit("1", "Чужое"))])

    assert [v.source_id for v in merged] == ["999", "998", "1"]


def test_duplicates_inside_one_answer_are_dropped():
    """Внутри чужой половины близнецы бывают и без своей: строка спрашивает
    один TMDB дважды — по названию и по имени, — и фильм может приехать обоими
    путями."""
    external = [view_from_hit(hit("157336")), view_from_hit(hit("157336"))]

    assert len(merge_results([], external)) == 1


def test_the_same_game_in_two_stores_shows_up_twice():
    """Общего ключа между Steam и GOG нет — склейки в выдаче тоже. Решает
    человек.

    Идентификатор нарочно один и тот же: диапазоны номеров у магазинов
    пересекаются, и ключ обязан быть составным. При склейке по одному
    `source_id` одна из двух игр молча пропала бы."""
    external = [
        view_from_hit(hit("100", "The Witcher 3", source=Source.STEAM)),
        view_from_hit(hit("100", "The Witcher 3", source=Source.GOG)),
    ]

    assert len(merge_results([], external)) == 2


def test_a_local_card_of_another_source_does_not_take_the_place():
    """Тот же составной ключ с другой стороны: своя карточка из Steam не
    подменяет собой кандидата из GOG под тем же номером."""
    mine = CardView(item_id=7, kind=Kind.GAME, source=Source.STEAM,
                    source_id="100", title="Ведьмак у меня")
    external = [view_from_hit(hit("100", "Ведьмак в GOG", source=Source.GOG,
                                  kind=Kind.GAME))]

    merged = merge_results([mine], external)

    assert [v.title for v in merged] == ["Ведьмак у меня", "Ведьмак в GOG"]


def test_order_of_the_source_is_kept():
    external = [view_from_hit(hit(str(n), f"Фильм {n}")) for n in range(5)]
    merged = merge_results([], external)

    assert [v.source_id for v in merged] == ["0", "1", "2", "3", "4"]


def test_nothing_found_anywhere_is_an_empty_answer():
    assert merge_results([], []) == []
