"""Books and records the tests build on, so no test has to spell one out."""

from __future__ import annotations

from datetime import date

from spikemaul.model.curve import Curve
from spikemaul.model.defect import Condition, Defect
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Inspection, Method, Scope
from spikemaul.model.line import Segment, Subdivision
from spikemaul.model.order import Reason, SlowOrder
from spikemaul.model.reading import Reading, Run
from spikemaul.model.side import Hand
from spikemaul.model.structure import (
    Bridge,
    Crossing,
    Structure,
    Surface,
    WarningDevice,
    check_letter,
)
from spikemaul.model.turnout import FrogKind, Throw, Turnout
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.store.book import Book, new_book
from spikemaul.store.migrations import migrate
from spikemaul.units.chainage import Chainage, Equation
from spikemaul.units.curvature import Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed

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


def a_crossing(
    number: str = "244",
    at: str = "22.10",
    road: str = "County Road 14",
    digits: int = 244160,
    subdivision: str = "PLAINS",
) -> Crossing:
    """A public crossing with flashers on it."""
    return Crossing(
        ident=Ident.named(Kind.CROSSING, number),
        subdivision=Ident.named(Kind.SUBDIVISION, subdivision),
        at=Milepost.parse(at),
        road=road,
        inventory=f"{digits:06d}{check_letter(digits)}",
        surface=Surface.RUBBER,
        warning=WarningDevice.FLASHERS,
    )


def a_bridge(
    number: str = "77",
    at: str = "34.80",
    normal: int = 60,
    maximum: int = 72,
    subdivision: str = "PLAINS",
) -> Bridge:
    """A three span deck girder over a creek."""
    return Bridge(
        ident=Ident.named(Kind.BRIDGE, number),
        subdivision=Ident.named(Kind.SUBDIVISION, subdivision),
        at=Milepost.parse(at),
        kind=Structure.DECK_GIRDER,
        spans=3,
        length_feet=186,
        normal_rating=normal,
        maximum_rating=maximum,
        built=1927,
    )


def an_inspection(
    sequence: int = 41,
    on: date = date(2025, 4, 14),
    span: str = "0.00-61.40",
    scope: Scope = Scope.TRACK,
    method: Method = Method.HI_RAIL,
    by: str = "RSTIVERS",
    subdivision: str = "PLAINS",
) -> Inspection:
    """A hi rail trip over the north end of the Plains."""
    return Inspection(
        ident=Ident.numbered(Kind.INSPECTION, on.year, sequence),
        subdivision=Ident.named(Kind.SUBDIVISION, subdivision),
        span=Span.parse(span),
        on=on,
        by=Ident.named(Kind.PERSON, by),
        method=method,
        scope=scope,
    )


def a_reading(post: str, **changes: object) -> Reading:
    """One station of a geometry run, tangent and inside every limit."""
    fields: dict[str, object] = {
        "at": Milepost.parse(post),
        "gauge": Inches.parse("56 5/8"),
        "crosslevel": Inches.parse("1/4"),
        "profile": Inches.parse("1/2"),
        "alignment": Inches.parse("3/8"),
    }
    fields.update(changes)
    return Reading(**fields)  # type: ignore[arg-type]


def a_run(*posts: str, sequence: int = 52, on: date = date(2025, 5, 6)) -> Run:
    """A geometry run over the given stations."""
    return Run(
        inspection=Ident.numbered(Kind.INSPECTION, on.year, sequence),
        subdivision=Ident.named(Kind.SUBDIVISION, "PLAINS"),
        on=on,
        readings=[a_reading(post) for post in posts],
    )


def a_defect(
    sequence: int = 142,
    at: str = "13.22",
    found_on: date = date(2025, 5, 6),
    condition: Condition = Condition.GAUGE,
    reading: str = "57 7/8",
    meets: ClassOfTrack | None = ClassOfTrack.ONE,
    subdivision: str = "PLAINS",
    repaired_on: date | None = None,
    inspection: int | None = None,
) -> Defect:
    """A gauge card off a hi rail trip."""
    return Defect(
        ident=Ident.numbered(Kind.DEFECT, found_on.year, sequence),
        subdivision=Ident.named(Kind.SUBDIVISION, subdivision),
        at=Milepost.parse(at),
        found_on=found_on,
        found_by=Ident.named(Kind.PERSON, "RSTIVERS"),
        condition=condition,
        reading=reading,
        meets=meets,
        repaired_on=repaired_on,
        inspection=(
            None
            if inspection is None
            else Ident.numbered(Kind.INSPECTION, found_on.year, inspection)
        ),
    )


def an_order(
    sequence: int = 31,
    span: str = "13.00-13.60",
    mph: int = 10,
    effective: date = date(2025, 5, 6),
    reason: Reason = Reason.TRACK_CONDITION,
    expires: date | None = None,
    subdivision: str = "PLAINS",
) -> SlowOrder:
    """A ten mile an hour order over the curve at MP 13."""
    return SlowOrder(
        ident=Ident.numbered(Kind.ORDER, effective.year, sequence),
        subdivision=Ident.named(Kind.SUBDIVISION, subdivision),
        span=Span.parse(span),
        speed=Speed(mph),
        reason=reason,
        effective=effective,
        authority="DKEHOE",
        expires=expires,
    )
