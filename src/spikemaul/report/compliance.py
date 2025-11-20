"""The compliance page: every segment against its cycle, on one sheet.

This is the page that gets handed to an inspector, so it is built to be
argued with. Every line names the stretch, the scope, the last inspection that
counted and the day the next one is due, and the ones that did not count are
listed underneath with the reason rather than left off.

The standings are built segment by segment because the cycle depends on the
class and the class is a property of the segment. A subdivision with a class 4
main and a class 1 branch has two cycles running on it and one line for the
whole subdivision would be wrong on both.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from spikemaul.model.ids import Ident
from spikemaul.model.inspection import Scope
from spikemaul.program.compliance import Standing, standing_for
from spikemaul.report.layout import Column, Page, Table, count_of
from spikemaul.store.records import Records

WATCHED: tuple[Scope, ...] = (Scope.TRACK, Scope.TURNOUTS, Scope.JOINT_BARS)
"""The scopes this page reports on, in the order it prints them."""


def standings_for(
    records: Records,
    subdivision: Ident,
    on: date,
    scopes: Sequence[Scope] = WATCHED,
) -> list[Standing]:
    """Where every segment stands against every scope, as of a day."""
    people = {one.ident: one for one in records.people.all()}
    inspections = records.inspections.on(subdivision)
    out = []
    for segment in records.segments.on(subdivision):
        for scope in scopes:
            if scope is Scope.JOINT_BARS and not segment.welded:
                continue
            if scope is Scope.TURNOUTS and not records.turnouts.within(subdivision, segment.span):
                continue
            out.append(
                standing_for(
                    span=segment.span,
                    scope=scope,
                    track_class=segment.authorized,
                    kind=segment.kind,
                    inspections=inspections,
                    people=people,
                    on=on,
                )
            )
    return out


def standing_table(standings: list[Standing]) -> Table:
    """Every standing, the late ones first."""
    table = Table(
        [
            Column("from"),
            Column("to"),
            Column("scope"),
            Column("cycle"),
            Column("last"),
            Column("due"),
            Column("late", numeric=True),
        ]
    )
    for standing in sorted(
        standings,
        key=lambda one: (not one.is_late, -one.days_late, one.span.begin.hundredths),
    ):
        table.add(
            standing.span.begin,
            standing.span.end,
            standing.scope.value,
            f"{standing.frequency.times} in {standing.frequency.period_days}d",
            standing.last.on if standing.last else "never",
            standing.due_on or "now",
            standing.days_late if standing.is_late else "",
        )
    return table


def uncounted_table(standings: list[Standing]) -> Table:
    """Inspections that were done and did not count towards a cycle."""
    table = Table(
        [Column("inspection"), Column("day"), Column("by"), Column("scope"), Column("stretch")]
    )
    for standing in standings:
        for one in standing.uncounted:
            table.add(one.ident, one.on, one.by.tail, one.scope.value, one.span)
    return table


def compliance_page(records: Records, subdivision: Ident, on: date) -> Page:
    """The whole compliance page for one subdivision."""
    record = records.subdivisions.get(subdivision)
    standings = standings_for(records, subdivision, on)
    page = Page(f"{record.name} inspection compliance {on.isoformat()}")

    late = [one for one in standings if one.is_late]
    page.say(f"{count_of(len(standings), 'cycle')} watched, {count_of(len(late), 'cycle')} late")

    page.heading("cycles")
    page.table(standing_table(standings), empty="nothing to watch")

    page.heading("did not count")
    page.table(
        uncounted_table(standings),
        empty="every inspection recorded counted towards its cycle",
    )
    return page
