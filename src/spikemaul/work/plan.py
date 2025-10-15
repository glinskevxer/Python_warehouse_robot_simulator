"""The gang's week, built out of what has to be done and what they get through.

Two things decide the plan and neither is negotiable by the office. The order
is set by the deadlines, because work that stops a train comes before work
that is due in October however far away it is. The amount is set by what a
gang gets through in a day, which is a production rate per kind of work and is
the closest thing this package has to an estimate.

Some work divides across days and some does not. Four hundred ties is four
days at a hundred a day. One turnout is one day or it is not started, because
a turnout half rebuilt at quitting time is a turnout nothing runs over
tonight. That distinction is on the kind of work rather than in the planner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Final

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident
from spikemaul.model.work import WorkKind
from spikemaul.work.needs import Need

PRODUCTION: Final[dict[WorkKind, int]] = {
    WorkKind.TIE_RENEWAL: 120,
    WorkKind.SURFACING: 2000,
    WorkKind.RAIL_CHANGE: 400,
    WorkKind.JOINT_REPAIR: 6,
    WorkKind.GAUGE_REPAIR: 800,
    WorkKind.CROSSING_REBUILD: 1,
    WorkKind.DRAINAGE: 600,
    WorkKind.VEGETATION: 4,
    WorkKind.TURNOUT_REPAIR: 1,
}
"""What one section gang gets through in a working day, in the work's own unit."""

INDIVISIBLE: Final[frozenset[WorkKind]] = frozenset(
    {WorkKind.CROSSING_REBUILD, WorkKind.TURNOUT_REPAIR}
)
"""Work that is either done in a day or not started."""


@dataclass(frozen=True)
class Task:
    """A piece of a need, put on one day."""

    need: Need
    quantity: int

    def describe(self) -> str:
        """One line for the day sheet."""
        return f"{self.need.span} {self.need.kind.value} {self.quantity} {self.need.unit}"


@dataclass
class Day:
    """One working day for one gang."""

    on: date
    tasks: list[Task] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """Whether the day has nothing on it."""
        return not self.tasks

    def describe(self) -> str:
        """One line for the week's plan."""
        if self.is_empty:
            return f"{self.on.isoformat()} nothing planned"
        return f"{self.on.isoformat()} " + "; ".join(one.describe() for one in self.tasks)


@dataclass
class Plan:
    """A week of days for one gang, and what would not fit."""

    gang: Ident
    days: list[Day]
    unplaced: list[Need] = field(default_factory=list)

    @property
    def is_full(self) -> bool:
        """Whether every day has something on it."""
        return all(not one.is_empty for one in self.days)

    def lines(self) -> list[str]:
        """The plan as the lines that get printed."""
        out = [f"{self.gang.tail} plan"]
        out.extend(one.describe() for one in self.days)
        for need in self.unplaced:
            out.append(f"not planned: {need.describe()}")
        return out


def working_days(first: date, count: int) -> list[date]:
    """The next so many working days, weekends left out."""
    if count < 1:
        raise InputError("a plan covers at least one day")
    out: list[date] = []
    day = first
    while len(out) < count:
        if day.weekday() < 5:
            out.append(day)
        day += timedelta(days=1)
    return out


def rate_for(kind: WorkKind) -> int:
    """How much of that work a gang gets through in a day."""
    return PRODUCTION[kind]


def plan_week(gang: Ident, needs: list[Need], first: date, days: int = 5) -> Plan:
    """Fill a gang's days from the needs, in the order the needs came in.

    The needs are taken as given rather than resorted, because the sorting is
    the deadline question and it has already been answered by whoever built
    the list.
    """
    plan = Plan(gang=gang, days=[Day(on=one) for one in working_days(first, days)])
    left = [(need, need.quantity) for need in needs]
    for day in plan.days:
        capacity: dict[WorkKind, int] = {}
        for index, (need, remaining) in enumerate(left):
            if remaining <= 0:
                continue
            rate = rate_for(need.kind)
            done_today = capacity.get(need.kind, 0)
            room = rate - done_today
            if room <= 0:
                continue
            if need.kind in INDIVISIBLE:
                if remaining > rate or done_today > 0:
                    continue
                taken = remaining
            else:
                taken = min(remaining, room)
            day.tasks.append(Task(need=need, quantity=taken))
            capacity[need.kind] = done_today + taken
            left[index] = (need, remaining - taken)
    plan.unplaced = [need for need, remaining in left if remaining > 0]
    return plan


def days_needed(needs: list[Need]) -> float:
    """Gang days the whole list would take, ignoring the order it is in."""
    total = 0.0
    for need in needs:
        total += need.quantity / rate_for(need.kind)
    return round(total, 2)
