"""The people and gang commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from spikemaul.cli.main import cli


@pytest.fixture
def book(tmp_path: Path) -> str:
    where = str(tmp_path / "plains.sqlite3")
    CliRunner().invoke(cli, ["--book", where, "init"], obj={})
    return where


def run(book: str, *args: str) -> Result:
    return CliRunner().invoke(cli, ["--book", book, *args], obj={})


def with_an_inspector(book: str) -> Result:
    return run(
        book,
        "person",
        "add",
        "RSTIVERS",
        "R Stivers",
        "--craft",
        "inspector",
        "--for",
        "track,turnouts",
        "--until",
        "2025-12-31",
    )


def test_somebody_goes_on_the_books_with_a_designation(book: str) -> None:
    assert with_an_inspector(book).exit_code == 0
    listed = run(book, "--on", "2025-06-01", "person", "list")
    assert "PN-RSTIVERS" in listed.output
    assert "track, turnouts" in listed.output
    assert "2025-12-31" in listed.output


def test_a_designation_that_has_run_out_is_marked_lapsed(book: str) -> None:
    with_an_inspector(book)
    listed = run(book, "--on", "2026-06-01", "person", "list")
    assert "lapsed" in listed.output


def test_somebody_with_no_designation_goes_on_the_books(book: str) -> None:
    result = run(book, "person", "add", "JHOLT", "J Holt", "--craft", "trackman")
    assert result.exit_code == 0
    assert "no designation" not in result.output


def test_a_scope_this_railroad_does_not_have_exits_two(book: str) -> None:
    result = run(
        book,
        "person",
        "add",
        "RSTIVERS",
        "R Stivers",
        "--for",
        "drone survey",
        "--until",
        "2025-12-31",
    )
    assert result.exit_code == 2
    assert "is not a scope" in result.output


def test_a_designation_can_be_renewed(book: str) -> None:
    with_an_inspector(book)
    result = run(book, "person", "qualify", "RSTIVERS", "--until", "2026-12-31")
    assert result.exit_code == 0
    assert "2026-12-31" in run(book, "person", "list").output


def test_renewing_a_designation_backwards_exits_four(book: str) -> None:
    with_an_inspector(book)
    result = run(book, "person", "qualify", "RSTIVERS", "--until", "2025-01-01")
    assert result.exit_code == 4
    assert "already designated through" in result.output


def test_the_list_can_be_asked_for_one_scope(book: str) -> None:
    with_an_inspector(book)
    run(book, "person", "add", "JHOLT", "J Holt")
    listed = run(book, "person", "list", "--scope", "track")
    assert "RSTIVERS" in listed.output
    assert "JHOLT" not in listed.output


def test_a_gang_goes_in_with_its_foreman_and_machines(book: str) -> None:
    run(book, "person", "add", "DKEHOE", "D Kehoe", "--craft", "foreman")
    added = run(
        book,
        "gang",
        "add",
        "SEC2",
        "Section 2",
        "--foreman",
        "DKEHOE",
        "--headcount",
        "4",
        "--machines",
        "tamper, regulator",
        "--at",
        "Alden",
    )
    assert added.exit_code == 0
    listed = run(book, "gang", "list")
    assert "GG-SEC2" in listed.output
    assert "tamper, regulator" in listed.output
    assert "Alden" in listed.output


def test_a_gang_whose_foreman_is_not_on_the_books_exits_five(book: str) -> None:
    result = run(book, "gang", "add", "SEC2", "Section 2", "--foreman", "NOBODY")
    assert result.exit_code == 5


def test_a_machine_can_be_added_and_not_twice(book: str) -> None:
    run(book, "person", "add", "DKEHOE", "D Kehoe", "--craft", "foreman")
    run(book, "gang", "add", "SEC2", "Section 2", "--foreman", "DKEHOE")
    first = run(book, "gang", "machine", "SEC2", "spiker")
    assert first.exit_code == 0
    again = run(book, "gang", "machine", "SEC2", "spiker")
    assert again.exit_code == 4
    assert "already on" in again.output
