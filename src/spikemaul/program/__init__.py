"""The inspection program: what is due, what is late, and what did not count.

Compliance is not about defects. It is about whether every piece of railroad
was looked at inside its cycle by somebody designated to look at it, and the
awkward part is the last clause.
"""

from spikemaul.program.compliance import Standing, standing_for

__all__ = ["Standing", "standing_for"]
