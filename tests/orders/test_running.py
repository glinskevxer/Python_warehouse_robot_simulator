"""Running time, and what the restrictions cost in minutes."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.orders.governing import SpeedPiece
from spikemaul.orders.running import (
    cost_of,
    minutes_lost,
    ranked_by_cost,
    running_time,
)
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed


def piece(span: str, mph: int, because: str = "class") -> SpeedPiece:
    return SpeedPiece(Span.parse(span), Speed(mph), because)


def test_running_time_is_the_miles_over_the_speed() -> None:
    got = running_time([piece("12.00-14.00", 40)])
    assert got.minutes == pytest.approx(3.0)
    assert got.is_complete
    assert got.describe() == "3.0 minutes"


def test_the_pieces_of_a_profile_add_up() -> None:
    got = running_time([piece("12.00-13.00", 40), piece("13.00-13.50", 10)])
    assert got.minutes == pytest.approx(1.5 + 3.0)


def test_restricted_speed_is_left_unpriced_rather_than_guessed() -> None:
    got = running_time([piece("12.00-13.00", 40), piece("13.00-13.50", 0)])
    assert got.minutes == pytest.approx(1.5)
    assert got.unpriced_miles == 0.5
    assert not got.is_complete
    assert got.describe().endswith("plus 0.5 miles at restricted speed")


def test_a_profile_at_timetable_speed_costs_nothing() -> None:
    assert minutes_lost([piece("12.00-14.00", 40)], Speed(40)) == pytest.approx(0.0)


def test_a_restriction_costs_the_difference() -> None:
    pieces = [piece("12.00-13.00", 40), piece("13.00-13.50", 10, "slow order")]
    assert minutes_lost(pieces, Speed(40)) == pytest.approx(3.0 - 0.75)


def test_a_piece_faster_than_the_timetable_does_not_earn_time_back() -> None:
    pieces = [piece("12.00-13.00", 60), piece("13.00-13.50", 10)]
    assert minutes_lost(pieces, Speed(40)) == pytest.approx(2.25)


def test_restricted_speed_cannot_be_costed_in_minutes() -> None:
    with pytest.raises(InputError, match="no running time to lose"):
        minutes_lost([piece("12.00-13.00", 0)], Speed(40))
    with pytest.raises(InputError, match="not a speed to compare against"):
        minutes_lost([piece("12.00-13.00", 10)], Speed(0))


def test_the_rule_of_thumb_adds_a_minute_a_restriction() -> None:
    pieces = [piece("12.00-13.00", 40), piece("13.00-13.50", 10)]
    plain = cost_of(pieces, Speed(40), with_approach=False)
    with_approach = cost_of(pieces, Speed(40))
    assert with_approach - plain == pytest.approx(1.0)


def test_two_restrictions_cost_two_minutes_of_rule_of_thumb() -> None:
    pieces = [piece("12.00-12.50", 10), piece("13.00-13.50", 10)]
    assert cost_of(pieces, Speed(40)) - cost_of(pieces, Speed(40), False) == pytest.approx(2.0)


def test_the_restrictions_rank_by_what_they_cost() -> None:
    pieces = [
        piece("12.00-12.50", 25, "slow order"),
        piece("13.00-14.00", 10, "slow order"),
    ]
    ranked = ranked_by_cost(pieces, Speed(40))
    assert [str(one.span) for one, _ in ranked] == ["13.00 to 14.00", "12.00 to 12.50"]
    assert ranked[0][1] > ranked[1][1]


def test_pieces_at_timetable_speed_are_not_ranked_at_all() -> None:
    pieces = [piece("12.00-14.00", 40), piece("14.00-14.50", 10)]
    ranked = ranked_by_cost(pieces, Speed(40))
    assert len(ranked) == 1


def test_a_piece_at_restricted_speed_is_left_out_of_the_ranking() -> None:
    pieces = [piece("12.00-12.50", 0), piece("13.00-14.00", 10)]
    ranked = ranked_by_cost(pieces, Speed(40))
    assert [str(one.span) for one, _ in ranked] == ["13.00 to 14.00"]
