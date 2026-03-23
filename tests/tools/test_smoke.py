"""The walk a freshly installed package takes."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.smoke import ON, walk


def test_the_walk_says_what_it_did(tmp_path: Path) -> None:
    said = walk(tmp_path)
    assert said[0].startswith("spikemaul ")
    assert any("schema" in one for one in said)


def test_the_walk_reads_the_book_back_after_closing_it(tmp_path: Path) -> None:
    said = walk(tmp_path)
    assert any("SG-014 holds class 3 at 40 mph" in one for one in said)


def test_the_walk_reads_a_run_against_the_class_the_segment_holds(tmp_path: Path) -> None:
    said = walk(tmp_path)
    assert any("supports class 1" in one for one in said)


def test_the_walk_prints_a_morning_page(tmp_path: Path) -> None:
    said = walk(tmp_path)
    assert any("morning page is" in one for one in said)


def test_the_walk_leaves_a_book_behind_in_the_directory_it_was_given(tmp_path: Path) -> None:
    walk(tmp_path)
    assert (tmp_path / "plains.sqlite3").exists()


def test_the_walk_is_taken_on_a_fixed_day() -> None:
    assert ON.year == 2025
