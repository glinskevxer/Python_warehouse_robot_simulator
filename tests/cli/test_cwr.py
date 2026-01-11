"""The welded rail commands."""

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
    run(where, "person", "add", "DKEHOE", "D Kehoe", "--craft", "foreman")
    return where


def a_destress(book: str, neutral: str = "95", on: str = "2025-04-20") -> Result:
    return run(
        book,
        "--on",
        on,
        "cwr",
        "destress",
        "PLAINS",
        "13.00-14.00",
        "--neutral",
        neutral,
        "--by",
        "DKEHOE",
    )


def test_a_destress_entry_goes_in_the_log(book: str) -> None:
    result = a_destress(book)
    assert result.exit_code == 0
    assert "heater to 95F" in result.output
    listed = run(book, "cwr", "log", "PLAINS").output
    assert "13.00" in listed
    assert "2025-04-20" in listed


def test_an_entry_out_of_specification_is_marked(book: str) -> None:
    a_destress(book, neutral="78")
    assert "out of specification" in run(book, "cwr", "log", "PLAINS").output


def test_an_empty_log_says_so(book: str) -> None:
    assert "nothing in the destress log" in run(book, "cwr", "log", "PLAINS").output


def test_a_stretch_with_no_entry_has_an_unknown_neutral_temperature(book: str) -> None:
    result = run(book, "--on", "2025-07-15", "cwr", "neutral", "PLAINS", "13.20-13.40")
    assert "unknown" in result.output


def test_a_stretch_with_an_entry_says_what_it_stands_at(book: str) -> None:
    a_destress(book)
    result = run(book, "--on", "2025-07-15", "cwr", "neutral", "PLAINS", "13.20-13.40")
    assert "stands at 95F" in result.output
    assert "86 days ago" in result.output


def test_a_cool_morning_calls_for_no_restriction(book: str) -> None:
    a_destress(book)
    result = run(
        book,
        "--on",
        "2025-07-15",
        "cwr",
        "heat",
        "PLAINS",
        "13.20-13.40",
        "--air",
        "80",
        "--sky",
        "overcast",
    )
    assert "no restriction" in result.output


def test_a_hot_afternoon_calls_for_a_cap(book: str) -> None:
    a_destress(book)
    result = run(
        book,
        "--on",
        "2025-07-15",
        "cwr",
        "heat",
        "PLAINS",
        "13.20-13.40",
        "--air",
        "100",
        "--sky",
        "clear",
    )
    assert "40 mph" in result.output


def test_a_curve_comes_in_one_band(book: str) -> None:
    a_destress(book)
    result = run(
        book,
        "--on",
        "2025-07-15",
        "cwr",
        "heat",
        "PLAINS",
        "13.20-13.40",
        "--air",
        "100",
        "--degrees",
        "3",
    )
    assert "25 mph" in result.output


def test_a_stretch_with_no_neutral_temperature_gets_the_worst_band(book: str) -> None:
    result = run(
        book,
        "--on",
        "2025-07-15",
        "cwr",
        "heat",
        "PLAINS",
        "20.00-21.00",
        "--air",
        "80",
        "--sky",
        "overcast",
    )
    assert "10 mph" in result.output
    assert "no neutral temperature on record" in result.output


def test_the_call_can_put_the_order_on(book: str) -> None:
    a_destress(book)
    result = run(
        book,
        "--on",
        "2025-07-15",
        "cwr",
        "heat",
        "PLAINS",
        "13.20-13.40",
        "--air",
        "100",
        "--issue",
        "--authority",
        "DKEHOE",
    )
    assert "issued SO-2025-0001" in result.output
    printed = run(book, "--on", "2025-07-15", "order", "bulletin", "PLAINS")
    assert "lapses" in printed.output


def test_issuing_without_an_authority_is_a_usage_error(book: str) -> None:
    a_destress(book)
    result = run(
        book,
        "--on",
        "2025-07-15",
        "cwr",
        "heat",
        "PLAINS",
        "13.20-13.40",
        "--air",
        "100",
        "--issue",
    )
    assert result.exit_code == 2
    assert "needs an authority" in result.output
