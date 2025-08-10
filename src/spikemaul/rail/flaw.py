"""Where a piece of rail stands in its flaw testing cycle.

The cycle has two clocks and the earlier one governs. Tonnage is the real
measure, because a detail fracture grows under wheels rather than under the
calendar, and the calendar backstop is there for the stretch that carries
almost nothing and would otherwise never come due.

The lower classes have no requirement at all, and the status says so rather
than reporting a cycle nobody has to keep. That distinction matters on this
railroad, where dropping a branch to class 1 for the winter takes it off the
detector's list, and putting it back to class 3 in the spring puts it back on
with the tonnage it accumulated in between still counting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from spikemaul.errors import InputError
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.rail import FlawCycle, flaw_cycle
from spikemaul.units.tonnage import ZERO, Tonnage


@dataclass(frozen=True)
class CycleStatus:
    """Where one stretch stands against its flaw testing cycle."""

    track_class: ClassOfTrack
    cycle: FlawCycle
    last_tested: date | None
    tonnage_since: Tonnage
    days_since: int | None

    @property
    def is_required(self) -> bool:
        """Whether this class has a flaw testing requirement at all."""
        return self.cycle.is_required

    @property
    def never_tested(self) -> bool:
        """Whether nobody has run a detector over this stretch."""
        return self.last_tested is None

    @property
    def tonnage_left(self) -> Tonnage | None:
        """Tonnage before the cycle comes due, or nothing where none applies."""
        if self.cycle.tonnage is None:
            return None
        if self.tonnage_since >= self.cycle.tonnage:
            return ZERO
        return self.cycle.tonnage - self.tonnage_since

    @property
    def days_left(self) -> int | None:
        """Days before the calendar backstop, or nothing where none applies."""
        if self.cycle.days is None or self.days_since is None:
            return None
        return max(self.cycle.days - self.days_since, 0)

    @property
    def is_due(self) -> bool:
        """Whether either clock has run out, which is what puts it on the list."""
        if not self.is_required:
            return False
        if self.never_tested:
            return True
        by_tonnage = self.tonnage_left is not None and self.tonnage_left == ZERO
        by_days = self.days_left is not None and self.days_left == 0
        return by_tonnage or by_days

    @property
    def governing(self) -> str:
        """Which clock brings it due first, in the words the report prints."""
        if not self.is_required:
            return "no requirement"
        if self.never_tested:
            return "never tested"
        if self.tonnage_left is not None and self.tonnage_left == ZERO:
            return "tonnage"
        if self.days_left is not None and self.days_left == 0:
            return "calendar"
        return "tonnage" if self._tonnage_runs_out_first() else "calendar"

    def _tonnage_runs_out_first(self) -> bool:
        if self.tonnage_left is None:
            return False
        if self.days_left is None:
            return True
        return self.tonnage_left.hundredths <= self.days_left

    def describe(self) -> str:
        """One line for the flaw testing page."""
        if not self.is_required:
            return f"{self.track_class}, no flaw testing requirement"
        if self.never_tested:
            return f"{self.track_class}, never tested"
        state = "due" if self.is_due else "in cycle"
        return (
            f"{self.track_class}, last tested {self.last_tested}, "
            f"{self.tonnage_since} since, {state} on {self.governing}"
        )


def status(
    track_class: ClassOfTrack,
    on: date,
    last_tested: date | None = None,
    tonnage_since: Tonnage = ZERO,
) -> CycleStatus:
    """Work out where a stretch stands as of a day."""
    if last_tested is not None and last_tested > on:
        raise InputError(f"{last_tested} is after {on}, so it is not a last test")
    days_since = None if last_tested is None else (on - last_tested).days
    return CycleStatus(
        track_class=track_class,
        cycle=flaw_cycle(track_class),
        last_tested=last_tested,
        tonnage_since=tonnage_since,
        days_since=days_since,
    )


def due_date(track_class: ClassOfTrack, last_tested: date) -> date | None:
    """The calendar backstop for a stretch, where it has one."""
    cycle = flaw_cycle(track_class)
    if cycle.days is None:
        return None
    return last_tested + timedelta(days=cycle.days)
