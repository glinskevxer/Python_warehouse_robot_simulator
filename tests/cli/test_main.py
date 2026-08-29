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


def test_a_backup_is_taken_beside_the_book(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    run("--book", str(where), "init")
    result = run("--book", str(where), "--on", "2025-06-01", "backup")
    assert result.exit_code == 0
    assert "reads clean" in result.output
    assert (tmp_path / "plains-2025-06-01.sqlite3").exists()


def test_a_backup_can_be_told_where_to_go(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    run("--book", str(where), "init")
    onto = tmp_path / "copies" / "monday.sqlite3"
    result = run("--book", str(where), "backup", "--to", str(onto))
    assert result.exit_code == 0
    assert onto.exists()


def test_a_second_backup_to_the_same_place_exits_five(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    run("--book", str(where), "init")
    onto = tmp_path / "monday.sqlite3"
    run("--book", str(where), "backup", "--to", str(onto))
    again = run("--book", str(where), "backup", "--to", str(onto))
    assert again.exit_code == 5
    assert "already a backup" in again.output


def test_the_book_is_written_out_as_one_csv_per_table(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    run("--book", str(where), "init")
    into = tmp_path / "csv"
    result = run("--book", str(where), "export", str(into))
    assert result.exit_code == 0
    assert (into / "segments.csv").exists()
    assert "segments:" in result.output


def test_exporting_twice_into_the_same_directory_exits_five(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    run("--book", str(where), "init")
    into = tmp_path / "csv"
    run("--book", str(where), "export", str(into))
    again = run("--book", str(where), "export", str(into))
    assert again.exit_code == 5


def test_a_search_finds_a_record_by_its_number(tmp_path: Path) -> None:
    where = str(tmp_path / "plains.sqlite3")
    run("--book", where, "init")
    run("--book", where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    result = run("--book", where, "find", "SD-PLAINS")
    assert result.exit_code == 0
    assert "subdivision" in result.output


def test_a_search_that_finds_nothing_says_so(tmp_path: Path) -> None:
    where = str(tmp_path / "plains.sqlite3")
    run("--book", where, "init")
    result = run("--book", where, "find", "nothing here")
    assert "nothing in the book matches" in result.output


def a_worked_book(tmp_path: Path) -> str:
    where = str(tmp_path / "plains.sqlite3")
    run("--book", where, "init")
    run("--book", where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    run("--book", where, "line", "segment", "PLAINS", "014", "0.00-120.00", "--laid", "1998-06-01")
    return where


def test_verify_says_nothing_is_wrong_with_a_covered_book(tmp_path: Path) -> None:
    where = a_worked_book(tmp_path)
    result = run("--book", where, "--on", "2025-05-20", "verify")
    assert result.exit_code == 0
    assert "PLAINS: 0 holes" in result.output
    assert "schema" in result.output


def test_verify_says_nothing_at_all_when_told_to_be_quiet(tmp_path: Path) -> None:
    where = a_worked_book(tmp_path)
    result = run("--book", where, "--on", "2025-05-20", "verify", "--quiet")
    assert result.exit_code == 0
    assert result.output.strip() == "verify: nothing to put right"


def test_verify_exits_one_where_the_records_leave_a_hole(tmp_path: Path) -> None:
    where = str(tmp_path / "plains.sqlite3")
    run("--book", where, "init")
    run("--book", where, "line", "add", "PLAINS", "Plains", "--end", "120.00")
    result = run("--book", where, "--on", "2025-05-20", "verify")
    assert result.exit_code == 1
    assert "no segment covers it" in result.output
    assert "things to put right" in result.output


def test_verify_says_so_where_the_book_holds_nothing(tmp_path: Path) -> None:
    where = str(tmp_path / "plains.sqlite3")
    run("--book", where, "init")
    result = run("--book", where, "verify")
    assert result.exit_code == 0
    assert "holds no subdivisions" in result.output


def test_the_book_can_come_from_the_environment(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    runner = CliRunner(env={"SPIKEMAUL_BOOK": str(where)})
    made = runner.invoke(cli, ["init"], obj={})
    assert made.exit_code == 0
    assert where.exists()
    listed = runner.invoke(cli, ["status"], obj={})
    assert "subdivisions" in listed.output


def test_the_option_wins_over_the_environment(tmp_path: Path) -> None:
    named = tmp_path / "named.sqlite3"
    runner = CliRunner(env={"SPIKEMAUL_BOOK": str(tmp_path / "environment.sqlite3")})
    made = runner.invoke(cli, ["--book", str(named), "init"], obj={})
    assert made.exit_code == 0
    assert named.exists()
    assert not (tmp_path / "environment.sqlite3").exists()


def test_the_version_the_script_prints_is_the_package_version() -> None:
    result = run("--version")
    assert "1.0.0" in result.output
