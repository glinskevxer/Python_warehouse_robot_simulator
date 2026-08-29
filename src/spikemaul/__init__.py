"""Track department records and rules for a shortline railroad.

The package is layered. Nothing in ``units`` knows about a record, nothing in
``model`` knows about storage, and nothing below ``cli`` prints. The layering
is checked by ``spikemaul.tools.check_layers`` rather than left to memory.
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
