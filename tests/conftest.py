"""What every test in this suite gets whether it asks or not.

The books are the reason this file exists. A test that opens one and does not
close it leaves an sqlite connection to be collected whenever the interpreter
gets round to it, and on python 3.13 that is a ResourceWarning, which this
suite turns into an error because ``filterwarnings`` is set to error. The
warning is not raised by the test that leaked, it is raised by whichever test
happens to be running when the collector runs, so the failure moves around and
points at innocent code.

So every book opened during a test is closed at the end of it, here, once. The
package itself is unchanged: closing a book is the caller's job and
:class:`spikemaul.store.book.Book` is a context manager for exactly that.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from spikemaul.store import book as book_module


@pytest.fixture(autouse=True)
def close_every_book(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Close any book a test opened, however it opened it."""
    opened: list[book_module.Book] = []
    real = book_module.open_book

    def watched(*args: Any, **kwargs: Any) -> book_module.Book:
        made = real(*args, **kwargs)
        opened.append(made)
        return made

    monkeypatch.setattr(book_module, "open_book", watched)
    for name in ("records", "migrations"):
        module = __import__(f"spikemaul.store.{name}", fromlist=["open_book"])
        if hasattr(module, "open_book"):
            monkeypatch.setattr(module, "open_book", watched, raising=False)
    yield
    for made in opened:
        made.close()
