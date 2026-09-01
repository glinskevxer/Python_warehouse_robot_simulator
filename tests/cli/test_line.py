"""The line commands, through the console script."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.console import a_book, run, with_a_segment, with_a_subdivision


@pytest.fixture
def book(tmp_path: Path) -> str:
    return a_book(tmp_path)


def test_a_subdivision_goes_in_and_lists(book: str) -> None:
    with_a_subdivision(book)
    listed = run(book, "line", "list")
    assert listed.exit_code == 0
    assert "PLAINS" in listed.output
    assert "120.00" in listed.output


def test_the_same_subdivision_twice_exits_four(book: str) -> None:
    with_a_subdivision(book)
    again = run(book, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    assert again.exit_code == 4
    assert "already in the book" in again.output


def test_an_equation_goes_on_a_subdivision(book: str) -> None:
    with_a_subdivision(book)
    result = run(book, "line", "equate", "PLAINS", "61.40", "61.15")
    assert result.exit_code == 0
    assert "MP 61.40 = MP 61.15" in result.output
    assert "1" in run(book, "line", "list").output


def test_an_equation_on_a_subdivision_that_is_not_there_exits_three(book: str) -> None:
    result = run(book, "line", "equate", "PLAINS", "61.40", "61.15")
    assert result.exit_code == 3


def test_a_segment_goes_in_and_lists(book: str) -> None:
    with_a_subdivision(book)
    added = run(
        book,
        "line",
        "segment",
        "PLAINS",
        "014",
        "12.00-14.50",
        "--laid",
        "1998-06-01",
        "--class",
        "3",
    )
    assert added.exit_code == 0
    listed = run(book, "line", "segments", "PLAINS")
    assert "SG-014" in listed.output
    assert "class 3" in listed.output
    assert "40" in listed.output


def test_a_segment_lying_on_another_exits_four(book: str) -> None:
    with_a_subdivision(book)
    run(book, "line", "segment", "PLAINS", "014", "12.00-14.50", "--laid", "1998-06-01")
    clash = run(book, "line", "segment", "PLAINS", "015", "14.00-16.00", "--laid", "1998-06-01")
    assert clash.exit_code == 4
    assert "lies on top of" in clash.output


def test_a_class_that_is_not_a_class_exits_two(book: str) -> None:
    with_a_subdivision(book)
    result = run(
        book,
        "line",
        "segment",
        "PLAINS",
        "014",
        "12.00-14.50",
        "--laid",
        "1998-06-01",
        "--class",
        "9",
    )
    assert result.exit_code == 2
    assert "not a class of track" in result.output


def test_where_says_the_segment_and_whether_there_is_a_curve(book: str) -> None:
    with_a_subdivision(book)
    run(book, "line", "segment", "PLAINS", "014", "12.00-14.50", "--laid", "1998-06-01")
    result = run(book, "line", "where", "PLAINS", "13.20")
    assert result.exit_code == 0
    assert "SG-014" in result.output
    assert "no curve here" in result.output


def test_where_on_track_with_no_segment_exits_three(book: str) -> None:
    with_a_subdivision(book)
    result = run(book, "line", "where", "PLAINS", "40.00")
    assert result.exit_code == 3
    assert "no segment at" in result.output


def test_a_welded_segment_says_cwr_in_the_listing(book: str) -> None:
    with_a_subdivision(book)
    run(
        book,
        "line",
        "segment",
        "PLAINS",
        "014",
        "12.00-14.50",
        "--laid",
        "1998-06-01",
        "--welded",
    )
    assert "cwr" in run(book, "line", "segments", "PLAINS").output


def test_a_segment_can_be_held_to_a_lower_class(book: str) -> None:
    with_a_subdivision(book)
    with_a_segment(book, span="12.00-14.00")
    result = run(book, "line", "reclass", "PLAINS", "014", "1")
    assert result.exit_code == 0
    assert "goes down from 40 mph to 10 mph" in result.output
    assert "class 1" in run(book, "line", "segments", "PLAINS").output


def test_raising_a_segment_past_its_open_cards_exits_four(book: str) -> None:
    with_a_subdivision(book)
    with_a_segment(book, span="12.00-14.00")
    run(book, "person", "add", "RSTIVERS", "R Stivers", "--craft", "inspector")
    run(
        book,
        "--on",
        "2025-05-06",
        "defect",
        "raise",
        "PLAINS",
        "13.22",
        "gauge",
        "--reading",
        "57 7/8",
        "--meets",
        "1",
        "--by",
        "RSTIVERS",
    )
    result = run(book, "line", "reclass", "PLAINS", "014", "4")
    assert result.exit_code == 4
    assert "cannot be raised" in result.output
    assert "DF-2025-0001" in result.output


def test_raising_a_segment_with_nothing_in_the_way_is_allowed(book: str) -> None:
    with_a_subdivision(book)
    with_a_segment(book, span="12.00-14.00")
    result = run(book, "line", "reclass", "PLAINS", "014", "4")
    assert result.exit_code == 0
    assert "goes up" in result.output
