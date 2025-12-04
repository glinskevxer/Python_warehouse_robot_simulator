"""Reading a geometry run out of a csv."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from spikemaul.errors import InputError
from spikemaul.loading.runs import read_run
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.measure import Inches

NUMBER = Ident.numbered(Kind.INSPECTION, 2025, 52)
PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
ON = date(2025, 5, 6)

GOOD = """milepost,gauge,crosslevel,profile,alignment
12.00,56 5/8,1/4,1/2,3/8
12.01,56 3/4,-1/4,1/2,3/8
12.02,57 1/8,1/2,3/4,1/2
"""


def written(tmp_path: Path, text: str) -> Path:
    where = tmp_path / "run.csv"
    where.write_text(text, encoding="utf-8")
    return where


def test_a_good_file_reads_into_a_run(tmp_path: Path) -> None:
    run = read_run(written(tmp_path, GOOD), NUMBER, PLAINS, ON)
    assert len(run.readings) == 3
    assert run.readings[0].gauge == Inches.parse("56 5/8")
    assert run.readings[1].crosslevel == Inches.parse("-1/4")
    assert str(run.span) == "12.00 to 12.02"


def test_the_columns_can_be_in_any_order_and_any_case(tmp_path: Path) -> None:
    text = """ALIGNMENT,Milepost,gauge,PROFILE,crosslevel
3/8,12.00,56 5/8,1/2,1/4
3/8,12.01,56 5/8,1/2,1/4
"""
    run = read_run(written(tmp_path, text), NUMBER, PLAINS, ON)
    assert len(run.readings) == 2


def test_a_missing_column_is_named(tmp_path: Path) -> None:
    text = "milepost,gauge,crosslevel,profile\n12.00,56 5/8,1/4,1/2\n"
    with pytest.raises(InputError, match="no alignment column"):
        read_run(written(tmp_path, text), NUMBER, PLAINS, ON)


def test_a_column_this_package_does_not_know_is_refused(tmp_path: Path) -> None:
    text = (
        "milepost,gauge,crosslevel,profile,alignment,twist\n"
        "12.00,56 5/8,1/4,1/2,3/8,1/4\n12.01,56 5/8,1/4,1/2,3/8,1/4\n"
    )
    with pytest.raises(InputError, match="does not know: twist"):
        read_run(written(tmp_path, text), NUMBER, PLAINS, ON)


def test_a_row_that_will_not_parse_names_its_line(tmp_path: Path) -> None:
    text = GOOD.replace("12.01,56 3/4", "12.01,wide")
    with pytest.raises(InputError, match="line 3"):
        read_run(written(tmp_path, text), NUMBER, PLAINS, ON)


def test_a_blank_cell_names_its_column_and_line(tmp_path: Path) -> None:
    text = GOOD.replace("12.01,56 3/4,-1/4", "12.01,,-1/4")
    with pytest.raises(InputError, match="line 3 has nothing in the gauge column"):
        read_run(written(tmp_path, text), NUMBER, PLAINS, ON)


def test_a_file_that_is_not_there_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="there is no file at"):
        read_run(tmp_path / "nothing.csv", NUMBER, PLAINS, ON)


def test_a_file_with_no_headings_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="no heading row"):
        read_run(written(tmp_path, ""), NUMBER, PLAINS, ON)


def test_a_file_with_one_reading_has_nothing_to_compare(tmp_path: Path) -> None:
    text = "milepost,gauge,crosslevel,profile,alignment\n12.00,56 5/8,1/4,1/2,3/8\n"
    with pytest.raises(InputError, match="at least two readings"):
        read_run(written(tmp_path, text), NUMBER, PLAINS, ON)


def test_a_run_that_does_not_read_forward_is_refused(tmp_path: Path) -> None:
    text = GOOD.replace("12.02", "12.00")
    with pytest.raises(InputError, match="a run reads forward"):
        read_run(written(tmp_path, text), NUMBER, PLAINS, ON)
