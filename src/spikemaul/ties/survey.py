"""A walk down a stretch of track, one length at a time.

The survey is what the tie gang works off. It answers three questions and they
want different arithmetic. What class does this stretch hold, which is the
worst length on it. How many ties do we need, which is the sum of what each
length is short by, not the worst one multiplied out. And where do we go, which
is the runs of consecutive bad lengths, because a gang set up to renew ties
does not want a list of forty scattered lengths a mile apart.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.ties import SEGMENT_FEET
from spikemaul.ties.condition import TieLength, class_supported
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span, merge_all


@dataclass(frozen=True)
class TieSurvey:
    """Every thirty nine foot length somebody counted on one walk."""

    subdivision: Ident
    span: Span
    on: date
    lengths: Sequence[TieLength]

    def __post_init__(self) -> None:
        if self.subdivision.kind is not Kind.SUBDIVISION:
            raise InputError(f"{self.subdivision} is not a subdivision number")
        if not self.lengths:
            raise InputError("a survey with no lengths counted is not a survey")
        for earlier, later in zip(self.lengths, self.lengths[1:], strict=False):
            if later.at <= earlier.at:
                raise InputError(
                    f"a survey walks forward, MP {later.at} does not follow MP {earlier.at}"
                )
        for one in self.lengths:
            if not self.span.contains(one.at):
                raise InputError(f"MP {one.at} is outside the stretch that was walked")

    @property
    def counted(self) -> int:
        """How many lengths were counted."""
        return len(self.lengths)

    def class_supported(self) -> ClassOfTrack | None:
        """The class the whole stretch holds, which is its worst length."""
        answers = [class_supported(one) for one in self.lengths]
        if any(one is None for one in answers):
            return None
        return min(one for one in answers if one is not None)

    def worst(self) -> TieLength:
        """The length holding the stretch down."""

        def rank(one: TieLength) -> tuple[int, int]:
            held = class_supported(one)
            return (-1 if held is None else held.rank, one.at.hundredths)

        return min(self.lengths, key=rank)

    def failing(self, held_at: ClassOfTrack) -> list[TieLength]:
        """Every length that does not hold the class the track is held to."""
        out = []
        for one in self.lengths:
            held = class_supported(one)
            if held is None or held < held_at:
                out.append(one)
        return out

    def ties_needed(self, target: ClassOfTrack) -> int:
        """Good ties the stretch is short of holding a class, added up."""
        return sum(one.short_by(target) for one in self.lengths)

    def clusters(self, held_at: ClassOfTrack) -> list[Span]:
        """Runs of failing lengths, merged into stretches a gang can work."""
        failing = self.failing(held_at)
        if not failing:
            return []
        spans = [Span(one.at, one.at.advanced_feet(SEGMENT_FEET)) for one in failing]
        return merge_all(spans)

    def at(self, post: Milepost) -> TieLength | None:
        """The length a milepost falls in, or nothing where none was counted."""
        for one in self.lengths:
            if Span(one.at, one.at.advanced_feet(SEGMENT_FEET)).contains(post):
                return one
        return None

    def describe(self) -> str:
        """One line for the survey list."""
        held = self.class_supported()
        holds = "nothing" if held is None else str(held)
        return (
            f"{self.subdivision.tail} {self.span} {self.on.isoformat()} "
            f"{self.counted} lengths, holds {holds}"
        )
