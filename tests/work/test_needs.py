"""Needs, which carry where they came from and the deadline that came with it."""

from __future__ import annotations

from datetime import date

from spikemaul.model.defect import Condition
from spikemaul.model.work import WorkKind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.ties.condition import TieLength
from spikemaul.ties.survey import TieSurvey
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.work.needs import (
    need_from_defect,
    needs_from_defects,
    needs_from_survey,
    total_by_kind,
    work_for,
)
from tests.support.books import a_defect

HELD_AT = ClassOfTrack.THREE


def test_every_condition_names_a_kind_of_work() -> None:
    for condition in Condition:
        assert isinstance(work_for(condition), WorkKind)


def test_a_gauge_card_becomes_gauge_repair_at_the_milepost() -> None:
    got = need_from_defect(a_defect(), HELD_AT)
    assert got.kind is WorkKind.GAUGE_REPAIR
    assert got.quantity == 1
    assert got.unit == "feet"
    assert got.due_on == date(2025, 6, 5)
    assert not got.stops_trains


def test_a_geometry_card_becomes_surfacing_either_side_of_it() -> None:
    got = need_from_defect(a_defect(condition=Condition.WARP, reading="2 1/4"), HELD_AT)
    assert got.kind is WorkKind.SURFACING
    assert got.span.begin < Milepost.parse("13.22") < got.span.end
    assert got.quantity == got.span.feet


def test_a_card_that_stops_trains_says_so_instead_of_carrying_a_date() -> None:
    broken = a_defect(condition=Condition.RAIL_BREAK, meets=None, reading="broken base")
    got = need_from_defect(broken, HELD_AT)
    assert got.stops_trains
    assert got.due_on is None
    assert got.describe().endswith("before the next train")


def test_the_needs_that_stop_trains_come_first() -> None:
    broken = a_defect(
        sequence=150, at="20.00", condition=Condition.RAIL_BREAK, meets=None, reading="broken"
    )
    got = needs_from_defects([a_defect(), broken], HELD_AT)
    assert got[0].stops_trains
    assert [one.because.split()[0] for one in got] == ["DF-2025-0150", "DF-2025-0142"]


def test_a_repaired_card_calls_for_nothing() -> None:
    repaired = a_defect(repaired_on=date(2025, 5, 20))
    assert needs_from_defects([repaired], HELD_AT) == []


def test_a_card_that_meets_the_class_still_carries_no_deadline() -> None:
    got = need_from_defect(a_defect(), ClassOfTrack.ONE)
    assert got.due_on is None
    assert not got.stops_trains


def test_a_tie_survey_becomes_one_need_per_run_of_bad_lengths() -> None:
    survey = TieSurvey(
        subdivision=a_defect().subdivision,
        span=Span.parse("13.00-14.00"),
        on=date(2025, 8, 4),
        lengths=[
            TieLength(at=Milepost.parse("13.10"), total=22, good=9, longest_run=2),
            TieLength(at=Milepost.parse("13.11"), total=22, good=10, longest_run=2),
            TieLength(at=Milepost.parse("13.50"), total=22, good=16, longest_run=2),
        ],
    )
    got = needs_from_survey(survey, ClassOfTrack.FOUR, date(2025, 10, 1))
    assert len(got) == 1
    assert got[0].kind is WorkKind.TIE_RENEWAL
    assert got[0].quantity == 5
    assert got[0].due_on == date(2025, 10, 1)


def test_a_survey_with_nothing_short_calls_for_nothing() -> None:
    survey = TieSurvey(
        subdivision=a_defect().subdivision,
        span=Span.parse("13.00-14.00"),
        on=date(2025, 8, 4),
        lengths=[TieLength(at=Milepost.parse("13.10"), total=22, good=16, longest_run=2)],
    )
    assert needs_from_survey(survey, ClassOfTrack.FOUR, None) == []


def test_the_totals_are_kept_in_their_own_units() -> None:
    needs = needs_from_defects(
        [
            a_defect(),
            a_defect(sequence=143, at="14.00", condition=Condition.TIES, reading="9 good"),
        ],
        HELD_AT,
    )
    totals = total_by_kind(needs)
    assert set(totals) == {WorkKind.GAUGE_REPAIR, WorkKind.TIE_RENEWAL}
    assert totals[WorkKind.TIE_RENEWAL] == 1
