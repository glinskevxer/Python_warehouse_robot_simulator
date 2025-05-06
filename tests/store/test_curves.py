"""The curve register, whose milepost search has to take in the spirals."""

from __future__ import annotations

import pytest

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.curves import Curves
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from tests.support.books import a_book, a_curve, a_plain_subdivision, a_subdivision

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")


def register() -> Curves:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    return Curves(book)


def test_a_curve_comes_back_the_way_it_went_in() -> None:
    curves = register()
    curves.add(a_curve())
    assert curves.get(Ident.named(Kind.CURVE, "118")) == a_curve()


def test_the_same_curve_twice_is_refused() -> None:
    curves = register()
    curves.add(a_curve())
    with pytest.raises(DuplicateError, match="already in the book"):
        curves.add(a_curve())


def test_a_curve_that_is_not_there_is_not_invented() -> None:
    curves = register()
    with pytest.raises(NotFoundError, match="no curve"):
        curves.get(Ident.named(Kind.CURVE, "118"))


def test_a_milepost_in_the_body_finds_the_curve() -> None:
    curves = register()
    curves.add(a_curve())
    found = curves.at(PLAINS, Milepost.parse("13.20"))
    assert found is not None
    assert found.ident.tail == "118"


def test_a_milepost_in_a_spiral_finds_the_curve_too() -> None:
    curves = register()
    curves.add(a_curve())
    assert curves.at(PLAINS, Milepost.parse("13.07")) is not None
    assert curves.at(PLAINS, Milepost.parse("13.43")) is not None


def test_a_milepost_outside_the_spirals_finds_nothing() -> None:
    curves = register()
    curves.add(a_curve())
    assert curves.at(PLAINS, Milepost.parse("13.05")) is None
    assert curves.at(PLAINS, Milepost.parse("20.00")) is None


def test_a_curve_on_another_subdivision_is_not_found_here() -> None:
    curves = register()
    curves.add(a_curve(subdivision="RIVER"))
    assert curves.at(PLAINS, Milepost.parse("13.20")) is None


def test_the_curves_covering_a_stretch_include_ones_only_their_spirals_reach() -> None:
    curves = register()
    curves.add(a_curve())
    got = curves.covering(PLAINS, Span.parse("13.05-13.08"))
    assert [one.ident.tail for one in got] == ["118"]
    assert curves.covering(PLAINS, Span.parse("13.00-13.05")) == []


def test_every_curve_comes_back_in_order() -> None:
    curves = register()
    curves.add(a_curve(number="120", body="18.00-18.30"))
    curves.add(a_curve())
    curves.add(a_curve(number="220", subdivision="RIVER", body="4.00-4.20"))
    assert [one.ident.tail for one in curves.all()] == ["118", "120", "220"]
    assert [one.ident.tail for one in curves.on(PLAINS)] == ["118", "120"]


def test_a_curve_can_be_written_over() -> None:
    curves = register()
    curves.add(a_curve())
    curves.update(a_curve(elevation="3", spirals=300))
    got = curves.get(Ident.named(Kind.CURVE, "118"))
    assert got.elevation == Inches.parse("3")
    assert got.entry_spiral_feet == 300


def test_updating_or_removing_something_that_is_not_there_is_refused() -> None:
    curves = register()
    with pytest.raises(NotFoundError, match="no curve"):
        curves.update(a_curve())
    with pytest.raises(NotFoundError, match="no curve"):
        curves.remove(Ident.named(Kind.CURVE, "118"))


def test_a_curve_can_be_taken_out() -> None:
    curves = register()
    curves.add(a_curve())
    curves.remove(Ident.named(Kind.CURVE, "118"))
    assert curves.count() == 0
