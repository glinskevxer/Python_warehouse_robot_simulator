"""The segment register, asked what is at a milepost all day long."""

from __future__ import annotations

import pytest

from spikemaul.errors import BookError, DuplicateError, NotFoundError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.segments import Segments
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from tests.support.books import a_book, a_plain_subdivision, a_segment, a_subdivision

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
RIVER = Ident.named(Kind.SUBDIVISION, "RIVER")


def register() -> Segments:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    return Segments(book)


def test_a_segment_comes_back_the_way_it_went_in() -> None:
    segments = register()
    segments.add(a_segment())
    assert segments.get(Ident.named(Kind.SEGMENT, "014")) == a_segment()


def test_the_same_segment_twice_is_refused() -> None:
    segments = register()
    segments.add(a_segment())
    with pytest.raises(DuplicateError, match="already in the book"):
        segments.add(a_segment())


def test_a_segment_lying_on_top_of_another_is_refused() -> None:
    segments = register()
    segments.add(a_segment())
    with pytest.raises(RuleError, match="lies on top of SG-014"):
        segments.add(a_segment(number="015", span="14.00-16.00"))


def test_a_segment_that_only_touches_another_is_allowed() -> None:
    segments = register()
    segments.add(a_segment())
    segments.add(a_segment(number="015", span="14.50-16.00"))
    assert segments.count() == 2


def test_the_same_mileposts_on_another_subdivision_are_allowed() -> None:
    segments = register()
    segments.add(a_segment())
    segments.add(a_segment(number="115", subdivision="RIVER"))
    assert len(segments.on(RIVER)) == 1


def test_a_segment_that_is_not_there_is_not_invented() -> None:
    segments = register()
    with pytest.raises(NotFoundError, match="no segment"):
        segments.get(Ident.named(Kind.SEGMENT, "014"))


def test_the_segment_at_a_milepost_is_the_one_that_holds_it() -> None:
    segments = register()
    segments.add(a_segment())
    segments.add(a_segment(number="015", span="14.50-16.00"))
    assert segments.at(PLAINS, Milepost.parse("13.00")).ident.tail == "014"
    assert segments.at(PLAINS, Milepost.parse("14.50")).ident.tail == "015"


def test_a_milepost_with_no_segment_on_it_is_not_invented() -> None:
    segments = register()
    segments.add(a_segment())
    with pytest.raises(NotFoundError, match="no segment at"):
        segments.at(PLAINS, Milepost.parse("40.00"))


def test_the_segments_covering_a_stretch_come_back_in_order() -> None:
    segments = register()
    segments.add(a_segment(number="013", span="10.00-12.00"))
    segments.add(a_segment())
    segments.add(a_segment(number="015", span="14.50-16.00"))
    got = segments.covering(PLAINS, Span.parse("11.00-15.00"))
    assert [one.ident.tail for one in got] == ["013", "014", "015"]


def test_a_stretch_that_only_touches_a_segment_does_not_cover_it() -> None:
    segments = register()
    segments.add(a_segment())
    assert segments.covering(PLAINS, Span.parse("14.50-16.00")) == []


def test_every_segment_comes_back_in_subdivision_and_milepost_order() -> None:
    segments = register()
    segments.add(a_segment(number="115", subdivision="RIVER"))
    segments.add(a_segment(number="015", span="14.50-16.00"))
    segments.add(a_segment())
    assert [one.ident.tail for one in segments.all()] == ["014", "015", "115"]


def test_a_segment_can_be_written_over() -> None:
    segments = register()
    segments.add(a_segment())
    segments.update(a_segment(authorized=ClassOfTrack.ONE, welded=True))
    got = segments.get(Ident.named(Kind.SEGMENT, "014"))
    assert got.authorized == ClassOfTrack.ONE
    assert got.welded


def test_updating_or_removing_something_that_is_not_there_is_refused() -> None:
    segments = register()
    with pytest.raises(NotFoundError, match="no segment"):
        segments.update(a_segment())
    with pytest.raises(NotFoundError, match="no segment"):
        segments.remove(Ident.named(Kind.SEGMENT, "014"))


def test_a_segment_can_be_taken_out() -> None:
    segments = register()
    segments.add(a_segment())
    segments.remove(Ident.named(Kind.SEGMENT, "014"))
    assert segments.count() == 0


def test_a_segment_on_a_subdivision_that_is_not_there_is_refused() -> None:
    segments = register()
    with pytest.raises(BookError, match="FOREIGN KEY"):
        segments.add(a_segment(subdivision="NOWHERE"))
