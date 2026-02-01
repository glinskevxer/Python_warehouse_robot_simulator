"""The slow order commands, the bulletin and the cost."""

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
    return where


def an_order(book: str, span: str = "13.00-13.60", speed: str = "10") -> Result:
    return run(
        book,
        "--on",
        "2025-05-06",
        "order",
        "issue",
        "PLAINS",
        span,
        speed,
        "--authority",
        "DKEHOE",
    )


def test_an_order_goes_on_and_shows_on_the_bulletin(book: str) -> None:
    assert an_order(book).exit_code == 0
    printed = run(book, "--on", "2025-05-10", "order", "bulletin", "PLAINS")
    assert "SO-2025-0001" in printed.output
    assert "10 mph" in printed.output


def test_a_bulletin_with_nothing_on_it_says_so(book: str) -> None:
    printed = run(book, "--on", "2025-05-10", "order", "bulletin", "PLAINS")
    assert "no restrictions in force" in printed.output


def test_an_order_that_has_been_lifted_is_off_the_bulletin(book: str) -> None:
    an_order(book)
    run(book, "--on", "2025-05-08", "order", "lift", "SO-2025-0001")
    printed = run(book, "--on", "2025-05-10", "order", "bulletin", "PLAINS")
    assert "no restrictions in force" in printed.output


def test_a_heat_order_needs_the_day_it_lapses(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-07-15",
        "order",
        "issue",
        "PLAINS",
        "13.00-13.60",
        "25",
        "--reason",
        "heat",
        "--authority",
        "DKEHOE",
    )
    assert result.exit_code == 4
    assert "carries the day it lapses" in result.output


def test_a_speed_that_is_not_a_speed_exits_two(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-05-06",
        "order",
        "issue",
        "PLAINS",
        "13.00-13.60",
        "fast",
        "--authority",
        "DKEHOE",
    )
    assert result.exit_code == 2


def test_the_changes_between_two_days_are_listed(book: str) -> None:
    an_order(book)
    run(book, "--on", "2025-05-08", "order", "lift", "SO-2025-0001")
    result = run(book, "--on", "2025-05-10", "order", "changes", "PLAINS", "2025-05-07")
    assert "off" in result.output
    assert "SO-2025-0001" in result.output


def test_a_day_with_no_change_says_so(book: str) -> None:
    result = run(book, "--on", "2025-05-10", "order", "changes", "PLAINS", "2025-05-07")
    assert "no change" in result.output


def test_the_profile_shows_the_class_and_then_the_order(book: str) -> None:
    an_order(book)
    result = run(book, "--on", "2025-05-10", "order", "profile", "PLAINS", "12.00-16.00")
    assert result.exit_code == 0
    assert "class" in result.output
    assert "slow order" in result.output
    assert "40" in result.output
    assert "10" in result.output


def test_the_profile_names_track_with_no_records_on_it(book: str) -> None:
    result = run(book, "--on", "2025-05-10", "order", "profile", "PLAINS", "12.00-20.00")
    assert "no record covers" in result.output


def test_the_cost_ranks_the_restrictions(book: str) -> None:
    an_order(book)
    an_order(book, span="14.00-14.20", speed="25")
    result = run(
        book, "--on", "2025-05-10", "order", "cost", "PLAINS", "12.00-16.00", "--timetable", "40"
    )
    assert result.exit_code == 0
    assert "minutes lost" in result.output
    assert result.output.index("13.00") < result.output.index("14.00")


def test_a_stretch_with_nothing_on_it_costs_nothing(book: str) -> None:
    result = run(
        book, "--on", "2025-05-10", "order", "cost", "PLAINS", "12.00-16.00", "--timetable", "40"
    )
    assert "0.0 minutes lost" in result.output
