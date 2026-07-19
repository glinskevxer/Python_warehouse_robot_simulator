"""The check that the readme and the script agree."""

from __future__ import annotations

from pathlib import Path

import pytest

from spikemaul.tools import check_readme
from spikemaul.tools.check_readme import groups, named_in, problems, readme


def test_the_readme_names_every_group_and_invents_none() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_groups_come_off_the_console_script() -> None:
    assert "line" in groups()
    assert "order" in groups()


def test_the_commands_are_read_out_of_backticks() -> None:
    found = named_in("run `line add` and then `order bulletin`")
    assert "line add" in found
    assert "order bulletin" in found


def test_the_readme_is_in_the_checkout() -> None:
    assert readme().name == "README.md"
    assert readme().exists()


def test_a_checkout_with_no_readme_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(check_readme, "project_root", lambda: tmp_path)
    found = [one.says for one in check_readme.problems()]
    assert found == ["there is no readme"]


def test_a_readme_that_names_a_command_the_script_does_not_have_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    every = " ".join(f"`{one}`" for one in sorted(groups()))
    (tmp_path / "README.md").write_text(f"{every} and `line reticulate`\n", encoding="utf-8")
    monkeypatch.setattr(check_readme, "project_root", lambda: tmp_path)
    found = [one.says for one in check_readme.problems()]
    assert any("which the script does not have" in one for one in found)
