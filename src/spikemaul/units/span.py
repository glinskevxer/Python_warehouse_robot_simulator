"""A stretch of railroad between two mileposts on one track.

Almost everything the track department records is a stretch rather than a
point: a segment, a slow order, a tie gang's day, a piece of curve. The
awkward part is not the arithmetic, it is deciding what happens at the ends. A
span here is half open, ``[begin, end)``, so two spans that meet at MP 44.00
do not both contain it and a bulletin printed from them does not say the same
foot of railroad twice.

Zero length spans are refused. A point on the railroad is a
:class:`~spikemaul.units.milepost.Milepost` and calling it a span of no length
loses that distinction the first time somebody sorts a list.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from spikemaul.errors import InputError
from spikemaul.units.milepost import FEET_PER_MILE, HUNDREDTHS_PER_MILE, Milepost

_TEXT = re.compile(r"^(?:MP\s*)?(.+?)\s*(?:--|-|to)\s*(?:MP\s*)?(.+?)$", re.IGNORECASE)


@dataclass(frozen=True, order=True)
class Span:
    """Half open stretch of one track, from ``begin`` up to but not ``end``."""

    begin: Milepost
    end: Milepost

    def __post_init__(self) -> None:
        if self.end <= self.begin:
            raise InputError(f"a span has to run forward, {self.begin} to {self.end} does not")

    @classmethod
    def of(cls, begin: str, end: str) -> Span:
        """Build from two mileposts written the way the paperwork writes them."""
        return cls(Milepost.parse(begin), Milepost.parse(end))

    @classmethod
    def parse(cls, text: str) -> Span:
        """Read ``43.20-44.10`` or ``MP 43.20 to MP 44.10`` off a form."""
        found = _TEXT.match(text.strip())
        if found is None:
            raise InputError(f"{text!r} is not a milepost range")
        return cls(Milepost.parse(found.group(1)), Milepost.parse(found.group(2)))

    @property
    def hundredths(self) -> int:
        """Length in hundredths of a mile."""
        return self.end.hundredths - self.begin.hundredths

    @property
    def miles(self) -> Decimal:
        """Nominal length in miles, ignoring any equation point inside."""
        return Decimal(self.hundredths) / HUNDREDTHS_PER_MILE

    @property
    def feet(self) -> int:
        """Nominal length in feet, ignoring any equation point inside."""
        return round(self.hundredths * FEET_PER_MILE / HUNDREDTHS_PER_MILE)

    def contains(self, post: Milepost) -> bool:
        """Whether the milepost falls in this span, the far end excluded."""
        return self.begin <= post < self.end

    def covers(self, other: Span) -> bool:
        """Whether every foot of ``other`` is inside this span."""
        return self.begin <= other.begin and other.end <= self.end

    def overlaps(self, other: Span) -> bool:
        """Whether the two share any railroad at all."""
        return self.begin < other.end and other.begin < self.end

    def touches(self, other: Span) -> bool:
        """Whether the two are adjacent, one ending where the other begins."""
        return self.end == other.begin or other.end == self.begin

    def intersection(self, other: Span) -> Span | None:
        """The railroad both spans cover, or ``None`` if they do not meet."""
        begin = max(self.begin, other.begin)
        end = min(self.end, other.end)
        if end <= begin:
            return None
        return Span(begin, end)

    def merged(self, other: Span) -> Span:
        """One span covering both, refusing a gap that would be invented."""
        if not (self.overlaps(other) or self.touches(other)):
            raise InputError(f"{self} and {other} do not meet, merging them would invent track")
        return Span(min(self.begin, other.begin), max(self.end, other.end))

    def split_at(self, post: Milepost) -> tuple[Span, Span]:
        """The two pieces either side of a milepost inside this span."""
        if not (self.begin < post < self.end):
            raise InputError(f"{post} is not inside {self}, so it does not split it")
        return Span(self.begin, post), Span(post, self.end)

    def without(self, other: Span) -> list[Span]:
        """What is left of this span once ``other`` is taken out of it."""
        cut = self.intersection(other)
        if cut is None:
            return [self]
        left = [Span(self.begin, cut.begin)] if self.begin < cut.begin else []
        right = [Span(cut.end, self.end)] if cut.end < self.end else []
        return left + right

    def __str__(self) -> str:
        return f"{self.begin} to {self.end}"


def merge_all(spans: Iterable[Span]) -> list[Span]:
    """Sort and coalesce spans, so overlapping and touching pieces become one."""
    ordered = sorted(spans)
    if not ordered:
        return []
    out = [ordered[0]]
    for span in ordered[1:]:
        if out[-1].overlaps(span) or out[-1].touches(span):
            out[-1] = out[-1].merged(span)
        else:
            out.append(span)
    return out


def subtract_all(span: Span, taken: Iterable[Span]) -> list[Span]:
    """What is left of ``span`` once every span in ``taken`` is removed."""
    left = [span]
    for cut in merge_all(taken):
        after: list[Span] = []
        for piece in left:
            after.extend(piece.without(cut))
        left = after
    return left


def total_miles(spans: Sequence[Span]) -> Decimal:
    """Nominal miles covered by the spans, counting overlap once."""
    return sum((span.miles for span in merge_all(spans)), Decimal(0))
