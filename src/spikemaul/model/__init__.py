"""The records the track department keeps, and nothing about storing them.

A record here validates itself on the way in and answers questions about
itself. It does not know what a book is, it does not know how it is printed,
and it holds no reference to a register. Everything that needs two records
together lives a layer up.
"""

from spikemaul.model.crew import Craft, Gang, Person
from spikemaul.model.curve import Curve
from spikemaul.model.defect import Condition, Defect
from spikemaul.model.ids import Ident, Kind, next_number
from spikemaul.model.inspection import Inspection, Method, Scope
from spikemaul.model.line import Segment, Subdivision
from spikemaul.model.order import Reason, SlowOrder
from spikemaul.model.reading import Reading, Run
from spikemaul.model.side import Hand
from spikemaul.model.structure import Bridge, Crossing, Structure, Surface, WarningDevice
from spikemaul.model.turnout import FrogKind, Throw, Turnout
from spikemaul.model.work import WorkKind, WorkOrder

__all__ = [
    "Bridge",
    "Condition",
    "Craft",
    "Crossing",
    "Curve",
    "Defect",
    "FrogKind",
    "Gang",
    "Hand",
    "Ident",
    "Inspection",
    "Kind",
    "Method",
    "Person",
    "Reading",
    "Reason",
    "Run",
    "Scope",
    "Segment",
    "SlowOrder",
    "Structure",
    "Subdivision",
    "Surface",
    "Throw",
    "Turnout",
    "WarningDevice",
    "WorkKind",
    "WorkOrder",
    "next_number",
]
