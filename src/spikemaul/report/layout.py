"""Laying a page out in fixed width text.

The rules are few and they are all about being readable on paper. Columns are
as wide as their widest cell and no wider. Numbers sit right, words sit left,
because that is how a column of numbers is read. A cell that has nothing in it
prints a dash rather than a blank, because a blank looks like a missing column
rather than a missing value.

Nothing here knows what a defect is. It takes rows of strings and gives back
lines, which is why it can be tested without a book.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from spikemaul.errors import InputError

BLANK = "-"
"""What a cell with nothing in it prints."""

GAP = "  "
"""What separates two columns."""

RULE = "="
"""What a heading is underlined with."""


@dataclass(frozen=True)
class Column:
    """One column of a table, and which way its cells sit."""

    heading: str
    numeric: bool = False


@dataclass
class Table:
    """Rows of strings with headings over them."""

    columns: list[Column]
    rows: list[list[str]] = field(default_factory=list)

    def add(self, *cells: object) -> None:
        """Add a row, turning everything into text and blanks into dashes."""
        if len(cells) != len(self.columns):
            raise InputError(f"a row of {len(cells)} does not fit {len(self.columns)} columns")
        self.rows.append([BLANK if one is None or one == "" else str(one) for one in cells])

    @property
    def is_empty(self) -> bool:
        """Whether the table has no rows in it."""
        return not self.rows

    def widths(self) -> list[int]:
        """How wide each column has to be."""
        out = []
        for index, column in enumerate(self.columns):
            longest = max((len(row[index]) for row in self.rows), default=0)
            out.append(max(len(column.heading), longest))
        return out

    def lines(self) -> list[str]:
        """The table as lines, headings first."""
        widths = self.widths()
        out = [
            GAP.join(
                column.heading.rjust(width) if column.numeric else column.heading.ljust(width)
                for column, width in zip(self.columns, widths, strict=True)
            ).rstrip()
        ]
        for row in self.rows:
            out.append(
                GAP.join(
                    cell.rjust(width) if column.numeric else cell.ljust(width)
                    for cell, column, width in zip(row, self.columns, widths, strict=True)
                ).rstrip()
            )
        return out


@dataclass
class Page:
    """A titled page made of headings, paragraphs and tables."""

    title: str
    body: list[str] = field(default_factory=list)

    def heading(self, text: str) -> None:
        """Start a section."""
        if self.body:
            self.body.append("")
        self.body.append(text)
        self.body.append(RULE * len(text))

    def say(self, text: str) -> None:
        """Put one line on the page."""
        self.body.append(text)

    def table(self, table: Table, empty: str = "nothing") -> None:
        """Put a table on the page, or a line saying it was empty."""
        if table.is_empty:
            self.body.append(empty)
            return
        self.body.extend(table.lines())

    def lines(self) -> list[str]:
        """The whole page as lines, title first."""
        return [self.title, RULE * len(self.title), *self.body]


def render(page: Page) -> str:
    """The page as one string, with a newline at the end."""
    return "\n".join(page.lines()) + "\n"


def count_of(number: int, thing: str) -> str:
    """A count in words, with the plural the office would use."""
    if number == 1:
        return f"1 {thing}"
    return f"{number} {thing}s"
