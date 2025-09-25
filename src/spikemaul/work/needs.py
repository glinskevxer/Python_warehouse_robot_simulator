"""What has to be done, before anybody decides who does it.

A need is a piece of work the records say is required: this many ties over
this stretch, this many feet of surfacing, this joint bar replaced. It carries
where it came from, because a need off a defect card has a deadline the rule
set and a need off a tie survey has a deadline the roadmaster set, and mixing
them loses the difference.

Needs are not work orders. A need can be met by half of an existing work
order, or three needs can become one order because the gang is going there
anyway. That merging is the plan's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.model.defect import Condition, Defect
from spikemaul.model.ids import Ident
from spikemaul.model.work import WorkKind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.remedial import Clock
from spikemaul.standards.ties import SEGMENT_FEET
from spikemaul.ties.survey import TieSurvey
from spikemaul.units.span import Span

_FROM_CONDITION: dict[Condition, WorkKind] = {
    Condition.GAUGE: WorkKind.GAUGE_REPAIR,
    Condition.CROSSLEVEL: WorkKind.SURFACING,
    Condition.WARP: WorkKind.SURFACING,
    Condition.PROFILE: WorkKind.SURFACING,
    Condition.ALIGNMENT: WorkKind.SURFACING,
    Condition.ELEVATION: WorkKind.SURFACING,
    Condition.TIES: WorkKind.TIE_RENEWAL,
    Condition.RAIL_WEAR: WorkKind.RAIL_CHANGE,
    Condition.RAIL_BREAK: WorkKind.RAIL_CHANGE,
    Condition.JOINT_BAR: WorkKind.JOINT_REPAIR,
    Condition.SWITCH_POINT: WorkKind.TURNOUT_REPAIR,
    Condition.FROG: WorkKind.TURNOUT_REPAIR,
    Condition.GUARD_RAIL: WorkKind.TURNOUT_REPAIR,
    Condition.BALLAST: WorkKind.SURFACING,
    Condition.DRAINAGE: WorkKind.DRAINAGE,
    Condition.VEGETATION: WorkKind.VEGETATION,
}

SURFACING_FEET_EITHER_SIDE = 100
"""How much track a surfacing gang works either side of a geometry exception."""


@dataclass(frozen=True)
class Need:
    """One piece of work the records say is required."""

    span: Span
    kind: WorkKind
    quantity: int
    because: str
    due_on: date | None = None
    stops_trains: bool = False
    defect: Ident | None = None

    @property
    def unit(self) -> str:
        """The unit the quantity is in, off the kind of work."""
        return self.kind.unit

    def describe(self) -> str:
        """One line for the needs list."""
        when = "before the next train" if self.stops_trains else str(self.due_on or "no date")
        return f"{self.span} {self.kind.value} {self.quantity} {self.unit}, {self.because}, {when}"


def work_for(condition: Condition) -> WorkKind:
    """The kind of work a condition calls for."""
    return _FROM_CONDITION[condition]


def need_from_defect(defect: Defect, held_at: ClassOfTrack) -> Need:
    """The work one defect card calls for, with the deadline the rule set."""
    action = defect.action(held_at)
    deadline = action.deadline
    stops = deadline is not None and deadline.clock is Clock.TRAINS
    kind = work_for(defect.condition)
    if kind is WorkKind.SURFACING:
        span = Span(
            defect.at.advanced_feet(-SURFACING_FEET_EITHER_SIDE),
            defect.at.advanced_feet(SURFACING_FEET_EITHER_SIDE),
        )
        quantity = span.feet
    else:
        span = Span(defect.at, defect.at.advanced(1))
        quantity = 1
    return Need(
        span=span,
        kind=kind,
        quantity=quantity,
        because=f"{defect.ident} {defect.condition.value}",
        due_on=defect.due_on(held_at),
        stops_trains=stops,
        defect=defect.ident,
    )


def needs_from_defects(defects: list[Defect], held_at: ClassOfTrack) -> list[Need]:
    """The work every open card calls for, the ones stopping trains first."""
    out = [need_from_defect(one, held_at) for one in defects if one.is_open]
    return sorted(
        out,
        key=lambda one: (
            not one.stops_trains,
            one.due_on or date.max,
            one.span.begin.hundredths,
        ),
    )


def needs_from_survey(survey: TieSurvey, target: ClassOfTrack, due_on: date | None) -> list[Need]:
    """Tie renewal off a survey, one need per run of bad lengths."""
    out = []
    for cluster in survey.clusters(target):
        inside = [
            one
            for one in survey.lengths
            if cluster.contains(one.at) or cluster.contains(one.at.advanced_feet(SEGMENT_FEET - 1))
        ]
        ties = sum(one.short_by(target) for one in inside)
        if ties == 0:
            continue
        out.append(
            Need(
                span=cluster,
                kind=WorkKind.TIE_RENEWAL,
                quantity=ties,
                because=f"tie survey {survey.on.isoformat()} to hold {target}",
                due_on=due_on,
            )
        )
    return out


def total_by_kind(needs: list[Need]) -> dict[WorkKind, int]:
    """How much of each kind of work is outstanding, in its own unit."""
    out: dict[WorkKind, int] = {}
    for need in needs:
        out[need.kind] = out.get(need.kind, 0) + need.quantity
    return out
