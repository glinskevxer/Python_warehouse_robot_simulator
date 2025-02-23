"""How often track gets looked at, and what counts as looking at it.

Two numbers govern an inspection cycle and only one of them is obvious. The
first is how often: main track at class 3 gets walked or hi railed once a
week. The second is how close together those inspections may be, because two
inspections on consecutive days do not cover a week, and a foreman running
both on a Monday to clear a backlog has not inspected anything on Thursday.

The frequency depends on the class, which is the point. Track dropped to
class 1 by a defect is inspected on the class 1 cycle from that day, and track
brought back up is inspected on the higher cycle from the day it comes back.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from spikemaul.errors import InputError
from spikemaul.standards.classes import ClassOfTrack, TrackKind


@dataclass(frozen=True)
class Frequency:
    """A number of inspections in a period, with a floor on the gap between."""

    times: int
    period_days: int
    minimum_gap_days: int

    def __post_init__(self) -> None:
        if self.times < 1 or self.period_days < 1:
            raise InputError("a frequency is at least one inspection in at least one day")
        if self.minimum_gap_days >= self.period_days:
            raise InputError("a minimum gap as long as the period allows no inspections")

    @property
    def max_gap_days(self) -> int:
        """The longest a piece of track may go unlooked at."""
        return self.period_days // self.times

    def describe(self) -> str:
        """The frequency in the words the roadmaster uses for it."""
        every = {7: "week", 30: "month", 365: "year"}.get(self.period_days)
        period = every if every else f"{self.period_days} days"
        times = {1: "once", 2: "twice", 3: "three times"}.get(self.times, f"{self.times} times")
        return f"{times} a {period}, at least {self.minimum_gap_days} days apart"


class Weather(Enum):
    """A weather event that puts track under a special inspection."""

    HEAVY_RAIN = "heavy rain"
    FLOOD = "flood"
    HEAT = "heat"
    COLD = "cold"
    EARTHQUAKE = "earthquake"

    @classmethod
    def parse(cls, text: str) -> Weather:
        """Read the event off the dispatcher's message."""
        try:
            return cls(text.strip().lower())
        except ValueError as exc:
            named = ", ".join(event.value for event in cls)
            raise InputError(f"{text!r} is not an event, expected one of {named}") from exc

    @property
    def before_a_train(self) -> bool:
        """Whether track has to be looked at before the next train, not just soon."""
        return self in {Weather.FLOOD, Weather.EARTHQUAKE}


WEEKLY: Final = Frequency(times=1, period_days=7, minimum_gap_days=3)
TWICE_WEEKLY: Final = Frequency(times=2, period_days=7, minimum_gap_days=1)
MONTHLY: Final = Frequency(times=1, period_days=30, minimum_gap_days=7)
TWICE_YEARLY: Final = Frequency(times=2, period_days=365, minimum_gap_days=90)
YEARLY: Final = Frequency(times=1, period_days=365, minimum_gap_days=180)

TURNOUT: Final = MONTHLY
"""Turnouts, switches and crossings, whatever the class of the track."""

JOINT_BARS_IN_CWR: Final = TWICE_YEARLY
"""Walking inspection of joint bars in continuous welded rail territory."""

BRIDGE: Final = YEARLY
"""Structures, which the bridge inspector owns rather than the roadmaster."""

_TRACK: Final[dict[ClassOfTrack, Frequency]] = {
    ClassOfTrack.EXCEPTED: WEEKLY,
    ClassOfTrack.ONE: WEEKLY,
    ClassOfTrack.TWO: WEEKLY,
    ClassOfTrack.THREE: WEEKLY,
    ClassOfTrack.FOUR: TWICE_WEEKLY,
    ClassOfTrack.FIVE: TWICE_WEEKLY,
}


def track_frequency(track_class: ClassOfTrack, kind: TrackKind = TrackKind.MAIN) -> Frequency:
    """How often a piece of track is inspected, given its class and its use."""
    if not kind.is_main:
        return MONTHLY
    return _TRACK[track_class]


def gap_is_legal(frequency: Frequency, days: int) -> bool:
    """Whether a gap between two inspections is inside the cycle."""
    if days < 0:
        raise InputError("one inspection cannot come before the one before it")
    return frequency.minimum_gap_days <= days <= frequency.max_gap_days


def is_overdue(frequency: Frequency, days_since: int) -> bool:
    """Whether track last looked at that many days ago is now late."""
    if days_since < 0:
        raise InputError("track cannot have been inspected in the future")
    return days_since > frequency.max_gap_days
