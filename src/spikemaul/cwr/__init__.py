"""Continuous welded rail: what temperature it was laid at, and what that
means on a hot afternoon.

Jointed rail moves at the joints. Welded rail cannot, so what would have been
movement is force instead, and the force depends on how far the rail is from
the temperature it was fastened down at. That temperature is the one number
this whole subpackage turns on, and it is a record rather than a measurement:
nobody can go and read it off the rail later.
"""

from spikemaul.cwr.neutral import Destress, neutral_at

__all__ = ["Destress", "neutral_at"]
