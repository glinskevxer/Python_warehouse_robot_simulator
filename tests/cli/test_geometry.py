"""The geometry commands: loading a run and reading it back."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import Result

from tests.support.console import run

GOOD = """milepost,gauge,crosslevel,profile,alignment
12.00,56 5/8,1/4,1/2,3/8
12.50,56 5/8,1/4,1/2,3/8
13.10,56 5/8,1/4,1/2,3/8
13.50,56 5/8,1/4,1/2,3/8
"""

WIDE = GOOD.replace("13.10,56 5/8", "13.10,57 7/8")


@pytest.fixture
def book(tmp_path: Path) -> str:
    where = str(tmp_path / "plains.sqlite3")
    run(where, "init")
    run(where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    run(where, "line", "segment", "PLAINS", "014", "12.00-13.00", "--laid", "1998-06-01")
    run(
        where,
        "line",
        "segment",
        "PLAINS",
        "015",
        "13.00-14.00",
        "--laid",
        "1998-06-01",
        "--class",
        "4",
    )
    run(
        where,
        "person",
        "add",
        "RSTIVERS",
        "R Stivers",
        "--craft",
        "inspector",
        "--for",
        "track",
        "--until",
        "2025-12-31",
    )
    return where


def load_it(book: str, path: str) -> Result:
    return run(book, "--on", "2025-05-06", "geometry", "load", "PLAINS", path, "--by", "RSTIVERS")


def a_file(tmp_path: Path, text: str = GOOD) -> str:
    where = tmp_path / "run.csv"
    where.write_text(text, encoding="utf-8")
    return str(where)


def test_a_run_loads_and_lists(book: str, tmp_path: Path) -> None:
    result = run(
        book,
        "--on",
        "2025-05-06",
        "geometry",
        "load",
        "PLAINS",
        a_file(tmp_path),
        "--by",
        "RSTIVERS",
    )
    assert result.exit_code == 0
    assert "IN-2025-0001" in result.output
    listed = run(book, "geometry", "runs", "PLAINS")
    assert "IN-2025-0001" in listed.output
    assert "4" in listed.output


def test_a_book_with_no_runs_says_so(book: str) -> None:
    assert "no runs recorded" in run(book, "geometry", "runs", "PLAINS").output


def test_a_file_that_will_not_parse_exits_two_and_loads_nothing(book: str, tmp_path: Path) -> None:
    bad = a_file(tmp_path, GOOD.replace("12.50,56 5/8", "12.50,wide"))
    result = load_it(book, bad)
    assert result.exit_code == 2
    assert "no runs recorded" in run(book, "geometry", "runs", "PLAINS").output


def test_a_clean_run_prints_no_exceptions(book: str, tmp_path: Path) -> None:
    run(
        book,
        "--on",
        "2025-05-06",
        "geometry",
        "load",
        "PLAINS",
        a_file(tmp_path),
        "--by",
        "RSTIVERS",
    )
    result = run(book, "geometry", "exceptions", "PLAINS", "IN-2025-0001")
    assert result.exit_code == 0
    assert "no exceptions" in result.output
    assert "SG-014" in result.output


def test_a_wide_gauge_shows_up_with_the_class_it_meets(book: str, tmp_path: Path) -> None:
    load_it(book, a_file(tmp_path, WIDE))
    result = run(book, "geometry", "exceptions", "PLAINS", "IN-2025-0001")
    assert "MP 13.10" in result.output
    assert "class 1" in result.output


def test_worst_names_the_segment_left_holding_least(book: str, tmp_path: Path) -> None:
    load_it(book, a_file(tmp_path, WIDE))
    result = run(book, "geometry", "worst", "PLAINS", "IN-2025-0001")
    assert "SG-015" in result.output
    assert "hold at class 1" in result.output


def test_a_run_number_that_is_not_there_exits_three(book: str) -> None:
    result = run(book, "geometry", "exceptions", "PLAINS", "IN-2025-0009")
    assert result.exit_code == 3


def test_a_number_of_the_wrong_kind_exits_two(book: str) -> None:
    result = run(book, "geometry", "exceptions", "PLAINS", "DF-2025-0001")
    assert result.exit_code == 2
    assert "not a inspection one" in result.output or "not an inspection" in result.output


def test_span_says_which_segments_a_stretch_crosses(book: str) -> None:
    result = run(book, "geometry", "span", "PLAINS", "12.50-13.50")
    assert result.exit_code == 0
    assert "SG-014" in result.output
    assert "SG-015" in result.output


def test_a_stretch_with_no_segments_exits_two(book: str) -> None:
    result = run(book, "geometry", "span", "PLAINS", "40.00-41.00")
    assert result.exit_code == 2
    assert "no segment covers" in result.output
