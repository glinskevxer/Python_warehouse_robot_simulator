"""The console script: the book option, the day option and the exit statuses."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from spikemaul import __version__
from spikemaul.cli.clock import today
from spikemaul.cli.common import as_day, status_for
from spikemaul.cli.main import cli
from spikemaul.errors import BookError, InputError, NotFoundError, RuleError


def run(*args: str) -> Result:
    return CliRunner().invoke(cli, list(args), obj={})


def test_the_script_says_its_version() -> None:
    result = run("--version")
    assert result.exit_code == 0
    assert __version__ in result.output


def test_a_book_is_made_where_there_is_none(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    result = run("--book", str(where), "init")
    assert result.exit_code == 0
    assert where.exists()
    assert "schema" in result.output


def test_status_says_what_is_in_the_book(tmp_path: Path) -> None:
    where = str(tmp_path / "plains.sqlite3")
    run("--book", where, "init")
    result = run("--book", where, "status")
    assert result.exit_code == 0
    assert "subdivisions" in result.output


def test_a_book_that_is_not_there_exits_five(tmp_path: Path) -> None:
    result = run("--book", str(tmp_path / "nothing.sqlite3"), "status")
    assert result.exit_code == 5
    assert "there is no book" in result.output


def test_a_day_that_is_not_a_day_exits_two(tmp_path: Path) -> None:
    result = run("--book", str(tmp_path / "x.sqlite3"), "--on", "yesterday", "init")
    assert result.exit_code == 2
    assert "is not a day" in result.output


def test_the_day_is_read_as_an_iso_date() -> None:
    assert as_day("2025-05-06") == date(2025, 5, 6)
    assert as_day(None) is None
    with pytest.raises(InputError, match="is not a day"):
        as_day("06/05/2025")


def test_every_kind_of_failure_has_its_own_status() -> None:
    assert status_for(InputError("x")) == 2
    assert status_for(NotFoundError("segment", "SG-014")) == 3
    assert status_for(RuleError("x")) == 4
    assert status_for(BookError("x")) == 5


def test_the_clock_is_only_asked_when_no_day_is_given() -> None:
    assert isinstance(today(), date)


def test_the_book_defaults_to_a_file_in_this_directory(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"], obj={})
        assert result.exit_code == 0
        assert Path("spikemaul.sqlite3").exists()
