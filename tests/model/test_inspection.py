"""Inspection records, which are worth more than what they found."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Inspection, Method, Scope
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span


def inspection(**changes: object) -> Inspection:
    fields: dict[str, object] = {
        "ident": Ident.numbered(Kind.INSPECTION, 2025, 41),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "span": Span.parse("0.00-61.40"),
        "on": date(2025, 4, 14),
        "by": Ident.named(Kind.PERSON, "RSTIVERS"),
        "method": Method.HI_RAIL,
        "scope": Scope.TRACK,
    }
    fields.update(changes)
    return Inspection(**fields)  # type: ignore[arg-type]


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not an inspection number"):
        inspection(ident=Ident.numbered(Kind.DEFECT, 2025, 41))
    with pytest.raises(InputError, match="is not a person"):
        inspection(by=Ident.named(Kind.GANG, "SEC2"))


def test_the_number_and_the_date_agree_on_the_year() -> None:
    with pytest.raises(InputError, match="numbered in a different year"):
        inspection(ident=Ident.numbered(Kind.INSPECTION, 2024, 41))


def test_a_scope_is_only_done_by_the_methods_that_can_do_it() -> None:
    with pytest.raises(RuleError, match="not done by hi rail"):
        inspection(scope=Scope.TURNOUTS, method=Method.HI_RAIL)
    with pytest.raises(RuleError, match="not done by walking"):
        inspection(scope=Scope.RAIL_FLAW, method=Method.WALKING)
    assert inspection(scope=Scope.RAIL_FLAW, method=Method.FLAW_DETECTOR).scope is Scope.RAIL_FLAW


def test_the_methods_that_are_bought_in_are_named() -> None:
    assert Method.GEOMETRY_CAR.is_contracted
    assert Method.FLAW_DETECTOR.is_contracted
    assert not Method.WALKING.is_contracted
    assert Method.WALKING.is_on_foot
    assert not Method.HI_RAIL.is_on_foot


def test_an_inspection_covers_a_stretch_rather_than_a_point() -> None:
    subject = inspection()
    assert subject.covers(Milepost.parse("43.20"))
    assert not subject.covers(Milepost.parse("61.40"))
    assert subject.covers_all_of(Span.parse("12.00-14.50"))
    assert not subject.covers_all_of(Span.parse("60.00-70.00"))


def test_a_special_inspection_says_it_was_not_on_the_cycle() -> None:
    assert inspection(scope=Scope.SPECIAL, method=Method.WALKING).is_special
    assert not inspection().is_special


def test_the_gap_between_two_inspections_is_counted_in_days() -> None:
    first = inspection()
    second = inspection(ident=Ident.numbered(Kind.INSPECTION, 2025, 44), on=date(2025, 4, 21))
    assert first.days_before(second) == 7
    with pytest.raises(InputError, match="is before"):
        second.days_before(first)


def test_two_records_count_to_the_same_cycle_only_where_they_meet() -> None:
    first = inspection()
    same = inspection(
        ident=Ident.numbered(Kind.INSPECTION, 2025, 44), span=Span.parse("40.00-80.00")
    )
    assert first.same_cycle_as(same)
    other_scope = inspection(
        ident=Ident.numbered(Kind.INSPECTION, 2025, 45),
        scope=Scope.JOINT_BARS,
    )
    assert not first.same_cycle_as(other_scope)
    other_sub = inspection(
        ident=Ident.numbered(Kind.INSPECTION, 2025, 46),
        subdivision=Ident.named(Kind.SUBDIVISION, "RIVER"),
    )
    assert not first.same_cycle_as(other_sub)


def test_two_records_on_track_that_does_not_meet_are_separate_cycles() -> None:
    first = inspection()
    apart = inspection(
        ident=Ident.numbered(Kind.INSPECTION, 2025, 47), span=Span.parse("61.40-90.00")
    )
    assert not first.same_cycle_as(apart)


def test_an_inspection_says_itself_in_one_line() -> None:
    assert inspection().describe() == (
        "IN-2025-0041 2025-04-14 PLAINS 0.00 to 61.40 track by hi rail RSTIVERS"
    )
