"""The tie table, which counts good ties rather than ties."""

from __future__ import annotations

import pytest

from spikemaul.standards.classes import ALL, ClassOfTrack
from spikemaul.standards.ties import (
    JOINT_WINDOW_INCHES,
    SEGMENT_FEET,
    class_for_consecutive_defective,
    class_for_tie_count,
    required_ties,
    standard_for,
)
from spikemaul.units.curvature import Curvature


def test_a_tie_count_is_taken_over_a_rail_length() -> None:
    assert SEGMENT_FEET == 39
    assert JOINT_WINDOW_INCHES == 24


def test_every_class_has_a_row() -> None:
    assert {one: standard_for(one) for one in ALL}.keys() == set(ALL)


def test_the_count_rises_with_the_class() -> None:
    counts = [required_ties(one) for one in ALL]
    assert counts == sorted(counts)
    assert counts[0] == 5
    assert counts[-1] == 12


def test_a_sharp_curve_wants_one_more_tie_at_the_upper_classes() -> None:
    sharp = Curvature.of(3)
    assert required_ties(ClassOfTrack.FOUR, sharp) == 13
    assert required_ties(ClassOfTrack.THREE, sharp) == 9
    assert required_ties(ClassOfTrack.TWO, sharp) == 8


def test_a_curve_at_the_threshold_is_not_a_sharp_curve() -> None:
    assert required_ties(ClassOfTrack.FOUR, Curvature.of(2)) == 12
    assert required_ties(ClassOfTrack.FOUR, Curvature.of(2, 1)) == 13


def test_a_count_of_good_ties_names_the_class_it_supports() -> None:
    assert class_for_tie_count(12) == ClassOfTrack.FIVE
    assert class_for_tie_count(11) == ClassOfTrack.THREE
    assert class_for_tie_count(8) == ClassOfTrack.THREE
    assert class_for_tie_count(7) == ClassOfTrack.ONE
    assert class_for_tie_count(5) == ClassOfTrack.ONE


def test_a_segment_that_cannot_even_hold_excepted_track_says_so() -> None:
    assert class_for_tie_count(4) is None
    assert class_for_tie_count(0) is None


def test_the_curve_count_pulls_the_class_down_for_the_same_ties() -> None:
    assert class_for_tie_count(12, Curvature.of(4)) == ClassOfTrack.THREE
    assert class_for_tie_count(12, Curvature.of(1)) == ClassOfTrack.FIVE


def test_a_run_of_defective_ties_is_its_own_limit() -> None:
    assert class_for_consecutive_defective(0) == ClassOfTrack.FIVE
    assert class_for_consecutive_defective(2) == ClassOfTrack.FIVE
    assert class_for_consecutive_defective(3) == ClassOfTrack.THREE
    assert class_for_consecutive_defective(4) == ClassOfTrack.TWO
    assert class_for_consecutive_defective(5) is None


def test_a_negative_count_is_a_programming_mistake_not_an_input_one() -> None:
    with pytest.raises(ValueError, match="fewer than no good ties"):
        class_for_tie_count(-1)
    with pytest.raises(ValueError, match="cannot be negative"):
        class_for_consecutive_defective(-1)


def test_the_run_limit_tightens_as_the_class_rises() -> None:
    runs = [standard_for(one).max_consecutive_defective for one in ALL]
    assert runs == sorted(runs, reverse=True)
