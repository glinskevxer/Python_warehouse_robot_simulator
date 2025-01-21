"""Quantities the railroad measures in, and nothing else.

Nothing in this subpackage knows what a segment or an inspection is. The rule
is that a unit can be constructed from a string an operator typed and printed
back in the form the paperwork uses, and that it refuses anything it cannot
represent exactly.
"""

from spikemaul.units.milepost import FEET_PER_MILE, Milepost

__all__ = ["FEET_PER_MILE", "Milepost"]
