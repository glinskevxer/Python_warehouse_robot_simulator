"""The records the track department keeps, and nothing about storing them.

A record here validates itself on the way in and answers questions about
itself. It does not know what a book is, it does not know how it is printed,
and it holds no reference to a register. Everything that needs two records
together lives a layer up.
"""

from spikemaul.model.ids import Ident, Kind, next_number

__all__ = ["Ident", "Kind", "next_number"]
