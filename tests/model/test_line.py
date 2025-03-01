"""Subdivisions and segments, the two records everything else hangs off."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.line import Segment, Subdivision
from spikemaul.standards.classes import ClassOfTrack, TrackKind, Traffic
from spikemaul.units.chainage import Chainage, Equation
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed


def chainage() -> Chainage:
    return Chainage(
        Milepost.parse("0.00"),
        Milepost.parse("120.00"),
        (Equation(Milepost.parse("61.40"), Milepost.parse("61.15")),),
    )


def subdivision() -> Subdivision:
    return Subdivision(Ident.named(Kind.SUBDIVISION, "PLAINS"), "Plains", chainage())


def segment(**changes: object) -> Segment:
    fields: dict[str, object] = {
        "ident": Ident.named(Kind.SEGMENT, "014"),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "span": Span.parse("12.00-14.50"),
        "kind": TrackKind.MAIN,
        "authorized": ClassOfTrack.THREE,
        "rail_section": "115 RE",
        "rail_laid": date(1998, 6, 1),
    }
    fields.update(changes)
    return Segment(**fields)  # type: ignore[arg-type]


def test_a_subdivision_carries_its_own_mileposting() -> None:
    sub = subdivision()
    assert sub.code == "PLAINS"
    assert sub.span == Span.parse("0.00-120.00")
    assert sub.miles == 120.25
    assert sub.describe() == "PLAINS Plains, 0.00 to 120.00, 120.25 miles"


def test_a_subdivision_knows_which_mileposts_are_on_it() -> None:
    sub = subdivision()
    assert sub.holds(Milepost.parse("43.20"))
    assert not sub.holds(Milepost.parse("130.00"))


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not a subdivision number"):
        Subdivision(Ident.named(Kind.SEGMENT, "014"), "Plains", chainage())
    with pytest.raises(InputError, match="not a segment number"):
        segment(ident=Ident.named(Kind.CURVE, "118"))
    with pytest.raises(InputError, match="not a subdivision number"):
        segment(subdivision=Ident.named(Kind.SEGMENT, "014"))


def test_a_subdivision_has_a_name() -> None:
    with pytest.raises(InputError, match="has a name"):
        Subdivision(Ident.named(Kind.SUBDIVISION, "PLAINS"), "   ", chainage())


def test_a_segment_holds_the_mileposts_inside_it() -> None:
    piece = segment()
    assert piece.holds(Milepost.parse("12.00"))
    assert piece.holds(Milepost.parse("14.49"))
    assert not piece.holds(Milepost.parse("14.50"))
    assert piece.miles == 2.5


def test_a_segments_speed_is_its_class_before_anything_is_put_on_it() -> None:
    assert segment().speed() == Speed(40)
    assert segment().speed(Traffic.PASSENGER) == Speed(60)
    assert segment(authorized=ClassOfTrack.ONE).speed() == Speed(10)


def test_main_track_is_not_carried_as_excepted() -> None:
    with pytest.raises(InputError, match="not carried as excepted"):
        segment(authorized=ClassOfTrack.EXCEPTED)
    yard = segment(kind=TrackKind.YARD, authorized=ClassOfTrack.EXCEPTED)
    assert yard.authorized.is_excepted


def test_a_rail_section_this_railroad_does_not_have_is_refused() -> None:
    with pytest.raises(InputError, match="not a rail section here"):
        segment(rail_section="141 AB")
    assert segment().rail.pounds_per_yard == 115


def test_two_segments_on_the_same_subdivision_may_not_claim_the_same_track() -> None:
    first = segment()
    second = segment(ident=Ident.named(Kind.SEGMENT, "015"), span=Span.parse("14.00-16.00"))
    assert first.overlaps(second)
    apart = segment(ident=Ident.named(Kind.SEGMENT, "016"), span=Span.parse("14.50-16.00"))
    assert not first.overlaps(apart)


def test_segments_on_different_subdivisions_never_overlap() -> None:
    other = segment(subdivision=Ident.named(Kind.SUBDIVISION, "RIVER"))
    assert not segment().overlaps(other)


def test_the_age_of_the_rail_is_counted_from_the_day_it_was_laid() -> None:
    assert segment().rail_age_days(date(1999, 6, 1)) == 365
    with pytest.raises(InputError, match="before the rail was laid"):
        segment().rail_age_days(date(1997, 1, 1))


def test_a_segment_says_itself_in_one_line() -> None:
    assert segment().describe() == "SG-014 PLAINS 12.00 to 14.50 main class 3 115 RE jointed"
    assert segment(welded=True).describe().endswith("cwr")
