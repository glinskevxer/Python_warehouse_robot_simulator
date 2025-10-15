"""The gang's week, and the work that will not divide across days."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.work import WorkKind
from spikemaul.units.span import Span
from spikemaul.work.needs import Need
from spikemaul.work.plan import days_needed, plan_week, rate_for, working_days

SEC2 = Ident.named(Kind.GANG, "SEC2")
MONDAY = date(2025, 6, 2)


def need(kind: WorkKind, quantity: int, span: str = "13.00-13.60") -> Need:
    return Need(
        span=Span.parse(span),
        kind=kind,
        quantity=quantity,
        because="tie survey",
    )


def test_the_working_days_leave_the_weekend_out() -> None:
    got = working_days(date(2025, 6, 6), 3)
    assert [one.isoformat() for one in got] == ["2025-06-06", "2025-06-09", "2025-06-10"]


def test_a_plan_covers_at_least_a_day() -> None:
    with pytest.raises(InputError, match="at least one day"):
        working_days(MONDAY, 0)


def test_a_days_work_is_the_production_rate() -> None:
    plan = plan_week(SEC2, [need(WorkKind.TIE_RENEWAL, 120)], MONDAY)
    assert plan.days[0].tasks[0].quantity == 120
    assert plan.days[1].is_empty
    assert not plan.is_full


def test_work_bigger_than_a_day_spreads_across_days() -> None:
    plan = plan_week(SEC2, [need(WorkKind.TIE_RENEWAL, 400)], MONDAY)
    quantities = [one.tasks[0].quantity for one in plan.days if not one.is_empty]
    assert quantities == [120, 120, 120, 40]
    assert plan.unplaced == []


def test_work_bigger_than_the_week_leaves_the_rest_unplanned() -> None:
    plan = plan_week(SEC2, [need(WorkKind.TIE_RENEWAL, 1000)], MONDAY, days=2)
    assert sum(one.tasks[0].quantity for one in plan.days) == 240
    assert plan.unplaced != []


def test_a_turnout_is_a_whole_day_or_it_is_not_started() -> None:
    needs = [need(WorkKind.TURNOUT_REPAIR, 1), need(WorkKind.TURNOUT_REPAIR, 1)]
    plan = plan_week(SEC2, needs, MONDAY)
    assert [len(one.tasks) for one in plan.days[:2]] == [1, 1]


def test_two_turnouts_on_one_need_do_not_fit_a_day_at_all() -> None:
    plan = plan_week(SEC2, [need(WorkKind.TURNOUT_REPAIR, 2)], MONDAY)
    assert all(one.is_empty for one in plan.days)
    assert plan.unplaced != []


def test_two_kinds_of_work_share_a_day_because_the_rates_are_separate() -> None:
    needs = [need(WorkKind.TIE_RENEWAL, 60), need(WorkKind.SURFACING, 1000)]
    plan = plan_week(SEC2, needs, MONDAY)
    assert len(plan.days[0].tasks) == 2


def test_the_needs_are_taken_in_the_order_they_arrive() -> None:
    needs = [
        need(WorkKind.TIE_RENEWAL, 120, "20.00-20.60"),
        need(WorkKind.TIE_RENEWAL, 120, "13.00-13.60"),
    ]
    plan = plan_week(SEC2, needs, MONDAY)
    assert str(plan.days[0].tasks[0].need.span.begin) == "20.00"


def test_a_plan_says_what_it_could_not_fit() -> None:
    plan = plan_week(SEC2, [need(WorkKind.TIE_RENEWAL, 1000)], MONDAY, days=1)
    lines = plan.lines()
    assert lines[0] == "SEC2 plan"
    assert any(one.startswith("not planned:") for one in lines)


def test_an_empty_day_says_so() -> None:
    plan = plan_week(SEC2, [], MONDAY, days=1)
    assert plan.days[0].describe().endswith("nothing planned")


def test_the_days_a_list_would_take_ignores_the_order() -> None:
    needs = [need(WorkKind.TIE_RENEWAL, 240), need(WorkKind.SURFACING, 1000)]
    assert days_needed(needs) == 2.5
    assert rate_for(WorkKind.TIE_RENEWAL) == 120


def test_every_kind_of_work_has_a_rate() -> None:
    for kind in WorkKind:
        assert rate_for(kind) > 0
