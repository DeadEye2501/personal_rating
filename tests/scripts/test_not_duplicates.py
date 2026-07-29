"""Вердикт живёт, пока живо то, что он сравнивал."""

import not_duplicates
from not_duplicates import expired, malformed, places, sealed

LINE = "- `a.py:one` `11111111` ≠ `b.py:two` `22222222` — причина"
INDEX = {"a.py:one": "11111111", "b.py:two": "22222222"}


def test_places_are_only_the_sides_of_a_verdict():
    """В строке вердикта есть и имена из объяснения. Приняв их за стороны,
    проверка требовала бы отпечаток у того, что объявлением не является."""
    line = "- `a.py:one` `11111111` ≠ `b.py:two` — общее ушло в `Repository._mapped`"

    assert [place for place, _ in places(line)] == ["a.py:one", "b.py:two"]
    assert places("") == []


def test_sealing_stamps_what_has_no_stamp():
    line = "- `a.py:one` `11111111` ≠ `b.py:two` — причина"

    assert sealed(line, INDEX) == LINE


def test_a_stale_stamp_is_left_alone_to_die():
    """Заменить разошедшийся отпечаток — значит воскресить вердикт, который
    проверка уже признала протухшим, и сделать это молча, на пересборке карт."""
    stale = "- `a.py:one` `11111111` ≠ `b.py:two` `99999999` — причина"

    assert sealed(stale, INDEX) == stale
    assert expired([stale], INDEX)


def test_a_verdict_dies_when_the_body_it_judged_changes():
    assert expired([LINE], INDEX) == []

    changed = expired([LINE], {**INDEX, "b.py:two": "99999999"})
    assert [place.split(" ")[0] for place in changed] == ["b.py:two"]


def test_a_verdict_pointing_at_nothing_dies_too():
    """Перенесённое в соседний модуль — это тоже исчезнувшее: вердикт разбирали
    для другого места."""
    assert len(expired([LINE], {"a.py:one": "11111111"})) == 1


def test_prose_around_the_list_is_not_a_verdict():
    """В пояснении файла объявления упоминаются, и приняв их за вердикт,
    проверка краснела бы навсегда."""
    prose = "Пример: `a.py:one` сравнивали с `b.py:gone` и признали разными."

    assert expired([prose], INDEX) == []


def test_a_verdict_must_name_two_sides_and_a_reason():
    assert malformed(LINE) == ""
    assert malformed("- `a.py:one` `11111111` — одинокая") == "сторон меньше двух"
    assert malformed(f"{LINE.split(' — ')[0]}") == "нет причины"


def test_a_side_named_twice_is_refused():
    """Иначе каждая сборка дописывала бы ей ещё один отпечаток, и строка росла
    бы бесконечно."""
    twice = "- `a.py:one` `11111111` ≠ `a.py:one` `11111111` — причина"

    assert malformed(twice) == "сторона названа дважды"
    assert expired([twice], INDEX)


def test_sealing_writes_the_file(tmp_path, monkeypatch):
    """Путь записи не сторожил никто: `seal`, не пишущий вовсе, проходил и
    тесты, и `--check` — карты-то от него не зависят."""
    verdicts = tmp_path / "not-duplicates.md"
    verdicts.write_text("# Пары\n\n- `a.py:one` ≠ `b.py:two` — причина\n",
                        encoding="utf-8")
    monkeypatch.setattr(not_duplicates, "VERDICTS", verdicts)

    not_duplicates.seal(INDEX)

    assert "`a.py:one` `11111111`" in verdicts.read_text(encoding="utf-8")
    assert "`b.py:two` `22222222`" in verdicts.read_text(encoding="utf-8")


def test_sealing_a_sealed_file_changes_nothing(tmp_path, monkeypatch):
    """Иначе каждая сборка правила бы файл, и `--check` расходился бы сам с
    собой на ровном месте."""
    verdicts = tmp_path / "not-duplicates.md"
    verdicts.write_text(f"# Пары\n\n{LINE}\n", encoding="utf-8")
    monkeypatch.setattr(not_duplicates, "VERDICTS", verdicts)
    before = verdicts.read_bytes()

    not_duplicates.seal(INDEX)

    assert verdicts.read_bytes() == before


def test_missing_file_is_not_an_error(tmp_path, monkeypatch):
    """Проект без разобранных пар — обычное дело, особенно первый день."""
    monkeypatch.setattr(not_duplicates, "VERDICTS", tmp_path / "нет-такого.md")

    not_duplicates.seal(INDEX)

    assert not_duplicates.verdict_lines() == []
