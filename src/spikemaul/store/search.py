"""One search across every register, because the caller has a number and not
a kind.

Somebody rings up with SO-2025-0031 written on a scrap of paper and does not
know or care that it is a slow order rather than a work order. Making them
choose the right command first is making them answer the question they rang up
to ask.

So this looks in every register for a number that matches, and for text in the
fields somebody would have written a name into. It is a small book and this is
a handful of queries; when it stops being a small book the fix is an index
rather than a different shape here.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.model.ids import Ident, Kind
from spikemaul.store.records import Records


@dataclass(frozen=True)
class Hit:
    """One record a search found."""

    kind: Kind
    ident: Ident
    says: str

    def describe(self) -> str:
        """One line for the search output."""
        return f"{self.kind.label:<12} {self.says}"


def _matches(text: str, *fields: str) -> bool:
    wanted = text.strip().lower()
    return any(wanted in one.lower() for one in fields if one)


def by_number(records: Records, text: str) -> list[Hit]:
    """Everything filed under a number, whatever kind of record it is."""
    raw = text.strip().upper()
    out = []
    for kind, register in (
        (Kind.SUBDIVISION, records.subdivisions),
        (Kind.SEGMENT, records.segments),
        (Kind.CURVE, records.curves),
        (Kind.TURNOUT, records.turnouts),
        (Kind.CROSSING, records.crossings),
        (Kind.BRIDGE, records.bridges),
        (Kind.INSPECTION, records.inspections),
        (Kind.DEFECT, records.defects),
        (Kind.ORDER, records.orders),
        (Kind.WORK, records.work),
        (Kind.PERSON, records.people),
        (Kind.GANG, records.gangs),
    ):
        for record in register.all():
            ident = record.ident
            if raw in str(ident):
                out.append(Hit(kind=kind, ident=ident, says=record.describe()))
    return out


def _text_of(record: object) -> tuple[str, ...]:
    """The fields somebody would have written a name or a note into."""
    return tuple(
        str(getattr(record, name))
        for name in ("name", "road", "inventory", "leads_to", "headquarters", "reading", "note")
        if getattr(record, name, None)
    )


def by_text(records: Records, text: str) -> list[Hit]:
    """Everything with that text written into a name, a road or a note."""
    out = []
    for kind, register in (
        (Kind.SUBDIVISION, records.subdivisions),
        (Kind.CROSSING, records.crossings),
        (Kind.TURNOUT, records.turnouts),
        (Kind.PERSON, records.people),
        (Kind.GANG, records.gangs),
        (Kind.DEFECT, records.defects),
        (Kind.WORK, records.work),
    ):
        for record in register.all():
            if _matches(text, *_text_of(record)):
                out.append(Hit(kind=kind, ident=record.ident, says=record.describe()))
    return out


def find(records: Records, text: str) -> list[Hit]:
    """Everything in the book that matches, numbers first."""
    seen: set[tuple[Kind, str]] = set()
    out = []
    for hit in by_number(records, text) + by_text(records, text):
        key = (hit.kind, str(hit.ident))
        if key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return out
