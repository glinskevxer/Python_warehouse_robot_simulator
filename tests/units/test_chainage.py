"""Distance on a line whose mileposting has been equated twice."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.units.chainage import Chainage, Equation, Stretch
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

OVERLAP = Equation(Milepost.parse("61.40"), Milepost.parse("61.15"))
GAP = Equation(Milepost.parse("150.00"), Milepost.parse("150.60"))


def line() -> Chainage:
    return Chainage(Milepost.parse("0.00"), Milepost.parse("214.00"), (OVERLAP, GAP))


def post(text: str) -> Milepost:
    return Milepost.parse(text)


def test_an_equation_that_changes_nothing_is_refused() -> None:
    with pytest.raises(InputError, match="changes nothing"):
        Equation(post("61.40"), post("61.40"))


def test_an_equation_says_whether_numbering_repeats_or_skips() -> None:
    assert OVERLAP.kind == "overlap"
    assert OVERLAP.hundredths == -25
    assert GAP.kind == "gap"
    assert GAP.hundredths == 60
    assert str(OVERLAP) == "MP 61.40 = MP 61.15"


def test_equations_have_to_come_in_the_order_they_are_passed() -> None:
    with pytest.raises(InputError, match="not past the one before it"):
        Chainage(post("0.00"), post("214.00"), (GAP, OVERLAP))


def test_a_line_that_ends_before_its_last_equation_is_refused() -> None:
    with pytest.raises(InputError, match="before its last equation"):
        Chainage(post("0.00"), post("100.00"), (OVERLAP, GAP))


def test_a_backwards_line_is_refused() -> None:
    with pytest.raises(InputError, match="runs forward"):
        Chainage(post("10.00"), post("5.00"))


def test_the_line_breaks_into_one_stretch_per_equation_plus_one() -> None:
    stretches = line().stretches
    assert [str(s.begin) for s in stretches] == ["0.00", "61.15", "150.60"]
    assert [str(s.end) for s in stretches] == ["61.40", "150.00", "214.00"]
    assert stretches[0].origin_feet == 0
    assert stretches[1].origin_feet == 61 * 5280 + 2112


def test_the_length_on_the_ground_is_not_the_last_milepost() -> None:
    assert line().feet == round(214.00 * 5280) + round(0.25 * 5280) - round(0.60 * 5280)


def test_a_milepost_inside_the_repeated_quarter_mile_is_two_places() -> None:
    assert len(line().occurrences(post("61.20"))) == 2
    with pytest.raises(InputError, match="on this line twice"):
        line().position(post("61.20"))


def test_a_milepost_the_equations_skipped_is_not_on_the_line() -> None:
    assert line().occurrences(post("150.30")) == []
    with pytest.raises(InputError, match="not on this line"):
        line().position(post("150.30"))


def test_an_ordinary_milepost_has_one_position() -> None:
    assert line().position(post("10.00")) == 52800
    assert line().position(post("100.00")) == round(100.00 * 5280) + round(0.25 * 5280)


def test_distance_across_an_overlap_is_longer_than_the_numbers_say() -> None:
    got = line().feet_between(post("61.00"), post("62.00"))
    assert got == round(1.25 * 5280)
    assert line().feet_between(post("62.00"), post("61.00")) == -round(1.25 * 5280)


def test_distance_across_a_gap_is_longer_than_the_numbers_say() -> None:
    assert line().feet_between(post("149.00"), post("151.00")) == round(1.40 * 5280)


def test_a_distance_along_the_line_reads_back_as_a_milepost() -> None:
    subject = line()
    assert subject.post_at(0) == post("0.00")
    assert subject.post_at(52800) == post("10.00")
    assert subject.post_at(subject.feet) == post("214.00")
    assert subject.post_at(subject.position(post("100.00"))) == post("100.00")


def test_a_distance_off_the_end_is_refused() -> None:
    subject = line()
    with pytest.raises(InputError, match="off the end"):
        subject.post_at(-1)
    with pytest.raises(InputError, match="off the end"):
        subject.post_at(subject.feet + 1)


def test_a_span_across_an_equation_comes_back_in_pieces() -> None:
    pieces = line().pieces(Span.parse("61.00-62.00"))
    assert pieces == [Span.parse("61.00-61.40"), Span.parse("61.15-62.00")]
    assert line().true_feet(Span.parse("61.00-62.00")) == round(1.25 * 5280)


def test_a_span_running_through_skipped_numbering_is_refused() -> None:
    with pytest.raises(InputError, match="numbering the equations skipped"):
        line().pieces(Span.parse("149.00-151.00"))


def test_a_span_off_the_line_is_refused() -> None:
    with pytest.raises(InputError, match="not on this line"):
        line().pieces(Span.parse("300.00-301.00"))
    with pytest.raises(InputError, match="not on this line"):
        line().pieces(Span.parse("213.00-215.00"))


def test_a_span_inside_one_stretch_is_left_alone() -> None:
    assert line().pieces(Span.parse("10.00-12.00")) == [Span.parse("10.00-12.00")]
    assert line().true_feet(Span.parse("10.00-12.00")) == 10560


def test_a_stretch_holds_both_of_its_ends() -> None:
    stretch = Stretch(post("0.00"), post("61.40"), 0)
    assert stretch.holds(post("0.00"))
    assert stretch.holds(post("61.40"))
    assert not stretch.holds(post("61.41"))
    assert stretch.span == Span.parse("0.00-61.40")
