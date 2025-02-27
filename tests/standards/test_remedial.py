"""Remedial action, and the four clocks a deadline can be on."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError, RuleError
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.remedial import (
    NO_ACTION,
    Clock,
    Deadline,
    Remedy,
    decide,
    most_severe,
)


def test_a_condition_that_meets_the_class_needs_nothing_doing() -> None:
    action = decide(ClassOfTrack.THREE, ClassOfTrack.THREE)
    assert action == NO_ACTION
    assert action.remedy is Remedy.NONE
    assert action.describe() == "no action, the condition meets the class"


def test_a_condition_that_meets_a_better_class_still_needs_nothing() -> None:
    assert decide(ClassOfTrack.TWO, ClassOfTrack.FIVE) == NO_ACTION


def test_a_condition_that_meets_a_lower_class_holds_the_track_there() -> None:
    action = decide(ClassOfTrack.FOUR, ClassOfTrack.TWO)
    assert action.remedy is Remedy.RESTRICT
    assert action.hold_at == ClassOfTrack.TWO
    assert action.deadline == Deadline.days(30)
    assert action.describe() == "hold at class 2, within 30 days"


def test_a_condition_that_meets_nothing_takes_the_track_out() -> None:
    action = decide(ClassOfTrack.FOUR, None)
    assert action.takes_track_out
    assert action.hold_at is None
    assert action.deadline == Deadline.before_next_train()
    assert action.describe() == "out of service until repaired"


def test_the_deadline_says_itself_the_way_the_card_carries_it() -> None:
    assert Deadline.before_next_train().describe() == "before the next train"
    assert Deadline.by_next_inspection().describe() == "by the next inspection"
    assert Deadline.days(30).describe() == "within 30 days"
    assert Deadline(Clock.SHIFTS, 2).describe() == "within 2 shifts"


def test_a_deadline_does_not_run_backwards() -> None:
    with pytest.raises(InputError, match="does not run backwards"):
        Deadline.days(-1)


def test_two_deadlines_on_the_same_clock_have_a_sooner_one() -> None:
    assert Deadline.days(30).sooner_of(Deadline.days(10)) == Deadline.days(10)
    assert Deadline.days(10).sooner_of(Deadline.days(30)) == Deadline.days(10)


def test_two_deadlines_on_different_clocks_do_not_compare() -> None:
    with pytest.raises(RuleError, match="does not compare with"):
        Deadline.days(30).sooner_of(Deadline.before_next_train())
    assert not Deadline.days(1).comparable_to(Deadline.by_next_inspection())


def test_only_a_deadline_in_days_can_become_a_date() -> None:
    assert Clock.DAYS.is_calendar
    assert not Clock.TRAINS.is_calendar
    assert not Clock.INSPECTIONS.is_calendar


def test_out_of_service_beats_a_restriction_however_low() -> None:
    out = decide(ClassOfTrack.FIVE, None)
    slow = decide(ClassOfTrack.FIVE, ClassOfTrack.EXCEPTED)
    assert most_severe([slow, out]) == out
    assert most_severe([out, slow]) == out


def test_the_lowest_restriction_governs_when_several_apply() -> None:
    first = decide(ClassOfTrack.FIVE, ClassOfTrack.THREE)
    second = decide(ClassOfTrack.FIVE, ClassOfTrack.ONE)
    third = decide(ClassOfTrack.FIVE, ClassOfTrack.FIVE)
    assert most_severe([first, second, third]) == second


def test_nothing_applying_is_no_action() -> None:
    assert most_severe([]) == NO_ACTION
    assert most_severe([NO_ACTION, NO_ACTION]) == NO_ACTION


def test_the_remedies_are_ranked_so_a_list_of_them_sorts() -> None:
    ranks = [one.rank for one in (Remedy.NONE, Remedy.REPAIR, Remedy.RESTRICT)]
    assert ranks == sorted(ranks)
    assert Remedy.OUT_OF_SERVICE.rank > Remedy.RESTRICT.rank
