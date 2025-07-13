"""What class a piece of track actually holds, and what to do about it.

This is where the two halves meet. A run is read against the class the track
is being held to, which says what is outside the limits. The findings then say
what class the track does hold, which is the lowest class any single reading
supports. That second number is the one the remedial action is worked out
from.

The two directions could in principle chase each other. Reading against a
lower class gives fewer findings, and fewer findings could suggest a higher
class. They do not chase each other here, and the reason is worth stating: the
class a reading supports is a property of the reading and the limit tables
alone, and does not depend on the class the run was read against. So the walk
settles on the first step, and there is a test that says so rather than a
comment claiming it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from spikemaul.geometry.finding import Finding, findings
from spikemaul.geometry.warp import warp_findings
from spikemaul.model.reading import Run
from spikemaul.standards.classes import ALL, ClassOfTrack
from spikemaul.standards.geometry import WARP_WINDOW_FEET
from spikemaul.standards.remedial import NO_ACTION, RemedialAction, decide
from spikemaul.units.span import Span


@dataclass(frozen=True)
class Assessment:
    """What a run says about a piece of track held to a class."""

    span: Span
    held_at: ClassOfTrack
    supports: ClassOfTrack | None
    exceptions: list[Finding] = field(default_factory=list)

    @property
    def is_clear(self) -> bool:
        """Whether the track meets the class it is being held to."""
        return not self.exceptions

    @property
    def action(self) -> RemedialAction:
        """What the rule says to do, worked out from what the track supports."""
        if self.is_clear:
            return NO_ACTION
        return decide(self.held_at, self.supports)

    @property
    def worst(self) -> Finding | None:
        """The finding that is holding the class down."""
        if not self.exceptions:
            return None
        return min(
            self.exceptions,
            key=lambda one: (one.meets.rank if one.meets is not None else -1, one.at.hundredths),
        )

    def describe(self) -> str:
        """One line for the roadmaster's page."""
        if self.is_clear:
            return f"{self.span} meets {self.held_at}, {len(self.exceptions)} exceptions"
        supports = "nothing" if self.supports is None else str(self.supports)
        return (
            f"{self.span} held at {self.held_at}, {len(self.exceptions)} exceptions, "
            f"supports {supports}"
        )


def supported_class(run: Run, window_feet: int = WARP_WINDOW_FEET) -> ClassOfTrack | None:
    """The highest class every reading in the run meets.

    Read against class five, so every channel is judged against the tightest
    row and nothing is let through for being inside a looser one.
    """
    top = ClassOfTrack.FIVE
    every = findings(run, top) + warp_findings(run, top, window_feet)
    if not every:
        return top
    if any(one.meets is None for one in every):
        return None
    return min(one.meets for one in every if one.meets is not None)


def assess(run: Run, held_at: ClassOfTrack, window_feet: int = WARP_WINDOW_FEET) -> Assessment:
    """Read a run against the class the track is held to."""
    exceptions = findings(run, held_at) + warp_findings(run, held_at, window_feet)
    exceptions.sort(key=lambda one: (one.at.hundredths, one.condition.value))
    return Assessment(
        span=run.span,
        held_at=held_at,
        supports=supported_class(run, window_feet),
        exceptions=exceptions,
    )


def downgrade_path(
    run: Run, held_at: ClassOfTrack, window_feet: int = WARP_WINDOW_FEET
) -> list[ClassOfTrack]:
    """The classes the track walks down through, held first, supported last.

    A track that meets its class has a path of one. A track that supports
    nothing has a path ending at excepted with the assessment still failing,
    which is the caller's clue that no speed makes this legal.
    """
    supports = supported_class(run, window_feet)
    if supports is not None and supports >= held_at:
        return [held_at]
    walk = [one for one in ALL if one <= held_at]
    if supports is None:
        return sorted(walk, reverse=True)
    return sorted([one for one in walk if one >= supports], reverse=True)
