"""The week ahead, cycle work and what the weather added."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError
from spikemaul.model.crew import Person
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Inspection, Scope
from spikemaul.program.compliance import Standing, standing_for
from spikemaul.program.schedule import due_between, due_from, special_for, week_ahead
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.standards.inspection import Weather
from spikemaul.units.span import Span
from tests.support.books import a_person, an_inspection

RSTIVERS = Ident.named(Kind.PERSON, "RSTIVERS")
ON = date(2025, 5, 20)


def people() -> dict[Ident, Person]:
    return {RSTIVERS: a_person()}


def standing(span: str, inspections: list[Inspection], on: date = ON) -> Standing:
    return standing_for(
        span=Span.parse(span),
        scope=Scope.TRACK,
        track_class=ClassOfTrack.THREE,
        kind=TrackKind.MAIN,
        inspections=inspections,
        people=people(),
        on=on,
    )


def test_a_stretch_in_cycle_is_due_on_the_day_the_cycle_runs_out() -> None:
    got = due_from(standing("12.00-14.00", [an_inspection(on=date(2025, 5, 19))]), ON)
    assert got.due_on == date(2025, 5, 26)
    assert got.days_left == 6
    assert not got.is_now
    assert got.describe().endswith("due 2025-05-26")


def test_a_stretch_nobody_has_walked_is_due_now() -> None:
    got = due_from(standing("12.00-14.00", []), ON)
    assert got.due_on is None
    assert got.is_now
    assert "never inspected" in got.describe()


def test_an_overdue_stretch_is_on_the_list_whatever_its_date() -> None:
    late = standing("12.00-14.00", [an_inspection(on=date(2025, 5, 1))])
    got = due_between([late], date(2025, 5, 20), date(2025, 5, 26))
    assert len(got) == 1
    assert got[0].late
    assert got[0].describe().endswith("overdue")


def test_a_stretch_due_after_the_week_is_not_on_it() -> None:
    fresh = standing("12.00-14.00", [an_inspection(on=date(2025, 5, 19))])
    assert due_between([fresh], date(2025, 5, 20), date(2025, 5, 22)) == []
    assert len(due_between([fresh], date(2025, 5, 20), date(2025, 5, 27))) == 1


def test_the_late_work_sorts_before_the_work_that_is_merely_due() -> None:
    late = standing("20.00-21.00", [an_inspection(sequence=41, on=date(2025, 5, 1))])
    soon = standing("12.00-14.00", [an_inspection(sequence=44, on=date(2025, 5, 19))])
    got = due_between([soon, late], date(2025, 5, 20), date(2025, 5, 27))
    assert [str(one.span.begin) for one in got] == ["20.00", "12.00"]


def test_a_week_that_runs_backwards_is_refused() -> None:
    with pytest.raises(InputError, match="a week runs forward"):
        due_between([], date(2025, 5, 27), date(2025, 5, 20))


def test_a_flood_calls_for_an_inspection_before_the_next_train() -> None:
    got = special_for(Weather.FLOOD, Span.parse("12.00-14.00"), ON)
    assert got.before_a_train
    assert got.describe().endswith("before the next train")


def test_heat_calls_for_one_as_soon_as_possible() -> None:
    got = special_for(Weather.HEAT, Span.parse("12.00-14.00"), ON)
    assert not got.before_a_train
    assert got.describe().endswith("as soon as possible")


def test_the_week_prints_the_specials_first() -> None:
    late = standing("12.00-14.00", [an_inspection(on=date(2025, 5, 1))])
    special = special_for(Weather.FLOOD, Span.parse("20.00-21.00"), ON)
    lines = week_ahead([late], [special], date(2025, 5, 20), date(2025, 5, 27))
    assert lines[0].startswith("week of")
    assert "special after flood" in lines[1]
    assert "overdue" in lines[2]


def test_the_specials_that_stop_a_train_print_before_the_ones_that_do_not() -> None:
    flood = special_for(Weather.FLOOD, Span.parse("20.00-21.00"), ON)
    heat = special_for(Weather.HEAT, Span.parse("12.00-14.00"), ON)
    lines = week_ahead([], [heat, flood], date(2025, 5, 20), date(2025, 5, 27))
    assert "flood" in lines[1]
    assert "heat" in lines[2]


def test_a_quiet_week_says_nothing_is_due() -> None:
    fresh = standing("12.00-14.00", [an_inspection(on=date(2025, 5, 19))])
    lines = week_ahead([fresh], [], date(2025, 5, 20), date(2025, 5, 22))
    assert lines[-1] == "nothing due"
