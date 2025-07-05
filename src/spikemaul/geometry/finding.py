"""What a run says, read against one class of track.

A finding is a reading that does not meet the class the track is being held
to, together with the highest class it does meet. That second part is the
useful half. Knowing that a gauge of 57 7/8 fails class three is a fact about
the number; knowing it holds class one is what decides whether the track runs
at ten miles an hour tonight or does not run at all.

Each channel is read separately, because the remedies differ and because a
run with three channels outside on the same station is three findings and one
piece of railroad. Putting them together is the assessment's job, not this
one's.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.model.defect import Condition
from spikemaul.model.reading import Reading, Run
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.geometry import (
    class_for_alignment,
    class_for_crosslevel,
    class_for_elevation_deviation,
    class_for_gauge,
    class_for_profile,
)
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost


@dataclass(frozen=True)
class Finding:
    """One reading outside the limits, and the class it does meet."""

    at: Milepost
    condition: Condition
    reading: Inches
    meets: ClassOfTrack | None

    @property
    def is_out_of_service(self) -> bool:
        """Whether the reading meets no class at all."""
        return self.meets is None

    def describe(self) -> str:
        """One line for the exception listing."""
        meets = "nothing" if self.meets is None else str(self.meets)
        return f"MP {self.at} {self.condition.value} {self.reading} meets {meets}"


def _finding(
    reading: Reading,
    condition: Condition,
    measured: Inches,
    meets: ClassOfTrack | None,
    held_at: ClassOfTrack,
) -> Finding | None:
    if meets is not None and meets >= held_at:
        return None
    return Finding(at=reading.at, condition=condition, reading=measured, meets=meets)


def gauge_findings(run: Run, held_at: ClassOfTrack) -> list[Finding]:
    """Gauge readings outside the limits for a class."""
    out = []
    for reading in run.readings:
        found = _finding(
            reading, Condition.GAUGE, reading.gauge, class_for_gauge(reading.gauge), held_at
        )
        if found is not None:
            out.append(found)
    return out


def crosslevel_findings(run: Run, held_at: ClassOfTrack) -> list[Finding]:
    """Crosslevel readings outside the limits for a class."""
    out = []
    for reading in run.readings:
        found = _finding(
            reading,
            Condition.CROSSLEVEL,
            reading.crosslevel,
            class_for_crosslevel(reading.crosslevel),
            held_at,
        )
        if found is not None:
            out.append(found)
    return out


def profile_findings(run: Run, held_at: ClassOfTrack) -> list[Finding]:
    """Profile deviations outside the limits for a class."""
    out = []
    for reading in run.readings:
        found = _finding(
            reading,
            Condition.PROFILE,
            reading.profile,
            class_for_profile(reading.profile),
            held_at,
        )
        if found is not None:
            out.append(found)
    return out


def alignment_findings(run: Run, held_at: ClassOfTrack) -> list[Finding]:
    """Alignment deviations, judged on the curve row where the run says curve."""
    out = []
    for reading in run.readings:
        found = _finding(
            reading,
            Condition.ALIGNMENT,
            reading.alignment,
            class_for_alignment(reading.alignment, reading.on_curve),
            held_at,
        )
        if found is not None:
            out.append(found)
    return out


def elevation_findings(run: Run, held_at: ClassOfTrack) -> list[Finding]:
    """Deviations from the elevation a curve is supposed to carry.

    Only readings that name a designated elevation are looked at. A curve
    reading with no designated elevation on it is a reading the office has not
    finished writing down, and guessing the designation from the reading makes
    every curve perfect.
    """
    out = []
    for reading in run.readings:
        deviation = reading.elevation_deviation
        if deviation is None:
            continue
        found = _finding(
            reading,
            Condition.ELEVATION,
            deviation,
            class_for_elevation_deviation(deviation),
            held_at,
        )
        if found is not None:
            out.append(found)
    return out


def findings(run: Run, held_at: ClassOfTrack) -> list[Finding]:
    """Every channel read against a class, in milepost then channel order."""
    found = (
        gauge_findings(run, held_at)
        + crosslevel_findings(run, held_at)
        + profile_findings(run, held_at)
        + alignment_findings(run, held_at)
        + elevation_findings(run, held_at)
    )
    return sorted(found, key=lambda one: (one.at.hundredths, one.condition.value))
