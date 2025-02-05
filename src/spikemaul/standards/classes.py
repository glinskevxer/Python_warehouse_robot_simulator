"""Classes of track and the speeds they allow.

A class of track is not a description of how good the track is. It is a
declaration of the limits the track is being held to, and the speed follows
from it. Excepted track is the odd one out: it is a class in the sense that it
has its own limits, but it carries conditions that are not about speed at all,
so it is kept in the same enumeration and asked about separately.

The whole of the rest of the package reads its thresholds out of a table keyed
on one of these, which is why this module sits underneath all of them.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

from spikemaul.errors import InputError
from spikemaul.units.speed import Speed


class Traffic(Enum):
    """What is running over the track, which changes the speed a class gives."""

    FREIGHT = "freight"
    PASSENGER = "passenger"

    @classmethod
    def parse(cls, text: str) -> Traffic:
        """Read the kind of traffic off a form."""
        try:
            return cls(text.strip().lower())
        except ValueError as exc:
            raise InputError(f"{text!r} is not freight or passenger") from exc


class ClassOfTrack(Enum):
    """A class of track, excepted through five."""

    EXCEPTED = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

    @classmethod
    def parse(cls, text: str) -> ClassOfTrack:
        """Read ``3``, ``class 3`` or ``excepted`` off a form or a chart."""
        raw = text.strip().lower().removeprefix("class").strip()
        if raw in {"excepted", "x", "e"}:
            return cls.EXCEPTED
        if raw.isdigit() and 1 <= int(raw) <= 5:
            return cls(int(raw))
        raise InputError(f"{text!r} is not a class of track")

    @property
    def is_excepted(self) -> bool:
        """Whether this is excepted track, which carries its own conditions."""
        return self is ClassOfTrack.EXCEPTED

    @property
    def rank(self) -> int:
        """A number that sorts, with excepted lowest."""
        return self.value

    def speed(self, traffic: Traffic = Traffic.FREIGHT) -> Speed:
        """The fastest that traffic may run on track held to this class."""
        return _SPEEDS[self][traffic]

    def carries(self, traffic: Traffic) -> bool:
        """Whether that traffic may run on this class of track at all."""
        return not (self.is_excepted and traffic is Traffic.PASSENGER)

    def __lt__(self, other: ClassOfTrack) -> bool:
        return self.rank < other.rank

    def __le__(self, other: ClassOfTrack) -> bool:
        return self.rank <= other.rank

    def __gt__(self, other: ClassOfTrack) -> bool:
        return self.rank > other.rank

    def __ge__(self, other: ClassOfTrack) -> bool:
        return self.rank >= other.rank

    def __str__(self) -> str:
        return "excepted" if self.is_excepted else f"class {self.value}"


_SPEEDS: Final[dict[ClassOfTrack, dict[Traffic, Speed]]] = {
    ClassOfTrack.EXCEPTED: {Traffic.FREIGHT: Speed(10), Traffic.PASSENGER: Speed(0)},
    ClassOfTrack.ONE: {Traffic.FREIGHT: Speed(10), Traffic.PASSENGER: Speed(15)},
    ClassOfTrack.TWO: {Traffic.FREIGHT: Speed(25), Traffic.PASSENGER: Speed(30)},
    ClassOfTrack.THREE: {Traffic.FREIGHT: Speed(40), Traffic.PASSENGER: Speed(60)},
    ClassOfTrack.FOUR: {Traffic.FREIGHT: Speed(60), Traffic.PASSENGER: Speed(80)},
    ClassOfTrack.FIVE: {Traffic.FREIGHT: Speed(80), Traffic.PASSENGER: Speed(90)},
}

ALL: Final = tuple(ClassOfTrack)
"""Every class, lowest first, which is the order remedial action walks."""


def speed_limit(track_class: ClassOfTrack, traffic: Traffic = Traffic.FREIGHT) -> Speed:
    """The speed a class allows, refusing traffic the class does not carry."""
    if not track_class.carries(traffic):
        raise InputError(f"{traffic.value} does not run on {track_class}")
    return track_class.speed(traffic)


def class_for_speed(speed: Speed, traffic: Traffic = Traffic.FREIGHT) -> ClassOfTrack:
    """The lowest class that allows a speed, which is the class to hold to."""
    for track_class in ALL:
        if track_class.carries(traffic) and track_class.speed(traffic) >= speed:
            return track_class
    raise InputError(f"no class of track carries {traffic.value} at {speed}")


def classes_at_or_below(track_class: ClassOfTrack) -> tuple[ClassOfTrack, ...]:
    """Every class this one could be dropped to, highest first."""
    return tuple(sorted((one for one in ALL if one <= track_class), reverse=True))
