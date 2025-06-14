"""The people and gang registers, and the two list columns they carry."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import BookError, NotFoundError
from spikemaul.model.crew import Craft
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Scope
from spikemaul.store.crew import Gangs, People
from tests.support.books import a_book, a_gang, a_person


def registers() -> tuple[People, Gangs]:
    book = a_book()
    people = People(book)
    people.add(a_person())
    people.add(a_person(initials="DKEHOE", name="D Kehoe", craft=Craft.FOREMAN))
    return people, Gangs(book)


def test_a_person_comes_back_with_their_designation() -> None:
    people, _ = registers()
    got = people.get(Ident.named(Kind.PERSON, "RSTIVERS"))
    assert got == a_person()
    assert got.may_inspect(Scope.TRACK, date(2025, 6, 1))


def test_somebody_with_no_designation_comes_back_with_none() -> None:
    people, _ = registers()
    people.add(
        a_person(
            initials="JHOLT", name="J Holt", craft=Craft.TRACKMAN, scopes=frozenset(), until=None
        )
    )
    got = people.get(Ident.named(Kind.PERSON, "JHOLT"))
    assert got.qualified_for == frozenset()
    assert got.qualified_until is None


def test_the_designated_can_be_asked_for_by_scope_and_by_craft() -> None:
    people, _ = registers()
    assert [one.initials for one in people.qualified_for(Scope.TRACK)] == ["DKEHOE", "RSTIVERS"]
    assert people.qualified_for(Scope.RAIL_FLAW) == []
    assert [one.initials for one in people.of_craft(Craft.FOREMAN)] == ["DKEHOE"]


def test_requalifying_writes_back_over_the_person() -> None:
    people, _ = registers()
    person = people.get(Ident.named(Kind.PERSON, "RSTIVERS"))
    people.update(person.requalified(date(2026, 12, 31)))
    got = people.get(Ident.named(Kind.PERSON, "RSTIVERS"))
    assert got.may_inspect(Scope.TRACK, date(2026, 6, 1))


def test_a_gang_comes_back_with_its_machines_in_order() -> None:
    _, gangs = registers()
    gangs.add(a_gang())
    got = gangs.get(Ident.named(Kind.GANG, "SEC2"))
    assert got == a_gang()
    assert got.machines == ("tamper", "regulator")


def test_a_gang_with_no_machines_comes_back_with_none() -> None:
    _, gangs = registers()
    gangs.add(a_gang(code="SEC1", name="Section 1", machines=()))
    assert gangs.get(Ident.named(Kind.GANG, "SEC1")).machines == ()


def test_gangs_can_be_asked_for_by_machine_and_by_foreman() -> None:
    _, gangs = registers()
    gangs.add(a_gang())
    gangs.add(a_gang(code="SEC1", name="Section 1", machines=("spiker",)))
    assert [one.ident.tail for one in gangs.with_machine("tamper")] == ["SEC2"]
    assert [one.ident.tail for one in gangs.led_by(Ident.named(Kind.PERSON, "DKEHOE"))] == [
        "SEC1",
        "SEC2",
    ]


def test_a_gang_whose_foreman_is_not_on_the_books_is_refused() -> None:
    _, gangs = registers()
    with pytest.raises(BookError, match="FOREIGN KEY"):
        gangs.add(a_gang(foreman="NOBODY"))


def test_a_person_or_gang_that_is_not_there_is_not_invented() -> None:
    people, gangs = registers()
    with pytest.raises(NotFoundError, match="no person"):
        people.get(Ident.named(Kind.PERSON, "NOBODY"))
    with pytest.raises(NotFoundError, match="no gang"):
        gangs.get(Ident.named(Kind.GANG, "SEC9"))


def test_a_scope_this_version_does_not_know_is_refused_on_the_way_out() -> None:
    people, _ = registers()
    people.book.execute(
        "UPDATE people SET qualified_for = ? WHERE ident = ?", ("drone survey", "PN-RSTIVERS")
    )
    with pytest.raises(BookError, match="is not a Scope"):
        people.get(Ident.named(Kind.PERSON, "RSTIVERS"))
