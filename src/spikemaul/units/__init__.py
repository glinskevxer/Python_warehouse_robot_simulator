"""Quantities the railroad measures in, and nothing else.

Nothing in this subpackage knows what a segment or an inspection is. The rule
is that a unit can be constructed from a string an operator typed and printed
back in the form the paperwork uses, and that it refuses anything it cannot
represent exactly.
"""

from spikemaul.units.chainage import Chainage, Equation, Stretch
from spikemaul.units.curvature import Curvature, equilibrium_elevation, maximum_speed
from spikemaul.units.measure import STANDARD_GAUGE, Inches, gauge_deviation, widest
from spikemaul.units.milepost import FEET_PER_MILE, Milepost
from spikemaul.units.span import Span, merge_all, subtract_all, total_miles
from spikemaul.units.speed import Speed, minutes_lost, slowest

__all__ = [
    "FEET_PER_MILE",
    "STANDARD_GAUGE",
    "Chainage",
    "Curvature",
    "Equation",
    "Inches",
    "Milepost",
    "Span",
    "Speed",
    "Stretch",
    "equilibrium_elevation",
    "gauge_deviation",
    "maximum_speed",
    "merge_all",
    "minutes_lost",
    "slowest",
    "subtract_all",
    "total_miles",
    "widest",
]
