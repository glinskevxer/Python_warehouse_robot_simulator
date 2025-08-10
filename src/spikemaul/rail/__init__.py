"""Rail: how worn it is, and when it was last looked inside.

Two questions with nothing in common except the rail they are about. Wear is
measured with a gauge on the head and answers what class the rail still holds.
Flaw testing is a cycle on tonnage with a calendar backstop and answers
whether the rail is legal to run over at all at this class.
"""

from spikemaul.rail.wear import WearReading, wear_findings

__all__ = ["WearReading", "wear_findings"]
