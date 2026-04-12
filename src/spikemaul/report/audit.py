"""Holes in the book, which are not the same as problems on the railroad.

Everything else here reports what the records say. This reports where they do
not say anything: track with no segment on it, a defect card at a milepost the
segment list does not cover, welded rail with no destress entry, an open card
nobody has raised work for.

None of these is a defect and every one of them makes another page wrong. A
compliance page cannot report a cycle for track it does not know exists, and
the honest thing is to say so on a page of its own rather than to leave the
gap out of every other page quietly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.model.ids import Ident
from spikemaul.report.layout import Column, Page, Table, count_of
from spikemaul.store.records import Records
from spikemaul.units.span import Span, subtract_all


@dataclass(frozen=True)
class Hole:
    """One thing the book does not say."""

    kind: str
    where: str
    says: str

    def describe(self) -> str:
        """One line for the audit page."""
        return f"{self.kind} {self.where}: {self.says}"


def unsegmented(records: Records, subdivision: Ident) -> list[Hole]:
    """Track on the subdivision that no segment covers.

    Coverage is measured in the numbering rather than on the ground. On a
    subdivision with an overlap equation the repeated quarter mile is one
    range of numbers and two pieces of railroad, and the segment register
    holds one segment per range, so this cannot see the second piece. That is
    a limitation of the segment register rather than of this page, and it is
    written here because this is where somebody would notice it.
    """
    record = records.subdivisions.get(subdivision)
    whole = Span(record.chainage.begin, record.chainage.end)
    covered = [one.span for one in records.segments.on(subdivision)]
    return [Hole("track", str(one), "no segment covers it") for one in subtract_all(whole, covered)]


def cards_off_the_line(records: Records, subdivision: Ident) -> list[Hole]:
    """Open defect cards at a milepost no segment covers."""
    out = []
    for card in records.defects.open_on(subdivision):
        covering = records.segments.covering(subdivision, Span(card.at, card.at.advanced(1)))
        if not covering:
            out.append(Hole("defect", str(card.ident), f"MP {card.at} is on no segment"))
    return out


def curves_off_the_line(records: Records, subdivision: Ident) -> list[Hole]:
    """Curves that run off the end of every segment."""
    out = []
    for curve in records.curves.on(subdivision):
        covering = records.segments.covering(subdivision, curve.span)
        if not covering:
            out.append(Hole("curve", str(curve.ident), f"{curve.span} is on no segment"))
    return out


def welded_without_a_neutral(records: Records, subdivision: Ident, on: date) -> list[Hole]:
    """Welded segments with no destress entry covering them."""
    entries = records.destress.on(subdivision)
    out = []
    for segment in records.segments.on(subdivision):
        if not segment.welded:
            continue
        covering = [one for one in entries if one.covers(segment.span) and one.on <= on]
        if not covering:
            out.append(Hole("segment", str(segment.ident), "is welded and has no destress entry"))
    return out


def cards_with_no_work(records: Records, subdivision: Ident) -> list[Hole]:
    """Open cards nobody has raised a work order against."""
    out = []
    for card in records.defects.open_on(subdivision):
        if not records.work.for_defect(card.ident):
            out.append(Hole("defect", str(card.ident), "is open with no work order against it"))
    return out


def orders_without_a_card(records: Records, subdivision: Ident, on: date) -> list[Hole]:
    """Slow orders on for track condition with no defect card behind them."""
    out = []
    for order in records.orders.in_force(subdivision, on):
        if order.reason.is_planned or order.reason.comes_off_by_itself:
            continue
        if order.defect is None:
            out.append(Hole("order", str(order.ident), "is on with no card behind it"))
    return out


def holes(records: Records, subdivision: Ident, on: date) -> list[Hole]:
    """Everything the book does not say about one subdivision."""
    return [
        *unsegmented(records, subdivision),
        *cards_off_the_line(records, subdivision),
        *curves_off_the_line(records, subdivision),
        *welded_without_a_neutral(records, subdivision, on),
        *cards_with_no_work(records, subdivision),
        *orders_without_a_card(records, subdivision, on),
    ]


def audit_page(records: Records, subdivision: Ident, on: date) -> Page:
    """The audit page for one subdivision."""
    record = records.subdivisions.get(subdivision)
    found = holes(records, subdivision, on)
    page = Page(f"{record.name} records audit {on.isoformat()}")
    page.say(f"{count_of(len(found), 'hole')} in the book")

    page.heading("the book")
    table = Table([Column("kind"), Column("where"), Column("says")])
    for one in found:
        table.add(one.kind, one.where, one.says)
    page.table(table, empty="the book covers the whole subdivision")

    page.heading("the file")
    integrity = records.book.check_integrity()
    keys = records.book.foreign_key_problems()
    if not integrity and not keys:
        page.say("sqlite is happy with the file")
    for line in integrity + keys:
        page.say(line)
    return page
