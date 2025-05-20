"""The crossing and bridge registers, both shared with somebody outside."""

from __future__ import annotations

import pytest

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.structures import Bridges, Crossings
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.span import Span
from tests.support.books import (
    a_book,
    a_bridge,
    a_crossing,
    a_plain_subdivision,
    a_subdivision,
)

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")


def registers() -> tuple[Crossings, Bridges]:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    return Crossings(book), Bridges(book)


def test_a_crossing_comes_back_the_way_it_went_in() -> None:
    crossings, _ = registers()
    crossings.add(a_crossing())
    assert crossings.get(Ident.named(Kind.CROSSING, "244")) == a_crossing()


def test_the_same_inventory_number_twice_is_a_copying_mistake() -> None:
    crossings, _ = registers()
    crossings.add(a_crossing())
    with pytest.raises(DuplicateError, match="crossing inventory number"):
        crossings.add(a_crossing(number="245", at="30.00"))


def test_a_crossing_is_found_by_the_number_the_road_quotes() -> None:
    crossings, _ = registers()
    crossings.add(a_crossing())
    found = crossings.by_inventory(a_crossing().inventory.lower())
    assert found is not None
    assert found.road == "County Road 14"
    assert crossings.by_inventory("000000A") is None


def test_crossings_come_back_in_milepost_order_inside_a_stretch() -> None:
    crossings, _ = registers()
    crossings.add(a_crossing(number="246", at="26.00", digits=244180))
    crossings.add(a_crossing())
    got = crossings.within(PLAINS, Span.parse("22.00-27.00"))
    assert [one.ident.tail for one in got] == ["244", "246"]
    assert crossings.within(PLAINS, Span.parse("10.00-20.00")) == []


def test_a_crossing_that_is_not_there_is_not_invented() -> None:
    crossings, _ = registers()
    with pytest.raises(NotFoundError, match="no crossing"):
        crossings.get(Ident.named(Kind.CROSSING, "244"))
    with pytest.raises(NotFoundError, match="no crossing"):
        crossings.remove(Ident.named(Kind.CROSSING, "244"))


def test_a_crossing_can_be_taken_out() -> None:
    crossings, _ = registers()
    crossings.add(a_crossing())
    assert crossings.count() == 1
    crossings.remove(Ident.named(Kind.CROSSING, "244"))
    assert crossings.all() == []


def test_a_bridge_comes_back_the_way_it_went_in() -> None:
    _, bridges = registers()
    bridges.add(a_bridge())
    assert bridges.get(Ident.named(Kind.BRIDGE, "77")) == a_bridge()


def test_the_same_bridge_twice_is_refused() -> None:
    _, bridges = registers()
    bridges.add(a_bridge())
    with pytest.raises(DuplicateError, match="already in the book"):
        bridges.add(a_bridge())


def test_the_weakest_bridge_is_the_one_that_sets_the_line() -> None:
    _, bridges = registers()
    bridges.add(a_bridge())
    bridges.add(a_bridge(number="78", at="40.00", normal=40, maximum=50))
    weakest = bridges.weakest()
    assert weakest is not None
    assert weakest.ident.tail == "78"


def test_a_book_with_no_bridges_has_no_weakest_one() -> None:
    _, bridges = registers()
    assert bridges.weakest() is None
    assert bridges.count() == 0


def test_bridges_come_back_in_order_and_inside_a_stretch() -> None:
    _, bridges = registers()
    bridges.add(a_bridge(number="78", at="40.00"))
    bridges.add(a_bridge())
    assert [one.ident.tail for one in bridges.all()] == ["77", "78"]
    got = bridges.within(PLAINS, Span.parse("34.00-38.00"))
    assert [one.ident.tail for one in got] == ["77"]


def test_a_bridge_that_is_not_there_is_not_invented() -> None:
    _, bridges = registers()
    with pytest.raises(NotFoundError, match="no bridge"):
        bridges.get(Ident.named(Kind.BRIDGE, "77"))
    with pytest.raises(NotFoundError, match="no bridge"):
        bridges.remove(Ident.named(Kind.BRIDGE, "77"))


def test_a_bridge_can_be_taken_out() -> None:
    _, bridges = registers()
    bridges.add(a_bridge())
    bridges.remove(Ident.named(Kind.BRIDGE, "77"))
    assert bridges.count() == 0
