"""What the restrictions cost in running time.

The operating department asks this question in dollars and the track
department can only answer it in minutes, so minutes is what this computes. A
train that would run a stretch at forty and runs it at ten loses the
difference, and the number is worth having because it decides which of eleven
open slow orders the surfacing gang goes to first.

Two things are left out on purpose. Acceleration and braking either side of a
restriction, which are real and which this railroad's trains do slowly enough
that the office rule of thumb is a minute a restriction, added separately by
whoever wants it. And restricted speed, which has no running time at all, so a
stretch under it is reported as unpriced rather than given a number.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.errors import InputError
from spikemaul.orders.governing import SpeedPiece
from spikemaul.units.speed import Speed

APPROACH_MINUTES = 1.0
"""The office rule of thumb for slowing down and getting back up to speed."""


@dataclass(frozen=True)
class RunningTime:
    """Minutes over a stretch, and the part of it nobody can price."""

    minutes: float
    unpriced_miles: float

    @property
    def is_complete(self) -> bool:
        """Whether every mile of the stretch could be priced."""
        return self.unpriced_miles == 0

    def describe(self) -> str:
        """One line for the running time page."""
        if self.is_complete:
            return f"{self.minutes:.1f} minutes"
        return f"{self.minutes:.1f} minutes plus {self.unpriced_miles} miles at restricted speed"


def running_time(pieces: list[SpeedPiece]) -> RunningTime:
    """Minutes to run a profile, with restricted speed left unpriced."""
    minutes = 0.0
    unpriced = 0.0
    for piece in pieces:
        if piece.speed.is_restricted:
            unpriced += float(piece.span.miles)
            continue
        minutes += piece.speed.minutes_over(float(piece.span.miles))
    return RunningTime(minutes=minutes, unpriced_miles=unpriced)


def minutes_lost(pieces: list[SpeedPiece], timetable: Speed) -> float:
    """Minutes the restrictions cost against running the lot at timetable speed.

    Only the pieces slower than the timetable count. A piece already at
    timetable speed costs nothing, and a piece somehow faster is a mistake in
    the records rather than a saving.
    """
    if timetable.is_restricted:
        raise InputError("a timetable speed of restricted is not a speed to compare against")
    lost = 0.0
    for piece in pieces:
        if piece.speed >= timetable:
            continue
        if piece.speed.is_restricted:
            raise InputError(
                f"{piece.span} is at restricted speed, which has no running time to lose"
            )
        miles = float(piece.span.miles)
        lost += piece.speed.minutes_over(miles) - timetable.minutes_over(miles)
    return lost


def cost_of(pieces: list[SpeedPiece], timetable: Speed, with_approach: bool = True) -> float:
    """Minutes lost including the rule of thumb for slowing and speeding up."""
    slower = [one for one in pieces if one.speed < timetable]
    approach = APPROACH_MINUTES * len(slower) if with_approach else 0.0
    return minutes_lost(pieces, timetable) + approach


def ranked_by_cost(
    pieces: list[SpeedPiece], timetable: Speed, with_approach: bool = True
) -> list[tuple[SpeedPiece, float]]:
    """Every restricted piece with what it costs, dearest first."""
    out = []
    for piece in pieces:
        if piece.speed >= timetable or piece.speed.is_restricted:
            continue
        cost = cost_of([piece], timetable, with_approach)
        out.append((piece, cost))
    return sorted(out, key=lambda pair: (-pair[1], pair[0].span.begin.hundredths))
