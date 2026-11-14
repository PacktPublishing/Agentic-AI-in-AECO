"""The Chapter 3 listings, in the order they appear in the chapter.

    python -m ch3.listings

The chapter shows the orchestration idea with small functions and a linear
graph. ``project_memory``, ``review_cost_impact`` and the other helpers the
text refers to are given minimal working definitions here so the listings
run. The production version used by later chapters is ``ch3/orchestrator.py``.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel

from horizon_core.project import HorizonOneTowerProject
from horizon_core.review import detect_conflicts as _conflicts
from horizon_core.review import detect_missing_evidence as _missing
from horizon_core.schemas import AgentFinding as _CoreFinding
from ch2.data_pipeline import build_knowledge_base


# Listing 3.1 - the standard specialist output
class AgentFinding(BaseModel):
    agent: str
    finding: str
    sources: List[str]
    assumptions: List[str]
    risks: List[str]
    confidence: str
    recommended_action: str


# Listing 3.2 - a finding from the Cost Agent
cost_finding = AgentFinding(
    agent="Cost Agent",
    finding="Terracotta increases the façade package cost.",
    sources=["Cost Plan Rev P06"],
    assumptions=["Current façade quantity remains unchanged"],
    risks=["Supplier rates have not yet been confirmed"],
    confidence="Medium",
    recommended_action="Commercial review required",
)
print(cost_finding.model_dump())

# Listing 3.3 - the shared state passed between the agents
from typing import TypedDict  # noqa: E402

from langgraph.graph import END, StateGraph  # noqa: E402


class ProjectState(TypedDict):
    request: str
    bim: dict
    cost: dict
    sustainability: dict
    procurement: dict
    conflicts: list
    approved: bool


# Supporting definitions the text assumes (not printed in the chapter)
project = HorizonOneTowerProject()
project_memory = build_knowledge_base(project)
plan = project.cost_plan()["facade_package"]
workbook = project.sustainability_workbook()["facade_package"]


def review_cost_impact(context) -> dict:
    movement = plan["proposed_option"]["total"] - plan["current_option"]["total"]
    return {**cost_finding.model_dump(), "finding": f"Terracotta increases the façade package cost by GBP {movement:,}."}


def review_sustainability_impact(context) -> dict:
    a = workbook["current_option"]["embodied_carbon_kgco2e_per_m2"]
    b = workbook["proposed_option"]["embodied_carbon_kgco2e_per_m2"]
    return AgentFinding(
        agent="Sustainability Agent",
        finding=f"Screening figure falls from {a} to {b} kgCO2e/m2 (A1-A3, panels and supports).",
        sources=["sustainability_workbook.json"],
        assumptions=["Same screened area"],
        risks=["Product-specific EPD not yet supplied"],
        confidence="Low",
        recommended_action="Request product-specific EPD before relying on the figure",
    ).model_dump()


def bim_agent(state):
    return {"bim": {"agent": "BIM Audit Agent", "finding": "ISS-0144 bracket depth open",
                    "sources": ["issue_log.json#ISS-0144"], "assumptions": [], "risks": [],
                    "confidence": "Medium", "recommended_action": "Review bracket interface before proceeding"}}


def procurement_agent(state):
    return {"procurement": {"agent": "Procurement Agent", "finding": "Two suppliers; one lead time 18 weeks",
                            "sources": ["procurement_tracker.json"], "assumptions": [],
                            "risks": ["Availability provisional"], "confidence": "Medium",
                            "recommended_action": "Commercial review required"}}


# Listing 3.4 - specialist agents query the shared project memory
def cost_agent(state):
    context = project_memory.query(
        f"Cost evidence for: {state['request']}"
    )
    return {
        "cost": review_cost_impact(context)
    }


def sustainability_agent(state):
    context = project_memory.query(
        f"Sustainability evidence for: {state['request']}"
    )
    return {
        "sustainability":
            review_sustainability_impact(context)
    }


# Listing 3.5 - connecting the agents into a graph
workflow = StateGraph(ProjectState)
workflow.add_node("bim", bim_agent)
workflow.add_node("cost", cost_agent)
workflow.add_node("sustainability", sustainability_agent)
workflow.add_node("procurement", procurement_agent)
workflow.set_entry_point("bim")
workflow.add_edge("bim", "cost")
workflow.add_edge("cost", "sustainability")
workflow.add_edge("sustainability", "procurement")
workflow.add_edge("procurement", END)
app = workflow.compile()

state = app.invoke({"request": "DCR-0007 podium façade substitution"})
print({k: v["recommended_action"] for k, v in state.items() if isinstance(v, dict)})


# Listing 3.6 - the review gate
def _findings(state) -> list:
    keys = ("bim", "cost", "sustainability", "procurement")
    return [_CoreFinding(**state[k]) for k in keys if state.get(k)]


def detect_conflicts(state):
    return _conflicts(_findings(state))


def detect_missing_evidence(state):
    return _missing(_findings(state))


def review_gate(state):
    conflicts = detect_conflicts(state)
    missing_evidence = detect_missing_evidence(state)
    if conflicts:
        return "human_review"
    if missing_evidence:
        return "human_review"
    return "prepare_summary"


# Listings 3.7 and 3.8 - attaching the gate and the human review node
def compare_findings(state):
    return {"conflicts": detect_conflicts(state)}


def human_review(state):
    return {
        "approved": False,
        "review_status": "Awaiting Design and Commercial Review",
    }


def prepare_summary(state):
    return {"approved": False, "review_status": "Ready for normal approval"}


class ReviewState(ProjectState, total=False):
    review_status: str


workflow = StateGraph(ReviewState)
for name, fn in [("bim", bim_agent), ("cost", cost_agent), ("sustainability", sustainability_agent),
                 ("procurement", procurement_agent), ("compare_findings", compare_findings),
                 ("human_review", human_review), ("prepare_summary", prepare_summary)]:
    workflow.add_node(name, fn)
workflow.set_entry_point("bim")
workflow.add_edge("bim", "cost")
workflow.add_edge("cost", "sustainability")
workflow.add_edge("sustainability", "procurement")
workflow.add_edge("procurement", "compare_findings")
workflow.add_conditional_edges(
    "compare_findings",
    review_gate,
    {
        "human_review": "human_review",
        "prepare_summary": "prepare_summary",
    },
)
workflow.add_edge("human_review", END)
workflow.add_edge("prepare_summary", END)
result = workflow.compile().invoke({"request": "DCR-0007 podium façade substitution"})
print(result["review_status"])
