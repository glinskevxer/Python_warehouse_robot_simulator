"""Marking up a run with what the book knows about the curves.

The file the geometry car hands over does not know where the curves are. It
has a crosslevel channel, and on a curve that channel is reading the elevation
the track is carrying, which is supposed to be there. Judged as tangent
crosslevel every curve on the railroad is an exception, and judged with no
designated elevation to compare against, no curve is ever wrong.

So the run is marked up from the curve register before it is read: each
station is told whether it is in a curve, whether it is in a spiral, and what
elevation the chart says the track should be carrying there. The elevation in
a spiral is run in proportionally, which is what the section gang built and
what the chart means.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from spikemaul.model.curve import Curve
from spikemaul.model.reading import Reading, Run
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost


def curve_at(curves: list[Curve], post: Milepost) -> Curve | None:
    """The curve a milepost falls in, spirals included, or nothing."""
    for curve in curves:
        if curve.holds(post):
            return curve
    return None


def designated_at(curve: Curve, post: Milepost) -> Inches:
    """The elevation the chart says the track carries at that milepost.

    In the body of the curve that is the curve's elevation. In a spiral it is
    run in from nothing to full elevation across the spiral's length, rounded
    to the sixteenth the track level reads.
    """
    if not curve.holds(post):
        raise ValueError(f"MP {post} is not in {curve.ident}")
    if curve.body.contains(post) or post == curve.body.end:
        return curve.elevation
    whole = curve.elevation.sixteenths
    if post < curve.body.begin:
        run_in = curve.entry_spiral_feet
        along = curve.span.begin.nominal_feet_to(post)
    else:
        run_in = curve.exit_spiral_feet
        along = post.nominal_feet_to(curve.span.end)
    if run_in <= 0:
        return curve.elevation
    part = Decimal(along) / Decimal(run_in)
    return Inches(int(Decimal(whole) * part))


def mark_up(run: Run, curves: list[Curve]) -> Run:
    """The same run with every station told what the chart says about it."""
    marked: list[Reading] = []
    for reading in run.readings:
        curve = curve_at(curves, reading.at)
        if curve is None:
            marked.append(replace(reading, on_curve=False, designated_elevation=None))
            continue
        marked.append(
            replace(
                reading,
                on_curve=True,
                designated_elevation=designated_at(curve, reading.at),
            )
        )
    return Run(
        inspection=run.inspection,
        subdivision=run.subdivision,
        on=run.on,
        readings=marked,
    )


def in_spiral(curves: list[Curve], post: Milepost) -> bool:
    """Whether a milepost is in a spiral rather than the body of a curve."""
    curve = curve_at(curves, post)
    return curve is not None and curve.in_spiral(post)
