"""Designations, and the date they lapse on."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError
from spikemaul.model.crew import Person
from spikemaul.model.inspection import Scope
from spikemaul.program.qualification import (
    WINDOW_DAYS,
    lapsed,
    lapsing,
    next_to_lapse,
    standings,
    uncovered,
    window_from,
)
from tests.support.books import a_person

ON = date(2025, 11, 1)
WATCHED = (Scope.TRACK, Scope.TURNOUTS, Scope.RAIL_FLAW)


def people() -> list[Person]:
    return [
        a_person(),
        a_person(
            initials="DKEHOE",
            name="D Kehoe",
            scopes=frozenset({Scope.TRACK}),
            until=date(2026, 6, 30),
        ),
        a_person(initials="JHOLT", name="J Holt", scopes=frozenset(), until=None),
    ]


def test_everybody_comes_back_soonest_to_lapse_first() -> None:
    got = standings(people(), ON)
    assert [one.person.initials for one in got] == ["RSTIVERS", "DKEHOE", "JHOLT"]


def test_somebody_designated_for_nothing_says_so() -> None:
    got = standings(people(), ON)[-1]
    assert not got.has_one
    assert got.describe().endswith("designated for nothing")
    assert got.days_left is None


def test_a_designation_that_has_run_out_is_lapsed() -> None:
    got = lapsed(people(), date(2026, 1, 1))
    assert [one.person.initials for one in got] == ["RSTIVERS"]
    assert "lapsed 2025-12-31" in got[0].describe()


def test_nothing_has_lapsed_while_the_dates_are_ahead() -> None:
    assert lapsed(people(), ON) == []


def test_a_designation_inside_the_window_is_lapsing() -> None:
    got = lapsing(people(), date(2025, 12, 1), days=60)
    assert [one.person.initials for one in got] == ["RSTIVERS"]


def test_a_designation_that_has_already_lapsed_is_not_lapsing() -> None:
    assert lapsing(people(), date(2026, 1, 1), days=60) == []


def test_a_window_that_looks_backwards_is_refused() -> None:
    with pytest.raises(InputError, match="looks forward"):
        lapsing(people(), ON, days=-1)


def test_a_scope_nobody_is_designated_for_is_named() -> None:
    assert uncovered(people(), ON, WATCHED) == [Scope.RAIL_FLAW]


def test_a_scope_whose_only_person_has_lapsed_is_uncovered() -> None:
    got = uncovered(people(), date(2026, 1, 1), WATCHED)
    assert Scope.TURNOUTS in got
    assert Scope.TRACK not in got


def test_the_next_to_lapse_is_the_first_date_ahead() -> None:
    got = next_to_lapse(people(), ON)
    assert got is not None
    assert got.person.initials == "RSTIVERS"


def test_a_book_with_nobody_dated_has_nothing_to_lapse() -> None:
    nobody = [a_person(initials="JHOLT", name="J Holt", scopes=frozenset(), until=None)]
    assert next_to_lapse(nobody, ON) is None


def test_the_window_is_a_date_and_the_default_is_two_months() -> None:
    assert WINDOW_DAYS == 60
    assert window_from(ON) == date(2025, 12, 31)
