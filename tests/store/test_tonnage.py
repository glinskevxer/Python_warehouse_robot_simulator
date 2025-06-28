"""The monthly tonnage sheets, kept in the shape they arrive in."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import DuplicateError, InputError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.store.tonnage import MonthlyTonnage, TonnageSheets
from spikemaul.units.tonnage import ZERO, Tonnage
from tests.support.books import a_book, a_plain_subdivision, a_subdivision

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
RIVER = Ident.named(Kind.SUBDIVISION, "RIVER")


def register() -> TonnageSheets:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    return TonnageSheets(book)


def sheet(year: int, month: int, mgt: str, subdivision: Ident = PLAINS) -> MonthlyTonnage:
    return MonthlyTonnage(subdivision, year, month, Tonnage.of(mgt))


def test_a_month_comes_back_the_way_it_went_in() -> None:
    sheets = register()
    sheets.add(sheet(2025, 1, "1.20"))
    got = sheets.get(PLAINS, 2025, 1)
    assert got.tonnage == Tonnage.of("1.20")
    assert got.describe() == "PLAINS 2025-01 1.20 MGT"


def test_a_month_that_is_not_a_month_is_refused() -> None:
    with pytest.raises(InputError, match="is not a month"):
        MonthlyTonnage(PLAINS, 2025, 13, Tonnage.of(1))


def test_posting_the_same_month_twice_is_refused() -> None:
    sheets = register()
    sheets.add(sheet(2025, 1, "1.20"))
    with pytest.raises(DuplicateError, match="tonnage sheet"):
        sheets.add(sheet(2025, 1, "1.30"))


def test_a_month_can_be_corrected_when_the_sheet_is_reissued() -> None:
    sheets = register()
    sheets.add(sheet(2025, 1, "1.20"))
    sheets.correct(sheet(2025, 1, "1.35"))
    assert sheets.get(PLAINS, 2025, 1).tonnage == Tonnage.of("1.35")


def test_correcting_a_month_nobody_posted_is_refused() -> None:
    sheets = register()
    with pytest.raises(NotFoundError, match="no tonnage sheet"):
        sheets.correct(sheet(2025, 1, "1.20"))
    with pytest.raises(NotFoundError, match="no tonnage sheet"):
        sheets.get(PLAINS, 2025, 1)


def test_the_months_come_back_oldest_first() -> None:
    sheets = register()
    sheets.add(sheet(2025, 3, "1.30"))
    sheets.add(sheet(2024, 12, "1.10"))
    sheets.add(sheet(2025, 1, "1.20"))
    assert [(one.year, one.month) for one in sheets.months(PLAINS)] == [
        (2024, 12),
        (2025, 1),
        (2025, 3),
    ]


def test_a_range_counts_the_months_whose_first_day_falls_in_it() -> None:
    sheets = register()
    sheets.add(sheet(2025, 1, "1.20"))
    sheets.add(sheet(2025, 2, "1.10"))
    sheets.add(sheet(2025, 3, "1.30"))
    got = sheets.since(PLAINS, date(2025, 1, 1), date(2025, 2, 28))
    assert got == Tonnage.of("2.30")


def test_a_range_with_no_months_in_it_is_no_tonnage() -> None:
    sheets = register()
    sheets.add(sheet(2025, 1, "1.20"))
    assert sheets.since(PLAINS, date(2025, 6, 1), date(2025, 8, 1)) == ZERO


def test_a_range_that_runs_backwards_is_refused() -> None:
    sheets = register()
    with pytest.raises(InputError, match="runs forward"):
        sheets.since(PLAINS, date(2025, 6, 1), date(2025, 1, 1))


def test_the_subdivisions_do_not_borrow_each_others_tonnage() -> None:
    sheets = register()
    sheets.add(sheet(2025, 1, "1.20"))
    sheets.add(sheet(2025, 1, "0.40", RIVER))
    assert sheets.since(RIVER, date(2025, 1, 1), date(2025, 12, 31)) == Tonnage.of("0.40")


def test_the_latest_month_is_the_last_one_posted() -> None:
    sheets = register()
    assert sheets.latest(PLAINS) is None
    sheets.add(sheet(2025, 1, "1.20"))
    sheets.add(sheet(2025, 2, "1.10"))
    latest = sheets.latest(PLAINS)
    assert latest is not None
    assert latest.month == 2
