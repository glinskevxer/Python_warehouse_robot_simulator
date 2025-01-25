"""Quantities the railroad measures in, and nothing else.

Nothing in this subpackage knows what a segment or an inspection is. The rule
is that a unit can be constructed from a string an operator typed and printed
back in the form the paperwork uses, and that it refuses anything it cannot
represent exactly.
"""

from spikemaul.units.milepost import FEET_PER_MILE, Milepost
from spikemaul.units.span import Span, merge_all, subtract_all, total_miles

__all__ = ["FEET_PER_MILE", "Milepost", "Span", "merge_all", "subtract_all", "total_miles"]
