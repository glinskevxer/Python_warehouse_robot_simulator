"""Geometry runs, which go into the book whole and come out whole."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Method, Scope
from spikemaul.store.inspections import Inspections
from spikemaul.store.runs import Runs
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.measure import Inches
from tests.support.books import a_book, a_reading, a_run, a_subdivision, an_inspection

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
RUN_ON = date(2025, 5, 6)
NUMBER = Ident.numbered(Kind.INSPECTION, 2025, 52)


def register() -> Runs:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    Inspections(book).add(
        an_inspection(
            sequence=52,
            on=RUN_ON,
            span="12.00-14.00",
            method=Method.GEOMETRY_CAR,
            scope=Scope.TRACK,
        )
    )
    return Runs(book)


def test_a_run_comes_back_the_way_it_went_in() -> None:
    runs = register()
    runs.add(a_run("12.00", "12.01", "12.02"))
    got = runs.get(NUMBER, PLAINS, RUN_ON)
    assert got == a_run("12.00", "12.01", "12.02")


def test_the_readings_come_back_in_the_order_they_were_taken() -> None:
    runs = register()
    runs.add(a_run("12.00", "12.01", "12.02"))
    got = runs.get(NUMBER, PLAINS, RUN_ON)
    assert [str(one.at) for one in got.readings] == ["12.00", "12.01", "12.02"]


def test_a_curve_reading_keeps_its_designated_elevation() -> None:
    runs = register()
    curved = a_reading(
        "12.01",
        on_curve=True,
        crosslevel=Inches.parse("2"),
        designated_elevation=Inches.parse("2"),
    )
    run = a_run("12.00", "12.02")
    whole = type(run)(
        inspection=run.inspection,
        subdivision=run.subdivision,
        on=run.on,
        readings=[run.readings[0], curved, run.readings[1]],
    )
    runs.add(whole)
    got = runs.get(NUMBER, PLAINS, RUN_ON)
    assert got.readings[1].on_curve
    assert got.readings[1].designated_elevation == Inches.parse("2")
    assert got.readings[0].designated_elevation is None


def test_the_same_run_twice_is_refused() -> None:
    runs = register()
    runs.add(a_run("12.00", "12.01"))
    with pytest.raises(DuplicateError, match="geometry run"):
        runs.add(a_run("12.00", "12.01"))


def test_a_run_that_is_not_there_is_not_invented() -> None:
    runs = register()
    with pytest.raises(NotFoundError, match="no geometry run"):
        runs.get(NUMBER, PLAINS, RUN_ON)
    with pytest.raises(NotFoundError, match="no geometry run"):
        runs.remove(NUMBER)


def test_a_run_can_be_taken_out_whole() -> None:
    runs = register()
    runs.add(a_run("12.00", "12.01"))
    assert runs.count_readings(NUMBER) == 2
    runs.remove(NUMBER)
    assert runs.count_readings(NUMBER) == 0
    assert runs.runs_recorded() == []


def test_the_book_says_which_inspections_have_a_run_against_them() -> None:
    runs = register()
    runs.add(a_run("12.00", "12.01"))
    assert runs.runs_recorded() == [NUMBER]


def test_taking_the_inspection_out_takes_the_run_with_it() -> None:
    runs = register()
    runs.add(a_run("12.00", "12.01"))
    Inspections(runs.book).remove(NUMBER)
    assert runs.count_readings(NUMBER) == 0
