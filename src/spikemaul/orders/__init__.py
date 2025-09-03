"""What a train is actually allowed to do, foot by foot.

Four things cap a speed and they do not know about each other: the class the
segment is held to, the curve the track is going round, any slow order in
force, and any heat restriction called that morning. A crew gets one number,
and it is the lowest of them at that foot of railroad.
"""

from spikemaul.orders.governing import SpeedPiece, profile

__all__ = ["SpeedPiece", "profile"]
