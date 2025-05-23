"""What every register does the same way, written once.

Five registers in and the shape had stopped varying: check for the number,
insert the columns in a fixed order, read the row back through the codecs,
list in a stated order, refuse an update or a removal of something that is not
there. The only parts that differ per record are the column list, the row a
record turns into and the record a row turns into.

So those three are what a register declares, and everything else is here. The
registers that need a question of their own, like which segment is at this
milepost, still write their own sql for it. This is not an attempt to make the
interesting queries generic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.book import Book

Record = TypeVar("Record")


@dataclass
class Register(ABC, Generic[Record]):
    """One table, one kind of record, and the five things every register does."""

    book: Book

    table: ClassVar[str]
    columns: ClassVar[tuple[str, ...]]
    kind: ClassVar[Kind]
    ordered_by: ClassVar[str] = "ident"

    @abstractmethod
    def ident_of(self, record: Record) -> Ident:
        """The number the record is filed under."""

    @abstractmethod
    def row_of(self, record: Record) -> tuple[Any, ...]:
        """The record as column values, in the order ``columns`` names them."""

    @abstractmethod
    def record_of(self, row: Any) -> Record:
        """The row back as a record, through the codecs."""

    @property
    def _column_list(self) -> str:
        return ", ".join(self.columns)

    @property
    def _label(self) -> str:
        return self.kind.label

    def add(self, record: Record) -> None:
        """Write a new record, refusing one that is already filed."""
        ident = self.ident_of(record)
        if self.exists(ident):
            raise DuplicateError(self._label, str(ident))
        marks = ", ".join("?" for _ in self.columns)
        self.book.execute(
            f"INSERT INTO {self.table} ({self._column_list}) VALUES ({marks})",
            self.row_of(record),
        )

    def exists(self, ident: Ident) -> bool:
        """Whether that record is in the book."""
        found = self.book.one(
            f"SELECT 1 FROM {self.table} WHERE ident = ?",
            (str(ident),),
        )
        return found is not None

    def get(self, ident: Ident) -> Record:
        """One record by its number."""
        row = self.book.one(
            f"SELECT {self._column_list} FROM {self.table} WHERE ident = ?",
            (str(ident),),
        )
        if row is None:
            raise NotFoundError(self._label, str(ident))
        return self.record_of(row)

    def all(self) -> list[Record]:
        """Every record, in the order the register is read in."""
        rows = self.book.query(
            f"SELECT {self._column_list} FROM {self.table} ORDER BY {self.ordered_by}"
        )
        return [self.record_of(row) for row in rows]

    def where(self, clause: str, values: tuple[Any, ...], order: str | None = None) -> list[Record]:
        """Records matching a clause the register itself wrote."""
        rows = self.book.query(
            f"SELECT {self._column_list} FROM {self.table} WHERE {clause} "
            f"ORDER BY {order or self.ordered_by}",
            values,
        )
        return [self.record_of(row) for row in rows]

    def first(
        self, clause: str, values: tuple[Any, ...], order: str | None = None
    ) -> Record | None:
        """The first record matching a clause, or nothing."""
        found = self.where(clause, values, order)
        return found[0] if found else None

    def update(self, record: Record) -> None:
        """Write a record that is already in the book, over the top of it."""
        ident = self.ident_of(record)
        if not self.exists(ident):
            raise NotFoundError(self._label, str(ident))
        values = self.row_of(record)
        assignments = ", ".join(f"{name} = ?" for name in self.columns[1:])
        self.book.execute(
            f"UPDATE {self.table} SET {assignments} WHERE ident = ?",
            (*values[1:], values[0]),
        )

    def remove(self, ident: Ident) -> None:
        """Take a record out of the book."""
        if not self.exists(ident):
            raise NotFoundError(self._label, str(ident))
        self.book.execute(
            f"DELETE FROM {self.table} WHERE ident = ?",
            (str(ident),),
        )

    def count(self) -> int:
        """How many records are in the book."""
        row = self.book.one(f"SELECT COUNT(*) AS n FROM {self.table}")
        return 0 if row is None else int(row["n"])
