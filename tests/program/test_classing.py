"""Raising and lowering the class a segment is held to."""

from __future__ import annotations

import pytest

from spikemaul.errors import RuleError
from spikemaul.model.defect import Condition
from spikemaul.model.line import Segment
from spikemaul.program.classing import (
    cards_on,
    held_to,
    reasons_against,
    supported_by_cards,
    would_change,
)
from spikemaul.standards.classes import ClassOfTrack
from tests.support.books import a_defect, a_segment


def segment(track_class: ClassOfTrack = ClassOfTrack.THREE) -> Segment:
    return a_segment(span="12.00-14.00", authorized=track_class)


def test_the_cards_on_a_segment_are_the_open_ones_inside_it() -> None:
    inside = a_defect(at="13.00")
    outside = a_defect(sequence=143, at="20.00")
    repaired = a_defect(sequence=144, at="13.50", repaired_on=inside.found_on)
    found = cards_on(segment(), [inside, outside, repaired])
    assert [one.ident.sequence for one in found] == [142]


def test_a_segment_with_no_open_cards_is_supported_at_the_top() -> None:
    assert supported_by_cards(segment(), []) == ClassOfTrack.FIVE


def test_the_open_cards_hold_a_segment_to_the_lowest_of_them() -> None:
    cards = [a_defect(at="13.00"), a_defect(sequence=143, at="13.50", meets=ClassOfTrack.TWO)]
    assert supported_by_cards(segment(), cards) == ClassOfTrack.ONE


def test_a_card_that_meets_nothing_supports_nothing() -> None:
    cards = [a_defect(at="13.00", meets=None, condition=Condition.RAIL_BREAK, reading="broken")]
    assert supported_by_cards(segment(), cards) is None


def test_lowering_the_class_is_always_allowed() -> None:
    changed = held_to(segment(), ClassOfTrack.ONE, [a_defect(at="13.00")])
    assert changed.authorized == ClassOfTrack.ONE


def test_raising_past_what_the_cards_support_is_refused() -> None:
    cards = [a_defect(at="13.00")]
    with pytest.raises(RuleError, match="cannot be raised to class 4"):
        held_to(segment(), ClassOfTrack.FOUR, cards)


def test_the_refusal_names_the_cards_in_the_way() -> None:
    cards = [a_defect(at="13.00")]
    against = reasons_against(segment(), ClassOfTrack.FOUR, cards)
    assert "DF-2025-0142" in against[0]
    assert "meets class 1" in against[0]


def test_raising_with_nothing_in_the_way_is_allowed() -> None:
    changed = held_to(segment(), ClassOfTrack.FOUR, [])
    assert changed.authorized == ClassOfTrack.FOUR


def test_a_repaired_card_is_not_in_the_way() -> None:
    cards = [a_defect(at="13.00").repaired(a_defect().found_on)]
    assert held_to(segment(), ClassOfTrack.FOUR, cards)


def test_holding_a_segment_to_the_class_it_already_has_is_refused() -> None:
    with pytest.raises(RuleError, match="already held at class 3"):
        held_to(segment(), ClassOfTrack.THREE, [])


def test_main_track_cannot_be_dropped_to_excepted() -> None:
    with pytest.raises(RuleError, match="not carried as excepted"):
        held_to(segment(), ClassOfTrack.EXCEPTED, [])


def test_the_change_says_what_it_does_to_the_speed() -> None:
    assert "goes down from 40 mph to 10 mph" in would_change(segment(), ClassOfTrack.ONE)
    assert "goes up" in would_change(segment(), ClassOfTrack.FOUR)
