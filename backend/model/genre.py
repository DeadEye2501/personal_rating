from dataclasses import dataclass

from backend.model.kinds import GenreKind


@dataclass(frozen=True, slots=True)
class Genre:
    id: int
    name: str
    kind: GenreKind
