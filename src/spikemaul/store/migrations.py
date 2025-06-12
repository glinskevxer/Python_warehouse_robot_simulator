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
    Migration(
        number=2,
        name="segments",
        statements=(
            """
            CREATE TABLE segments (
                ident TEXT PRIMARY KEY,
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident),
                begin_post INTEGER NOT NULL,
                end_post INTEGER NOT NULL,
                kind TEXT NOT NULL,
                authorized INTEGER NOT NULL,
                rail_section TEXT NOT NULL,
                rail_laid TEXT NOT NULL,
                welded INTEGER NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                CHECK (end_post > begin_post),
                CHECK (authorized BETWEEN 0 AND 5),
                CHECK (welded IN (0, 1))
            )
            """,
            "CREATE INDEX segments_by_place ON segments (subdivision, begin_post)",
        ),
    ),
    Migration(
        number=3,
        name="curves",
        statements=(
            """
            CREATE TABLE curves (
                ident TEXT PRIMARY KEY,
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident),
                begin_post INTEGER NOT NULL,
                end_post INTEGER NOT NULL,
                curvature INTEGER NOT NULL,
                elevation INTEGER NOT NULL,
                hand TEXT NOT NULL,
                entry_spiral_feet INTEGER NOT NULL DEFAULT 0,
                exit_spiral_feet INTEGER NOT NULL DEFAULT 0,
                CHECK (end_post > begin_post),
                CHECK (curvature > 0),
                CHECK (elevation >= 0),
                CHECK (entry_spiral_feet >= 0 AND exit_spiral_feet >= 0)
            )
            """,
            "CREATE INDEX curves_by_place ON curves (subdivision, begin_post)",
        ),
    ),
    Migration(
        number=4,
        name="turnouts",
        statements=(
            """
            CREATE TABLE turnouts (
                ident TEXT PRIMARY KEY,
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident),
                point_of_switch INTEGER NOT NULL,
                size INTEGER NOT NULL,
                hand TEXT NOT NULL,
                frog TEXT NOT NULL,
                throw TEXT NOT NULL,
                leads_to TEXT NOT NULL DEFAULT '',
                CHECK (point_of_switch >= 0),
                CHECK (size > 0)
            )
            """,
            "CREATE INDEX turnouts_by_place ON turnouts (subdivision, point_of_switch)",
        ),
    ),
    Migration(
        number=5,
        name="crossings and bridges",
        statements=(
            """
            CREATE TABLE crossings (
                ident TEXT PRIMARY KEY,
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident),
                at_post INTEGER NOT NULL,
                road TEXT NOT NULL,
                inventory TEXT NOT NULL UNIQUE,
                surface TEXT NOT NULL,
                warning TEXT NOT NULL,
                public INTEGER NOT NULL DEFAULT 1,
                CHECK (at_post >= 0),
                CHECK (public IN (0, 1))
            )
            """,
            """
            CREATE TABLE bridges (
                ident TEXT PRIMARY KEY,
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident),
                at_post INTEGER NOT NULL,
                kind TEXT NOT NULL,
                spans INTEGER NOT NULL,
                length_feet INTEGER NOT NULL,
                normal_rating INTEGER NOT NULL,
                maximum_rating INTEGER NOT NULL,
                built INTEGER NOT NULL,
                CHECK (spans > 0 AND length_feet > 0),
                CHECK (maximum_rating >= normal_rating)
            )
            """,
            "CREATE INDEX crossings_by_place ON crossings (subdivision, at_post)",
            "CREATE INDEX bridges_by_place ON bridges (subdivision, at_post)",
        ),
    ),
    Migration(
        number=6,
        name="inspections",
        statements=(
            """
            CREATE TABLE inspections (
                ident TEXT PRIMARY KEY,
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident),
                begin_post INTEGER NOT NULL,
                end_post INTEGER NOT NULL,
                on_day TEXT NOT NULL,
                by_person TEXT NOT NULL,
                method TEXT NOT NULL,
                scope TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                CHECK (end_post > begin_post)
            )
            """,
            "CREATE INDEX inspections_by_day ON inspections (subdivision, scope, on_day)",
        ),
    ),
    Migration(
        number=7,
        name="geometry readings",
        statements=(
            """
            CREATE TABLE readings (
                inspection TEXT NOT NULL REFERENCES inspections (ident) ON DELETE CASCADE,
                ordinal INTEGER NOT NULL,
                at_post INTEGER NOT NULL,
                gauge INTEGER NOT NULL,
                crosslevel INTEGER NOT NULL,
                profile INTEGER NOT NULL,
                alignment INTEGER NOT NULL,
                on_curve INTEGER NOT NULL DEFAULT 0,
                designated_elevation INTEGER,
                PRIMARY KEY (inspection, ordinal),
                CHECK (gauge > 0),
                CHECK (profile >= 0 AND alignment >= 0),
                CHECK (on_curve IN (0, 1))
            )
            """,
            "CREATE INDEX readings_by_place ON readings (inspection, at_post)",
        ),
    ),
    Migration(
        number=8,
        name="defects",
        statements=(
            """
            CREATE TABLE defects (
                ident TEXT PRIMARY KEY,
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident),
                at_post INTEGER NOT NULL,
                found_on TEXT NOT NULL,
                found_by TEXT NOT NULL,
                condition TEXT NOT NULL,
                reading TEXT NOT NULL,
                meets INTEGER,
                inspection TEXT REFERENCES inspections (ident),
                repaired_on TEXT,
                note TEXT NOT NULL DEFAULT '',
                CHECK (at_post >= 0),
                CHECK (meets IS NULL OR meets BETWEEN 0 AND 5)
            )
            """,
            "CREATE INDEX defects_open ON defects (subdivision, repaired_on, at_post)",
        ),
    ),
    Migration(
        number=9,
        name="slow orders",
        statements=(
            """
            CREATE TABLE orders (
                ident TEXT PRIMARY KEY,
                subdivision TEXT NOT NULL REFERENCES subdivisions (ident),
                begin_post INTEGER NOT NULL,
                end_post INTEGER NOT NULL,
                speed INTEGER NOT NULL,
                reason TEXT NOT NULL,
                effective TEXT NOT NULL,
                authority TEXT NOT NULL,
                expires TEXT,
                lifted_on TEXT,
                defect TEXT REFERENCES defects (ident),
                note TEXT NOT NULL DEFAULT '',
                CHECK (end_post > begin_post),
                CHECK (speed >= 0),
                CHECK (expires IS NULL OR expires >= effective)
            )
            """,
            "CREATE INDEX orders_in_force ON orders (subdivision, effective, expires)",
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
