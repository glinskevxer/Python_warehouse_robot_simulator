"""Reading a tie survey out of the sheet the inspector fills in.

The sheet is a printed form with a line per thirty nine foot length, and it is
typed up as a csv at the end of the week. The columns are the ones on the
form, and the same rule applies as to the geometry file: it loads whole or not
at all, and a line that will not parse says which line it is.

The curvature column is on the form because the tie count on a curve is
different, and the inspector is standing there with the track chart. Working
it out later from the curve register is possible and it is not what the form
does, so the column stays.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident
from spikemaul.ties.condition import TieLength
from spikemaul.ties.survey import TieSurvey
from spikemaul.units.curvature import TANGENT, Curvature
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

REQUIRED = ("milepost", "total", "good", "run")
"""The columns a tie sheet has to carry."""

OPTIONAL = ("joints", "supported", "degrees")
"""Columns the form has that a short sheet may leave out."""


def _whole(row: dict[str, str], name: str, line: int, default: int | None = None) -> int:
    raw = (row.get(name) or "").strip()
    if not raw:
        if default is None:
            raise InputError(f"line {line} has nothing in the {name} column")
        return default
    if not raw.isdigit():
        raise InputError(f"line {line}: {raw!r} is not a whole number of {name}")
    return int(raw)


def _length(row: dict[str, str], line: int) -> TieLength:
    degrees = (row.get("degrees") or "").strip()
    try:
        return TieLength(
            at=Milepost.parse((row.get("milepost") or "").strip()),
            total=_whole(row, "total", line),
            good=_whole(row, "good", line),
            longest_run=_whole(row, "run", line),
            joints=_whole(row, "joints", line, 0),
            joints_supported=_whole(row, "supported", line, 0),
            curve=Curvature.parse(degrees) if degrees else TANGENT,
        )
    except InputError as exc:
        raise InputError(f"line {line}: {exc}") from exc


def read_rows(rows: Iterable[dict[str, str]], headings: list[str] | None) -> list[TieLength]:
    """Turn parsed csv rows into lengths, refusing anything unexpected."""
    if headings is None:
        raise InputError("the sheet has no heading row")
    named = [one.strip().lower() for one in headings]
    missing = [one for one in REQUIRED if one not in named]
    if missing:
        raise InputError(f"the sheet has no {missing[0]} column")
    extra = [one for one in named if one not in REQUIRED + OPTIONAL]
    if extra:
        raise InputError(f"the sheet has a column this package does not know: {extra[0]}")
    out = []
    for line, row in enumerate(rows, start=2):
        cleaned = {key.strip().lower(): (value or "") for key, value in row.items()}
        out.append(_length(cleaned, line))
    if not out:
        raise InputError("a survey with no lengths counted is not a survey")
    return out


def read_survey(path: str | Path, subdivision: Ident, span: Span, on: date) -> TieSurvey:
    """Read a whole tie survey out of a csv sheet."""
    where = Path(path)
    if not where.exists():
        raise InputError(f"there is no file at {where}")
    with where.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        headings = list(reader.fieldnames) if reader.fieldnames else None
        lengths = read_rows(reader, headings)
    return TieSurvey(subdivision=subdivision, span=span, on=on, lengths=lengths)
