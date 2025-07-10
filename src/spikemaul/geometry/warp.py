"""Warp, which is the difference between two crosslevel readings.

Warp is not a reading. It is the difference in crosslevel between any two
points on the track less than sixty two feet apart, and that definition has
two consequences the code has to carry.

The first is that one bad station makes several findings. A crosslevel that is
an inch and a half out will be an inch and a half out against every station
within the window, so a station spacing of fifteen feet gives four findings off
one bad spot. That is not double counting, it is what the rule measures, and
collapsing them here would hide a genuinely twisted piece of track that has no
single bad station in it at all.

The station spacing matters as much as the window. The car reports every few
feet and the file loaded into the book is decimated to the hundredth of a
mile, which is fifty three feet, so at that spacing a sixty two foot window
pairs neighbours and nothing else. A run loaded at a finer spacing pairs more,
and the window is passed in rather than assumed for exactly that reason.

The second is that a run with a station missing understates warp. The pair
that would have shown it is not there to compare. So a run with gaps is worth
saying so about, and the caller is told rather than quietly given a clean
answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.geometry.finding import Finding
from spikemaul.model.defect import Condition
from spikemaul.model.reading import Reading, Run
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.geometry import WARP_WINDOW_FEET, class_for_warp
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost


@dataclass(frozen=True)
class WarpPair:
    """Two crosslevel readings inside the window, and what they differ by."""

    first: Reading
    second: Reading
    difference: Inches

    @property
    def feet_apart(self) -> int:
        """How far apart the two stations are."""
        return self.first.at.nominal_feet_to(self.second.at)

    @property
    def at(self) -> Milepost:
        """Where the finding is written, which is the second station."""
        return self.second.at

    def describe(self) -> str:
        """One line naming both ends, because one end means nothing."""
        return (
            f"MP {self.first.at} to MP {self.second.at} "
            f"{self.feet_apart} ft apart, warp {self.difference}"
        )


def pairs(run: Run, window_feet: int = WARP_WINDOW_FEET) -> list[WarpPair]:
    """Every pair of stations inside the window, with their difference."""
    out = []
    for first, second in run.pairs_within(window_feet):
        difference = second.crosslevel - first.crosslevel
        out.append(WarpPair(first=first, second=second, difference=difference))
    return out


def worst(run: Run, window_feet: int = WARP_WINDOW_FEET) -> WarpPair | None:
    """The pair with the biggest difference, or nothing on a flat run."""
    found = pairs(run, window_feet)
    if not found:
        return None
    return max(found, key=lambda one: abs(one.difference.sixteenths))


def warp_findings(
    run: Run, held_at: ClassOfTrack, window_feet: int = WARP_WINDOW_FEET
) -> list[Finding]:
    """Every pair whose difference is outside the limit for a class."""
    out = []
    for pair in pairs(run, window_feet):
        meets = class_for_warp(pair.difference)
        if meets is not None and meets >= held_at:
            continue
        out.append(
            Finding(
                at=pair.at,
                condition=Condition.WARP,
                reading=pair.difference,
                meets=meets,
            )
        )
    return out


def understates_warp(run: Run) -> bool:
    """Whether the run has gaps, which makes any warp answer off it a floor."""
    return run.has_gaps()
