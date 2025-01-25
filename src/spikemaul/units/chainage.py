"""Turning mileposts into distance along a line that has been re-surveyed.

Mileposts were painted once and the railroad has been changed since. Where a
line change shortened the route the numbers were not repainted, they were
equated: a sign at one physical spot reads ``MP 61.40 = MP 61.15``, meaning
the milepost numbering goes backwards a quarter of a mile at that point
without any track being added. The quarter mile between 61.15 and 61.40 exists
twice in the numbering and once on the ground.

The consequence is that milepost subtraction is not distance. A slow order
written 61.00 to 62.00 is nine tenths of a mile of railroad, not one mile, and
the milepost 61.20 in the middle of it is two different places. Everything in
this module exists so that the rest of the package can ask a line for the
answer instead of subtracting.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from spikemaul.errors import InputError
from spikemaul.units.milepost import FEET_PER_MILE, HUNDREDTHS_PER_MILE, Milepost
from spikemaul.units.span import Span

_FEET_PER_HUNDREDTH = FEET_PER_MILE / HUNDREDTHS_PER_MILE


@dataclass(frozen=True)
class Equation:
    """One point where the mileposting jumps, written back equals ahead."""

    back: Milepost
    ahead: Milepost

    def __post_init__(self) -> None:
        if self.back == self.ahead:
            raise InputError(f"an equation at {self.back} that changes nothing is not an equation")

    @property
    def kind(self) -> str:
        """``overlap`` when numbers repeat, ``gap`` when numbers are skipped."""
        return "overlap" if self.ahead < self.back else "gap"

    @property
    def hundredths(self) -> int:
        """How much numbering the equation adds, negative when it repeats."""
        return self.ahead.hundredths - self.back.hundredths

    def __str__(self) -> str:
        return f"MP {self.back} = MP {self.ahead}"


@dataclass(frozen=True)
class Stretch:
    """A run of continuous mileposting between two equations."""

    begin: Milepost
    end: Milepost
    origin_feet: int

    @property
    def span(self) -> Span:
        """The stretch as a milepost span."""
        return Span(self.begin, self.end)

    def holds(self, post: Milepost) -> bool:
        """Whether this stretch is where that milepost number lives."""
        return self.begin <= post <= self.end

    def feet_at(self, post: Milepost) -> int:
        """Feet from the start of the line to that post within this stretch."""
        past = post.hundredths - self.begin.hundredths
        return self.origin_feet + round(past * _FEET_PER_HUNDREDTH)


@dataclass(frozen=True)
class Chainage:
    """The mileposting of one line, equations and all.

    Construct it with the first and last milepost of the line and the
    equations in the order they are passed on the ground. Every question about
    distance on that line goes through here.
    """

    begin: Milepost
    end: Milepost
    equations: Sequence[Equation] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.end <= self.begin:
            raise InputError(f"a line runs forward, {self.begin} to {self.end} does not")
        here = self.begin
        for equation in self.equations:
            if equation.back <= here:
                raise InputError(f"equation {equation} is not past the one before it")
            here = equation.ahead
        if self.end <= here:
            raise InputError(f"the line ends at {self.end}, before its last equation")

    @property
    def stretches(self) -> list[Stretch]:
        """The line broken into runs of continuous mileposting."""
        out: list[Stretch] = []
        origin = 0
        begin = self.begin
        for equation in self.equations:
            stretch = Stretch(begin, equation.back, origin)
            out.append(stretch)
            origin = stretch.feet_at(equation.back)
            begin = equation.ahead
        out.append(Stretch(begin, self.end, origin))
        return out

    @property
    def feet(self) -> int:
        """The length of the line on the ground, equations taken out."""
        last = self.stretches[-1]
        return last.feet_at(self.end)

    def occurrences(self, post: Milepost) -> list[int]:
        """Every distance along the line that this milepost number sits at."""
        return [s.feet_at(post) for s in self.stretches if s.holds(post)]

    def position(self, post: Milepost) -> int:
        """Feet from the start of the line to that milepost.

        Refuses a number the equations skipped over, and refuses one that
        occurs twice, because guessing which of the two the foreman meant is
        how a gang ends up at the wrong end of a subdivision.
        """
        found = self.occurrences(post)
        if not found:
            raise InputError(f"MP {post} is not on this line")
        if len(found) > 1:
            raise InputError(f"MP {post} is on this line twice, so it does not name one place")
        return found[0]

    def feet_between(self, first: Milepost, second: Milepost) -> int:
        """Distance on the ground between two mileposts, signed."""
        return self.position(second) - self.position(first)

    def post_at(self, feet: int) -> Milepost:
        """The milepost at a distance along the line."""
        if feet < 0 or feet > self.feet:
            raise InputError(f"{feet} feet is off the end of a line of {self.feet} feet")
        for stretch in self.stretches:
            end = stretch.feet_at(stretch.end)
            if feet <= end:
                over = round((feet - stretch.origin_feet) / _FEET_PER_HUNDREDTH)
                return Milepost(stretch.begin.hundredths + over)
        raise InputError(f"{feet} feet is off the end of a line of {self.feet} feet")

    def pieces(self, span: Span) -> list[Span]:
        """Cut a span at the equations, so each piece is one place on the ground.

        A span that crosses an overlap comes back longer than it was written,
        because the numbering it names is on the ground twice. That is the
        point of asking rather than subtracting.
        """
        if span.begin < self.begin or span.end > self.end:
            raise InputError(f"{span} is not on this line")
        out: list[Span] = []
        for stretch in self.stretches:
            piece = span.intersection(stretch.span)
            if piece is not None:
                out.append(piece)
        if not out:
            raise InputError(f"{span} is not on this line")
        covered = sum(piece.hundredths for piece in out)
        if covered < span.hundredths:
            raise InputError(f"{span} runs through numbering the equations skipped")
        return out

    def true_feet(self, span: Span) -> int:
        """Feet of railroad a span covers, which is not its milepost length."""
        return sum(piece.feet for piece in self.pieces(span))
