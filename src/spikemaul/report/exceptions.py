"""The exception log off one geometry run.

The geometry car hands over a file and a fortnight later somebody asks what
was on it. This page is that answer: every reading outside the limits for the
class the track is held to, what class each of them does hold, and what the
track is left holding overall.

The page is built from the book rather than from the file. The run is marked
up from the curve register first, so a crosslevel reading in a curve is judged
against the elevation the chart says should be there, and the class each
segment is held to comes off the segment register rather than being passed in.
That is the whole reason this is a report and not a printout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.geometry.assessment import Assessment, assess
from spikemaul.geometry.curvature import mark_up
from spikemaul.geometry.finding import Finding
from spikemaul.model.line import Segment
from spikemaul.model.reading import Run
from spikemaul.report.layout import Column, Page, Table, count_of
from spikemaul.store.records import Records


@dataclass(frozen=True)
class SegmentAssessment:
    """What the run said about one segment."""

    segment: Segment
    assessment: Assessment

    @property
    def findings(self) -> list[Finding]:
        """The exceptions inside this segment."""
        return self.assessment.exceptions


def assess_run(records: Records, run: Run) -> list[SegmentAssessment]:
    """Read a run against every segment it crosses, one segment at a time.

    A run over five segments is five assessments, not one, because the class
    is a property of the segment and reading the whole run against the lowest
    of them would invent exceptions on the good track.
    """
    curves = records.curves.covering(run.subdivision, run.span)
    marked = mark_up(run, curves)
    out = []
    for segment in records.segments.covering(run.subdivision, run.span):
        inside = marked.within(segment.span)
        if len(inside) < 2:
            continue
        piece = Run(
            inspection=marked.inspection,
            subdivision=marked.subdivision,
            on=marked.on,
            readings=inside,
        )
        out.append(SegmentAssessment(segment=segment, assessment=assess(piece, segment.authorized)))
    return out


def exception_table(assessments: list[SegmentAssessment]) -> Table:
    """Every exception across the run, in milepost order."""
    table = Table(
        [
            Column("milepost"),
            Column("channel"),
            Column("reading", numeric=True),
            Column("meets"),
            Column("segment"),
            Column("held at"),
        ]
    )
    rows = []
    for one in assessments:
        for finding in one.findings:
            rows.append((finding, one.segment))
    for finding, segment in sorted(rows, key=lambda pair: pair[0].at.hundredths):
        table.add(
            f"MP {finding.at}",
            finding.condition.value,
            finding.reading,
            "nothing" if finding.meets is None else finding.meets,
            segment.ident,
            segment.authorized,
        )
    return table


def summary_table(assessments: list[SegmentAssessment]) -> Table:
    """One line per segment saying what it is left holding."""
    table = Table(
        [
            Column("segment"),
            Column("from"),
            Column("to"),
            Column("held at"),
            Column("supports"),
            Column("exceptions", numeric=True),
            Column("action"),
        ]
    )
    for one in assessments:
        supports = one.assessment.supports
        table.add(
            one.segment.ident,
            one.segment.span.begin,
            one.segment.span.end,
            one.segment.authorized,
            "nothing" if supports is None else supports,
            len(one.findings),
            one.assessment.action.describe(),
        )
    return table


def exception_page(records: Records, run: Run, on: date | None = None) -> Page:
    """The exception log for one run."""
    subdivision = records.subdivisions.get(run.subdivision)
    when = (on or run.on).isoformat()
    page = Page(f"{subdivision.name} geometry exceptions {when}")
    page.say(f"run {run.inspection} over {run.span}, {count_of(len(run.readings), 'reading')}")

    assessments = assess_run(records, run)
    page.heading("exceptions")
    page.table(exception_table(assessments), empty="no exceptions")

    page.heading("by segment")
    page.table(summary_table(assessments), empty="no segments covered")
    return page


def worst_segment(assessments: list[SegmentAssessment]) -> SegmentAssessment | None:
    """The segment left holding the lowest class, for the front of a report."""
    if not assessments:
        return None

    def rank(one: SegmentAssessment) -> tuple[int, int]:
        supports = one.assessment.supports
        return (-1 if supports is None else supports.rank, one.segment.span.begin.hundredths)

    return min(assessments, key=rank)
