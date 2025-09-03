"""The speed profile, which is the lowest cap at every foot."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError
from spikemaul.model.order import Reason
from spikemaul.orders.governing import (
    Cap,
    caps_from_curves,
    caps_from_orders,
    caps_from_segments,
    gaps,
    governing_at,
    profile,
)
from spikemaul.standards.classes import ClassOfTrack, Traffic
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed
from tests.support.books import a_curve, a_segment, an_order

ON = date(2025, 5, 10)


def cap(span: str, mph: int, because: str = "class", detail: str = "") -> Cap:
    return Cap(Span.parse(span), Speed(mph), because, detail)


def test_a_reason_the_profile_does_not_know_is_refused() -> None:
    with pytest.raises(InputError, match="is not a reason"):
        cap("12.00-13.00", 40, "because the foreman said so")


def test_one_cap_over_the_whole_stretch_is_one_piece() -> None:
    got = profile(Span.parse("12.00-14.00"), [cap("12.00-14.00", 40)])
    assert len(got) == 1
    assert got[0].speed == Speed(40)
    assert got[0].describe() == "12.00 to 14.00 40 mph class"


def test_the_lowest_cap_wins_where_two_overlap() -> None:
    caps = [cap("12.00-14.00", 40), cap("12.50-13.00", 10, "slow order", "SO-2025-0031")]
    got = profile(Span.parse("12.00-14.00"), caps)
    assert [one.speed.mph for one in got] == [40, 10, 40]
    assert got[1].because == "slow order"


def test_the_pieces_run_end_to_end_with_no_gaps_where_the_track_is_covered() -> None:
    caps = [cap("12.00-14.00", 40), cap("12.50-13.00", 10, "slow order")]
    got = profile(Span.parse("12.00-14.00"), caps)
    assert got[0].span.end == got[1].span.begin
    assert got[1].span.end == got[2].span.begin
    assert got[-1].span.end == Milepost.parse("14.00")


def test_two_pieces_at_the_same_speed_for_different_reasons_are_not_merged() -> None:
    caps = [
        cap("12.00-14.00", 40),
        cap("12.00-13.00", 25, "curve", "CV-118"),
        cap("13.00-14.00", 25, "slow order", "SO-2025-0031"),
    ]
    got = profile(Span.parse("12.00-14.00"), caps)
    assert len(got) == 2
    assert [one.because for one in got] == ["curve", "slow order"]


def test_two_pieces_at_the_same_speed_for_the_same_reason_are_merged() -> None:
    caps = [cap("12.00-13.00", 40), cap("13.00-14.00", 40)]
    got = profile(Span.parse("12.00-14.00"), caps)
    assert len(got) == 1
    assert got[0].span == Span.parse("12.00-14.00")


def test_a_tie_names_the_more_specific_reason() -> None:
    caps = [cap("12.00-14.00", 25), cap("12.00-14.00", 25, "curve", "CV-118")]
    got = profile(Span.parse("12.00-14.00"), caps)
    assert got[0].because == "curve"
    heat = [*caps, cap("12.00-14.00", 25, "heat", "SO-2025-0044")]
    assert profile(Span.parse("12.00-14.00"), heat)[0].because == "heat"


def test_track_with_no_cap_on_it_is_left_out_and_reported_as_a_gap() -> None:
    caps = [cap("12.00-13.00", 40)]
    got = profile(Span.parse("12.00-14.00"), caps)
    assert [str(one.span) for one in got] == ["12.00 to 13.00"]
    assert gaps(Span.parse("12.00-14.00"), caps) == [Span.parse("13.00-14.00")]


def test_a_stretch_fully_covered_has_no_gaps() -> None:
    assert gaps(Span.parse("12.00-14.00"), [cap("12.00-14.00", 40)]) == []


def test_the_speed_at_a_milepost_is_the_lowest_cap_covering_it() -> None:
    caps = [cap("12.00-14.00", 40), cap("12.50-13.00", 10, "slow order")]
    found = governing_at(Milepost.parse("12.60"), caps)
    assert found is not None
    assert found.speed == Speed(10)
    assert governing_at(Milepost.parse("20.00"), caps) is None


def test_the_caps_come_off_the_records_that_carry_them() -> None:
    segments = [a_segment(span="12.00-14.50", authorized=ClassOfTrack.THREE)]
    assert caps_from_segments(segments)[0].speed == Speed(40)
    assert caps_from_segments(segments, Traffic.PASSENGER)[0].speed == Speed(60)
    curves = [a_curve(body="13.10-13.40", elevation="2")]
    assert caps_from_curves(curves)[0].speed == Speed(48)


def test_only_the_orders_in_force_on_the_day_become_caps() -> None:
    orders = [an_order(effective=date(2025, 6, 1))]
    assert caps_from_orders(orders, ON) == []
    assert caps_from_orders(orders, date(2025, 6, 2)) != []


def test_a_heat_order_is_named_as_heat_rather_than_a_slow_order() -> None:
    orders = [an_order(reason=Reason.HEAT, expires=ON)]
    assert caps_from_orders(orders, ON)[0].because == "heat"
    assert caps_from_orders([an_order()], ON)[0].because == "slow order"


def test_a_curve_can_hold_a_class_four_segment_down() -> None:
    segments = [a_segment(span="12.00-14.50", authorized=ClassOfTrack.FOUR)]
    curves = [a_curve(body="13.10-13.40", elevation="1", degrees=6)]
    caps = caps_from_segments(segments) + caps_from_curves(curves)
    got = profile(Span.parse("12.00-14.50"), caps)
    assert [one.because for one in got] == ["class", "curve", "class"]
    assert got[1].speed == Speed(30)
