"""The railroad itself: subdivisions and the segments they are cut into.

A subdivision is a named piece of railroad with its own mileposting, and it
owns the equations, so every distance question on it goes through its
chainage. A segment is the unit everything else hangs off: one stretch of one
track, held to one class, laid with one rail section, that a foreman can point
at and say what is wrong with it.

Segments do not know what is on them. A curve, a turnout, a defect and a slow
order all carry their own mileposts and are matched to a segment by the span
they fall in, which is a question a register answers rather than a record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.standards.classes import ClassOfTrack, TrackKind, Traffic
from spikemaul.standards.rail import RailSection, section
from spikemaul.units.chainage import Chainage
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed


@dataclass(frozen=True)
class Subdivision:
    """A named piece of railroad with its own mileposting."""

    ident: Ident
    name: str
    chainage: Chainage

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.SUBDIVISION:
            raise InputError(f"{self.ident} is not a subdivision number")
        if not self.name.strip():
            raise InputError("a subdivision has a name")

    @property
    def code(self) -> str:
        """The short code the bulletins print, which is the number's tail."""
        return self.ident.tail

    @property
    def span(self) -> Span:
        """The whole subdivision as a span of mileposts."""
        return Span(self.chainage.begin, self.chainage.end)

    @property
    def miles(self) -> float:
        """Route miles on the ground, equations taken out."""
        return round(self.chainage.feet / 5280, 2)

    def holds(self, post: Milepost) -> bool:
        """Whether that milepost is on this subdivision at all."""
        return bool(self.chainage.occurrences(post))

    def describe(self) -> str:
        """One line for the front of a report."""
        return f"{self.code} {self.name}, {self.span}, {self.miles} miles"


@dataclass(frozen=True)
class Segment:
    """One stretch of one track, held to one class and laid with one rail."""

    ident: Ident
    subdivision: Ident
    span: Span
    kind: TrackKind
    authorized: ClassOfTrack
    rail_section: str
    rail_laid: date
    welded: bool = False
    note: str = ""

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.SEGMENT:
            raise InputError(f"{self.ident} is not a segment number")
        if self.subdivision.kind is not Kind.SUBDIVISION:
            raise InputError(f"{self.subdivision} is not a subdivision number")
        section(self.rail_section)
        if self.authorized.is_excepted and self.kind.is_main:
            raise InputError("main track is not carried as excepted here")

    @property
    def rail(self) -> RailSection:
        """The section as rolled, which the wear limits are read against."""
        return section(self.rail_section)

    @property
    def miles(self) -> float:
        """Length by the mileposts, which is not distance across an equation."""
        return float(self.span.miles)

    def speed(self, traffic: Traffic = Traffic.FREIGHT) -> Speed:
        """The timetable speed, before any restriction is put on it."""
        return self.authorized.speed(traffic)

    def holds(self, post: Milepost) -> bool:
        """Whether that milepost falls on this segment."""
        return self.span.contains(post)

    def overlaps(self, other: Segment) -> bool:
        """Whether two segments claim the same track, which they may not."""
        return self.subdivision == other.subdivision and self.span.overlaps(other.span)

    def rail_age_days(self, on: date) -> int:
        """How long the rail has been in the track, as of a date."""
        if on < self.rail_laid:
            raise InputError(f"{on} is before the rail was laid on {self.rail_laid}")
        return (on - self.rail_laid).days

    def describe(self) -> str:
        """One line for the segment list."""
        welded = "cwr" if self.welded else "jointed"
        return (
            f"{self.ident} {self.subdivision.tail} {self.span} "
            f"{self.kind.value} {self.authorized} {self.rail_section} {welded}"
        )
