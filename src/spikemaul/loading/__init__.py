"""Reading the files other people's machines hand over.

The geometry car and the rail flaw detector are contract services and what
arrives is a csv with somebody else's column names on it. Everything in here
turns one of those into records, and refuses a file it cannot read rather than
loading the half of it that parsed.
"""

from spikemaul.loading.runs import read_run

__all__ = ["read_run"]
