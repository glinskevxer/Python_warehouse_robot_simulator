"""What the geometry car wrote down, station by station.

A run is a file of readings at a fixed spacing along one track, and the
readings are only useful in order. Warp is the difference between two
crosslevel readings inside a window, so a run with a reading missing out of
the middle of it does not give the same answer as one without the gap, and a
run whose readings are not sorted gives an answer that is wrong without
looking wrong.

So a run validates its own shape on the way in: one subdivision, mileposts
strictly increasing, and a spacing it can state. What the numbers mean is
somebody else's problem, and it is the geometry package's problem.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span


@dataclass(frozen=True, order=True)
class Reading:
    """One station of a geometry run."""

    at: Milepost
    gauge: Inches
    crosslevel: Inches
    profile: Inches
    alignment: Inches
    on_curve: bool = False
    designated_elevation: Inches | None = None

    def __post_init__(self) -> None:
        if self.gauge.sixteenths <= 0:
            raise InputError(f"a gauge reading of {self.gauge} at MP {self.at} is not a reading")
        if self.profile.sixteenths < 0 or self.alignment.sixteenths < 0:
            raise InputError("profile and alignment are mid ordinates and have no sign")
        if self.designated_elevation is not None and not self.on_curve:
            raise InputError("tangent track has no designated elevation to deviate from")

    @property
    def elevation_deviation(self) -> Inches | None:
        """How far the crosslevel is off what the curve is supposed to carry."""
        if self.designated_elevation is None:
            return None
        return abs(self.crosslevel) - self.designated_elevation

    def describe(self) -> str:
        """One line for the exception listing."""
        where = "curve" if self.on_curve else "tangent"
        return (
            f"MP {self.at} {where} gauge {self.gauge} crosslevel {self.crosslevel} "
            f"profile {self.profile} alignment {self.alignment}"
        )


@dataclass(frozen=True)
class Run:
    """A geometry car run over one stretch of one track."""

    inspection: Ident
    subdivision: Ident
    on: date
    readings: Sequence[Reading]

    def __post_init__(self) -> None:
        if self.inspection.kind is not Kind.INSPECTION:
            raise InputError(f"{self.inspection} is not an inspection number")
        if len(self.readings) < 2:
            raise InputError("a run is at least two readings, or there is nothing to compare")
        for earlier, later in zip(self.readings, self.readings[1:], strict=False):
            if later.at <= earlier.at:
                raise InputError(
                    f"a run reads forward, MP {later.at} does not follow MP {earlier.at}"
                )

    @property
    def span(self) -> Span:
        """The stretch the run covers, first reading to last."""
        return Span(self.readings[0].at, self.readings[-1].at)

    @property
    def spacing_feet(self) -> int:
        """The nominal spacing, taken as the shortest gap between stations."""
        gaps = [
            earlier.at.nominal_feet_to(later.at)
            for earlier, later in zip(self.readings, self.readings[1:], strict=False)
        ]
        return min(gaps)

    def has_gaps(self) -> bool:
        """Whether any station is further from the last than the spacing."""
        spacing = self.spacing_feet
        return any(
            earlier.at.nominal_feet_to(later.at) > spacing
            for earlier, later in zip(self.readings, self.readings[1:], strict=False)
        )

    def within(self, span: Span) -> list[Reading]:
        """Readings that fall inside a stretch, in order."""
        return [one for one in self.readings if span.contains(one.at)]

    def pairs_within(self, feet: int) -> Iterator[tuple[Reading, Reading]]:
        """Every pair of readings closer together than a distance.

        Warp is measured across a window rather than between neighbours, so
        this yields every pair inside it and not just consecutive ones.
        """
        if feet <= 0:
            raise InputError("a window has a length")
        for index, earlier in enumerate(self.readings):
            for later in self.readings[index + 1 :]:
                if earlier.at.nominal_feet_to(later.at) >= feet:
                    break
                yield earlier, later

    def describe(self) -> str:
        """One line for the run register."""
        return (
            f"{self.inspection} {self.on.isoformat()} {self.subdivision.tail} {self.span} "
            f"{len(self.readings)} readings at {self.spacing_feet} ft"
        )
