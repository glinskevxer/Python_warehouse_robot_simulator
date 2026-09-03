"""The check that CI runs every check."""

from __future__ import annotations

from pathlib import Path

import pytest

from spikemaul.tools import check_workflow
from spikemaul.tools.check_workflow import (
    NOT_RUN,
    PYTHONS,
    check_modules,
    problems,
    workflow,
)


def test_the_workflow_runs_every_check_in_this_package() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_checks_are_the_modules_under_tools() -> None:
    found = check_modules()
    assert "check_layers" in found
    assert "check_sql" in found
    assert "sources" not in found


def test_the_tools_that_are_not_checks_are_named() -> None:
    assert "sources" in NOT_RUN
    assert "smoke" in NOT_RUN


def test_the_workflow_is_where_the_repository_keeps_it() -> None:
    assert workflow().exists()
    assert workflow().name == "ci.yml"


def test_every_check_module_is_named_in_the_workflow_text() -> None:
    text = workflow().read_text(encoding="utf-8")
    for name in check_modules():
        assert f"spikemaul.tools.{name}" in text


def test_the_tests_are_run_on_both_interpreters() -> None:
    text = workflow().read_text(encoding="utf-8")
    for version in PYTHONS:
        assert f'"{version}"' in text
    assert "3.13" in PYTHONS


def test_a_checkout_with_no_workflow_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(check_workflow, "project_root", lambda: tmp_path)
    found = [one.says for one in check_workflow.problems()]
    assert found == ["there is no workflow"]


def test_a_workflow_that_misses_a_check_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "ci.yml").parent.mkdir(parents=True, exist_ok=True)
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    monkeypatch.setattr(check_workflow, "project_root", lambda: tmp_path)
    found = [one.says for one in check_workflow.problems()]
    assert any("does not run spikemaul.tools.check_layers" in one for one in found)
    assert any("does not check schema_dump is current" in one for one in found)
    assert any("floor under the coverage" in one for one in found)
    assert any("does not run the tests on 3.13" in one for one in found)


def test_the_walk_lines_are_the_ones_that_call_the_script() -> None:
    lines = check_workflow.walk_lines()
    assert lines
    assert all(one.startswith("spikemaul ") for one in lines)
    assert any("report morning" in one for one in lines)


def test_a_line_continued_over_two_rows_is_read_as_one() -> None:
    joined = [one for one in check_workflow.walk_lines() if "--laid" in one]
    assert joined
    assert all("\\" not in one for one in joined)


def test_the_commands_the_walk_calls_stop_at_the_first_argument() -> None:
    found = check_workflow.walk_commands()
    assert ["line", "add", "PLAINS", "Plains"] in found
    assert ["init"] in found


def test_every_command_the_walk_calls_is_on_the_script() -> None:
    assert [one.says for one in check_workflow.walk_problems()] == []


def test_a_walk_calling_a_command_that_went_away_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "jobs:\n  walk:\n    steps:\n      - run: |\n"
        '          spikemaul --book "$book" order cost PLAINS 12.00-16.00\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(check_workflow, "project_root", lambda: tmp_path)
    found = [one.says for one in check_workflow.walk_problems()]
    assert any("which is not a command" in one for one in found)
