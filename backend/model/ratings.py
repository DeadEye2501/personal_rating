"""Ответ оценочного источника на границе слоёв."""

from dataclasses import dataclass, field

from backend.model.external import ExternalId, ExternalRating


@dataclass(frozen=True, slots=True)
class Ratings:
    """`external_ids` непуст там, где источник заодно сообщил идентификатор, по
    которому дальше ходить дешевле: у Кинопоиска это его собственный id. У
    MDBList и OMDB он пуст — мы их спрашиваем по тому же `imdb_id`, который и
    так знаем."""

    values: tuple[ExternalRating, ...] = field(default_factory=tuple)
    external_ids: tuple[ExternalId, ...] = field(default_factory=tuple)
