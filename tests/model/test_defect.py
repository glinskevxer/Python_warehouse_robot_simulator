"""Defect cards, which carry the reading rather than a verdict."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError, RuleError
from spikemaul.model.defect import Condition, Defect
from spikemaul.model.ids import Ident, Kind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.remedial import Remedy
from spikemaul.units.milepost import Milepost


def defect(**changes: object) -> Defect:
    fields: dict[str, object] = {
        "ident": Ident.numbered(Kind.DEFECT, 2025, 142),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "at": Milepost.parse("13.22"),
        "found_on": date(2025, 5, 6),
        "found_by": Ident.named(Kind.PERSON, "RSTIVERS"),
        "condition": Condition.GAUGE,
        "reading": "57 7/8",
        "meets": ClassOfTrack.ONE,
    }
    fields.update(changes)
    return Defect(**fields)  # type: ignore[arg-type]


def test_a_condition_reads_off_the_card() -> None:
    assert Condition.parse("gauge") == Condition.GAUGE
    assert Condition.parse(" Rail Break ") == Condition.RAIL_BREAK
    with pytest.raises(InputError, match="is not a condition"):
        Condition.parse("bent")


def test_the_conditions_the_geometry_car_finds_are_named() -> None:
    assert Condition.WARP.is_geometry
    assert Condition.PROFILE.is_geometry
    assert not Condition.TIES.is_geometry
    assert not Condition.FROG.is_geometry


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not a defect number"):
        defect(ident=Ident.numbered(Kind.ORDER, 2025, 142))
    with pytest.raises(InputError, match="is not a person"):
        defect(found_by=Ident.named(Kind.GANG, "SEC2"))
    with pytest.raises(InputError, match="not an inspection number"):
        defect(inspection=Ident.named(Kind.SEGMENT, "014"))


def test_the_number_and_the_date_agree_on_the_year() -> None:
    with pytest.raises(InputError, match="numbered in a different year"):
        defect(ident=Ident.numbered(Kind.DEFECT, 2024, 142))


def test_a_card_carries_what_was_measured() -> None:
    with pytest.raises(InputError, match="carries what was measured"):
        defect(reading="   ")


def test_a_broken_rail_does_not_meet_a_class_of_track() -> None:
    with pytest.raises(RuleError, match="does not meet a class"):
        defect(condition=Condition.RAIL_BREAK, meets=ClassOfTrack.ONE)
    broken = defect(condition=Condition.RAIL_BREAK, meets=None, reading="broken base")
    assert broken.action(ClassOfTrack.THREE).takes_track_out


def test_the_same_card_reads_differently_on_two_classes() -> None:
    card = defect()
    assert card.action(ClassOfTrack.ONE).remedy is Remedy.NONE
    assert card.action(ClassOfTrack.THREE).remedy is Remedy.RESTRICT
    assert card.action(ClassOfTrack.THREE).hold_at == ClassOfTrack.ONE


def test_a_calendar_deadline_becomes_a_date() -> None:
    assert defect().due_on(ClassOfTrack.THREE) == date(2025, 6, 5)


def test_a_deadline_that_is_not_on_the_calendar_has_no_date() -> None:
    assert defect().due_on(ClassOfTrack.ONE) is None
    out = defect(meets=None, condition=Condition.RAIL_BREAK, reading="broken base")
    assert out.due_on(ClassOfTrack.THREE) is None


def test_a_card_is_overdue_the_day_after_its_window_runs_out() -> None:
    card = defect()
    assert not card.is_overdue(ClassOfTrack.THREE, date(2025, 6, 5))
    assert card.is_overdue(ClassOfTrack.THREE, date(2025, 6, 6))


def test_a_repaired_card_is_never_overdue() -> None:
    card = defect().repaired(date(2025, 5, 20))
    assert not card.is_open
    assert not card.is_overdue(ClassOfTrack.THREE, date(2026, 1, 1))


def test_a_card_cannot_be_repaired_twice_or_before_it_was_found() -> None:
    card = defect().repaired(date(2025, 5, 20))
    with pytest.raises(RuleError, match="already repaired"):
        card.repaired(date(2025, 6, 1))
    with pytest.raises(InputError, match="repaired before it was found"):
        defect(repaired_on=date(2025, 5, 1))


def test_a_card_says_itself_in_one_line() -> None:
    assert defect().describe() == (
        "DF-2025-0142 2025-05-06 PLAINS MP 13.22 gauge 57 7/8 meets class 1, open"
    )
    assert (
        defect(meets=None, condition=Condition.RAIL_BREAK, reading="x")
        .describe()
        .endswith("meets nothing, open")
    )
