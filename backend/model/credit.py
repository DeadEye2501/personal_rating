"""Человек или студия в роли на карточке."""

from dataclasses import dataclass

from backend.model.kinds import CompanyRole, PersonRole, Source


@dataclass(frozen=True, slots=True)
class Credit:
    name: str
    role: PersonRole | CompanyRole
    position: int | None = None   # порядок в титрах, нужен для «топ-5 актёров»

    # Строка человека или студии в своей базе. Нужна клику по имени: тёзок
    # различает она, а не имя, и внешней идентичности у половины строк нет.
    # Пуста у приехавшего из источника — его в базе может ещё не быть.
    entity_id: int | None = None

    # Идентичность во внешнем источнике, если он её дал. У TMDB она лежит в
    # том же ответе, что и состав, — берётся даром. Steam и GOG отдают студии
    # голыми строками, у них тут пусто, и таких склеиваем по имени.
    source: Source | None = None
    source_id: str | None = None
