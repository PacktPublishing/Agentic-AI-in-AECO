"""Section 1.6, "A simple AECO agent in code".

A deliberately small agent with no framework, so the anatomy from Section 1.7
is visible in one screen: a goal, guardrails, a tool that does the counting,
a step that words the result (where a language model would be called), an
audit record and a review status. The framework version of the same agent
is ``ch1/coordination_agent.py``.

    python -m ch1.simple_agent
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

DATA = Path("data") / "horizon_one_tower"
AS_OF = date(2026, 9, 13)
GOAL = "Summarize open coordination issues for the BIM manager."
CANNOT_DO = ("close issues", "assign responsibility",
             "issue instructions")


def check_guardrails(request: str) -> None:
    for forbidden in CANNOT_DO:
        if forbidden in request.lower():
            raise PermissionError(
                f"Outside this agent's role: {forbidden}")


def count_open_issues(issues: list) -> dict:
    open_issues = [i for i in issues if i["status"] != "Closed"]
    overdue = [i["issue_id"] for i in open_issues
               if date.fromisoformat(i["due_date"]) < AS_OF]
    return {"open": len(open_issues), "overdue": overdue}


def draft_wording(facts: dict) -> str:
    overdue = ", ".join(facts["overdue"]) or "none"
    return (f"{facts['open']} coordination issues are open; "
            f"{len(facts['overdue'])} are overdue ({overdue}).")


def run(request: str) -> dict:
    check_guardrails(request)
    issues = json.loads((DATA / "issue_log.json").read_text())
    facts = count_open_issues(issues)
    return {
        "goal": GOAL,
        "summary": draft_wording(facts),
        "sources": ["issue_log.json"],
        "audit": {
            "time": datetime.now(timezone.utc).isoformat(
                timespec="seconds"),
            "request": request,
            "tool": "count_open_issues",
        },
        "status": "Awaiting BIM manager review",
    }


if __name__ == "__main__":
    result = run("Prepare this week's coordination summary")
    print(result["summary"])
    print(result["status"])
    try:
        run("Close issues that are older than a month")
    except PermissionError as exc:
        print("Refused:", exc)
