"""Appendix A.2: an evaluation harness with expected answers.

A test checks that code still works; an evaluation checks that an agent
still gives the right answer. Each golden case names an agent, a request and
facts the finding must contain. Run the set after any change of model,
prompt, data or library version, and compare the score with the last run:

    python -m appendix_a.evaluation            # offline MockLLM
    ANTHROPIC_API_KEY=... python -m appendix_a.evaluation   # live model

With a live model, the narrative wording changes but the facts must not.
A failure means a model has dropped, changed or invented a figure.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from horizon_core.agent_base import AGENT_REGISTRY
from horizon_core.context import default_context
from horizon_core.llm import LLMClient

CASES = Path(__file__).resolve().parent / "golden_cases.json"


@dataclass
class CaseResult:
    case_id: str
    agent: str
    status: str  # pass | fail | skipped
    failures: List[str] = field(default_factory=list)


def check(finding, expect: dict) -> List[str]:
    text, action = (
        finding.finding.replace("\n    ", " "),
        finding.recommended_action,
    )
    fails = []
    for s in expect.get("contains", []):
        if s not in text:
            fails.append(f"finding lacks '{s}'")
    for s in expect.get("contains_action", []):
        if s not in action:
            fails.append(f"recommended action lacks '{s}'")
    for s in expect.get("sources_include", []):
        if s not in finding.sources:
            fails.append(f"sources lack '{s}'")
    for s in expect.get("risks_include", []):
        if not any(s in r for r in finding.risks):
            fails.append(f"risks lack '{s}'")
    if (
        "confidence_in" in expect
        and finding.confidence not in expect["confidence_in"]
    ):
        fails.append(
            f"confidence {finding.confidence} not in "
            f"{expect['confidence_in']}"
        )
    if expect.get("sources_nonempty") and not finding.sources:
        fails.append("no sources cited")
    return fails


def run_cases(
    llm: Optional[LLMClient] = None,
    case_ids: Optional[List[str]] = None,
) -> List[CaseResult]:
    results = []
    for case in json.loads(CASES.read_text()):
        if case_ids and case["id"] not in case_ids:
            continue
        missing = []
        for m in case.get("requires", []):
            try:
                importlib.import_module(m)
            except ImportError:
                missing.append(m)
        if missing:
            results.append(
                CaseResult(
                    case["id"],
                    case["agent"],
                    "skipped",
                    [f"needs {', '.join(missing)}"],
                )
            )
            continue
        importlib.import_module(case["module"])
        context = default_context()
        if llm is not None:
            context.llm = llm
        finding = AGENT_REGISTRY[case["agent"]](context).run(
            case["request"]
        )
        fails = check(finding, case["expect"])
        results.append(
            CaseResult(
                case["id"],
                case["agent"],
                "fail" if fails else "pass",
                fails,
            )
        )
    return results


if __name__ == "__main__":
    results = run_cases()
    for r in results:
        print(
            f"{r.case_id} {r.status:<7} {r.agent}"
            + (
                f"  -> {'; '.join(r.failures)}"
                if r.failures
                else ""
            )
        )
    scored = [r for r in results if r.status != "skipped"]
    print(
        f"\n{sum(r.status == 'pass' for r in scored)}/{len(scored)} passed"
    )
