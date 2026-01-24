"""The checks CI runs against this tree.

Every one of them is a module with a ``problems()`` function returning a list
of strings and a ``main()`` that prints them and exits one if there are any.
They are run in CI beside the tests, and they exist because the things they
check are the things reviews keep catching: a module with no docstring, a
layer importing upwards, a test whose name says nothing.

They read the tree they are installed from, so running them against a
different checkout is not something to do by accident.
"""

from spikemaul.tools.sources import Problem, report

__all__ = ["Problem", "report"]
