"""Chapter 4: reading planning documents into structured constraints.

The Zoning Compliance Agent should not hand a planning PDF to a model and
accept free text back. The pattern is:

1. retrieve the relevant pages from the Agent Knowledge Base (Chapter 2);
2. ask for output in a fixed structure (``ConstraintRecord``);
3. validate every record with Pydantic and reject anything that does not
   carry a clause reference and a source;
4. send the validated set to the planning consultant.

``extract_with_model`` shows step 2 for a live model. The offline default,
``extract_with_rules``, reads the same pages with simple patterns so the
example runs without an API key and gives a known answer for tests.
"""
from __future__ import annotations

import json
import re
from typing import List, Tuple

from pydantic import ValidationError

from horizon_core.llm import LLMClient
from horizon_core.schemas import ConstraintRecord, DocumentRecord

PROMPT = """Extract every planning constraint from the pages below.
Return only a JSON list. Each item must have: topic, description,
clause_reference, source_document, requirement_type ("hard_requirement" or
"subject_to_justification") and value. Do not interpret or summarise beyond
the text. If a field is not stated, omit the item.

PAGES:
{pages}"""

_CLAUSE = re.compile(r"Clause reference:\s*(.+)")
_STATUS = re.compile(r"Status:\s*(.+)")
_VALUE = re.compile(r"Reference value:\s*(.+)")
_TITLE = re.compile(r"Section \d+:\s*(.+)")


def extract_with_rules(pages: List[DocumentRecord]) -> List[ConstraintRecord]:
    records = []
    for page in pages:
        lines = [l.strip() for l in page.text.splitlines() if l.strip()]
        text = "\n".join(lines)
        clause, status, title = _CLAUSE.search(text), _STATUS.search(text), _TITLE.search(text)
        if not (clause and status and title):
            continue
        body = [l for l in lines if not l.startswith(("Section", "Clause", "Status", "Reference"))]
        value = _VALUE.search(text)
        records.append(ConstraintRecord(
            topic=title.group(1),
            description=" ".join(body),
            clause_reference=clause.group(1),
            source_document=f"{page.file} p.{page.page}",
            requirement_type="hard_requirement" if "Hard" in status.group(1) else "subject_to_justification",
            value=value.group(1) if value else None,
        ))
    return records


def extract_with_model(pages: List[DocumentRecord], llm: LLMClient) -> Tuple[List[ConstraintRecord], List[str]]:
    """Ask a model for structured output and keep only valid records."""
    raw = llm.complete(PROMPT.format(pages="\n\n".join(f"[{p.citation()}]\n{p.text}" for p in pages)))
    try:
        items = json.loads(raw.strip().removeprefix("```json").removesuffix("```"))
    except json.JSONDecodeError:
        return [], ["Model output was not valid JSON; nothing accepted."]
    accepted, rejected = [], []
    for item in items:
        try:
            accepted.append(ConstraintRecord(**item))
        except (ValidationError, TypeError) as exc:
            rejected.append(f"Rejected item {item!r}: {exc.__class__.__name__}")
    return accepted, rejected


if __name__ == "__main__":
    from horizon_core.project import HorizonOneTowerProject
    from ch2.data_pipeline import ingest_planning_report

    pages = ingest_planning_report(HorizonOneTowerProject())
    for c in extract_with_rules(pages):
        flag = "HARD " if c.is_hard_requirement else "JUSTIFY"
        print(f"{flag} {c.topic:<22} {c.clause_reference:<45} {c.value}")
