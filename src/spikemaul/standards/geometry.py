"""The geometry limits, one row per class of track.

Every number here is a limit a reading is judged against, and which row is
read depends on the class the segment is being held to. That is the whole
reason this table exists as data rather than as a pile of comparisons: the
same reading is inside the limit on one class and outside it on another, and
the remedial action for an exception is usually to hold the track to a lower
class, which means reading the table again on a different row.

Deviations are mid ordinates on a sixty two foot chord except where the class
says otherwise. Gauge is an absolute measurement, not a deviation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from spikemaul.standards.classes import ALL, ClassOfTrack
from spikemaul.units.measure import Inches

CHORD_FEET: Final = 62
"""The chord alignment and profile are measured on."""

WARP_WINDOW_FEET: Final = 62
"""Two crosslevel readings closer than this are compared for warp."""


@dataclass(frozen=True)
class GeometryLimits:
    """One row of the geometry table, for one class of track."""

    gauge_min: Inches
    gauge_max: Inches
    crosslevel: Inches
    warp: Inches
    alignment_tangent: Inches
    alignment_curve: Inches
    profile: Inches
    elevation_deviation: Inches

    def alignment(self, on_curve: bool) -> Inches:
        """The alignment limit, which is tighter on a curve at the top classes."""
        return self.alignment_curve if on_curve else self.alignment_tangent

    def gauge_holds(self, reading: Inches) -> bool:
        """Whether a gauge reading is inside this row, both ways."""
        return self.gauge_min <= reading <= self.gauge_max


def _row(
    gauge_min: str,
    gauge_max: str,
    crosslevel: str,
    warp: str,
    alignment_tangent: str,
    alignment_curve: str,
    profile: str,
    elevation_deviation: str,
) -> GeometryLimits:
    return GeometryLimits(
        gauge_min=Inches.parse(gauge_min),
        gauge_max=Inches.parse(gauge_max),
        crosslevel=Inches.parse(crosslevel),
        warp=Inches.parse(warp),
        alignment_tangent=Inches.parse(alignment_tangent),
        alignment_curve=Inches.parse(alignment_curve),
        profile=Inches.parse(profile),
        elevation_deviation=Inches.parse(elevation_deviation),
    )


_TABLE: Final[dict[ClassOfTrack, GeometryLimits]] = {
    ClassOfTrack.EXCEPTED: _row("56", "58 1/2", "3", "3", "5", "5", "3", "1 1/2"),
    ClassOfTrack.ONE: _row("56", "58", "3", "3", "5", "5", "3", "1 1/2"),
    ClassOfTrack.TWO: _row("56", "57 3/4", "2", "2 1/4", "3", "3", "2 3/4", "1 1/2"),
    ClassOfTrack.THREE: _row("56", "57 3/4", "1 3/4", "2", "1 3/4", "1 3/4", "2 1/4", "1 1/4"),
    ClassOfTrack.FOUR: _row("56", "57 1/2", "1 1/4", "1 3/4", "1 1/2", "1 1/2", "2", "1"),
    ClassOfTrack.FIVE: _row("56", "57 1/2", "1", "1 1/2", "3/4", "5/8", "1 1/4", "3/4"),
}


def limits_for(track_class: ClassOfTrack) -> GeometryLimits:
    """The row of the table this class of track is judged against."""
    return _TABLE[track_class]


def class_for_gauge(reading: Inches) -> ClassOfTrack | None:
    """The highest class a gauge reading meets, or ``None`` if it meets none.

    ``None`` is not the same as excepted. It means the track does not meet the
    loosest limit on the table and the remedy is not a slower speed.
    """
    for track_class in sorted(ALL, reverse=True):
        if limits_for(track_class).gauge_holds(reading):
            return track_class
    return None


def _class_meeting(reading: Inches, limit: str) -> ClassOfTrack | None:
    size = abs(reading)
    for track_class in sorted(ALL, reverse=True):
        if size <= getattr(limits_for(track_class), limit):
            return track_class
    return None


def class_for_crosslevel(reading: Inches) -> ClassOfTrack | None:
    """The highest class a crosslevel deviation meets."""
    return _class_meeting(reading, "crosslevel")


def class_for_warp(reading: Inches) -> ClassOfTrack | None:
    """The highest class a warp reading meets."""
    return _class_meeting(reading, "warp")


def class_for_profile(reading: Inches) -> ClassOfTrack | None:
    """The highest class a profile deviation meets."""
    return _class_meeting(reading, "profile")


def class_for_alignment(reading: Inches, on_curve: bool) -> ClassOfTrack | None:
    """The highest class an alignment deviation meets, curve or tangent."""
    return _class_meeting(reading, "alignment_curve" if on_curve else "alignment_tangent")


def class_for_elevation_deviation(reading: Inches) -> ClassOfTrack | None:
    """The highest class a deviation from designated elevation meets."""
    return _class_meeting(reading, "elevation_deviation")
