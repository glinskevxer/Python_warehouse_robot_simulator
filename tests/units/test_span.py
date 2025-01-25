"""Milepost spans, and the end that is deliberately not included."""

from __future__ import annotations

from decimal import Decimal

import pytest

from spikemaul.errors import InputError
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span, merge_all, subtract_all, total_miles


def span(begin: str, end: str) -> Span:
    return Span.of(begin, end)


def test_a_span_reads_and_prints_the_way_a_bulletin_writes_it() -> None:
    assert str(Span.parse("43.20-44.10")) == "43.20 to 44.10"
    assert Span.parse("MP 43.20 to MP 44.10") == span("43.20", "44.10")
    assert Span.parse("43.20 -- 44.10") == span("43.20", "44.10")


@pytest.mark.parametrize("text", ["43.20", "", "43.20-", "north to south", "43.20-43.20"])
def test_rubbish_and_empty_spans_are_refused(text: str) -> None:
    with pytest.raises(InputError):
        Span.parse(text)


def test_a_backwards_span_is_refused_rather_than_swapped() -> None:
    with pytest.raises(InputError, match="has to run forward"):
        span("44.10", "43.20")


def test_the_length_is_available_in_the_three_units_it_gets_asked_for() -> None:
    piece = span("43.20", "44.10")
    assert piece.hundredths == 90
    assert piece.miles == Decimal("0.90")
    assert piece.feet == 4752


def test_the_far_end_is_not_in_the_span() -> None:
    piece = span("43.20", "44.10")
    assert piece.contains(Milepost.parse("43.20"))
    assert piece.contains(Milepost.parse("44.09"))
    assert not piece.contains(Milepost.parse("44.10"))
    assert not piece.contains(Milepost.parse("43.19"))


def test_two_spans_meeting_at_a_post_do_not_overlap() -> None:
    first = span("43.00", "44.00")
    second = span("44.00", "45.00")
    assert not first.overlaps(second)
    assert first.touches(second)
    assert first.intersection(second) is None


def test_covering_is_not_the_same_as_overlapping() -> None:
    big = span("43.00", "46.00")
    small = span("44.00", "45.00")
    edge = span("45.00", "47.00")
    assert big.covers(small)
    assert not small.covers(big)
    assert big.overlaps(edge)
    assert not big.covers(edge)


def test_the_shared_railroad_is_returned_as_a_span() -> None:
    got = span("43.00", "45.00").intersection(span("44.20", "46.00"))
    assert got == span("44.20", "45.00")


def test_merging_two_spans_that_do_not_meet_is_refused() -> None:
    with pytest.raises(InputError, match="would invent track"):
        span("43.00", "44.00").merged(span("44.01", "45.00"))


def test_merging_takes_the_outside_of_both() -> None:
    assert span("43.00", "44.50").merged(span("44.00", "45.00")) == span("43.00", "45.00")
    assert span("44.00", "45.00").merged(span("43.00", "44.00")) == span("43.00", "45.00")


def test_a_span_splits_at_a_post_inside_it_only() -> None:
    left, right = span("43.00", "45.00").split_at(Milepost.parse("44.00"))
    assert left == span("43.00", "44.00")
    assert right == span("44.00", "45.00")
    with pytest.raises(InputError, match="does not split it"):
        span("43.00", "45.00").split_at(Milepost.parse("45.00"))


def test_taking_a_piece_out_of_the_middle_leaves_two() -> None:
    left = span("43.00", "46.00").without(span("44.00", "45.00"))
    assert left == [span("43.00", "44.00"), span("45.00", "46.00")]


def test_taking_out_an_end_leaves_one_and_taking_out_everything_leaves_none() -> None:
    assert span("43.00", "46.00").without(span("42.00", "44.00")) == [span("44.00", "46.00")]
    assert span("43.00", "46.00").without(span("43.00", "46.00")) == []
    assert span("43.00", "46.00").without(span("47.00", "48.00")) == [span("43.00", "46.00")]


def test_merging_a_list_coalesces_overlapping_and_touching_pieces() -> None:
    got = merge_all(
        [
            span("44.00", "45.00"),
            span("43.00", "43.50"),
            span("43.50", "44.20"),
            span("46.00", "46.50"),
        ]
    )
    assert got == [span("43.00", "45.00"), span("46.00", "46.50")]


def test_merging_nothing_gives_nothing() -> None:
    assert merge_all([]) == []


def test_subtracting_several_pieces_works_through_them_in_order() -> None:
    left = subtract_all(
        span("40.00", "50.00"),
        [span("41.00", "42.00"), span("41.50", "43.00"), span("49.00", "51.00")],
    )
    assert left == [span("40.00", "41.00"), span("43.00", "49.00")]


def test_overlapping_miles_are_counted_once() -> None:
    assert total_miles([span("43.00", "44.00"), span("43.50", "45.00")]) == Decimal("2.00")
    assert total_miles([]) == Decimal(0)
