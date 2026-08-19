"""Work orders, whose quantities carry the unit they are counted in."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.work import WorkKind, WorkOrder
from spikemaul.units.span import Span


def work(**changes: object) -> WorkOrder:
    fields: dict[str, object] = {
        "ident": Ident.numbered(Kind.WORK, 2025, 88),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "span": Span.parse("13.00-13.60"),
        "kind": WorkKind.TIE_RENEWAL,
        "quantity": 400,
        "raised_on": date(2025, 5, 6),
        "raised_by": Ident.named(Kind.PERSON, "DKEHOE"),
    }
    fields.update(changes)
    return WorkOrder(**fields)  # type: ignore[arg-type]


def test_a_kind_of_work_reads_off_the_order() -> None:
    assert WorkKind.parse("surfacing") == WorkKind.SURFACING
    assert WorkKind.parse(" Tie Renewal ") == WorkKind.TIE_RENEWAL
    with pytest.raises(InputError, match="is not work we order"):
        WorkKind.parse("painting")


def test_every_kind_of_work_carries_its_unit() -> None:
    assert WorkKind.TIE_RENEWAL.unit == "ties"
    assert WorkKind.RAIL_CHANGE.unit == "feet"
    assert WorkKind.VEGETATION.unit == "acres"
    assert {one.unit for one in WorkKind}


def test_the_work_that_needs_the_track_held_is_named() -> None:
    assert WorkKind.SURFACING.needs_track_time
    assert not WorkKind.VEGETATION.needs_track_time
    assert not WorkKind.DRAINAGE.needs_track_time


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not a work order number"):
        work(ident=Ident.numbered(Kind.DEFECT, 2025, 88))
    with pytest.raises(InputError, match="is not a person"):
        work(raised_by=Ident.named(Kind.GANG, "SEC2"))
    with pytest.raises(InputError, match="is not a gang"):
        work(gang=Ident.named(Kind.PERSON, "DKEHOE"))
    with pytest.raises(InputError, match="not a defect number"):
        work(defect=Ident.named(Kind.SEGMENT, "014"))


def test_an_order_for_nothing_is_not_an_order() -> None:
    with pytest.raises(InputError, match="for nothing is not an order"):
        work(quantity=0)


def test_dates_that_run_backwards_are_refused() -> None:
    with pytest.raises(InputError, match="due before it was raised"):
        work(due_on=date(2025, 5, 1))
    with pytest.raises(InputError, match="done before it was raised"):
        work(done_on=date(2025, 5, 1), done_quantity=400)


def test_a_finished_order_carries_both_the_day_and_the_quantity() -> None:
    with pytest.raises(RuleError, match="both the day and what was done"):
        work(done_on=date(2025, 6, 1))
    with pytest.raises(RuleError, match="both the day and what was done"):
        work(done_quantity=400)


def test_an_order_is_open_until_it_is_finished() -> None:
    assert work().is_open
    assert not work().finished(date(2025, 6, 1)).is_open


def test_finishing_an_order_twice_is_refused() -> None:
    done = work().finished(date(2025, 6, 1))
    with pytest.raises(RuleError, match="was finished on"):
        done.finished(date(2025, 6, 2))


def test_finishing_short_leaves_a_shortfall() -> None:
    part = work().finished(date(2025, 6, 1), 250)
    assert part.shortfall == 150
    assert work().finished(date(2025, 6, 1)).shortfall == 0
    assert work().finished(date(2025, 6, 1), 500).shortfall == 0
    assert work().shortfall == 0


def test_a_negative_quantity_done_is_refused() -> None:
    with pytest.raises(InputError, match="not negative"):
        work().finished(date(2025, 6, 1), -1)


def test_a_gang_goes_on_an_order_once() -> None:
    assigned = work().assigned_to(Ident.named(Kind.GANG, "SEC2"))
    assert assigned.is_assigned
    with pytest.raises(RuleError, match="already on"):
        assigned.assigned_to(Ident.named(Kind.GANG, "SEC1"))


def test_an_order_is_overdue_only_while_it_is_open() -> None:
    due = work(due_on=date(2025, 6, 1))
    assert not due.is_overdue(date(2025, 6, 1))
    assert due.is_overdue(date(2025, 6, 2))
    assert not due.finished(date(2025, 6, 5)).is_overdue(date(2025, 7, 1))
    assert not work().is_overdue(date(2030, 1, 1))


def test_an_order_says_itself_in_one_line() -> None:
    assert work().describe() == (
        "WO-2025-0088 PLAINS 13.00 to 13.60 tie renewal 400 ties unassigned open"
    )
    line = work().assigned_to(Ident.named(Kind.GANG, "SEC2")).finished(date(2025, 6, 1)).describe()
    assert line.endswith("SEC2 done 2025-06-01")


def test_an_open_order_can_be_put_right() -> None:
    changed = work().amended(quantity=500, due_on=date(2025, 7, 1), note="more than we thought")
    assert changed.quantity == 500
    assert changed.due_on == date(2025, 7, 1)
    assert changed.note == "more than we thought"


def test_amending_leaves_alone_what_it_is_not_given() -> None:
    changed = work(due_on=date(2025, 6, 1)).amended(quantity=500)
    assert changed.due_on == date(2025, 6, 1)


def test_an_order_cannot_be_amended_to_nothing() -> None:
    with pytest.raises(InputError, match="for nothing is not an order"):
        work().amended(quantity=0)


def test_an_order_cannot_be_made_due_before_it_was_raised() -> None:
    with pytest.raises(RuleError, match="cannot be due before"):
        work().amended(due_on=date(2025, 1, 1))


def test_a_finished_order_stands_as_it_is() -> None:
    done = work().finished(date(2025, 6, 1))
    with pytest.raises(RuleError, match="stands as it is"):
        done.amended(quantity=500)
