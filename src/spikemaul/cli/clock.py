"""The one place in this package that asks what day it is.

Every function below the command line takes the day as an argument. That is
not tidiness, it is what makes the reports reproducible: a compliance page for
the fourteenth has to say the same thing whether it is printed on the
fourteenth or reprinted in November for an inspector.

So there is exactly one call to the system clock in the package, it is here,
and ``spikemaul.tools.check_clock`` fails the build if a second one appears.
"""

from __future__ import annotations

from datetime import UTC, date, datetime


def today() -> date:
    """The day this command is being run on."""
    return datetime.now(tz=UTC).date()
