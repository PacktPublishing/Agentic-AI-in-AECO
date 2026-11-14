"""Chapter 15: Building the Agentic AECO Enterprise.

The chapter has no code listings. This module turns its guidance into
artefacts a team can review, using evidence that already exists in the
repository. Each function follows a passage of the chapter:

* ``screen_use_cases`` - "A sensible use case normally has four
  characteristics": it occurs often, its information can be identified,
  its output is genuinely used, and its review can be assigned. A use case
  also needs a clear measure of value.
* ``pilot_decision`` - the four choices after a pilot: scale, redesign,
  retest or stop.
* ``workflow_card`` - the seven questions every workflow must answer, from
  "What starts it?" to "What evidence is retained?".
* ``agent_portfolio`` and ``governance_maturity`` - the agents built in the
  book, read from the automatic register, and the governance controls
  measured against them.
* ``skills_matrix`` - the orchestrator skills the chapter lists, compared
  with target levels.
* ``roadmap`` - the four stages of the 12-month route, with the evidence
  each stage must produce.

Every output is a draft for leadership to review. Nothing here commits
budget, people or suppliers.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pandas as pd

from horizon_core.agent_base import AGENT_REGISTRY

ROOT = Path(__file__).resolve().parent.parent
AGENT_MODULES = [
    "ch1.coordination_agent", "ch3.agents", "ch4.agents",
    "ch5.validation_agents", "ch6.audit_agent", "ch7.agent", "ch8.agent",
    "ch9.agent", "ch10.agent", "ch11.agent", "ch12.agent", "ch13.agent",
]

#: "The practical skills include task design, information structuring,
#: retrieval, evaluation, workflow mapping, governance, assurance and
#: communication." Target levels (1-5) are a starting point for discussion.
SKILLS = ["task_design", "information_structuring", "retrieval", "evaluation",
          "workflow_mapping", "governance", "assurance", "communication"]
TARGETS = {
    "default": dict.fromkeys(SKILLS, 3),
    "Digital Delivery Lead": dict.fromkeys(SKILLS, 4),
    "BIM Manager": {**dict.fromkeys(SKILLS, 3), "information_structuring": 4,
                    "workflow_mapping": 4, "governance": 4},
}

#: Thresholds used to turn pilot results into one of the four decisions.
PILOT_RULES = {"min_cases": 20, "pass_rate_scale": 0.90, "pass_rate_retest": 0.75,
               "min_value_change_pct": -20}


# ---------------------------------------------------------------- use cases
def screen_use_cases(backlog: pd.DataFrame) -> pd.DataFrame:
    """Apply the chapter's four characteristics and the value measure."""
    b = backlog.copy()
    text = lambda col: b[col].fillna("").astype(str).str.strip()  # noqa: E731
    checks = {
        "occurs often": b["frequency_per_month"].ge(2),
        "information identified": b["information_identified"].astype(bool),
        "output genuinely used": text("output_user").ne(""),
        "review can be assigned": text("reviewer").ne(""),
        "value can be measured": text("value_measure").ne(""),
    }
    b["missing"] = [
        ", ".join(name for name, ok in checks.items() if not ok.iloc[i])
        for i in range(len(b))
    ]
    b["candidate"] = b["missing"].eq("")
    b["first_pilot"] = b["candidate"] & b["risk"].le(3)
    b["priority"] = (b["frequency_per_month"].clip(upper=10) / 10 * 3
                     + (6 - b["risk"]) + (6 - b["effort"])).round(1)
    return b.sort_values(["first_pilot", "candidate", "priority"],
                         ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- pilots
def pilot_decision(result: dict, rules: dict = PILOT_RULES) -> tuple[str, str]:
    """Scale, redesign, retest or stop, with the reason."""
    faster = result["review_minutes_agent"] < result["review_minutes_manual"]
    valuable = result["value_change_pct"] <= rules["min_value_change_pct"]
    if not result["risk_acceptable"]:
        return "stop", "risk cannot be justified"
    if not faster or not valuable:
        return "stop", "review burden or value does not justify the workflow"
    if result["cases_tested"] < rules["min_cases"]:
        return "retest", "not yet enough evidence to deploy confidently"
    if result["pass_rate"] >= rules["pass_rate_scale"]:
        return "scale", "reliable, measurable value within the risk boundary"
    if result["pass_rate"] >= rules["pass_rate_retest"]:
        return "redesign", f"worthwhile, but fix the main error source: {result['main_error_source']}"
    return "stop", "performance too low for the effort required"


def pilot_decisions(results: pd.DataFrame) -> pd.DataFrame:
    out = results.copy()
    decided = [pilot_decision(r) for r in results.to_dict("records")]
    out["decision"] = [d for d, _ in decided]
    out["reason"] = [r for _, r in decided]
    return out


# ---------------------------------------------------------------- agents
def load_agents() -> dict:
    for module in AGENT_MODULES:
        try:
            importlib.import_module(module)
        except ImportError:  # optional heavy dependency missing
            pass
    return dict(AGENT_REGISTRY)


def workflow_card(cls) -> dict:
    """The seven questions from the chapter, answered from an agent's
    declared metadata. Blank answers are gaps to close before scaling."""
    return {
        "What starts it?": getattr(cls, "trigger", None) or "On request from the reviewer",
        "What information does it need?": f"{cls.data_class} project data (see its sources)",
        "What can the agent do?": "; ".join(cls.can_do),
        "What is it forbidden to do?": "; ".join(cls.cannot_do),
        "How is the result checked?": "Structured finding with sources, assumptions and confidence",
        "Who approves it?": cls.reviewer_role or "",
        "What evidence is retained?": "Audit record: agent, task, sources, tools, reviewer, status",
    }


def _golden_agents() -> set:
    path = ROOT / "appendix_a" / "golden_cases.json"
    return {c["agent"] for c in json.loads(path.read_text())} if path.exists() else set()


def agent_portfolio() -> pd.DataFrame:
    golden = _golden_agents()
    rows = []
    for name, cls in sorted(load_agents().items(), key=lambda kv: (kv[1].chapter or 0, kv[0])):
        rows.append({
            "agent": name, "chapter": cls.chapter, "reviewer_role": cls.reviewer_role,
            "data_class": cls.data_class, "can_do": len(cls.can_do), "cannot_do": len(cls.cannot_do),
            "has_tests": (ROOT / "tests" / f"test_ch{cls.chapter}.py").exists() if cls.chapter else False,
            "has_eval_set": name in golden,
        })
    return pd.DataFrame(rows)


def governance_maturity(portfolio: pd.DataFrame, checklist: list) -> pd.DataFrame:
    measures = {
        "G1": portfolio["reviewer_role"].notna(), "G2": portfolio["cannot_do"].gt(0),
        "G3": portfolio["data_class"].notna(), "G4": portfolio["has_tests"],
        "G5": portfolio["has_eval_set"], "G6": pd.Series(True, index=portfolio.index),
    }
    rows = []
    for item in checklist:
        passed = measures[item["id"]]
        rows.append({"id": item["id"], "control": item["control"],
                     "coverage_pct": round(100 * passed.mean()),
                     "gaps": ", ".join(portfolio.loc[~passed, "agent"]) or "none"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- people
def skills_matrix(survey: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in survey.to_dict("records"):
        target = TARGETS.get(r["role"], TARGETS["default"])
        for s in SKILLS:
            rows.append({"role": r["role"], "skill": s, "current": r[s], "target": target[s],
                         "gap": max(0, target[s] - r[s])})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- roadmap
STAGES = [
    ("1-3", "Foundation", "Select and prepare",
     "Named workflow owners, trusted inputs, clear approval points and agreed measures of value."),
    ("4-6", "Controlled pilots", "Test and learn",
     "Acceptable performance, traceable sources, understood limitations and evidence of practical value."),
    ("7-9", "Live deployment", "Use in real work",
     "Stable use, manageable exceptions, reviewer confidence and measurable improvement."),
    ("10-12", "Responsible scale", "Standardise and extend",
     "Repeatable business value, defined support ownership, governance maturity and maintainable workflows."),
]


def roadmap(screened: pd.DataFrame, decisions: pd.DataFrame) -> list:
    pilots = screened.loc[screened["first_pilot"], "use_case"].tolist()
    by_decision = decisions.groupby("decision")["use_case"].apply(list).to_dict()
    work = {
        "Foundation": [f"Prepare candidates: {', '.join(pilots[:4])}",
                       "Record baseline measures for each candidate"],
        "Controlled pilots": ["Test against historic Horizon One Tower data before live use",
                              "Record source, error type, missing information, review effort and consequence"],
        "Live deployment": [f"Deploy: {', '.join(by_decision.get('scale', [])) or 'none yet'}",
                            f"Redesign before retesting: {', '.join(by_decision.get('redesign', [])) or 'none'}"],
        "Responsible scale": [f"Retire: {', '.join(by_decision.get('stop', [])) or 'none'}",
                              "Reuse proven patterns; connect new data sources only where justified"],
    }
    return [{"months": m, "stage": s, "focus": f, "actions": work[s], "evidence": e}
            for m, s, f, e in STAGES]


def roadmap_markdown(plan: list) -> str:
    lines = ["# Horizon One Tower: 12-month route (draft for leadership review)", ""]
    for step in plan:
        lines += [f"## Months {step['months']}: {step['stage']} ({step['focus']})", ""]
        lines += [f"- {a}" for a in step["actions"]]
        lines += ["", f"Evidence checklist: {step['evidence']}", ""]
    return "\n".join(lines)
