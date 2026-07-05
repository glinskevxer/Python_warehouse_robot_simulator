"""What the work needs on the ground."""

from __future__ import annotations

from spikemaul.model.work import WorkKind
from spikemaul.units.span import Span
from spikemaul.work.material import for_need, for_needs, sheet
from spikemaul.work.needs import Need


def need(kind: WorkKind, quantity: int) -> Need:
    return Need(span=Span.parse("13.00-13.60"), kind=kind, quantity=quantity, because="survey")


def test_a_tie_order_carries_the_plates_and_the_spikes_that_go_with_it() -> None:
    found = {one.name: one.quantity for one in for_need(need(WorkKind.TIE_RENEWAL, 400))}
    assert found["crossties"] == 400
    assert found["tie plates"] == 800
    assert found["spikes"] == 1600


def test_a_tie_order_carries_the_ballast_the_tamper_will_want() -> None:
    found = {one.name: one.quantity for one in for_need(need(WorkKind.TIE_RENEWAL, 400))}
    assert found["ballast"] == 280.0


def test_surfacing_is_ballast_by_the_foot() -> None:
    found = for_need(need(WorkKind.SURFACING, 2000))
    assert [one.name for one in found] == ["ballast"]
    assert found[0].quantity == 700.0


def test_rail_is_ordered_in_sticks_and_the_bars_follow() -> None:
    found = {one.name: one.quantity for one in for_need(need(WorkKind.RAIL_CHANGE, 78))}
    assert found["rail"] == 78
    assert found["joint bars"] == 4
    assert found["track bolts"] == 16


def test_a_part_stick_of_rail_still_needs_its_bars() -> None:
    found = {one.name: one.quantity for one in for_need(need(WorkKind.RAIL_CHANGE, 40))}
    assert found["joint bars"] == 4


def test_a_joint_repair_is_bars_and_bolts() -> None:
    found = {one.name: one.quantity for one in for_need(need(WorkKind.JOINT_REPAIR, 6))}
    assert found["joint bars"] == 12
    assert found["track bolts"] == 24


def test_work_that_needs_nothing_off_the_shelf_orders_nothing() -> None:
    assert for_need(need(WorkKind.VEGETATION, 4)) == []
    assert for_need(need(WorkKind.DRAINAGE, 600)) == []


def test_two_orders_wanting_the_same_material_add_up() -> None:
    found = {
        one.name: one.quantity
        for one in for_needs([need(WorkKind.TIE_RENEWAL, 100), need(WorkKind.SURFACING, 1000)])
    }
    assert found["ballast"] == 420.0
    assert found["crossties"] == 100


def test_the_sheet_prints_a_line_per_material() -> None:
    lines = sheet([need(WorkKind.TIE_RENEWAL, 400)])
    assert "280 tons ballast" in lines
    assert "400 each crossties" in lines


def test_an_empty_list_of_work_orders_nothing() -> None:
    assert sheet([]) == ["nothing to order"]
