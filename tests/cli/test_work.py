"""The work order commands and the week's plan."""

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
    run(where, "line", "segment", "PLAINS", "014", "12.00-16.00", "--laid", "1998-06-01")
    run(where, "person", "add", "DKEHOE", "D Kehoe", "--craft", "foreman")
    run(where, "person", "add", "RSTIVERS", "R Stivers", "--craft", "inspector")
    run(where, "gang", "add", "SEC2", "Section 2", "--foreman", "DKEHOE", "--headcount", "4")
    return where


def an_order(book: str, quantity: int = 400, kind: str = "tie renewal") -> Result:
    return run(
        book,
        "--on",
        "2025-05-06",
        "work",
        "raise",
        "PLAINS",
        "13.00-13.60",
        kind,
        "--quantity",
        str(quantity),
        "--by",
        "DKEHOE",
    )


def test_a_work_order_is_raised_in_the_units_of_its_kind(book: str) -> None:
    result = an_order(book)
    assert result.exit_code == 0
    assert "400 ties" in result.output


def test_a_kind_of_work_this_railroad_does_not_order_exits_two(book: str) -> None:
    result = an_order(book, kind="painting")
    assert result.exit_code == 2
    assert "is not work we order" in result.output


def test_an_order_lists_and_can_be_assigned(book: str) -> None:
    an_order(book)
    assert "SEC2" not in run(book, "work", "list", "PLAINS").output
    run(book, "work", "assign", "WO-2025-0001", "SEC2")
    assert "SEC2" in run(book, "work", "list", "PLAINS").output


def test_assigning_a_second_gang_exits_four(book: str) -> None:
    an_order(book)
    run(book, "work", "assign", "WO-2025-0001", "SEC2")
    again = run(book, "work", "assign", "WO-2025-0001", "SEC2")
    assert again.exit_code == 4
    assert "already on" in again.output


def test_the_unassigned_work_can_be_asked_for(book: str) -> None:
    an_order(book)
    an_order(book)
    run(book, "work", "assign", "WO-2025-0001", "SEC2")
    listed = run(book, "work", "list", "PLAINS", "--unassigned")
    assert "WO-2025-0002" in listed.output
    assert "WO-2025-0001" not in listed.output


def test_finishing_short_says_how_short(book: str) -> None:
    an_order(book)
    result = run(book, "--on", "2025-06-01", "work", "finish", "WO-2025-0001", "--quantity", "250")
    assert result.exit_code == 0
    assert "150 ties short" in result.output
    assert "WO-2025-0001" not in run(book, "work", "list", "PLAINS").output


def test_finishing_an_order_twice_exits_four(book: str) -> None:
    an_order(book)
    run(book, "--on", "2025-06-01", "work", "finish", "WO-2025-0001")
    again = run(book, "--on", "2025-06-02", "work", "finish", "WO-2025-0001")
    assert again.exit_code == 4


def test_the_needs_come_off_the_open_cards(book: str) -> None:
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
    result = run(book, "work", "needs", "PLAINS")
    assert result.exit_code == 0
    assert "gauge repair" in result.output
    assert "gang days" in result.output


def test_a_book_with_no_cards_needs_nothing(book: str) -> None:
    assert "nothing needed" in run(book, "work", "needs", "PLAINS").output


def test_the_plan_fills_the_week_and_says_what_did_not_fit(book: str) -> None:
    an_order(book, quantity=1000)
    run(book, "work", "assign", "WO-2025-0001", "SEC2")
    result = run(book, "--on", "2025-06-02", "work", "plan", "PLAINS", "SEC2", "--days", "2")
    assert result.exit_code == 0
    assert "SEC2 plan" in result.output
    assert "not planned" in result.output


def test_a_gang_that_is_not_there_exits_three(book: str) -> None:
    assert run(book, "work", "plan", "PLAINS", "SEC9").exit_code == 3


def test_the_material_sheet_comes_off_the_open_work(book: str) -> None:
    an_order(book)
    result = run(book, "work", "material", "PLAINS")
    assert result.exit_code == 0
    assert "400 each crossties" in result.output
    assert "1600 each spikes" in result.output


def test_the_material_sheet_can_be_asked_for_one_gang(book: str) -> None:
    an_order(book)
    run(book, "work", "assign", "WO-2025-0001", "SEC2")
    result = run(book, "work", "material", "PLAINS", "--gang", "SEC2")
    assert "crossties" in result.output


def test_a_book_with_no_open_work_orders_nothing(book: str) -> None:
    assert "nothing to order" in run(book, "work", "material", "PLAINS").output


def test_an_open_work_order_can_be_put_right(book: str) -> None:
    an_order(book)
    result = run(book, "work", "amend", "WO-2025-0001", "--quantity", "500", "--due", "2025-07-01")
    assert result.exit_code == 0
    assert "500 ties" in result.output
    assert "2025-07-01" in run(book, "work", "list", "PLAINS").output


def test_a_finished_work_order_cannot_be_amended(book: str) -> None:
    an_order(book)
    run(book, "--on", "2025-06-01", "work", "finish", "WO-2025-0001")
    result = run(book, "work", "amend", "WO-2025-0001", "--quantity", "500")
    assert result.exit_code == 4
    assert "stands as it is" in result.output
