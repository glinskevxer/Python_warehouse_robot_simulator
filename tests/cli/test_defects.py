"""The defect commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import Result

from tests.support.console import run


@pytest.fixture
def book(tmp_path: Path) -> str:
    where = str(tmp_path / "plains.sqlite3")
    run(where, "init")
    run(where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    run(where, "line", "segment", "PLAINS", "014", "12.00-14.00", "--laid", "1998-06-01")
    run(where, "person", "add", "RSTIVERS", "R Stivers", "--craft", "inspector")
    return where


def a_card(book: str, post: str = "13.22", meets: str = "1") -> Result:
    return run(
        book,
        "--on",
        "2025-05-06",
        "defect",
        "raise",
        "PLAINS",
        post,
        "gauge",
        "--reading",
        "57 7/8",
        "--meets",
        meets,
        "--by",
        "RSTIVERS",
    )


def test_a_card_is_raised_and_says_what_the_rule_requires(book: str) -> None:
    result = a_card(book)
    assert result.exit_code == 0
    assert "DF-2025-0001" in result.output
    assert "hold at class 1" in result.output


def test_the_card_numbers_run_on_within_a_year(book: str) -> None:
    a_card(book)
    assert "DF-2025-0002" in a_card(book, post="13.40").output


def test_a_card_that_meets_nothing_takes_the_track_out(book: str) -> None:
    result = a_card(book, meets="none")
    assert "out of service" in result.output
    assert "DF-2025-0001" in run(book, "defect", "out", "PLAINS").output


def test_a_condition_this_package_does_not_record_exits_two(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-05-06",
        "defect",
        "raise",
        "PLAINS",
        "13.22",
        "bent",
        "--reading",
        "x",
        "--by",
        "RSTIVERS",
    )
    assert result.exit_code == 2
    assert "is not a condition" in result.output


def test_a_card_off_the_end_of_every_segment_says_so(book: str) -> None:
    result = a_card(book, post="40.00")
    assert result.exit_code == 0
    assert "no segment covers" in result.output
    assert "no segment" in run(book, "defect", "list", "PLAINS").output


def test_the_open_cards_list_and_the_repaired_ones_do_not(book: str) -> None:
    a_card(book)
    run(book, "--on", "2025-05-20", "defect", "repair", "DF-2025-0001")
    assert "DF-2025-0001" not in run(book, "defect", "list", "PLAINS").output
    assert "repaired 2025-05-20" in run(book, "defect", "list", "PLAINS", "--all").output


def test_repairing_a_card_twice_exits_four(book: str) -> None:
    a_card(book)
    run(book, "--on", "2025-05-20", "defect", "repair", "DF-2025-0001")
    again = run(book, "--on", "2025-05-21", "defect", "repair", "DF-2025-0001")
    assert again.exit_code == 4
    assert "already repaired" in again.output


def test_an_overdue_card_is_marked_in_the_list(book: str) -> None:
    a_card(book)
    listed = run(book, "--on", "2025-07-01", "defect", "list", "PLAINS")
    assert "overdue" in listed.output


def test_the_list_can_start_from_a_day(book: str) -> None:
    a_card(book)
    listed = run(book, "defect", "list", "PLAINS", "--since", "2025-06-01")
    assert "DF-2025-0001" not in listed.output


def test_action_says_the_remedy_and_the_date(book: str) -> None:
    a_card(book)
    result = run(book, "defect", "action", "DF-2025-0001")
    assert result.exit_code == 0
    assert "held at class 3" in result.output
    assert "due 2025-06-05" in result.output


def test_a_card_that_is_not_there_exits_three(book: str) -> None:
    assert run(book, "defect", "action", "DF-2025-0009").exit_code == 3


def test_a_quiet_subdivision_says_nothing_is_out_of_service(book: str) -> None:
    assert "nothing out of service" in run(book, "defect", "out", "PLAINS").output


def test_the_conditions_are_listed_with_how_they_are_found(book: str) -> None:
    result = run(book, "defect", "conditions")
    assert "gauge" in result.output
    assert "geometry" in result.output
    assert "walking" in result.output


def test_an_open_card_can_be_put_right_from_the_command_line(book: str) -> None:
    a_card(book)
    result = run(book, "defect", "amend", "DF-2025-0001", "--reading", "57 3/4", "--meets", "3")
    assert result.exit_code == 0
    assert "57 3/4" in result.output
    assert "meets class 3" in result.output


def test_a_repaired_card_cannot_be_amended(book: str) -> None:
    a_card(book)
    run(book, "--on", "2025-05-20", "defect", "repair", "DF-2025-0001")
    result = run(book, "defect", "amend", "DF-2025-0001", "--reading", "57 3/4")
    assert result.exit_code == 4
    assert "stands as it is" in result.output
