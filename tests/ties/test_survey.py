"""A tie survey, and the three different questions asked of it."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.ties.condition import TieLength
from spikemaul.ties.survey import TieSurvey
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
ON = date(2025, 8, 4)


def length(post: str, good: int = 16, run: int = 2, joints: int = 0, held: int = 0) -> TieLength:
    return TieLength(
        at=Milepost.parse(post),
        total=22,
        good=good,
        longest_run=run,
        joints=joints,
        joints_supported=held,
    )


def survey(*lengths: TieLength, span: str = "13.00-14.00") -> TieSurvey:
    return TieSurvey(subdivision=PLAINS, span=Span.parse(span), on=ON, lengths=list(lengths))


def test_a_survey_with_nothing_counted_is_not_a_survey() -> None:
    with pytest.raises(InputError, match="is not a survey"):
        survey()


def test_a_survey_that_walks_backwards_is_refused() -> None:
    with pytest.raises(InputError, match="walks forward"):
        survey(length("13.20"), length("13.10"))


def test_a_length_outside_the_stretch_walked_is_refused() -> None:
    with pytest.raises(InputError, match="outside the stretch"):
        survey(length("13.20"), length("15.00"))


def test_the_stretch_holds_what_its_worst_length_holds() -> None:
    subject = survey(length("13.10"), length("13.20", good=9), length("13.30"))
    assert subject.class_supported() == ClassOfTrack.THREE
    assert str(subject.worst().at) == "13.20"


def test_a_stretch_with_a_length_that_holds_nothing_holds_nothing() -> None:
    subject = survey(length("13.10"), length("13.20", good=4))
    assert subject.class_supported() is None
    assert str(subject.worst().at) == "13.20"


def test_the_failing_lengths_are_the_ones_below_the_class_held_to() -> None:
    subject = survey(length("13.10"), length("13.20", good=9), length("13.30", good=7))
    failing = subject.failing(ClassOfTrack.FOUR)
    assert [str(one.at) for one in failing] == ["13.20", "13.30"]
    assert subject.failing(ClassOfTrack.ONE) == []


def test_the_ties_needed_are_added_up_and_not_multiplied_out() -> None:
    subject = survey(length("13.10", good=10), length("13.20", good=9))
    assert subject.ties_needed(ClassOfTrack.FOUR) == 5
    assert subject.ties_needed(ClassOfTrack.THREE) == 0


def test_the_clusters_join_lengths_that_run_into_each_other() -> None:
    subject = survey(
        length("13.10", good=9),
        length("13.11", good=9),
        length("13.50", good=9),
    )
    clusters = subject.clusters(ClassOfTrack.FOUR)
    assert len(clusters) == 2
    assert clusters[0].begin == Milepost.parse("13.10")


def test_a_stretch_with_nothing_failing_has_no_clusters() -> None:
    assert survey(length("13.10"), length("13.20")).clusters(ClassOfTrack.FOUR) == []


def test_the_length_at_a_milepost_is_the_one_it_falls_in() -> None:
    subject = survey(length("13.10"), length("13.20"))
    found = subject.at(Milepost.parse("13.10"))
    assert found is not None
    assert str(found.at) == "13.10"
    assert subject.at(Milepost.parse("13.60")) is None


def test_a_survey_says_itself_in_one_line() -> None:
    subject = survey(length("13.10"), length("13.20", good=9))
    assert subject.describe() == ("PLAINS 13.00 to 14.00 2025-08-04 2 lengths, holds class 3")
    assert survey(length("13.10", good=4)).describe().endswith("holds nothing")
