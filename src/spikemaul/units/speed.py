"""Speeds, and the fact that the lowest one wins.

Every speed the track department deals with is a maximum: the class of track
allows one, a curve allows another, a slow order imposes a third, and what the
crew is given is the smallest. That is the only arithmetic on speeds that
matters, so it is the operation this module is built around.

Speeds are whole miles per hour. Nothing on a track bulletin has ever carried a
fraction, and restricted speed is not a number at all, so it is spelled.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from spikemaul.errors import InputError

RESTRICTED: Final = 0
"""Restricted speed, written as zero because nothing may be slower."""

_TEXT = re.compile(r"^(\d{1,3})\s*(?:mph|m\.p\.h\.)?$", re.IGNORECASE)


@dataclass(frozen=True, order=True)
class Speed:
    """A maximum speed in whole miles per hour."""

    mph: int

    def __post_init__(self) -> None:
        if self.mph < 0:
            raise InputError(f"{self.mph} mph is not a speed")
        if self.mph > 110:
            raise InputError(f"{self.mph} mph is faster than anything this railroad runs")

    @classmethod
    def parse(cls, text: str) -> Speed:
        """Read ``25``, ``25 mph`` or ``restricted`` off a bulletin."""
        raw = text.strip()
        if raw.lower() in {"restricted", "restricted speed", "rs"}:
            return cls(RESTRICTED)
        found = _TEXT.match(raw)
        if found is None:
            raise InputError(f"{text!r} is not a speed")
        return cls(int(found.group(1)))

    @property
    def is_restricted(self) -> bool:
        """Whether this is restricted speed rather than a number."""
        return self.mph == RESTRICTED

    def slower_of(self, other: Speed) -> Speed:
        """The lower of two speeds, which is what a crew is actually given."""
        return self if self.mph <= other.mph else other

    def minutes_over(self, miles: float) -> float:
        """Minutes to cover a distance at this speed, restricted excepted."""
        if self.is_restricted:
            raise InputError("restricted speed does not give a running time")
        return miles / self.mph * 60

    def __str__(self) -> str:
        return "restricted" if self.is_restricted else f"{self.mph} mph"


def slowest(speeds: list[Speed]) -> Speed:
    """The lowest of several speeds. An empty list has no answer and says so."""
    if not speeds:
        raise InputError("no speed applies here, which is not the same as no restriction")
    return min(speeds)


def minutes_lost(normal: Speed, imposed: Speed, miles: float) -> float:
    """Running time a restriction costs over a distance, in minutes.

    Restricted speed has no running time, so a restriction down to it cannot
    be costed in minutes and the caller is told rather than given a number.
    """
    if imposed > normal:
        raise InputError(f"{imposed} is not a restriction below {normal}")
    return imposed.minutes_over(miles) - normal.minutes_over(miles)
