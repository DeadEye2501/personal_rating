"""Ответ оценочного источника на границе слоёв."""

from dataclasses import dataclass, field

from backend.model.external import ExternalRating


@dataclass(frozen=True, slots=True)
class Ratings:
    """Оценки, которые источник знает об этой карточке.

    Идентификаторов здесь нет: MDBList не сообщает ни одного, которого мы не
    знали бы сами, — мы его по идентификатору и спрашиваем. Заведёт их тот
    источник, который отдаёт свой собственный, — у Кинопоиска это его id."""

    values: tuple[ExternalRating, ...] = field(default_factory=tuple)
