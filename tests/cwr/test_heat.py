"""Heat restrictions, and the three things that make a differential worse."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.cwr.heat import (
    HeatCall,
    band_for,
    call,
    call_from_forecast,
    cap_for_band,
    lapses_on,
)
from spikemaul.cwr.neutral import Destress
from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.curvature import Curvature
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed
from spikemaul.units.temperature import Sky, Temperature

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
GANG = Ident.named(Kind.PERSON, "DKEHOE")
ON = date(2025, 7, 15)


def log() -> list[Destress]:
    return [
        Destress(
            subdivision=PLAINS,
            span=Span.parse("13.00-14.00"),
            on=date(2025, 4, 20),
            neutral=Temperature(95),
            by=GANG,
        )
    ]


def test_rail_below_the_first_band_is_not_restricted() -> None:
    got = call(Temperature(115), Temperature(95))
    assert got.above_neutral == 20
    assert not got.is_restricted
    assert got.speed_with(Speed(40)) == Speed(40)
    assert got.describe() == "rail 115F, 20 above neutral, no restriction"


def test_each_band_brings_a_lower_cap() -> None:
    assert call(Temperature(125), Temperature(95)).cap == Speed(40)
    assert call(Temperature(135), Temperature(95)).cap == Speed(25)
    assert call(Temperature(145), Temperature(95)).cap == Speed(10)


def test_the_band_is_found_off_the_differential() -> None:
    assert band_for(25) == 0
    assert band_for(26) == 1
    assert band_for(45) == 2
    assert band_for(100) == 3
    assert cap_for_band(0) is None
    with pytest.raises(InputError, match="no band below"):
        cap_for_band(-1)


def test_a_sharp_curve_comes_in_one_band() -> None:
    flat = call(Temperature(125), Temperature(95))
    curved = call(Temperature(125), Temperature(95), curve=Curvature.of(3))
    assert flat.cap == Speed(40)
    assert curved.cap == Speed(25)
    assert "curve 3 deg 00 min" in curved.describe()


def test_a_curve_at_the_threshold_does_not_come_in_a_band() -> None:
    got = call(Temperature(125), Temperature(95), curve=Curvature.of(2))
    assert got.cap == Speed(40)


def test_track_surfaced_recently_comes_in_one_band() -> None:
    recent = call(Temperature(125), Temperature(95), surfaced_on=date(2025, 6, 20), on=ON)
    assert recent.cap == Speed(25)
    old = call(Temperature(125), Temperature(95), surfaced_on=date(2025, 1, 20), on=ON)
    assert old.cap == Speed(40)


def test_a_surfacing_date_needs_the_day_to_compare_it_with() -> None:
    with pytest.raises(InputError, match="needs the day"):
        call(Temperature(125), Temperature(95), surfaced_on=date(2025, 6, 20))


def test_both_reasons_stack_into_two_bands() -> None:
    got = call(
        Temperature(125),
        Temperature(95),
        curve=Curvature.of(3),
        surfaced_on=date(2025, 6, 20),
        on=ON,
    )
    assert got.cap == Speed(10)
    assert len(got.reasons) == 2


def test_a_stretch_with_no_neutral_temperature_gets_the_worst_band() -> None:
    got = call(Temperature(100), None)
    assert got.cap == Speed(10)
    assert got.above_neutral is None
    assert "no neutral temperature on record" in got.describe()


def test_the_crew_gets_the_lower_of_the_cap_and_the_timetable() -> None:
    got = call(Temperature(135), Temperature(95))
    assert got.speed_with(Speed(40)) == Speed(25)
    assert got.speed_with(Speed(10)) == Speed(10)


def test_the_morning_call_comes_off_the_forecast_and_the_log() -> None:
    got = call_from_forecast(Temperature(100), Sky.CLEAR, log(), Span.parse("13.20-13.40"), ON)
    assert got.rail == Temperature(130)
    assert got.above_neutral == 35
    assert got.cap == Speed(40)


def test_a_stretch_the_log_does_not_cover_gets_the_worst_band() -> None:
    got = call_from_forecast(Temperature(100), Sky.CLEAR, log(), Span.parse("20.00-21.00"), ON)
    assert got.neutral is None
    assert got.cap == Speed(10)


def test_an_overcast_forecast_puts_the_same_air_in_a_lower_band() -> None:
    clear = call_from_forecast(Temperature(100), Sky.CLEAR, log(), Span.parse("13.20-13.40"), ON)
    overcast = call_from_forecast(
        Temperature(100), Sky.OVERCAST, log(), Span.parse("13.20-13.40"), ON
    )
    assert clear.is_restricted
    assert not overcast.is_restricted


def test_a_heat_order_comes_off_the_day_it_goes_on() -> None:
    assert lapses_on(ON) == ON


def test_a_call_is_a_record_and_carries_its_reasons() -> None:
    got = call(Temperature(125), Temperature(95), curve=Curvature.of(3))
    assert isinstance(got, HeatCall)
    assert got.band == 2
