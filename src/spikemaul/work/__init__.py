"""Turning what was found into what the gang does.

A defect is a condition; a work order is a decision. This subpackage is where
the one becomes the other, and where the week's plan is built out of what the
gang can actually get through.
"""

from spikemaul.work.needs import Need, needs_from_defects

__all__ = ["Need", "needs_from_defects"]
