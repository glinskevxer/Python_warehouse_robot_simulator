"""Rail wear readings and detector runs, neither of which has a number."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Method, Scope
from spikemaul.model.side import Hand
from spikemaul.rail.wear import WearReading
from spikemaul.store.inspections import Inspections
from spikemaul.store.rails import FlawTest, FlawTests, WearReadings
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.tonnage import Tonnage
from tests.support.books import a_book, a_subdivision, an_inspection

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
NUMBER = Ident.numbered(Kind.INSPECTION, 2025, 70)


def registers() -> tuple[WearReadings, FlawTests]:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    Inspections(book).add(
        an_inspection(
            sequence=70,
            on=date(2025, 9, 2),
            span="0.00-61.40",
            method=Method.FLAW_DETECTOR,
            scope=Scope.RAIL_FLAW,
        )
    )
    return WearReadings(book), FlawTests(book)


def reading(at: str = "13.20", on: date = date(2025, 4, 1), **changes: object) -> WearReading:
    fields: dict[str, object] = {
        "at": Milepost.parse(at),
        "hand": Hand.LEFT,
        "rail_section": "115 RE",
        "vertical": Inches.parse("1/4"),
        "gauge_face": Inches.parse("1/4"),
        "measured_on": on,
    }
    fields.update(changes)
    return WearReading(**fields)  # type: ignore[arg-type]


def test_a_wear_reading_comes_back_the_way_it_went_in() -> None:
    wear, _ = registers()
    wear.add(reading(), PLAINS)
    got = wear.at(PLAINS, Milepost.parse("13.20"), Hand.LEFT)
    assert got == [reading()]


def test_the_same_rail_measured_twice_on_a_day_is_refused() -> None:
    wear, _ = registers()
    wear.add(reading(), PLAINS)
    with pytest.raises(DuplicateError, match="wear reading"):
        wear.add(reading(), PLAINS)


def test_the_other_rail_at_the_same_place_is_a_different_reading() -> None:
    wear, _ = registers()
    wear.add(reading(), PLAINS)
    wear.add(reading(hand=Hand.RIGHT), PLAINS)
    assert wear.count() == 2
    assert len(wear.at(PLAINS, Milepost.parse("13.20"), Hand.LEFT)) == 1


def test_readings_of_one_rail_come_back_oldest_first() -> None:
    wear, _ = registers()
    wear.add(reading(on=date(2026, 4, 1), vertical=Inches.parse("3/8")), PLAINS)
    wear.add(reading(), PLAINS)
    got = wear.at(PLAINS, Milepost.parse("13.20"), Hand.LEFT)
    assert [one.measured_on.year for one in got] == [2025, 2026]


def test_a_stretch_gives_the_latest_reading_of_each_rail() -> None:
    wear, _ = registers()
    wear.add(reading(), PLAINS)
    wear.add(reading(on=date(2026, 4, 1), vertical=Inches.parse("3/8")), PLAINS)
    wear.add(reading(at="13.40", hand=Hand.RIGHT), PLAINS)
    got = wear.within(PLAINS, Span.parse("13.00-14.00"), date(2026, 6, 1))
    assert len(got) == 2
    assert got[0].vertical == Inches.parse("3/8")


def test_a_stretch_ignores_readings_after_the_day_asked_about() -> None:
    wear, _ = registers()
    wear.add(reading(), PLAINS)
    wear.add(reading(on=date(2026, 4, 1), vertical=Inches.parse("3/8")), PLAINS)
    got = wear.within(PLAINS, Span.parse("13.00-14.00"), date(2025, 12, 31))
    assert got[0].vertical == Inches.parse("1/4")


def test_a_detector_run_comes_back_the_way_it_went_in() -> None:
    _, tests = registers()
    test = FlawTest(
        inspection=NUMBER,
        subdivision=PLAINS,
        span=Span.parse("0.00-61.40"),
        on=date(2025, 9, 2),
        tonnage_at=Tonnage.of("124.50"),
        found=3,
    )
    tests.add(test)
    assert tests.get(NUMBER) == test
    assert tests.get(NUMBER).describe().endswith("at 124.50 MGT, 3 found")


def test_the_same_detector_run_twice_is_refused() -> None:
    _, tests = registers()
    test = FlawTest(NUMBER, PLAINS, Span.parse("0.00-61.40"), date(2025, 9, 2), Tonnage.of(124))
    tests.add(test)
    with pytest.raises(DuplicateError, match="flaw test"):
        tests.add(test)


def test_a_detector_run_that_is_not_there_is_not_invented() -> None:
    _, tests = registers()
    with pytest.raises(NotFoundError, match="no flaw test"):
        tests.get(NUMBER)


def test_the_last_run_covering_a_stretch_has_to_take_in_all_of_it() -> None:
    _, tests = registers()
    tests.add(FlawTest(NUMBER, PLAINS, Span.parse("0.00-61.40"), date(2025, 9, 2), Tonnage.of(124)))
    found = tests.last_covering(PLAINS, Span.parse("13.00-14.00"), date(2025, 12, 1))
    assert found is not None
    assert found.found == 0
    assert tests.last_covering(PLAINS, Span.parse("13.00-90.00"), date(2025, 12, 1)) is None
    assert tests.last_covering(PLAINS, Span.parse("13.00-14.00"), date(2025, 9, 1)) is None


def test_the_runs_on_a_subdivision_come_back_oldest_first() -> None:
    _, tests = registers()
    tests.add(FlawTest(NUMBER, PLAINS, Span.parse("0.00-61.40"), date(2025, 9, 2), Tonnage.of(124)))
    assert [one.inspection for one in tests.on(PLAINS)] == [NUMBER]
