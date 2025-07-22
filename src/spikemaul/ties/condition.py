"""One thirty nine foot length of track, and what its ties will hold.

Three rules apply to the same length and they are not the same rule. Enough
good ties, no long run of bad ones, and a good tie beside every joint. Each
caps the class independently, and the length holds the lowest of the three.

The joint rule is the one that surprises people. A length can hold fourteen
good ties out of a needed twelve and still be a defect, because two of the bad
ones are the pair either side of a joint, and a joint with nothing under it is
where the rail ends start working against each other. This railroad holds a
length with an unsupported joint to excepted track, and one with two of them
to nothing, which is stricter than the count rule alone and is written down
here so it can be argued with.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.errors import InputError
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.ties import (
    class_for_consecutive_defective,
    class_for_tie_count,
    required_ties,
)
from spikemaul.units.curvature import TANGENT, Curvature
from spikemaul.units.milepost import Milepost


@dataclass(frozen=True)
class TieLength:
    """What the inspector wrote down for one thirty nine foot length."""

    at: Milepost
    total: int
    good: int
    longest_run: int
    joints: int = 0
    joints_supported: int = 0
    curve: Curvature = TANGENT

    def __post_init__(self) -> None:
        if self.total < 1:
            raise InputError(f"a length at MP {self.at} with no ties in it is not a count")
        if self.good < 0 or self.good > self.total:
            raise InputError(f"{self.good} good ties out of {self.total} is not a count")
        if self.longest_run < 0 or self.longest_run > self.total - self.good:
            raise InputError(
                f"a run of {self.longest_run} is longer than the {self.total - self.good} "
                "defective ties in the length"
            )
        if self.joints < 0 or self.joints_supported < 0:
            raise InputError("a joint count is not negative")
        if self.joints_supported > self.joints:
            raise InputError("more joints have a good tie beside them than there are joints")

    @property
    def defective(self) -> int:
        """Ties in the length that are no good."""
        return self.total - self.good

    @property
    def unsupported_joints(self) -> int:
        """Joints with no good tie within two feet of them."""
        return self.joints - self.joints_supported

    def meets_count(self) -> ClassOfTrack | None:
        """The class the number of good ties holds, curve allowance included."""
        return class_for_tie_count(self.good, self.curve)

    def meets_run(self) -> ClassOfTrack | None:
        """The class the longest run of defective ties holds."""
        return class_for_consecutive_defective(self.longest_run)

    def meets_joints(self) -> ClassOfTrack | None:
        """The class the joint support holds, which is this railroad's own rule."""
        if self.unsupported_joints == 0:
            return ClassOfTrack.FIVE
        if self.unsupported_joints == 1:
            return ClassOfTrack.EXCEPTED
        return None

    def short_by(self, track_class: ClassOfTrack) -> int:
        """How many more good ties this length needs to hold a class."""
        return max(required_ties(track_class, self.curve) - self.good, 0)

    def describe(self) -> str:
        """One line for the tie survey."""
        return (
            f"MP {self.at} {self.good} of {self.total} good, run of {self.longest_run}, "
            f"{self.unsupported_joints} joints unsupported"
        )


def class_supported(length: TieLength) -> ClassOfTrack | None:
    """The lowest class the three rules leave, which is what the length holds."""
    answers = [length.meets_count(), length.meets_run(), length.meets_joints()]
    if any(one is None for one in answers):
        return None
    return min(one for one in answers if one is not None)


def governing_rule(length: TieLength) -> str:
    """Which of the three rules is holding the length down."""
    held = class_supported(length)
    named = (
        ("count", length.meets_count()),
        ("run", length.meets_run()),
        ("joints", length.meets_joints()),
    )
    for name, answer in named:
        if answer == held:
            return name
    return "count"
