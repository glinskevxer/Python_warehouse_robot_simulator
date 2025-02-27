"""What the rule says to do once a condition is known.

The shape of every remedial action is the same. A condition is measured, the
highest class it meets is worked out, and that is compared with the class the
track is being held to. If the condition meets the class, there is nothing to
do. If it meets a lower one, the track runs at the lower one until it is
fixed. If it meets nothing at all, the track comes out of service, and no
speed is slow enough to make that untrue.

Deadlines are the part that gets mishandled. Before the next train, this
shift, thirty days and by the next inspection are four different clocks, and
turning one into another to make a tidy report is how a defect that had to be
fixed before a train ends up on a list of things due in October.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from spikemaul.errors import InputError, RuleError
from spikemaul.standards.classes import ClassOfTrack


class Clock(Enum):
    """The unit a deadline is counted in. They are not interchangeable."""

    TRAINS = "trains"
    SHIFTS = "shifts"
    DAYS = "days"
    INSPECTIONS = "inspections"

    @property
    def is_calendar(self) -> bool:
        """Whether this clock can be turned into a date on its own."""
        return self is Clock.DAYS


@dataclass(frozen=True, order=True)
class Deadline:
    """How long there is, in the unit the rule counts in."""

    clock: Clock
    count: int

    def __post_init__(self) -> None:
        if self.count < 0:
            raise InputError("a deadline does not run backwards")

    @classmethod
    def before_next_train(cls) -> Deadline:
        """No trains may pass over it until it is fixed."""
        return cls(Clock.TRAINS, 0)

    @classmethod
    def days(cls, count: int) -> Deadline:
        """A deadline on the calendar."""
        return cls(Clock.DAYS, count)

    @classmethod
    def by_next_inspection(cls) -> Deadline:
        """Fixed by the time somebody next walks it."""
        return cls(Clock.INSPECTIONS, 1)

    def comparable_to(self, other: Deadline) -> bool:
        """Whether two deadlines are counted in the same thing."""
        return self.clock is other.clock

    def sooner_of(self, other: Deadline) -> Deadline:
        """The tighter of two deadlines on the same clock.

        Two deadlines on different clocks have no sooner one, and inventing an
        answer is the mistake this refuses to make.
        """
        if not self.comparable_to(other):
            raise RuleError(
                f"a deadline in {self.clock.value} does not compare with one in {other.clock.value}"
            )
        return self if self.count <= other.count else other

    def describe(self) -> str:
        """The deadline in the words the defect card carries."""
        if self.clock is Clock.TRAINS and self.count == 0:
            return "before the next train"
        if self.clock is Clock.INSPECTIONS and self.count == 1:
            return "by the next inspection"
        return f"within {self.count} {self.clock.value}"


class Remedy(Enum):
    """What is being done about a condition."""

    NONE = "none"
    RESTRICT = "restrict"
    REPAIR = "repair"
    OUT_OF_SERVICE = "out of service"

    @property
    def rank(self) -> int:
        """How serious this is, which is how a list of them sorts."""
        return {
            Remedy.NONE: 0,
            Remedy.REPAIR: 1,
            Remedy.RESTRICT: 2,
            Remedy.OUT_OF_SERVICE: 3,
        }[self]


REPAIR_WINDOW_DAYS: Final = 30
"""How long a condition that only cost speed may be left, once restricted."""


@dataclass(frozen=True)
class RemedialAction:
    """The remedy, the class the track may run at, and by when."""

    remedy: Remedy
    hold_at: ClassOfTrack | None
    deadline: Deadline | None

    @property
    def takes_track_out(self) -> bool:
        """Whether this stops trains rather than slowing them."""
        return self.remedy is Remedy.OUT_OF_SERVICE

    def describe(self) -> str:
        """One line for the defect card and the exception log."""
        if self.remedy is Remedy.NONE:
            return "no action, the condition meets the class"
        if self.takes_track_out:
            return "out of service until repaired"
        by = f", {self.deadline.describe()}" if self.deadline else ""
        return f"hold at {self.hold_at}{by}"


NO_ACTION: Final = RemedialAction(Remedy.NONE, None, None)


def decide(held_at: ClassOfTrack, meets: ClassOfTrack | None) -> RemedialAction:
    """Work out the remedial action for a condition on a piece of track.

    ``meets`` is the highest class the condition itself satisfies, which is
    what the limit tables answer, and ``None`` means it satisfies none of
    them.
    """
    if meets is None:
        return RemedialAction(Remedy.OUT_OF_SERVICE, None, Deadline.before_next_train())
    if meets >= held_at:
        return NO_ACTION
    return RemedialAction(Remedy.RESTRICT, meets, Deadline.days(REPAIR_WINDOW_DAYS))


def most_severe(actions: list[RemedialAction]) -> RemedialAction:
    """The action that governs when several apply to the same track."""
    if not actions:
        return NO_ACTION
    worst = max(action.remedy.rank for action in actions)
    candidates = [action for action in actions if action.remedy.rank == worst]
    holds = [one.hold_at for one in candidates if one.hold_at is not None]
    if not holds:
        return candidates[0]
    lowest = min(holds)
    return next(one for one in candidates if one.hold_at == lowest)
