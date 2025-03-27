"""People and gangs, and the designation that makes an inspection an inspection."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError, RuleError
from spikemaul.model.crew import Craft, Gang, Person
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Scope


def person(**changes: object) -> Person:
    fields: dict[str, object] = {
        "ident": Ident.named(Kind.PERSON, "RSTIVERS"),
        "name": "R Stivers",
        "craft": Craft.INSPECTOR,
        "qualified_for": frozenset({Scope.TRACK, Scope.TURNOUTS}),
        "qualified_until": date(2025, 12, 31),
    }
    fields.update(changes)
    return Person(**fields)  # type: ignore[arg-type]


def gang(**changes: object) -> Gang:
    fields: dict[str, object] = {
        "ident": Ident.named(Kind.GANG, "SEC2"),
        "name": "Section 2",
        "foreman": Ident.named(Kind.PERSON, "DKEHOE"),
        "headcount": 4,
        "machines": ("tamper", "regulator"),
        "headquarters": "Alden",
    }
    fields.update(changes)
    return Gang(**fields)  # type: ignore[arg-type]


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not a person number"):
        person(ident=Ident.named(Kind.GANG, "SEC2"))
    with pytest.raises(InputError, match="not a gang number"):
        gang(ident=Ident.named(Kind.PERSON, "DKEHOE"))
    with pytest.raises(InputError, match="is not a person"):
        gang(foreman=Ident.named(Kind.GANG, "SEC2"))


def test_a_person_has_a_name() -> None:
    with pytest.raises(InputError, match="has a name"):
        person(name="  ")


def test_a_designation_without_an_end_date_is_refused() -> None:
    with pytest.raises(RuleError, match="designation has no end date"):
        person(qualified_until=None)
    with pytest.raises(RuleError, match="nothing designated for"):
        person(qualified_for=frozenset())


def test_somebody_with_no_designation_at_all_is_allowed() -> None:
    hand = person(craft=Craft.TRACKMAN, qualified_for=frozenset(), qualified_until=None)
    assert not hand.may_inspect(Scope.TRACK, date(2025, 5, 6))
    assert hand.describe().endswith("no designation")


def test_an_inspection_outside_the_designation_does_not_count() -> None:
    subject = person()
    assert subject.may_inspect(Scope.TRACK, date(2025, 5, 6))
    assert not subject.may_inspect(Scope.RAIL_FLAW, date(2025, 5, 6))


def test_a_designation_that_has_lapsed_does_not_count() -> None:
    subject = person()
    assert subject.may_inspect(Scope.TRACK, date(2025, 12, 31))
    assert not subject.may_inspect(Scope.TRACK, date(2026, 1, 1))


def test_requalifying_moves_the_date_forward_only() -> None:
    subject = person().requalified(date(2026, 12, 31))
    assert subject.may_inspect(Scope.TRACK, date(2026, 6, 1))
    with pytest.raises(RuleError, match="already designated through"):
        subject.requalified(date(2026, 1, 1))


def test_requalifying_can_change_what_is_designated() -> None:
    subject = person().requalified(date(2026, 12, 31), frozenset({Scope.JOINT_BARS}))
    assert subject.may_inspect(Scope.JOINT_BARS, date(2026, 6, 1))
    assert not subject.may_inspect(Scope.TRACK, date(2026, 6, 1))
    with pytest.raises(RuleError, match="cannot be requalified for nothing"):
        person().requalified(date(2027, 1, 1), frozenset())


def test_the_crafts_that_can_take_track_time_are_named() -> None:
    assert Craft.FOREMAN.may_hold_track_authority
    assert Craft.INSPECTOR.may_hold_track_authority
    assert not Craft.TRACKMAN.may_hold_track_authority


def test_a_person_says_themselves_in_one_line() -> None:
    assert person().describe() == (
        "PN-RSTIVERS R Stivers, inspector, track, turnouts through 2025-12-31"
    )
    assert person().initials == "RSTIVERS"


def test_a_gang_is_at_least_one_person() -> None:
    with pytest.raises(InputError, match="at least one person"):
        gang(headcount=0)


def test_a_machine_is_assigned_once() -> None:
    with pytest.raises(InputError, match="assigned to a gang once"):
        gang(machines=("tamper", "tamper"))
    with pytest.raises(RuleError, match="already on Section 2"):
        gang().with_machine("Tamper")


def test_a_machine_can_be_added_to_a_gang() -> None:
    bigger = gang().with_machine("spiker")
    assert bigger.has("spiker")
    assert not gang().has("spiker")


def test_a_gang_says_itself_in_one_line() -> None:
    assert gang().describe() == "GG-SEC2 Section 2, 4 men at Alden, tamper, regulator"
    assert gang(machines=(), headquarters="").describe().endswith("4 men, no machines")
