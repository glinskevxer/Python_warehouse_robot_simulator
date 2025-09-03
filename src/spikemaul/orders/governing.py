"""Building the speed profile: the lowest cap at every foot of railroad.

Every cap is a span and a speed. The profile is what you get by laying them
all on top of each other and reading off the lowest one at each point, and
that is exactly how it is worked out here: collect the boundaries, walk the
pieces between them, take the minimum over the caps that cover each piece.

Two details are worth stating because they are where this goes wrong. Adjacent
pieces with the same speed are merged only when they come from the same
reason, so a bulletin does not print one line covering two miles where the
first mile is a slow order and the second is a curve, which the roadmaster
would have to unpick when the order comes off. And the reason for a piece is
the cap that set it, chosen by a stated order when two caps tie, rather than
whichever one happened to be first in the list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from typing import Final

from spikemaul.errors import InputError
from spikemaul.model.curve import Curve
from spikemaul.model.line import Segment
from spikemaul.model.order import SlowOrder
from spikemaul.standards.classes import Traffic
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span, subtract_all
from spikemaul.units.speed import Speed

PRIORITY: Final[tuple[str, ...]] = ("heat", "slow order", "curve", "class")
"""Which reason is named when two caps tie, most specific first."""


@dataclass(frozen=True)
class Cap:
    """One thing that limits speed over one stretch."""

    span: Span
    speed: Speed
    because: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.because not in PRIORITY:
            named = ", ".join(PRIORITY)
            raise InputError(f"{self.because!r} is not a reason, we know {named}")


@dataclass(frozen=True)
class SpeedPiece:
    """A stretch of railroad with one speed on it, and what set it."""

    span: Span
    speed: Speed
    because: str
    detail: str = ""

    def describe(self) -> str:
        """The line a bulletin prints for this piece."""
        detail = f" {self.detail}" if self.detail else ""
        return f"{self.span} {self.speed} {self.because}{detail}"


def caps_from_segments(segments: list[Segment], traffic: Traffic = Traffic.FREIGHT) -> list[Cap]:
    """The class speed of each segment, which is the floor everything sits on."""
    return [Cap(one.span, one.speed(traffic), "class", str(one.authorized)) for one in segments]


def caps_from_curves(curves: list[Curve]) -> list[Cap]:
    """The speed each curve allows on the elevation it carries."""
    return [Cap(one.span, one.maximum_speed(), "curve", str(one.ident)) for one in curves]


def caps_from_orders(orders: list[SlowOrder], on: date) -> list[Cap]:
    """The slow orders in force on a day, heat orders named as heat."""
    out = []
    for order in orders:
        if not order.in_effect_on(on):
            continue
        because = "heat" if order.reason.comes_off_by_itself else "slow order"
        out.append(Cap(order.span, order.speed, because, str(order.ident)))
    return out


def _boundaries(over: Span, caps: list[Cap]) -> list[Milepost]:
    posts = {over.begin, over.end}
    for cap in caps:
        for post in (cap.span.begin, cap.span.end):
            if over.contains(post) or post == over.end:
                posts.add(post)
    return sorted(posts)


def _lowest(caps: list[Cap]) -> Cap:
    lowest = min(cap.speed for cap in caps)
    tied = [cap for cap in caps if cap.speed == lowest]
    return min(tied, key=lambda cap: PRIORITY.index(cap.because))


def profile(over: Span, caps: list[Cap]) -> list[SpeedPiece]:
    """Read the lowest cap at every foot of a stretch.

    A piece of railroad with no cap covering it at all is left out rather than
    given a speed, because there is no such thing as a default speed here and
    a gap in the profile is a gap in the records.
    """
    posts = _boundaries(over, caps)
    pieces: list[SpeedPiece] = []
    for begin, end in pairwise(posts):
        piece = Span(begin, end)
        covering = [cap for cap in caps if cap.span.covers(piece)]
        if not covering:
            continue
        winner = _lowest(covering)
        last = pieces[-1] if pieces else None
        if (
            last is not None
            and last.span.end == begin
            and last.speed == winner.speed
            and last.because == winner.because
            and last.detail == winner.detail
        ):
            pieces[-1] = SpeedPiece(
                Span(last.span.begin, end), last.speed, last.because, last.detail
            )
            continue
        pieces.append(SpeedPiece(piece, winner.speed, winner.because, winner.detail))
    return pieces


def governing_at(post: Milepost, caps: list[Cap]) -> SpeedPiece | None:
    """The speed at one milepost, or nothing where no cap covers it."""
    covering = [cap for cap in caps if cap.span.contains(post)]
    if not covering:
        return None
    winner = _lowest(covering)
    return SpeedPiece(winner.span, winner.speed, winner.because, winner.detail)


def gaps(over: Span, caps: list[Cap]) -> list[Span]:
    """Stretches with no cap on them at all, which are records that are missing."""
    covered = [piece.span for piece in profile(over, caps)]
    return subtract_all(over, covered)
