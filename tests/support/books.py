"""Books and records the tests build on, so no test has to spell one out."""

from __future__ import annotations

from datetime import date

from spikemaul.model.curve import Curve
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.line import Segment, Subdivision
from spikemaul.model.side import Hand
from spikemaul.model.turnout import FrogKind, Throw, Turnout
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.store.book import Book, new_book
from spikemaul.store.migrations import migrate
from spikemaul.units.chainage import Chainage, Equation
from spikemaul.units.curvature import Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

OPENED_ON = date(2025, 1, 6)


def a_book() -> Book:
    """A book in memory with the schema on it."""
    book = new_book()
    migrate(book, OPENED_ON)
    return book


def a_chainage() -> Chainage:
    """The Plains subdivision mileposting, with both of its equations."""
    return Chainage(
        Milepost.parse("0.00"),
        Milepost.parse("120.00"),
        (
            Equation(Milepost.parse("61.40"), Milepost.parse("61.15")),
            Equation(Milepost.parse("94.00"), Milepost.parse("94.60")),
        ),
    )


def a_subdivision(code: str = "PLAINS", name: str = "Plains") -> Subdivision:
    """A subdivision record, equations and all."""
    return Subdivision(Ident.named(Kind.SUBDIVISION, code), name, a_chainage())


def a_plain_subdivision(code: str = "RIVER", name: str = "River") -> Subdivision:
    """A subdivision whose mileposting was never equated."""
    return Subdivision(
        Ident.named(Kind.SUBDIVISION, code),
        name,
        Chainage(Milepost.parse("0.00"), Milepost.parse("54.00")),
    )


def a_segment(
    number: str = "014",
    span: str = "12.00-14.50",
    authorized: ClassOfTrack = ClassOfTrack.THREE,
    kind: TrackKind = TrackKind.MAIN,
    subdivision: str = "PLAINS",
    welded: bool = False,
) -> Segment:
    """A segment record, on the Plains subdivision unless told otherwise."""
    return Segment(
        ident=Ident.named(Kind.SEGMENT, number),
        subdivision=Ident.named(Kind.SUBDIVISION, subdivision),
        span=Span.parse(span),
        kind=kind,
        authorized=authorized,
        rail_section="115 RE",
        rail_laid=date(1998, 6, 1),
        welded=welded,
    )


def a_curve(
    number: str = "118",
    body: str = "13.10-13.40",
    degrees: int = 3,
    elevation: str = "2",
    subdivision: str = "PLAINS",
    spirals: int = 200,
) -> Curve:
    """A curve record with a spiral at each end."""
    return Curve(
        ident=Ident.named(Kind.CURVE, number),
        subdivision=Ident.named(Kind.SUBDIVISION, subdivision),
        body=Span.parse(body),
        curvature=Curvature.of(degrees),
        elevation=Inches.parse(elevation),
        hand=Hand.LEFT,
        entry_spiral_feet=spirals,
        exit_spiral_feet=spirals,
    )


def a_turnout(
    number: str = "31",
    at: str = "18.60",
    size: int = 10,
    subdivision: str = "PLAINS",
    leads_to: str = "Bartels elevator",
) -> Turnout:
    """A hand throw turnout off the main."""
    return Turnout(
        ident=Ident.named(Kind.TURNOUT, number),
        subdivision=Ident.named(Kind.SUBDIVISION, subdivision),
        point_of_switch=Milepost.parse(at),
        size=size,
        hand=Hand.RIGHT,
        frog=FrogKind.RIGID,
        throw=Throw.HAND,
        leads_to=leads_to,
    )
