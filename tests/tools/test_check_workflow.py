"""The check that CI runs every check."""

from __future__ import annotations

from spikemaul.tools.check_workflow import NOT_RUN, check_modules, problems, workflow


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
