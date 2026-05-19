"""The registers and the migrations agree about the columns.

A register declares the columns it reads and writes, and a migration makes the
table. Nothing connects the two except that they were written on the same
afternoon. Rename a column in a new migration and the register keeps its old
spelling until somebody runs the command that uses it, which on a register
like the tie surveys might be a season later.

So this builds a book out of the migrations and asks it. Every column a
register names has to be in the table, every table has to be named by
something, and a table nothing reads is either dead or a register nobody
finished.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Final

from spikemaul.store.book import new_book
from spikemaul.store.crew import Gangs, People
from spikemaul.store.curves import Curves
from spikemaul.store.defects import Defects
from spikemaul.store.inspections import Inspections
from spikemaul.store.migrations import migrate
from spikemaul.store.orders import Orders
from spikemaul.store.register import Register
from spikemaul.store.segments import Segments
from spikemaul.store.structures import Bridges, Crossings
from spikemaul.store.turnouts import Turnouts
from spikemaul.store.work import WorkOrders
from spikemaul.tools.sources import Problem, package_root, run

BUILT_ON: Final = date(2025, 1, 6)

REGISTERS: Final[tuple[type[Register[Any]], ...]] = (
    Segments,
    Curves,
    Turnouts,
    Crossings,
    Bridges,
    Inspections,
    Defects,
    Orders,
    WorkOrders,
    People,
    Gangs,
)
"""Every register that declares its columns."""

READ_ELSEWHERE: Final[frozenset[str]] = frozenset(
    {
        "subdivisions",
        "equations",
        "readings",
        "tie_surveys",
        "tie_lengths",
        "wear_readings",
        "flaw_tests",
        "destress",
        "tonnage",
        "schema_migrations",
    }
)
"""Tables held by a register that writes its own sql, and the migration table."""


def columns_of(table: str) -> list[str]:
    """The columns a table has, out of a book the migrations built."""
    with new_book() as book:
        migrate(book, BUILT_ON)
        return [str(row["name"]) for row in book.query(f"PRAGMA table_info({table})")]


def tables() -> list[str]:
    """Every table a book has."""
    with new_book() as book:
        migrate(book, BUILT_ON)
        return book.tables


def problems() -> list[Problem]:
    """Every column a register names that the book does not have."""
    where = package_root() / "store"
    found = []
    named = set()
    have = set(tables())
    for register in REGISTERS:
        table = register.table
        named.add(table)
        if table not in have:
            found.append(
                Problem(where, 1, f"{register.__name__} reads {table}, which is not there")
            )
            continue
        columns = set(columns_of(table))
        for column in register.columns:
            if column not in columns:
                found.append(
                    Problem(
                        where,
                        1,
                        f"{register.__name__} reads {table}.{column}, which is not there",
                    )
                )
    for table in sorted(have - named - READ_ELSEWHERE):
        found.append(Problem(where, 1, f"{table} is in the book and nothing reads it"))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "schema")


if __name__ == "__main__":
    main()
