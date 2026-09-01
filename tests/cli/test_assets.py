"""The curve, turnout, crossing and bridge commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from spikemaul.model.structure import check_letter
from tests.support.console import a_book, run, with_a_subdivision


@pytest.fixture
def book(tmp_path: Path) -> str:
    return with_a_subdivision(a_book(tmp_path))


def test_a_curve_goes_in_and_lists_with_its_speed(book: str) -> None:
    added = run(
        book,
        "curve",
        "add",
        "PLAINS",
        "118",
        "13.10-13.40",
        "--degrees",
        "3",
        "--elevation",
        "2",
        "--spiral",
        "200",
    )
    assert added.exit_code == 0
    listed = run(book, "curve", "list", "PLAINS")
    assert "CV-118" in listed.output
    assert "3 deg 00 min" in listed.output
    assert "48" in listed.output


def test_a_curve_of_no_degrees_exits_two(book: str) -> None:
    result = run(book, "curve", "add", "PLAINS", "118", "13.10-13.40", "--degrees", "0")
    assert result.exit_code == 2
    assert "tangent track" in result.output


def test_a_turnout_goes_in_and_lists_with_its_diverging_speed(book: str) -> None:
    added = run(
        book,
        "turnout",
        "add",
        "PLAINS",
        "31",
        "18.60",
        "--size",
        "10",
        "--leads-to",
        "Bartels elevator",
    )
    assert added.exit_code == 0
    listed = run(book, "turnout", "list", "PLAINS")
    assert "TO-31" in listed.output
    assert "20" in listed.output
    assert "Bartels elevator" in listed.output


def test_a_turnout_size_this_railroad_does_not_stock_exits_two(book: str) -> None:
    result = run(book, "turnout", "add", "PLAINS", "31", "18.60", "--size", "12")
    assert result.exit_code == 2
    assert "not a turnout size here" in result.output


def test_a_crossing_goes_in_with_a_checked_inventory_number(book: str) -> None:
    number = f"244160{check_letter(244160)}"
    added = run(
        book,
        "crossing",
        "add",
        "PLAINS",
        "244",
        "22.10",
        "County Road 14",
        "--inventory",
        number,
        "--surface",
        "rubber",
        "--warning",
        "flashers",
    )
    assert added.exit_code == 0


def test_a_crossing_whose_inventory_number_does_not_check_exits_two(book: str) -> None:
    result = run(
        book,
        "crossing",
        "add",
        "PLAINS",
        "244",
        "22.10",
        "County Road 14",
        "--inventory",
        "244160Z",
    )
    assert result.exit_code == 2
    assert "does not check" in result.output


def test_a_public_timber_crossing_with_crossbucks_exits_four(book: str) -> None:
    number = f"244160{check_letter(244160)}"
    result = run(
        book,
        "crossing",
        "add",
        "PLAINS",
        "244",
        "22.10",
        "County Road 14",
        "--inventory",
        number,
        "--surface",
        "timber",
        "--warning",
        "crossbucks",
    )
    assert result.exit_code == 4
    assert "no active warning" in result.output


def test_a_bridge_goes_in_and_the_weakest_is_marked(book: str) -> None:
    run(
        book,
        "bridge",
        "add",
        "PLAINS",
        "77",
        "34.80",
        "--length",
        "186",
        "--spans",
        "3",
        "--normal",
        "60",
        "--maximum",
        "72",
        "--built",
        "1927",
    )
    run(
        book,
        "bridge",
        "add",
        "PLAINS",
        "78",
        "40.00",
        "--length",
        "40",
        "--normal",
        "40",
        "--maximum",
        "50",
        "--built",
        "1955",
    )
    listed = run(book, "bridge", "list", "PLAINS")
    assert "BR-77" in listed.output
    assert "weakest" in listed.output
    assert listed.output.index("BR-78") < listed.output.index("weakest")


def test_a_bridge_rated_below_its_normal_load_exits_two(book: str) -> None:
    result = run(
        book,
        "bridge",
        "add",
        "PLAINS",
        "77",
        "34.80",
        "--length",
        "186",
        "--normal",
        "72",
        "--maximum",
        "60",
        "--built",
        "1927",
    )
    assert result.exit_code == 2
