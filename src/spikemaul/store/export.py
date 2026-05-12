"""Writing the book out as csv, one file per table.

Somebody always wants the book in a spreadsheet, and the honest way to give it
to them is a file per table with the column names on the first line. Nothing
is renamed, nothing is joined and nothing is prettied up, because the moment
this starts making the export readable it starts making decisions that the
reports have already made differently.

The tables are found by asking the book rather than from a list here. A list
here goes stale the first time somebody adds a migration and does not think
about the export, and the failure is a table quietly missing from the copy
somebody is about to do a season's analysis on.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from spikemaul.errors import BookError
from spikemaul.store.book import Book

SKIP = ("schema_migrations",)
"""Tables that are about the book rather than about the railroad."""


@dataclass(frozen=True)
class Written:
    """One table written out."""

    table: str
    where: Path
    rows: int

    def describe(self) -> str:
        """One line for whoever ran it."""
        return f"{self.table}: {self.rows} rows to {self.where.name}"


def tables_of(book: Book) -> list[str]:
    """Every table worth exporting, in name order."""
    return [one for one in book.tables if one not in SKIP]


def write_table(book: Book, table: str, into: Path) -> Written:
    """Write one table out and say how many rows went."""
    rows = book.query(f"SELECT * FROM {table}")
    columns = [one[1] for one in book.query(f"PRAGMA table_info({table})")]
    where = into / f"{table}.csv"
    with where.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row[name] for name in columns])
    return Written(table=table, where=where, rows=len(rows))


def write_all(book: Book, into: Path) -> list[Written]:
    """Write every table out into a directory that has to be empty of csv."""
    into.mkdir(parents=True, exist_ok=True)
    already = sorted(one.name for one in into.glob("*.csv"))
    if already:
        raise BookError(f"{into} already holds {already[0]} and others, empty it first")
    return [write_table(book, one, into) for one in tables_of(book)]
