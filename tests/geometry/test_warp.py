"""Warp, which is a difference and not a reading."""

from __future__ import annotations

from datetime import date

from spikemaul.geometry.warp import pairs, understates_warp, warp_findings, worst
from spikemaul.model.defect import Condition
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.reading import Reading, Run
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.units.measure import Inches
from tests.support.books import a_reading

CLASS_THREE = ClassOfTrack.THREE


def run_of(*readings: Reading) -> Run:
    return Run(
        inspection=Ident.numbered(Kind.INSPECTION, 2025, 52),
        subdivision=Ident.named(Kind.SUBDIVISION, "PLAINS"),
        on=date(2025, 5, 6),
        readings=list(readings),
    )


def stations(*levels: str) -> Run:
    return run_of(
        *[
            a_reading(f"12.{index:02d}", crosslevel=Inches.parse(level))
            for index, level in enumerate(levels)
        ]
    )


def test_a_flat_run_has_no_warp() -> None:
    run = stations("0", "0", "0")
    assert [str(one.difference) for one in pairs(run)] == ["0", "0"]
    assert warp_findings(run, CLASS_THREE) == []


def test_the_pairs_are_every_pair_inside_the_window() -> None:
    run = stations("0", "0", "0", "0")
    assert len(pairs(run)) == 3
    assert len(pairs(run, window_feet=120)) == 5


def test_the_difference_keeps_its_sign_and_names_both_ends() -> None:
    run = stations("0", "1 1/2")
    pair = pairs(run)[0]
    assert pair.difference == Inches.parse("1 1/2")
    assert pair.feet_apart == 53
    assert pair.describe() == "MP 12.00 to MP 12.01 53 ft apart, warp 1 1/2"


def test_one_bad_station_makes_several_findings() -> None:
    run = stations("0", "0", "2 1/4", "0", "0")
    found = warp_findings(run, CLASS_THREE)
    assert len(found) == 2
    assert {str(one.at) for one in found} == {"12.02", "12.03"}
    assert all(one.condition is Condition.WARP for one in found)


def test_a_twist_with_no_bad_pair_of_neighbours_is_still_found_in_a_wider_window() -> None:
    run = stations("0", "3/4", "1 5/8")
    assert warp_findings(run, ClassOfTrack.FIVE) == []
    wider = warp_findings(run, ClassOfTrack.FIVE, window_feet=120)
    assert [str(one.reading) for one in wider] == ["1 5/8"]


def test_the_class_the_pair_meets_comes_off_the_warp_row() -> None:
    run = stations("0", "2 1/8")
    found = warp_findings(run, CLASS_THREE)
    assert found[0].meets == ClassOfTrack.TWO


def test_a_warp_that_meets_nothing_says_so() -> None:
    run = stations("0", "3 1/4")
    found = warp_findings(run, CLASS_THREE)
    assert found[0].is_out_of_service


def test_the_worst_pair_is_the_biggest_difference_either_way() -> None:
    run = stations("0", "1/2", "-1 1/4")
    pair = worst(run)
    assert pair is not None
    assert pair.difference == Inches.parse("-1 3/4")


def test_a_run_with_a_gap_understates_warp_and_says_so() -> None:
    run = run_of(
        a_reading("12.00", crosslevel=Inches.parse("0")),
        a_reading("12.01", crosslevel=Inches.parse("0")),
        a_reading("12.04", crosslevel=Inches.parse("2")),
    )
    assert understates_warp(run)
    assert not understates_warp(stations("0", "0", "0"))


def test_a_narrower_window_finds_less() -> None:
    run = stations("0", "3/4", "1 5/8")
    wide = warp_findings(run, ClassOfTrack.FIVE, window_feet=120)
    narrow = warp_findings(run, ClassOfTrack.FIVE, window_feet=60)
    assert len(wide) > len(narrow)
    assert narrow == []
