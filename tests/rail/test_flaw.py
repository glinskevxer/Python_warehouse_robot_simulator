"""The flaw testing cycle, which has two clocks and takes the earlier one."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError
from spikemaul.rail.flaw import due_date, status
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.units.tonnage import ZERO, Tonnage

ON = date(2025, 9, 1)


def test_the_lower_classes_have_no_requirement_and_say_so() -> None:
    got = status(ClassOfTrack.TWO, ON)
    assert not got.is_required
    assert not got.is_due
    assert got.governing == "no requirement"
    assert got.describe() == "class 2, no flaw testing requirement"


def test_a_stretch_nobody_has_tested_is_due() -> None:
    got = status(ClassOfTrack.THREE, ON)
    assert got.never_tested
    assert got.is_due
    assert got.governing == "never tested"
    assert got.describe() == "class 3, never tested"


def test_a_stretch_inside_both_clocks_is_in_cycle() -> None:
    got = status(ClassOfTrack.THREE, ON, last_tested=date(2025, 6, 1), tonnage_since=Tonnage.of(10))
    assert not got.is_due
    assert got.tonnage_left == Tonnage.of(30)
    assert got.days_left == 273


def test_the_tonnage_clock_can_bring_it_due_on_its_own() -> None:
    got = status(ClassOfTrack.THREE, ON, last_tested=date(2025, 6, 1), tonnage_since=Tonnage.of(41))
    assert got.is_due
    assert got.governing == "tonnage"
    assert got.tonnage_left == ZERO
    assert got.days_left != 0


def test_the_calendar_clock_can_bring_it_due_on_its_own() -> None:
    got = status(ClassOfTrack.THREE, ON, last_tested=date(2024, 6, 1), tonnage_since=Tonnage.of(2))
    assert got.is_due
    assert got.governing == "calendar"
    assert got.days_left == 0
    assert got.tonnage_left != ZERO


def test_a_higher_class_comes_due_sooner_on_the_same_history() -> None:
    tested = date(2025, 4, 1)
    tonnage = Tonnage.of(25)
    assert not status(ClassOfTrack.THREE, ON, tested, tonnage).is_due
    assert status(ClassOfTrack.FIVE, ON, tested, tonnage).is_due


def test_a_last_test_in_the_future_is_refused() -> None:
    with pytest.raises(InputError, match="is not a last test"):
        status(ClassOfTrack.THREE, ON, last_tested=date(2026, 1, 1))


def test_the_calendar_backstop_is_a_date_where_there_is_one() -> None:
    assert due_date(ClassOfTrack.THREE, date(2025, 1, 1)) == date(2026, 1, 1)
    assert due_date(ClassOfTrack.FIVE, date(2025, 1, 1)) == date(2025, 6, 30)
    assert due_date(ClassOfTrack.ONE, date(2025, 1, 1)) is None


def test_a_stretch_in_cycle_says_which_clock_will_bring_it_due() -> None:
    heavy = status(
        ClassOfTrack.THREE, ON, last_tested=date(2025, 8, 1), tonnage_since=Tonnage.of(39)
    )
    assert heavy.governing == "tonnage"
    light = status(
        ClassOfTrack.THREE, ON, last_tested=date(2024, 9, 15), tonnage_since=Tonnage.of(1)
    )
    assert light.governing == "calendar"


def test_a_stretch_says_itself_in_one_line() -> None:
    got = status(ClassOfTrack.THREE, ON, last_tested=date(2025, 6, 1), tonnage_since=Tonnage.of(10))
    assert got.describe() == (
        "class 3, last tested 2025-06-01, 10.00 MGT since, in cycle on calendar"
    )
