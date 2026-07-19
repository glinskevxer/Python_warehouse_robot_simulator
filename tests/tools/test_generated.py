"""The tools that write a document, run the way CI runs them.

Every one of these has a ``--check`` that CI depends on and a write that
somebody runs by hand, and neither is exercised by asking the functions
underneath. So these run ``main`` against a checkout in a temporary directory:
the document is missing, the check fails, the write puts it there, and the
check passes.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType

import pytest

from spikemaul.tools import build_docs, build_glossary, coverage_gate, schema_dump, smoke

WRITERS: list[ModuleType] = [schema_dump, build_docs, build_glossary]


def named(module: ModuleType) -> str:
    return module.__name__.rsplit(".", maxsplit=1)[-1]


@pytest.mark.parametrize("module", WRITERS, ids=named)
def test_a_missing_document_is_not_current_and_the_write_puts_it_there(
    module: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "project_root", lambda: tmp_path)
    assert not module.is_current()
    written = module.write()
    assert written.exists()
    assert module.is_current()


@pytest.mark.parametrize("module", WRITERS, ids=named)
def test_the_check_exits_one_where_the_document_is_stale(
    module: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(module, "project_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", [named(module), "--check"])
    with pytest.raises(SystemExit) as leaving:
        module.main()
    assert leaving.value.code == 1
    assert "is not what" in capsys.readouterr().out


@pytest.mark.parametrize("module", WRITERS, ids=named)
def test_the_check_exits_zero_once_the_document_has_been_written(
    module: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(module, "project_root", lambda: tmp_path)
    module.write()
    monkeypatch.setattr("sys.argv", [named(module), "--check"])
    with pytest.raises(SystemExit) as leaving:
        module.main()
    assert leaving.value.code == 0
    assert "is current" in capsys.readouterr().out


@pytest.mark.parametrize("module", WRITERS, ids=named)
def test_the_write_says_where_the_document_went(
    module: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(module, "project_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", [named(module)])
    module.main()
    assert "wrote" in capsys.readouterr().out


def test_the_walk_prints_what_it_did(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["smoke"])
    smoke.main()
    printed = capsys.readouterr().out
    assert "schema" in printed
    assert "morning page" in printed


def test_the_walk_says_only_that_it_finished_when_quiet(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["smoke", "--quiet"])
    smoke.main()
    assert capsys.readouterr().out.strip() == "smoke: the walk finished"


def a_report(tmp_path: Path, total: float) -> Path:
    where = tmp_path / "coverage.json"
    where.write_text(
        json.dumps(
            {
                "files": {"a.py": {"summary": {"percent_covered": total, "missing_lines": 1}}},
                "totals": {"percent_covered": total},
            }
        ),
        encoding="utf-8",
    )
    return where


def test_the_coverage_gate_exits_zero_over_the_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv", ["coverage_gate", "--report", str(a_report(tmp_path, 99.0)), "--worst", "1"]
    )
    with pytest.raises(SystemExit) as leaving:
        coverage_gate.main()
    assert leaving.value.code == 0
    assert "total 99.00%" in capsys.readouterr().out


def test_the_coverage_gate_exits_one_under_the_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["coverage_gate", "--report", str(a_report(tmp_path, 50.0))])
    with pytest.raises(SystemExit) as leaving:
        coverage_gate.main()
    assert leaving.value.code == 1
    assert "under the floor" in capsys.readouterr().out


def test_the_coverage_gate_reads_the_report_beside_the_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(coverage_gate, "project_root", lambda: tmp_path)
    a_report(tmp_path, 99.0)
    monkeypatch.setattr("sys.argv", ["coverage_gate"])
    with pytest.raises(SystemExit) as leaving:
        coverage_gate.main()
    assert leaving.value.code == 0
