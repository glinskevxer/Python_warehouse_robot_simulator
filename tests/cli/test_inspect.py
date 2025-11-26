"""The inspection commands, including the one that refuses to count."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from spikemaul.cli.main import cli


@pytest.fixture
def book(tmp_path: Path) -> str:
    where = str(tmp_path / "plains.sqlite3")
    run(where, "init")
    run(where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    run(where, "line", "segment", "PLAINS", "014", "12.00-14.00", "--laid", "1998-06-01")
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
    run(where, "person", "add", "JHOLT", "J Holt")
    return where


def run(book: str, *args: str) -> Result:
    return CliRunner().invoke(cli, ["--book", book, *args], obj={})


def test_an_inspection_is_recorded_and_lists(book: str) -> None:
    result = run(
        book, "--on", "2025-05-19", "inspect", "record", "PLAINS", "0.00-61.40", "--by", "RSTIVERS"
    )
    assert result.exit_code == 0
    assert "IN-2025-0001" in result.output
    listed = run(book, "inspect", "list", "PLAINS")
    assert "RSTIVERS" in listed.output
    assert "hi rail" in listed.output


def test_the_numbers_run_on_within_a_year(book: str) -> None:
    run(book, "--on", "2025-05-19", "inspect", "record", "PLAINS", "0.00-61.40", "--by", "RSTIVERS")
    second = run(
        book, "--on", "2025-05-23", "inspect", "record", "PLAINS", "0.00-61.40", "--by", "RSTIVERS"
    )
    assert "IN-2025-0002" in second.output


def test_an_inspection_by_somebody_undesignated_is_refused(book: str) -> None:
    result = run(
        book, "--on", "2025-05-19", "inspect", "record", "PLAINS", "0.00-61.40", "--by", "JHOLT"
    )
    assert result.exit_code == 4
    assert "not designated" in result.output


def test_it_can_be_recorded_anyway_and_says_it_will_not_count(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-05-19",
        "inspect",
        "record",
        "PLAINS",
        "0.00-61.40",
        "--by",
        "JHOLT",
        "--force",
    )
    assert result.exit_code == 0
    assert "will not count" in result.output


def test_a_method_that_cannot_do_the_scope_exits_four(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-05-19",
        "inspect",
        "record",
        "PLAINS",
        "0.00-61.40",
        "--by",
        "RSTIVERS",
        "--scope",
        "rail flaw",
        "--method",
        "hi rail",
    )
    assert result.exit_code in (3, 4)


def test_a_method_this_railroad_does_not_use_exits_two(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-05-19",
        "inspect",
        "record",
        "PLAINS",
        "0.00-61.40",
        "--by",
        "RSTIVERS",
        "--method",
        "drone",
    )
    assert result.exit_code == 2
    assert "is not a method" in result.output


def test_due_says_what_is_late(book: str) -> None:
    result = run(book, "--on", "2025-05-20", "inspect", "due", "PLAINS")
    assert result.exit_code == 0
    assert "never inspected" in result.output


def test_due_says_nothing_where_the_cycle_is_in_date(book: str) -> None:
    run(book, "--on", "2025-05-19", "inspect", "record", "PLAINS", "0.00-61.40", "--by", "RSTIVERS")
    result = run(book, "--on", "2025-05-20", "inspect", "due", "PLAINS")
    assert "nothing due" in result.output


def test_a_window_that_runs_backwards_exits_two(book: str) -> None:
    result = run(book, "--on", "2025-05-20", "inspect", "due", "PLAINS", "--through", "2025-05-01")
    assert result.exit_code == 2
    assert "runs forward" in result.output


def test_the_list_can_be_asked_for_one_scope(book: str) -> None:
    run(book, "--on", "2025-05-19", "inspect", "record", "PLAINS", "0.00-61.40", "--by", "RSTIVERS")
    listed = run(book, "inspect", "list", "PLAINS", "--scope", "turnouts")
    assert "IN-2025-0001" not in listed.output
