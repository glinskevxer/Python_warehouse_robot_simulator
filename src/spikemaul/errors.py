"""Every exception this package raises on purpose.

The rule is that a caller can tell three things apart without reading a
message: the operator typed something wrong, the book does not hold what was
asked for, and the railroad's own rules refuse the thing being asked. The CLI
turns the first into an exit status of 2, the second into 3 and the third into
4, so the distinction has to survive being caught.
"""

from __future__ import annotations


class SpikemaulError(Exception):
    """Base for everything raised here.

    Carries a short machine readable ``code`` alongside the message so a
    caller that is formatting a report does not have to match on prose.
    """

    code = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class InputError(SpikemaulError):
    """The value handed in is not one this package can work with.

    Raised before anything is read or written. A milepost that will not parse,
    a negative tonnage, a class of track that does not exist.
    """

    code = "input"


class NotFoundError(SpikemaulError):
    """The book does not hold the record that was asked for."""

    code = "not_found"

    def __init__(self, kind: str, ident: str) -> None:
        super().__init__(f"no {kind} {ident} in the book")
        self.kind = kind
        self.ident = ident


class DuplicateError(SpikemaulError):
    """A record with that identifier is already in the book."""

    code = "exists"

    def __init__(self, kind: str, ident: str) -> None:
        super().__init__(f"{kind} {ident} is already in the book")
        self.kind = kind
        self.ident = ident


class RuleError(SpikemaulError):
    """The railroad's own rules refuse this.

    A curve elevated past what the class allows, a slow order that comes off
    before it goes on, a segment put back in service with an open defect that
    the rule says has to be repaired first.
    """

    code = "rule"


class BookError(SpikemaulError):
    """The book itself is wrong: missing, unreadable, or at a schema this
    version of the package does not know how to read."""

    code = "book"
