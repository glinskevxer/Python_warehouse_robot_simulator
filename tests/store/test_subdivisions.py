"""The subdivision register, which never hands back half a mileposting."""

from __future__ import annotations

import pytest

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.milepost import Milepost
from tests.support.books import a_book, a_plain_subdivision, a_subdivision


def register() -> Subdivisions:
    return Subdivisions(a_book())


def test_a_subdivision_comes_back_the_way_it_went_in() -> None:
    subdivisions = register()
    subdivisions.add(a_subdivision())
    got = subdivisions.get(Ident.named(Kind.SUBDIVISION, "PLAINS"))
    assert got == a_subdivision()
    assert len(got.chainage.equations) == 2


def test_a_subdivision_with_no_equations_comes_back_with_none() -> None:
    subdivisions = register()
    subdivisions.add(a_plain_subdivision())
    got = subdivisions.get(Ident.named(Kind.SUBDIVISION, "RIVER"))
    assert got.chainage.equations == ()
    assert got.miles == 54.0


def test_the_same_subdivision_twice_is_refused() -> None:
    subdivisions = register()
    subdivisions.add(a_subdivision())
    with pytest.raises(DuplicateError, match="already in the book"):
        subdivisions.add(a_subdivision())


def test_a_subdivision_that_is_not_there_is_not_invented() -> None:
    subdivisions = register()
    with pytest.raises(NotFoundError, match="no subdivision"):
        subdivisions.get(Ident.named(Kind.SUBDIVISION, "PLAINS"))
    assert not subdivisions.exists(Ident.named(Kind.SUBDIVISION, "PLAINS"))


def test_every_subdivision_comes_back_in_number_order() -> None:
    subdivisions = register()
    subdivisions.add(a_plain_subdivision())
    subdivisions.add(a_subdivision())
    assert [one.code for one in subdivisions.all()] == ["PLAINS", "RIVER"]
    assert subdivisions.count() == 2


def test_an_empty_book_has_nothing_in_it() -> None:
    subdivisions = register()
    assert subdivisions.all() == []
    assert subdivisions.count() == 0


def test_updating_replaces_the_equations_rather_than_adding_to_them() -> None:
    subdivisions = register()
    subdivisions.add(a_subdivision())
    plain = a_plain_subdivision(code="PLAINS", name="Plains")
    subdivisions.update(plain)
    got = subdivisions.get(Ident.named(Kind.SUBDIVISION, "PLAINS"))
    assert got.chainage.equations == ()
    assert got.chainage.end == Milepost.parse("54.00")


def test_updating_something_that_is_not_there_is_refused() -> None:
    subdivisions = register()
    with pytest.raises(NotFoundError, match="no subdivision"):
        subdivisions.update(a_subdivision())


def test_removing_a_subdivision_takes_its_equations_with_it() -> None:
    subdivisions = register()
    subdivisions.add(a_subdivision())
    subdivisions.remove(Ident.named(Kind.SUBDIVISION, "PLAINS"))
    assert subdivisions.count() == 0
    left = subdivisions.book.query("SELECT * FROM equations")
    assert left == []


def test_removing_something_that_is_not_there_is_refused() -> None:
    subdivisions = register()
    with pytest.raises(NotFoundError, match="no subdivision"):
        subdivisions.remove(Ident.named(Kind.SUBDIVISION, "PLAINS"))


def test_the_equations_come_back_in_the_order_they_are_passed_on_the_ground() -> None:
    subdivisions = register()
    subdivisions.add(a_subdivision())
    got = subdivisions.get(Ident.named(Kind.SUBDIVISION, "PLAINS"))
    assert [str(one.back) for one in got.chainage.equations] == ["61.40", "94.00"]
