"""The coverage gate, which reads a report rather than running the tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spikemaul.tools.coverage_gate import Coverage, FileCoverage, gate, read


def a_report(tmp_path: Path, files: dict[str, float], total: float) -> Path:
    where = tmp_path / "coverage.json"
    where.write_text(
        json.dumps(
            {
                "files": {
                    name: {"summary": {"percent_covered": percent, "missing_lines": 3}}
                    for name, percent in files.items()
                },
                "totals": {"percent_covered": total},
            }
        ),
        encoding="utf-8",
    )
    return where


def test_a_report_is_read_into_files_and_a_total(tmp_path: Path) -> None:
    got = read(a_report(tmp_path, {"a.py": 100.0, "b.py": 40.0}, 82.5))
    assert got.total == 82.5
    assert [one.name for one in got.files] == ["a.py", "b.py"]


def test_a_report_that_is_not_there_stops_the_gate(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="there is no coverage report"):
        read(tmp_path / "nothing.json")


def test_a_report_over_both_floors_passes() -> None:
    coverage = Coverage(98.0, [FileCoverage("a.py", 96.0, 2)])
    status, lines = gate(coverage, 95.0, 80.0, 0)
    assert status == 0
    assert lines[0].startswith("total 98.00%")


def test_a_total_under_the_floor_fails_and_says_by_how_much() -> None:
    coverage = Coverage(90.0, [FileCoverage("a.py", 90.0, 2)])
    status, lines = gate(coverage, 95.0, 80.0, 0)
    assert status == 1
    assert any("under the floor by 5.00" in one for one in lines)


def test_one_thin_file_fails_a_report_that_is_high_overall() -> None:
    coverage = Coverage(98.0, [FileCoverage("a.py", 100.0, 0), FileCoverage("b.py", 40.0, 30)])
    status, lines = gate(coverage, 95.0, 80.0, 0)
    assert status == 1
    assert any("under the file floor" in one and "b.py" in one for one in lines)


def test_the_thinnest_files_are_listed_fewest_first() -> None:
    coverage = Coverage(
        99.0,
        [
            FileCoverage("a.py", 100.0, 0),
            FileCoverage("b.py", 90.0, 4),
            FileCoverage("c.py", 95.0, 2),
        ],
    )
    _, lines = gate(coverage, 95.0, 80.0, 2)
    listed = [one for one in lines if one.startswith("  ")]
    assert "b.py" in listed[0]
    assert "c.py" in listed[1]


def test_a_file_line_says_the_percent_and_what_is_missing() -> None:
    assert "40.00%" in FileCoverage("b.py", 40.0, 30).describe()
    assert "30 missing" in FileCoverage("b.py", 40.0, 30).describe()
