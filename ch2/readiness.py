"""Section 2.7, "Sample data-readiness checklist", as executable checks.

The chapter lists the questions a team should ask before a document reaches
an agent. These functions ask them of every ``DocumentRecord`` and return
plain findings, so the result can be reviewed like any other agent output.
Nothing here edits the source documents; it only reports.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, List

from horizon_core.schemas import DocumentRecord

USABLE_STATUSES = {"Approved", "For Coordination"}


@dataclass
class ReadinessResult:
    file: str
    ready: bool
    problems: List[str] = field(default_factory=list)


def check_record(record: DocumentRecord) -> List[str]:
    problems = []
    if record.status not in USABLE_STATUSES:
        problems.append(f"status is {record.status}; only {sorted(USABLE_STATUSES)} may be used")
    if not record.revision:
        problems.append("missing revision")
    if not record.source:
        problems.append("missing source system")
    if not (record.text or "").strip():
        problems.append("no extractable text (scanned or empty page?)")
    if record.owner is None:
        problems.append("no owner recorded; nobody can confirm the content")
    return problems


def check_superseded(records: Iterable[DocumentRecord]) -> List[str]:
    """Flag files present in more than one revision, the classic way an
    agent ends up citing a superseded document."""
    revisions = defaultdict(set)
    for r in records:
        revisions[r.file].add(r.revision)
    return [f"{f} present in revisions {sorted(v)}" for f, v in revisions.items() if len(v) > 1]


def readiness_report(records: List[DocumentRecord]) -> List[ReadinessResult]:
    by_file = defaultdict(list)
    for r in records:
        by_file[r.file].extend(check_record(r))
    results = [ReadinessResult(f, not p, sorted(set(p))) for f, p in by_file.items()]
    for message in check_superseded(records):
        file = message.split(" ", 1)[0]
        for res in results:
            if res.file == file:
                res.ready = False
                res.problems.append(message)
    return results


if __name__ == "__main__":
    from horizon_core.project import HorizonOneTowerProject
    from ch2.data_pipeline import ingest_architecture_model, ingest_planning_report

    project = HorizonOneTowerProject()
    records = ingest_planning_report(project) + ingest_architecture_model(project)
    for res in readiness_report(records):
        print(("READY  " if res.ready else "REVIEW ") + res.file)
        for p in res.problems:
            print("        -", p)
