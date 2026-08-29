"""The generated command reference."""

from __future__ import annotations

from spikemaul import __version__
from spikemaul.tools.build_docs import DOCUMENT, build, is_current, where


def test_the_document_on_disk_is_what_the_script_would_write() -> None:
    assert is_current(), f"{DOCUMENT} is stale, run python -m spikemaul.tools.build_docs"


def test_every_group_on_the_script_is_in_the_document() -> None:
    text = build()
    for name in ("## line", "## order", "## defect", "## report", "## ties"):
        assert name in text


def test_a_command_carries_its_arguments_and_options() -> None:
    text = build()
    assert "### line segment" in text
    assert "`--laid`, required" in text
    assert "`SPAN`, required" in text


def test_the_top_level_options_are_at_the_top() -> None:
    text = build()
    assert text.index("`--book`") < text.index("## bridge")


def test_the_document_says_it_is_generated_and_names_the_version() -> None:
    text = build()
    assert "Do not edit" in text
    assert f"spikemaul {__version__}" in text


def test_the_document_lives_in_the_checkout() -> None:
    assert where().name == "commands.md"
    assert where().parent.name == "docs"
