"""The rail wear and flaw testing commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from spikemaul.cli.main import cli


def run(book: str, *args: str) -> Result:
    return CliRunner().invoke(cli, ["--book", book, *args], obj={})


@pytest.fixture
def book(tmp_path: Path) -> str:
    where = str(tmp_path / "plains.sqlite3")
    run(where, "init")
    run(where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    run(where, "line", "segment", "PLAINS", "014", "12.00-16.00", "--laid", "1998-06-01")
    run(where, "person", "add", "RSTIVERS", "R Stivers", "--craft", "inspector")
    return where


def a_reading(book: str, on: str, vertical: str = "1/4", post: str = "13.20") -> Result:
    return run(
        book,
        "--on",
        on,
        "rail",
        "measure",
        "PLAINS",
        post,
        "--vertical",
        vertical,
        "--gauge-face",
        "1/4",
    )


def test_a_reading_is_recorded_and_says_what_it_holds(book: str) -> None:
    result = a_reading(book, "2025-04-01")
    assert result.exit_code == 0
    assert "holds class 5" in result.output


def test_a_rail_past_every_row_says_it_holds_nothing(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-04-01",
        "rail",
        "measure",
        "PLAINS",
        "13.20",
        "--vertical",
        "1",
        "--gauge-face",
        "1",
    )
    assert "holds no class of track" in result.output


def test_the_same_rail_measured_twice_on_a_day_exits_four(book: str) -> None:
    a_reading(book, "2025-04-01")
    again = a_reading(book, "2025-04-01")
    assert again.exit_code == 4


def test_the_latest_reading_of_each_rail_lists(book: str) -> None:
    a_reading(book, "2025-04-01")
    a_reading(book, "2026-04-01", vertical="3/8")
    listed = run(book, "--on", "2026-06-01", "rail", "wear", "PLAINS", "12.00-16.00")
    assert "3/8" in listed.output
    assert listed.output.count("13.20") == 1


def test_a_projection_needs_two_readings(book: str) -> None:
    a_reading(book, "2025-04-01")
    result = run(book, "rail", "project", "PLAINS", "13.20", "--tonnage", "12", "--class", "4")
    assert result.exit_code == 2
    assert "fewer than two readings" in result.output


def test_a_projection_says_the_rate_and_what_is_left(book: str) -> None:
    a_reading(book, "2025-04-01")
    a_reading(book, "2026-04-01", vertical="3/8")
    result = run(book, "rail", "project", "PLAINS", "13.20", "--tonnage", "12", "--class", "4")
    assert result.exit_code == 0
    assert "sixteenths per MGT" in result.output
    assert "before it fails class 4" in result.output


def test_rail_that_is_not_wearing_has_no_date_to_plan_against(book: str) -> None:
    a_reading(book, "2025-04-01")
    a_reading(book, "2026-04-01")
    result = run(book, "rail", "project", "PLAINS", "13.20", "--tonnage", "12", "--class", "4")
    assert "no date to plan against" in result.output


def test_a_segment_nobody_has_tested_is_due(book: str) -> None:
    result = run(book, "--on", "2025-09-01", "rail", "cycle", "PLAINS")
    assert result.exit_code == 0
    assert "never" in result.output
    assert "due" in result.output


def test_a_detector_run_is_recorded_and_takes_the_segment_out_of_due(book: str) -> None:
    run(
        book,
        "--on",
        "2025-09-02",
        "inspect",
        "record",
        "PLAINS",
        "12.00-16.00",
        "--by",
        "RSTIVERS",
        "--scope",
        "rail flaw",
        "--method",
        "flaw detector",
        "--force",
    )
    recorded = run(
        book,
        "--on",
        "2025-09-02",
        "rail",
        "tested",
        "PLAINS",
        "12.00-16.00",
        "--inspection",
        "IN-2025-0001",
        "--tonnage",
        "124.50",
        "--found",
        "3",
    )
    assert recorded.exit_code == 0
    assert "3 found" in recorded.output
    listed = run(book, "--on", "2025-10-01", "rail", "cycle", "PLAINS")
    assert "in cycle" in listed.output


def test_a_detector_run_on_an_inspection_that_is_not_there_exits_three(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-09-02",
        "rail",
        "tested",
        "PLAINS",
        "12.00-16.00",
        "--inspection",
        "IN-2025-0009",
        "--tonnage",
        "124.50",
    )
    assert result.exit_code == 3
