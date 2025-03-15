"""Geometry runs, which are only useful in order."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.reading import Reading, Run
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span


def reading(post: str, **changes: object) -> Reading:
    fields: dict[str, object] = {
        "at": Milepost.parse(post),
        "gauge": Inches.parse("56 5/8"),
        "crosslevel": Inches.parse("1/4"),
        "profile": Inches.parse("1/2"),
        "alignment": Inches.parse("3/8"),
    }
    fields.update(changes)
    return Reading(**fields)  # type: ignore[arg-type]


def run(*posts: str) -> Run:
    return Run(
        inspection=Ident.numbered(Kind.INSPECTION, 2025, 52),
        subdivision=Ident.named(Kind.SUBDIVISION, "PLAINS"),
        on=date(2025, 5, 6),
        readings=[reading(post) for post in posts],
    )


def test_a_gauge_reading_of_nothing_is_not_a_reading() -> None:
    with pytest.raises(InputError, match="is not a reading"):
        reading("12.00", gauge=Inches(0))


def test_profile_and_alignment_are_mid_ordinates_with_no_sign() -> None:
    with pytest.raises(InputError, match="have no sign"):
        reading("12.00", profile=-Inches.of(1))
    with pytest.raises(InputError, match="have no sign"):
        reading("12.00", alignment=-Inches.of(1))


def test_tangent_track_has_no_designated_elevation() -> None:
    with pytest.raises(InputError, match="no designated elevation"):
        reading("12.00", designated_elevation=Inches.of(2))
    assert reading("12.00").elevation_deviation is None


def test_the_deviation_is_the_crosslevel_against_what_the_curve_carries() -> None:
    high = reading(
        "13.20",
        on_curve=True,
        crosslevel=Inches.parse("2 1/2"),
        designated_elevation=Inches.parse("2"),
    )
    assert high.elevation_deviation == Inches.parse("1/2")
    low = reading(
        "13.20",
        on_curve=True,
        crosslevel=Inches.parse("1 1/4"),
        designated_elevation=Inches.parse("2"),
    )
    assert low.elevation_deviation == -Inches.parse("3/4")


def test_a_reading_says_itself_in_one_line() -> None:
    assert reading("12.00").describe() == (
        "MP 12.00 tangent gauge 56 5/8 crosslevel 1/4 profile 1/2 alignment 3/8"
    )
    assert reading("13.20", on_curve=True).describe().startswith("MP 13.20 curve")


def test_a_run_of_one_reading_has_nothing_to_compare() -> None:
    with pytest.raises(InputError, match="at least two readings"):
        Run(
            inspection=Ident.numbered(Kind.INSPECTION, 2025, 52),
            subdivision=Ident.named(Kind.SUBDIVISION, "PLAINS"),
            on=date(2025, 5, 6),
            readings=[reading("12.00")],
        )


def test_a_run_reads_forward() -> None:
    with pytest.raises(InputError, match="a run reads forward"):
        run("12.00", "12.02", "12.01")
    with pytest.raises(InputError, match="a run reads forward"):
        run("12.00", "12.00")


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not an inspection number"):
        Run(
            inspection=Ident.named(Kind.SEGMENT, "014"),
            subdivision=Ident.named(Kind.SUBDIVISION, "PLAINS"),
            on=date(2025, 5, 6),
            readings=[reading("12.00"), reading("12.01")],
        )


def test_the_span_is_the_first_reading_to_the_last() -> None:
    assert run("12.00", "12.01", "12.02").span == Span.parse("12.00-12.02")


def test_the_spacing_is_the_shortest_gap_between_stations() -> None:
    assert run("12.00", "12.01", "12.02").spacing_feet == 53
    assert run("12.00", "12.02", "12.04").spacing_feet == 106


def test_a_run_with_a_station_missing_says_so() -> None:
    assert not run("12.00", "12.01", "12.02").has_gaps()
    assert run("12.00", "12.01", "12.04").has_gaps()


def test_readings_inside_a_stretch_come_back_in_order() -> None:
    subject = run("12.00", "12.01", "12.02", "12.03")
    got = subject.within(Span.parse("12.01-12.03"))
    assert [str(one.at) for one in got] == ["12.01", "12.02"]


def test_the_pairs_inside_a_window_are_every_pair_not_the_neighbours() -> None:
    subject = run("12.00", "12.01", "12.02", "12.03")
    pairs = list(subject.pairs_within(120))
    assert len(pairs) == 5
    assert all(one.at.nominal_feet_to(two.at) < 120 for one, two in pairs)


def test_a_window_of_no_length_is_refused() -> None:
    with pytest.raises(InputError, match="a window has a length"):
        list(run("12.00", "12.01").pairs_within(0))


def test_a_run_says_itself_in_one_line() -> None:
    assert run("12.00", "12.01", "12.02").describe() == (
        "IN-2025-0052 2025-05-06 PLAINS 12.00 to 12.02 3 readings at 53 ft"
    )
