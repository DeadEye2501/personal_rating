"""Свой тег на границе слоёв."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tag:
    """Своя метка. В отличие от жанра, снаружи не приходит никогда."""

    id: int
    name: str
