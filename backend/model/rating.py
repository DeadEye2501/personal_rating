from dataclasses import dataclass


def average_score(*aspects: int | None) -> float | None:
    """Среднее выставленных шкал. Невыставленная шкала в счёт не идёт —
    иначе одна проставленная оценка из трёх занижалась бы втрое."""
    filled = [aspect for aspect in aspects if aspect is not None]
    if not filled:
        return None
    return sum(filled) / len(filled)


@dataclass(frozen=True, slots=True)
class Rating:
    item_id: int
    score: float | None

    visual: int | None = None
    narrative: int | None = None
    gameplay: int | None = None
    review: str = ""
