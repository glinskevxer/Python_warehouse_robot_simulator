"""The limits, and only the limits.

Everything in this subpackage is a table out of the rule book or the
railroad's own standard practice, plus the arithmetic needed to read it. No
record, no book, no report. The point of keeping them here is that when the
limits are argued about, there is one file to argue over.
"""

from spikemaul.standards.classes import ClassOfTrack, Traffic, class_for_speed, speed_limit

__all__ = ["ClassOfTrack", "Traffic", "class_for_speed", "speed_limit"]
