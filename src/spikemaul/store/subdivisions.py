"""The subdivision register, and the equations that belong to each one.

A subdivision and its equations are one record as far as anybody outside this
module is concerned. They are two tables because the equations are a list, and
they are written and read together so that a subdivision never comes back with
half its mileposting.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.line import Subdivision
from spikemaul.store.book import Book
from spikemaul.store.codec import decode_ident, decode_post, encode_ident, encode_post
from spikemaul.units.chainage import Chainage, Equation


@dataclass
class Subdivisions:
    """Every subdivision on the railroad."""

    book: Book

    def add(self, subdivision: Subdivision) -> None:
        """Write a new subdivision and its equations."""
        if self.exists(subdivision.ident):
            raise DuplicateError("subdivision", str(subdivision.ident))
        with self.book.writing():
            self.book.execute(
                "INSERT INTO subdivisions (ident, name, begin_post, end_post) VALUES (?,?,?,?)",
                (
                    encode_ident(subdivision.ident),
                    subdivision.name,
                    encode_post(subdivision.chainage.begin),
                    encode_post(subdivision.chainage.end),
                ),
            )
            self._write_equations(subdivision)

    def _write_equations(self, subdivision: Subdivision) -> None:
        self.book.execute(
            "DELETE FROM equations WHERE subdivision = ?", (encode_ident(subdivision.ident),)
        )
        for ordinal, equation in enumerate(subdivision.chainage.equations, start=1):
            self.book.execute(
                "INSERT INTO equations (subdivision, ordinal, back_post, ahead_post) "
                "VALUES (?,?,?,?)",
                (
                    encode_ident(subdivision.ident),
                    ordinal,
                    encode_post(equation.back),
                    encode_post(equation.ahead),
                ),
            )

    def exists(self, ident: Ident) -> bool:
        """Whether that subdivision is in the book."""
        found = self.book.one("SELECT 1 FROM subdivisions WHERE ident = ?", (encode_ident(ident),))
        return found is not None

    def get(self, ident: Ident) -> Subdivision:
        """One subdivision, equations and all."""
        row = self.book.one(
            "SELECT ident, name, begin_post, end_post FROM subdivisions WHERE ident = ?",
            (encode_ident(ident),),
        )
        if row is None:
            raise NotFoundError("subdivision", str(ident))
        return self._read(row["ident"], row["name"], row["begin_post"], row["end_post"])

    def all(self) -> list[Subdivision]:
        """Every subdivision, in number order."""
        rows = self.book.query(
            "SELECT ident, name, begin_post, end_post FROM subdivisions ORDER BY ident"
        )
        return [
            self._read(row["ident"], row["name"], row["begin_post"], row["end_post"])
            for row in rows
        ]

    def _read(self, ident: object, name: object, begin: object, end: object) -> Subdivision:
        number = decode_ident(ident, Kind.SUBDIVISION)
        rows = self.book.query(
            "SELECT back_post, ahead_post FROM equations WHERE subdivision = ? ORDER BY ordinal",
            (encode_ident(number),),
        )
        equations = tuple(
            Equation(decode_post(row["back_post"]), decode_post(row["ahead_post"])) for row in rows
        )
        return Subdivision(
            ident=number,
            name=str(name),
            chainage=Chainage(decode_post(begin), decode_post(end), equations),
        )

    def update(self, subdivision: Subdivision) -> None:
        """Write a subdivision that is already in the book, equations and all."""
        if not self.exists(subdivision.ident):
            raise NotFoundError("subdivision", str(subdivision.ident))
        with self.book.writing():
            self.book.execute(
                "UPDATE subdivisions SET name = ?, begin_post = ?, end_post = ? WHERE ident = ?",
                (
                    subdivision.name,
                    encode_post(subdivision.chainage.begin),
                    encode_post(subdivision.chainage.end),
                    encode_ident(subdivision.ident),
                ),
            )
            self._write_equations(subdivision)

    def remove(self, ident: Ident) -> None:
        """Take a subdivision out, and its equations with it."""
        if not self.exists(ident):
            raise NotFoundError("subdivision", str(ident))
        with self.book.writing():
            self.book.execute("DELETE FROM subdivisions WHERE ident = ?", (encode_ident(ident),))

    def count(self) -> int:
        """How many subdivisions are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM subdivisions")
        return 0 if row is None else int(row["n"])
