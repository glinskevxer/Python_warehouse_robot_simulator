"""The pages the office prints, and the plain layout they are printed in.

Every report here is text in a fixed width, because that is what gets pinned
to the wall in the section house and faxed to the operating department. There
is no colour, no unicode drawing and no width that depends on a terminal.
"""

from spikemaul.report.layout import Page, Table, render

__all__ = ["Page", "Table", "render"]
