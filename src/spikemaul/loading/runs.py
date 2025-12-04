"""Reading a geometry run out of the csv the contractor sends.

The file is somebody else's and it arrives once a year, so the rules here are
strict on purpose. Every column the run needs has to be present and named, an
unknown column is refused rather than ignored, and a row that will not parse
names its own line number. A file that loads eighty percent of the way is the
worst outcome available: nobody notices, and the twenty percent that did not
load is the part with the exceptions in it.

The file does not know about curves. Marking the run up from the curve
register is a separate step and it happens after this.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident
from spikemaul.model.reading import Reading, Run
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost

REQUIRED = ("milepost", "gauge", "crosslevel", "profile", "alignment")
"""The columns a run file has to carry, whatever order they are in."""


def _cell(row: dict[str, str], name: str, line: int) -> str:
    value = row.get(name)
    if value is None or not value.strip():
        raise InputError(f"line {line} has nothing in the {name} column")
    return value.strip()


def _reading(row: dict[str, str], line: int) -> Reading:
    try:
        return Reading(
            at=Milepost.parse(_cell(row, "milepost", line)),
            gauge=Inches.parse(_cell(row, "gauge", line)),
            crosslevel=Inches.parse(_cell(row, "crosslevel", line)),
            profile=Inches.parse(_cell(row, "profile", line)),
            alignment=Inches.parse(_cell(row, "alignment", line)),
        )
    except InputError as exc:
        raise InputError(f"line {line}: {exc}") from exc


def read_rows(rows: Iterable[dict[str, str]], headings: list[str] | None) -> list[Reading]:
    """Turn parsed csv rows into readings, refusing anything unexpected."""
    if headings is None:
        raise InputError("the file has no heading row")
    named = [one.strip().lower() for one in headings]
    missing = [one for one in REQUIRED if one not in named]
    if missing:
        raise InputError(f"the file has no {missing[0]} column")
    extra = [one for one in named if one not in REQUIRED]
    if extra:
        raise InputError(f"the file has a column this package does not know: {extra[0]}")
    out = []
    for line, row in enumerate(rows, start=2):
        cleaned = {key.strip().lower(): (value or "") for key, value in row.items()}
        out.append(_reading(cleaned, line))
    if len(out) < 2:
        raise InputError("a run is at least two readings, or there is nothing to compare")
    return out


def read_run(path: str | Path, inspection: Ident, subdivision: Ident, on: date) -> Run:
    """Read a whole run out of a csv file."""
    where = Path(path)
    if not where.exists():
        raise InputError(f"there is no file at {where}")
    with where.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        headings = list(reader.fieldnames) if reader.fieldnames else None
        readings = read_rows(reader, headings)
    return Run(inspection=inspection, subdivision=subdivision, on=on, readings=readings)
