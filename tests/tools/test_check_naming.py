"""The check on test names."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_naming import LEAST_WORDS, VAGUE, problems, problems_in, words_of


def test_every_test_in_this_suite_says_what_is_true() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_words_of_a_name_drop_the_prefix() -> None:
    assert words_of("test_a_gauge_reading_is_refused") == [
        "a",
        "gauge",
        "reading",
        "is",
        "refused",
    ]


def test_a_short_name_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "test_sample.py"
    where.write_text('"""Tests."""\n\n\ndef test_gauge() -> None:\n    pass\n', encoding="utf-8")
    found = problems_in(where)
    assert len(found) == 1
    assert "does not say much" in found[0].says


def test_a_vague_word_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "test_sample.py"
    where.write_text(
        '"""Tests."""\n\n\ndef test_the_gauge_reading_works_here() -> None:\n    pass\n',
        encoding="utf-8",
    )
    found = problems_in(where)
    assert any("says works" in one.says for one in found)


def test_good_is_not_a_vague_word_here() -> None:
    assert "good" not in VAGUE
    assert LEAST_WORDS == 5


def test_a_name_that_says_something_is_left_alone(tmp_path: Path) -> None:
    where = tmp_path / "test_sample.py"
    where.write_text(
        '"""Tests."""\n\n\n'
        "def test_a_length_with_five_good_ties_holds_class_one() -> None:\n    pass\n",
        encoding="utf-8",
    )
    assert problems_in(where) == []
