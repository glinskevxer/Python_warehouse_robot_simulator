"""One length of ties, and the three rules that each cap it."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.ties.condition import TieLength, class_supported, governing_rule
from spikemaul.units.curvature import Curvature
from spikemaul.units.milepost import Milepost


def length(**changes: object) -> TieLength:
    fields: dict[str, object] = {
        "at": Milepost.parse("13.20"),
        "total": 22,
        "good": 16,
        "longest_run": 2,
        "joints": 1,
        "joints_supported": 1,
    }
    fields.update(changes)
    return TieLength(**fields)  # type: ignore[arg-type]


def test_a_length_with_no_ties_is_not_a_count() -> None:
    with pytest.raises(InputError, match="is not a count"):
        length(total=0)
    with pytest.raises(InputError, match="is not a count"):
        length(good=23)


def test_a_run_longer_than_the_defective_ties_is_refused() -> None:
    with pytest.raises(InputError, match="is longer than the"):
        length(good=20, longest_run=3)


def test_more_supported_joints_than_joints_is_refused() -> None:
    with pytest.raises(InputError, match="more joints have a good tie"):
        length(joints=1, joints_supported=2)
    with pytest.raises(InputError, match="not negative"):
        length(joints=-1)


def test_a_good_length_holds_the_top_class() -> None:
    assert class_supported(length()) == ClassOfTrack.FIVE


def test_the_count_rule_caps_it_on_its_own() -> None:
    assert class_supported(length(good=9, longest_run=2)) == ClassOfTrack.THREE
    assert governing_rule(length(good=9, longest_run=2)) == "count"


def test_the_curve_allowance_pulls_the_count_down() -> None:
    on_curve = length(good=12, curve=Curvature.of(4))
    assert class_supported(on_curve) == ClassOfTrack.THREE
    assert class_supported(length(good=12)) == ClassOfTrack.FIVE


def test_a_run_of_defective_ties_caps_it_with_the_count_still_good() -> None:
    subject = length(good=16, longest_run=4)
    assert subject.meets_count() == ClassOfTrack.FIVE
    assert class_supported(subject) == ClassOfTrack.TWO
    assert governing_rule(subject) == "run"


def test_a_joint_with_nothing_under_it_holds_the_length_to_excepted() -> None:
    subject = length(good=16, joints=2, joints_supported=1)
    assert subject.meets_count() == ClassOfTrack.FIVE
    assert class_supported(subject) == ClassOfTrack.EXCEPTED
    assert governing_rule(subject) == "joints"


def test_two_unsupported_joints_hold_the_length_to_nothing() -> None:
    subject = length(good=16, joints=2, joints_supported=0)
    assert subject.unsupported_joints == 2
    assert class_supported(subject) is None


def test_a_length_that_cannot_even_hold_excepted_track_says_so() -> None:
    subject = length(total=22, good=4, longest_run=2)
    assert class_supported(subject) is None


def test_the_shortfall_says_how_many_ties_the_gang_needs() -> None:
    subject = length(good=9)
    assert subject.short_by(ClassOfTrack.FOUR) == 3
    assert subject.short_by(ClassOfTrack.THREE) == 0
    assert length(good=9, curve=Curvature.of(4)).short_by(ClassOfTrack.THREE) == 0


def test_a_length_says_itself_in_one_line() -> None:
    assert length(good=16, joints=2, joints_supported=1).describe() == (
        "MP 13.20 16 of 22 good, run of 2, 1 joints unsupported"
    )
    assert length().defective == 6
