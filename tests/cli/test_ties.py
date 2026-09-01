"""The tie survey commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import Result

from tests.support.console import run

SHEET = """milepost,total,good,run,joints,supported,degrees
13.10,22,16,2,1,1,0
13.11,22,9,2,1,1,0
13.12,22,10,2,1,0,0
"""


@pytest.fixture
def book(tmp_path: Path) -> str:
    where = str(tmp_path / "plains.sqlite3")
    run(where, "init")
    run(where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    run(where, "person", "add", "RSTIVERS", "R Stivers", "--craft", "inspector")
    return where


def a_sheet(tmp_path: Path, text: str = SHEET) -> str:
    where = tmp_path / "ties.csv"
    where.write_text(text, encoding="utf-8")
    return str(where)


def load_it(book: str, path: str) -> Result:
    return run(
        book,
        "--on",
        "2025-08-04",
        "ties",
        "load",
        "PLAINS",
        "13.00-14.00",
        path,
        "--by",
        "RSTIVERS",
    )


def test_a_sheet_loads_and_says_what_the_stretch_holds(book: str, tmp_path: Path) -> None:
    result = load_it(book, a_sheet(tmp_path))
    assert result.exit_code == 0
    assert "3 lengths" in result.output
    assert "holds excepted" in result.output


def test_a_sheet_with_a_bad_line_loads_nothing(book: str, tmp_path: Path) -> None:
    bad = a_sheet(tmp_path, SHEET.replace("13.11,22,9", "13.11,22,many"))
    result = load_it(book, bad)
    assert result.exit_code == 2
    assert "line 3" in result.output


def test_a_column_the_form_does_not_have_is_refused(book: str, tmp_path: Path) -> None:
    bad = a_sheet(tmp_path, SHEET.replace("degrees", "temperature"))
    result = load_it(book, bad)
    assert result.exit_code == 2
    assert "does not know: temperature" in result.output


def test_the_survey_prints_length_by_length_with_the_governing_rule(
    book: str, tmp_path: Path
) -> None:
    load_it(book, a_sheet(tmp_path))
    result = run(book, "ties", "show", "IN-2025-0001")
    assert result.exit_code == 0
    assert "13.10" in result.output
    assert "joints" in result.output
    assert "count" in result.output


def test_the_survey_can_be_judged_against_a_class(book: str, tmp_path: Path) -> None:
    load_it(book, a_sheet(tmp_path))
    result = run(book, "ties", "show", "IN-2025-0001", "--class", "4")
    assert "lengths below class 4" in result.output
    assert "ties to hold class 4" in result.output


def test_the_needs_come_back_as_one_per_run_of_bad_lengths(book: str, tmp_path: Path) -> None:
    load_it(book, a_sheet(tmp_path))
    result = run(book, "ties", "needs", "IN-2025-0001", "--class", "4")
    assert result.exit_code == 0
    assert "tie renewal" in result.output
    assert "ties" in result.output


def test_a_survey_that_holds_the_class_needs_nothing(book: str, tmp_path: Path) -> None:
    good = a_sheet(tmp_path, "milepost,total,good,run\n13.10,22,16,2\n13.11,22,16,2\n")
    load_it(book, good)
    result = run(book, "ties", "needs", "IN-2025-0001", "--class", "4")
    assert "nothing needed" in result.output


def test_a_survey_that_is_not_there_exits_three(book: str) -> None:
    assert run(book, "ties", "show", "IN-2025-0009").exit_code == 3


def test_the_optional_columns_can_be_left_off(book: str, tmp_path: Path) -> None:
    short = a_sheet(tmp_path, "milepost,total,good,run\n13.10,22,16,2\n13.11,22,16,2\n")
    assert load_it(book, short).exit_code == 0
