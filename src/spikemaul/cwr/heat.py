"""Heat restrictions, worked out from how far the rail is above neutral.

The number that matters is the differential: rail temperature minus neutral
temperature. Ninety degree rail on track laid at ninety five is not a problem
and a hundred and twenty degree rail on track laid at seventy is.

Three things make the same differential worse, and all three are in the table
rather than in somebody's judgement on the day. A curve wants to straighten
out, so anything sharper than two degrees comes in one band. Track that has
been surfaced recently has had its ballast disturbed and has not been
consolidated by traffic yet, so it comes in one band as well. And a stretch
with no neutral temperature on record gets the worst band there is, because a
restriction is cheaper than a derailment and the paperwork is the fix.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

from spikemaul.cwr.neutral import Destress, neutral_at
from spikemaul.errors import InputError
from spikemaul.units.curvature import TANGENT, Curvature
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed
from spikemaul.units.temperature import Sky, Temperature, rail_temperature

SHARP_CURVE: Final = Curvature.of(2)
"""Sharper than this and the restriction comes in one band."""

RECENTLY_SURFACED_DAYS: Final = 45
"""Track surfaced inside this many days has not been consolidated."""

BANDS: Final[tuple[tuple[int, Speed | None], ...]] = (
    (25, None),
    (35, Speed(40)),
    (45, Speed(25)),
    (999, Speed(10)),
)
"""Degrees above neutral, and the speed cap that goes with each band."""


def band_for(above_neutral: int) -> int:
    """Which band a differential falls in, counting from zero."""
    for index, (ceiling, _) in enumerate(BANDS):
        if above_neutral <= ceiling:
            return index
    return len(BANDS) - 1


def cap_for_band(band: int) -> Speed | None:
    """The speed cap for a band, or nothing where the band has none."""
    if band < 0:
        raise InputError("there is no band below the first one")
    return BANDS[min(band, len(BANDS) - 1)][1]


@dataclass(frozen=True)
class HeatCall:
    """What the differential and the track say to do this afternoon."""

    rail: Temperature
    neutral: Temperature | None
    above_neutral: int | None
    band: int
    cap: Speed | None
    reasons: tuple[str, ...] = ()

    @property
    def is_restricted(self) -> bool:
        """Whether anything has to go on the bulletin."""
        return self.cap is not None

    def speed_with(self, timetable: Speed) -> Speed:
        """What a crew is given, which is the lower of the cap and the timetable."""
        return timetable if self.cap is None else self.cap.slower_of(timetable)

    def describe(self) -> str:
        """One line for the morning call."""
        if self.neutral is None:
            return (
                f"rail {self.rail}, no neutral temperature on record, {self.cap} until it has one"
            )
        if not self.is_restricted:
            return f"rail {self.rail}, {self.above_neutral} above neutral, no restriction"
        why = "".join(f", {one}" for one in self.reasons)
        return f"rail {self.rail}, {self.above_neutral} above neutral{why}, {self.cap}"


def call(
    rail: Temperature,
    neutral: Temperature | None,
    curve: Curvature = TANGENT,
    surfaced_on: date | None = None,
    on: date | None = None,
) -> HeatCall:
    """Work out the restriction for one stretch on one afternoon."""
    reasons: list[str] = []
    if neutral is None:
        return HeatCall(
            rail=rail,
            neutral=None,
            above_neutral=None,
            band=len(BANDS) - 1,
            cap=cap_for_band(len(BANDS) - 1),
            reasons=("no neutral temperature on record",),
        )
    above = rail.above(neutral)
    band = band_for(above)
    if curve > SHARP_CURVE:
        band += 1
        reasons.append(f"curve {curve}")
    if surfaced_on is not None:
        if on is None:
            raise InputError("a surfacing date needs the day it is being compared with")
        if (on - surfaced_on).days <= RECENTLY_SURFACED_DAYS:
            band += 1
            reasons.append(f"surfaced {surfaced_on.isoformat()}")
    return HeatCall(
        rail=rail,
        neutral=neutral,
        above_neutral=above,
        band=min(band, len(BANDS) - 1),
        cap=cap_for_band(band),
        reasons=tuple(reasons),
    )


def call_from_forecast(
    air: Temperature,
    sky: Sky,
    log: list[Destress],
    span: Span,
    on: date,
    curve: Curvature = TANGENT,
    surfaced_on: date | None = None,
) -> HeatCall:
    """The morning call, worked from the forecast and the destress log."""
    return call(
        rail=rail_temperature(air, sky),
        neutral=neutral_at(log, span, on),
        curve=curve,
        surfaced_on=surfaced_on,
        on=on,
    )


def lapses_on(on: date) -> date:
    """The day a heat order comes off, which is the day it went on."""
    return on + timedelta(days=0)
