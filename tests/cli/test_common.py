"""What every command shares: the day, the book path and the exit statuses."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from spikemaul.cli.common import (
    BOOK_VARIABLE,
    DEFAULT_BOOK,
    as_day,
    as_ident,
    book_path,
    status_for,
)
from spikemaul.errors import BookError, DuplicateError, InputError, NotFoundError, RuleError
from spikemaul.model.ids import Kind


def test_a_day_is_read_as_an_iso_date() -> None:
    assert as_day("2025-05-06") == date(2025, 5, 6)
    assert as_day(None) is None


def test_a_day_in_another_format_is_refused() -> None:
    with pytest.raises(InputError, match="write it as 2025-05-06"):
        as_day("06/05/2025")


def test_a_record_number_is_read_for_the_kind_expected() -> None:
    assert as_ident("SG-014", Kind.SEGMENT).tail == "014"
    with pytest.raises(InputError, match="not a segment one"):
        as_ident("DF-2025-0142", Kind.SEGMENT)


def test_the_book_path_falls_back_to_the_name_in_this_directory() -> None:
    assert book_path(None) == DEFAULT_BOOK
    assert book_path("/tmp/plains.sqlite3") == str(Path("/tmp/plains.sqlite3"))


def test_every_kind_of_failure_has_its_own_exit_status() -> None:
    assert status_for(InputError("x")) == 2
    assert status_for(NotFoundError("segment", "SG-014")) == 3
    assert status_for(DuplicateError("segment", "SG-014")) == 4
    assert status_for(RuleError("x")) == 4
    assert status_for(BookError("x")) == 5


def test_the_environment_variable_is_the_one_a_cron_job_would_set() -> None:
    assert BOOK_VARIABLE == "SPIKEMAUL_BOOK"
