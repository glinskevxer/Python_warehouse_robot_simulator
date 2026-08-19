"""Slow orders, the only thing here a train crew ever sees."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.order import Reason, SlowOrder
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed


def order(**changes: object) -> SlowOrder:
    fields: dict[str, object] = {
        "ident": Ident.numbered(Kind.ORDER, 2025, 31),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "span": Span.parse("13.00-13.60"),
        "speed": Speed(10),
        "reason": Reason.TRACK_CONDITION,
        "effective": date(2025, 5, 6),
        "authority": "DKEHOE",
    }
    fields.update(changes)
    return SlowOrder(**fields)  # type: ignore[arg-type]


def test_a_reason_reads_off_the_bulletin() -> None:
    assert Reason.parse("heat") == Reason.HEAT
    assert Reason.parse(" Tie Renewal ") == Reason.TIE_RENEWAL
    with pytest.raises(InputError, match="is not a reason"):
        Reason.parse("because")


def test_the_reasons_a_gang_puts_on_to_work_under_are_named() -> None:
    assert Reason.SURFACING.is_planned
    assert Reason.TIE_RENEWAL.is_planned
    assert not Reason.WASHOUT.is_planned
    assert not Reason.HEAT.is_planned


def test_an_order_carries_the_authority_it_was_issued_on() -> None:
    with pytest.raises(InputError, match="carries the authority"):
        order(authority="  ")


def test_an_order_that_comes_off_before_it_goes_on_is_refused() -> None:
    with pytest.raises(InputError, match="comes off before it goes on"):
        order(expires=date(2025, 5, 1))
    with pytest.raises(InputError, match="lifted before it went on"):
        order(lifted_on=date(2025, 5, 1))


def test_a_heat_order_carries_the_day_it_lapses() -> None:
    with pytest.raises(RuleError, match="carries the day it lapses"):
        order(reason=Reason.HEAT)
    lapsing = order(reason=Reason.HEAT, expires=date(2025, 5, 6))
    assert lapsing.reason.comes_off_by_itself
    assert not lapsing.is_standing


def test_an_order_with_no_end_date_stands_until_it_is_taken_off() -> None:
    assert order().is_standing
    assert order().in_effect_on(date(2030, 1, 1))


def test_an_order_is_not_in_effect_before_the_day_it_goes_on() -> None:
    assert not order().in_effect_on(date(2025, 5, 5))
    assert order().in_effect_on(date(2025, 5, 6))


def test_an_expiring_order_is_in_effect_through_its_last_day() -> None:
    subject = order(expires=date(2025, 5, 10))
    assert subject.in_effect_on(date(2025, 5, 10))
    assert not subject.in_effect_on(date(2025, 5, 11))


def test_a_lifted_order_is_off_from_the_day_it_was_lifted() -> None:
    subject = order().lifted(date(2025, 5, 8))
    assert subject.in_effect_on(date(2025, 5, 7))
    assert not subject.in_effect_on(date(2025, 5, 8))


def test_an_order_cannot_be_lifted_twice() -> None:
    subject = order().lifted(date(2025, 5, 8))
    with pytest.raises(RuleError, match="already lifted"):
        subject.lifted(date(2025, 5, 9))


def test_the_slower_order_governs_where_two_cover_the_same_track() -> None:
    slow = order()
    slower = order(ident=Ident.numbered(Kind.ORDER, 2025, 32), speed=Speed(25))
    assert slow.governs_over(slower)
    assert not slower.governs_over(slow)


def test_an_order_covers_the_mileposts_inside_it() -> None:
    assert order().covers(Milepost.parse("13.20"))
    assert not order().covers(Milepost.parse("13.60"))


def test_the_days_in_force_count_the_first_day() -> None:
    assert order().days_in_force(date(2025, 5, 6)) == 1
    assert order().days_in_force(date(2025, 5, 10)) == 5
    assert order().days_in_force(date(2025, 5, 1)) == 0


def test_the_days_in_force_stop_at_the_day_it_came_off() -> None:
    lifted = order().lifted(date(2025, 5, 8))
    assert lifted.days_in_force(date(2025, 6, 1)) == 3
    expiring = order(expires=date(2025, 5, 9))
    assert expiring.days_in_force(date(2025, 6, 1)) == 4


def test_a_defect_number_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not a defect number"):
        order(defect=Ident.named(Kind.SEGMENT, "014"))
    assert order(defect=Ident.numbered(Kind.DEFECT, 2025, 142)).defect is not None


def test_the_bulletin_line_says_when_it_comes_off() -> None:
    assert order().describe() == (
        "SO-2025-0031 PLAINS 13.00 to 13.60 10 mph track condition until removed"
    )
    assert order(expires=date(2025, 5, 10)).describe().endswith("until 2025-05-10")


def test_an_order_can_be_given_a_new_day_to_come_off() -> None:
    changed = order().extended(date(2025, 6, 1))
    assert changed.expires == date(2025, 6, 1)
    assert not changed.in_effect_on(date(2025, 6, 2))


def test_an_order_can_be_made_to_stand_until_somebody_lifts_it() -> None:
    changed = order(expires=date(2025, 5, 10)).extended(None)
    assert changed.is_standing


def test_an_order_cannot_be_made_to_come_off_before_it_went_on() -> None:
    with pytest.raises(RuleError, match="cannot come off before"):
        order().extended(date(2025, 5, 1))


def test_an_order_that_was_lifted_cannot_be_extended() -> None:
    lifted = order().lifted(date(2025, 5, 8))
    with pytest.raises(RuleError, match="is finished"):
        lifted.extended(date(2025, 6, 1))
