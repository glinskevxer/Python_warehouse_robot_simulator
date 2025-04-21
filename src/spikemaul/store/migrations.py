"""The schema, as a list of migrations that only ever gets appended to.

Every change to the shape of the book is a numbered migration with a name,
and the numbers that have been applied are written in the book. That is the
only way a program can open a file somebody else wrote last year and know
whether it understands it.

Nothing here is ever edited once it has been applied anywhere. A migration
that turned out to be wrong is followed by another one that puts it right,
because the file on the roadmaster's machine has already run the first one and
editing it here does not reach into that file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.errors import BookError
from spikemaul.store.book import Book

APPLIED_TABLE = "schema_migrations"


@dataclass(frozen=True)
class Migration:
    """One numbered change to the shape of the book."""

    number: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        number=1,
        name="subdivisions and their equations",
        statements=(
            """
            CREATE TABLE subdivisions (
                ident TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                begin_post INTEGER NOT NULL,
                end_post INTEGER NOT NULL,
                CHECK (end_post > begin_post)
            )
            """,
            """
            CREATE TABLE equations (
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident) ON DELETE CASCADE,
                ordinal INTEGER NOT NULL,
                back_post INTEGER NOT NULL,
                ahead_post INTEGER NOT NULL,
                PRIMARY KEY (subdivision, ordinal),
                CHECK (back_post <> ahead_post)
            )
            """,
        ),
    ),
)


def applied(book: Book) -> list[int]:
    """The migration numbers this book has run, in order."""
    rows = book.query(f"SELECT number FROM {APPLIED_TABLE} ORDER BY number")
    return [int(row["number"]) for row in rows]


def pending(book: Book) -> list[Migration]:
    """The migrations this book has not run yet."""
    done = set(applied(book))
    return [one for one in MIGRATIONS if one.number not in done]


def version(book: Book) -> int:
    """The highest migration the book has run, zero for a new one."""
    return max(applied(book), default=0)


def prepare(book: Book) -> None:
    """Make the table the migration numbers are written in."""
    book.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {APPLIED_TABLE} (
            number INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_on TEXT NOT NULL
        )
        """
    )


def migrate(book: Book, on: date) -> list[Migration]:
    """Run every migration the book has not run, and say which those were.

    The date is passed in rather than read off the clock, because the book is
    a record and everything written into it has to be reproducible.
    """
    prepare(book)
    ran: list[Migration] = []
    for migration in pending(book):
        with book.writing():
            for statement in migration.statements:
                book.execute(statement)
            book.execute(
                f"INSERT INTO {APPLIED_TABLE} (number, name, applied_on) VALUES (?, ?, ?)",
                (migration.number, migration.name, on.isoformat()),
            )
        ran.append(migration)
    return ran


def require_current(book: Book) -> None:
    """Refuse to work with a book that is behind or ahead of this package."""
    here = version(book)
    latest = max(one.number for one in MIGRATIONS)
    if here < latest:
        raise BookError(f"the book is at schema {here} and this package wants {latest}")
    if here > latest:
        raise BookError(f"the book is at schema {here}, which is newer than this package")
