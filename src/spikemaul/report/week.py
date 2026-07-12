"""The gang's week on one sheet.

What the foreman takes out on Monday morning: the days, what is on each of
them, what has to be on the ground before they start, and what did not fit.
The last part is the useful one. A week's plan that quietly drops the third
tie order reads like a week's work and is a week of somebody wondering why the
backlog is not moving.

The plan itself is arithmetic and lives in ``spikemaul.work.plan``. This
fetches the work, hands it over, and prints what comes back.
"""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident
from spikemaul.model.work import WorkOrder
from spikemaul.report.layout import Column, Page, Table, count_of
from spikemaul.store.records import Records
from spikemaul.work.material import sheet
from spikemaul.work.needs import Need
from spikemaul.work.plan import Plan, days_needed, plan_week


def needs_from(orders: list[WorkOrder]) -> list[Need]:
    """Turn work orders into the needs the planner takes.

    The order they arrive in is the order they are worked, and that order is
    the register's: oldest first, which is the closest thing to a deadline a
    work order without a date has.
    """
    return [
        Need(
            span=one.span,
            kind=one.kind,
            quantity=one.quantity,
            because=str(one.ident),
            due_on=one.due_on,
        )
        for one in orders
    ]


def week_for(records: Records, subdivision: Ident, gang: Ident, first: date, days: int = 5) -> Plan:
    """The plan for one gang, out of what it has open or what is open at all."""
    orders = records.work.for_gang(gang) or records.work.open_on(subdivision)
    return plan_week(gang, needs_from(orders), first, days)


def day_table(plan: Plan) -> Table:
    """One row per day, with what is on it."""
    table = Table([Column("day"), Column("work")])
    for one in plan.days:
        table.add(one.on, "; ".join(task.describe() for task in one.tasks) or "nothing planned")
    return table


def week_page(
    records: Records, subdivision: Ident, gang: Ident, first: date, days: int = 5
) -> Page:
    """The week sheet for one gang."""
    record = records.subdivisions.get(subdivision)
    crew = records.gangs.get(gang)
    plan = week_for(records, subdivision, gang, first, days)
    page = Page(f"{crew.name} week of {first.isoformat()} on {record.name}")
    page.say(f"{crew.headcount} men, {', '.join(crew.machines) or 'no machines'}")

    page.heading("days")
    page.table(day_table(plan), empty="no days in the plan")

    page.heading("on the ground")
    for line in sheet([task.need for one in plan.days for task in one.tasks]):
        page.say(line)

    page.heading("not planned")
    if plan.unplaced:
        page.say(f"{count_of(len(plan.unplaced), 'piece')} of work did not fit")
        for need in plan.unplaced:
            page.say(need.describe())
        page.say(f"{days_needed(plan.unplaced)} gang days to clear it")
    else:
        page.say("everything open fits in the week")
    return page
