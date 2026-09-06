"""The report and tonnage commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.console import a_book, run, with_a_gang, with_a_segment, with_a_subdivision


@pytest.fixture
def book(tmp_path: Path) -> str:
    where = str(tmp_path / "plains.sqlite3")
    run(where, "init")
    run(where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    run(where, "line", "segment", "PLAINS", "014", "12.00-16.00", "--laid", "1998-06-01")
    run(where, "person", "add", "RSTIVERS", "R Stivers", "--craft", "inspector")
    return where


def test_the_morning_page_prints_every_section(book: str) -> None:
    result = run(book, "--on", "2025-05-20", "report", "morning", "PLAINS")
    assert result.exit_code == 0
    assert "Plains morning page 2025-05-20" in result.output
    assert "nothing out of service" in result.output
    assert "no restrictions in force" in result.output


def test_the_morning_page_shows_an_order_that_is_on(book: str) -> None:
    run(
        book,
        "--on",
        "2025-05-06",
        "order",
        "issue",
        "PLAINS",
        "13.00-13.60",
        "10",
        "--authority",
        "DKEHOE",
    )
    result = run(book, "--on", "2025-05-20", "report", "morning", "PLAINS")
    assert "SO-2025-0001" in result.output
    assert "1 order in force" in result.output


def test_the_compliance_page_counts_the_cycles(book: str) -> None:
    result = run(book, "--on", "2025-05-20", "report", "compliance", "PLAINS")
    assert result.exit_code == 0
    assert "inspection compliance" in result.output
    assert "1 cycle watched" in result.output


def test_a_subdivision_that_is_not_there_exits_three(book: str) -> None:
    assert run(book, "report", "morning", "RIVER").exit_code == 3


def test_a_month_is_posted_and_lists(book: str) -> None:
    result = run(book, "tonnage", "post", "PLAINS", "2025-01", "1.20")
    assert result.exit_code == 0
    assert "1.20 MGT" in result.output
    listed = run(book, "tonnage", "list", "PLAINS")
    assert "2025-01" in listed.output
    assert "over 1 months" in listed.output


def test_posting_the_same_month_twice_exits_four(book: str) -> None:
    run(book, "tonnage", "post", "PLAINS", "2025-01", "1.20")
    again = run(book, "tonnage", "post", "PLAINS", "2025-01", "1.30")
    assert again.exit_code == 4


def test_a_month_can_be_corrected(book: str) -> None:
    run(book, "tonnage", "post", "PLAINS", "2025-01", "1.20")
    fixed = run(book, "tonnage", "post", "PLAINS", "2025-01", "1.35", "--correct")
    assert fixed.exit_code == 0
    assert "1.35" in run(book, "tonnage", "list", "PLAINS").output


def test_correcting_a_month_nobody_posted_exits_three(book: str) -> None:
    result = run(book, "tonnage", "post", "PLAINS", "2025-01", "1.20", "--correct")
    assert result.exit_code == 3


def test_a_month_that_is_not_a_month_is_a_usage_error(book: str) -> None:
    result = run(book, "tonnage", "post", "PLAINS", "january", "1.20")
    assert result.exit_code == 2
    assert "written as 2025-01" in result.output


def test_a_book_with_no_tonnage_says_so(book: str) -> None:
    assert "no tonnage posted" in run(book, "tonnage", "list", "PLAINS").output


def test_the_months_add_up_in_the_listing(book: str) -> None:
    run(book, "tonnage", "post", "PLAINS", "2025-01", "1.20")
    run(book, "tonnage", "post", "PLAINS", "2025-02", "1.10")
    listed = run(book, "tonnage", "list", "PLAINS")
    assert "2.30 MGT over 2 months" in listed.output


def test_the_milepost_page_answers_the_telephone_question(book: str) -> None:
    result = run(book, "--on", "2025-05-20", "report", "at", "PLAINS", "13.20")
    assert result.exit_code == 0
    assert "Plains MP 13.20 on 2025-05-20" in result.output
    assert "SG-014" in result.output
    assert "timetable speed 40 mph" in result.output
    assert "no open cards here" in result.output


def test_the_milepost_page_says_where_no_segment_covers_it(book: str) -> None:
    result = run(book, "--on", "2025-05-20", "report", "at", "PLAINS", "40.00")
    assert result.exit_code == 0
    assert "no segment covers this milepost" in result.output
    assert "nothing on record sets a speed here" in result.output


def test_a_milepost_that_will_not_parse_exits_two(book: str) -> None:
    result = run(book, "report", "at", "PLAINS", "13.9x")
    assert result.exit_code == 2
    assert "is not a milepost" in result.output


def test_the_rail_page_counts_what_has_been_measured(book: str) -> None:
    result = run(book, "--on", "2025-09-01", "report", "rail", "PLAINS")
    assert result.exit_code == 0
    assert "0 rails measured" in result.output
    assert "no rail has been measured" in result.output
    assert "never" in result.output


def test_the_audit_page_names_the_track_no_segment_covers(book: str) -> None:
    result = run(book, "--on", "2025-05-20", "report", "audit", "PLAINS")
    assert result.exit_code == 0
    assert "records audit" in result.output
    assert "no segment covers it" in result.output
    assert "sqlite is happy with the file" in result.output


def test_the_audit_page_is_quiet_on_a_subdivision_covered_end_to_end(
    tmp_path: Path,
) -> None:
    where = a_book(tmp_path, "covered.sqlite3")
    with_a_subdivision(where)
    with_a_segment(where, span="0.00-120.00")
    result = run(where, "--on", "2025-05-20", "report", "audit", "PLAINS")
    assert "0 holes in the book" in result.output
    assert "the book covers the whole subdivision" in result.output


def test_the_week_sheet_prints_the_days_and_the_material(book: str) -> None:
    with_a_gang(book)
    run(
        book,
        "--on",
        "2025-05-06",
        "work",
        "raise",
        "PLAINS",
        "13.00-13.60",
        "tie renewal",
        "--quantity",
        "240",
        "--by",
        "DKEHOE",
        "--gang",
        "SEC2",
    )
    result = run(book, "--on", "2025-06-02", "report", "week", "PLAINS", "SEC2", "--days", "3")
    assert result.exit_code == 0
    assert "Section 2 week of 2025-06-02" in result.output
    assert "crossties" in result.output
    assert "tie plates" in result.output


def test_the_week_sheet_says_what_did_not_fit(book: str) -> None:
    with_a_gang(book)
    run(
        book,
        "--on",
        "2025-05-06",
        "work",
        "raise",
        "PLAINS",
        "13.00-13.60",
        "tie renewal",
        "--quantity",
        "2000",
        "--by",
        "DKEHOE",
        "--gang",
        "SEC2",
    )
    result = run(book, "--on", "2025-06-02", "report", "week", "PLAINS", "SEC2", "--days", "2")
    assert "did not fit" in result.output
    assert "gang days to clear it" in result.output


def test_a_week_for_a_gang_that_is_not_there_exits_three(book: str) -> None:
    assert run(book, "report", "week", "PLAINS", "SEC9").exit_code == 3
