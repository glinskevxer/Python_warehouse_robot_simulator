"""Reading a geometry run against the limits for a class of track.

Nothing here writes anything down. It takes a run, a class the track is being
held to, and hands back what is outside the limits and what class each of
those readings does meet. Whether that becomes a defect card, a slow order or
a phone call is somebody else's decision.
"""

from spikemaul.geometry.finding import Finding, findings

__all__ = ["Finding", "findings"]
