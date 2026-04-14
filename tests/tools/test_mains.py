"""Every check has been seen to fire.

A check that has only ever passed has not been tested, it has been watched.
These run each one twice: once with nothing to report, which has to exit zero,
and once with something, which has to exit one and print it. The checks
themselves are tested against real broken files in their own test files; this
is about the two lines at the bottom of each module that everybody writes from
memory.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from spikemaul.tools import (
    check_clock,
    check_design,
    check_docstrings,
    check_exports,
    check_help,
    check_layers,
    check_messages,
    check_naming,
    check_package,
    check_readme,
    check_sql,
    check_tests,
    check_wiring,
    check_workflow,
)
from spikemaul.tools.check_workflow import GENERATED, check_modules
from spikemaul.tools.sources import Problem

CHECKS: list[ModuleType] = [
    check_clock,
    check_design,
    check_docstrings,
    check_exports,
    check_help,
    check_layers,
    check_messages,
    check_naming,
    check_package,
    check_readme,
    check_sql,
    check_tests,
    check_wiring,
    check_workflow,
]


def named(module: ModuleType) -> str:
    return module.__name__.rsplit(".", maxsplit=1)[-1]


@pytest.mark.parametrize("module", CHECKS, ids=named)
def test_a_check_with_nothing_to_report_exits_zero(
    module: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(module, "problems", list)
    if hasattr(module, "mirrored"):
        monkeypatch.setattr(module, "mirrored", list)
    with pytest.raises(SystemExit) as leaving:
        module.main()
    assert leaving.value.code == 0
    assert "nothing to report" in capsys.readouterr().out


@pytest.mark.parametrize("module", CHECKS, ids=named)
def test_a_check_with_something_to_report_exits_one(
    module: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def found() -> list[Problem]:
        return [Problem(Path("a.py"), 3, "something")]

    monkeypatch.setattr(module, "problems", found)
    if hasattr(module, "mirrored"):
        monkeypatch.setattr(module, "mirrored", list)
    with pytest.raises(SystemExit) as leaving:
        module.main()
    assert leaving.value.code == 1
    printed = capsys.readouterr().out
    assert "a.py:3 something" in printed
    assert "1 to fix" in printed


def test_every_check_module_in_the_package_is_run_here() -> None:
    plain = [one for one in check_modules() if one not in GENERATED]
    assert sorted(named(one) for one in CHECKS) == plain
