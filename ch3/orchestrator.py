"""Chapter 3's AECO Orchestrator, built with LangGraph.

The chapter text shows the simplest version: a ``ProjectState`` and four
specialist nodes joined in a line (see ``ch3/listings.py``). This module is
the version the rest of the book builds on. It keeps the same idea and adds
three things later chapters rely on:

1. **Pluggable specialists.** The graph is built from a mapping of state key
   to agent class. Chapters 7 to 14 add their own specialists (carbon, cost
   intelligence, procurement evaluation, governance) by passing a different
   mapping, without editing this file. This is the progressive build the book
   follows: the orchestrator from Chapter 3 is the shell, later chapters plug
   in.
2. **Sequential or parallel execution.** ``parallel=False`` reproduces the
   chapter's linear chain. ``parallel=True`` fans the specialists out from the
   start node and joins them at ``compare_findings``, which is how a real
   review would run when the specialists do not depend on each other.
3. **A real approval pause.** With ``pause_for_review=True`` the graph is
   compiled with a checkpointer and ``interrupt_before=["human_review"]``. It
   stops, the reviewer's decision is written into the saved state, and the
   graph resumes. This is the same pattern Chapter 11 uses for the print
   supervisor.

Routing still goes through :func:`horizon_core.review.review_gate`: conflicts,
missing evidence or a low-confidence finding send the change to human review.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, Mapping, Optional, Type, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from horizon_core.agent_base import AgentContext, BaseAECOAgent
from horizon_core.review import detect_conflicts, detect_missing_evidence, review_gate
from horizon_core.schemas import AgentFinding

from ch3.agents import (
    BimAuditAgent,
    CostAgent,
    OperationsAgent,
    PlanningRiskAgent,
    ProcurementAgent,
    SustainabilityAgent,
)

#: The six specialists Chapter 3 describes, in the order the text lists them.
DEFAULT_SPECIALISTS: Dict[str, Type[BaseAECOAgent]] = {
    "bim": BimAuditAgent,
    "cost": CostAgent,
    "sustainability": SustainabilityAgent,
    "procurement": ProcurementAgent,
    "planning_risk": PlanningRiskAgent,
    "operations": OperationsAgent,
}

#: Labels used in the trade-off summary. Later chapters can add their own.
LABELS: Dict[str, str] = {
    "bim": "BIM impact",
    "cost": "Cost impact",
    "sustainability": "Sustainability impact",
    "procurement": "Procurement impact",
    "planning_risk": "Planning risk",
    "operations": "Operations impact",
    "carbon": "Carbon screening (Chapter 7)",
    "cost_intelligence": "Cost movement (Chapter 8)",
    "supplier_evaluation": "Supplier evaluation (Chapter 9)",
}


class ProjectState(TypedDict, total=False):
    request: str
    # Each specialist writes {key: finding}. The reducer merges the dicts,
    # which is what allows specialists to run in parallel safely.
    findings: Annotated[Dict[str, dict], operator.or_]
    conflicts: list
    missing_evidence: list
    route: str
    decision: Optional[dict]
    review_status: str
    approved: Optional[bool]


def build_graph(
    context: AgentContext,
    specialists: Optional[Mapping[str, Type[BaseAECOAgent]]] = None,
    *,
    parallel: bool = False,
    pause_for_review: bool = False,
    reviewer_role: str = "Design Lead and Commercial Manager",
    checkpointer=None,
):
    """Build and compile the orchestration graph.

    Parameters
    ----------
    specialists:
        Mapping of state key to agent class. Defaults to the six Chapter 3
        specialists.
    parallel:
        Run specialists in parallel (fan-out/fan-in) instead of a chain.
    pause_for_review:
        Compile with a checkpointer and interrupt before ``human_review``.
    checkpointer:
        Where paused runs are saved. Defaults to in-memory; pass a
        persistent saver (e.g. SQLite, Appendix A.9) so a review can be
        resumed by another process.
    """
    specialists = dict(specialists or DEFAULT_SPECIALISTS)
    agents = {key: cls(context) for key, cls in specialists.items()}

    def make_node(key: str, agent: BaseAECOAgent):
        def node(state: ProjectState) -> dict:
            finding = agent.run(state["request"])
            return {"findings": {key: finding.model_dump()}}

        return node

    def collected(state: ProjectState):
        return [AgentFinding(**raw) for raw in state.get("findings", {}).values()]

    def compare_findings(state: ProjectState) -> dict:
        findings = collected(state)
        return {
            "conflicts": detect_conflicts(findings),
            "missing_evidence": detect_missing_evidence(findings),
            "route": review_gate(findings),
        }

    def human_review(state: ProjectState) -> dict:
        decision = state.get("decision")
        if not decision:
            return {"approved": None, "review_status": "Awaiting Review"}
        approved = bool(decision.get("approved"))
        return {
            "approved": approved,
            "review_status": (
                f"{'Approved' if approved else 'Rejected'} by "
                f"{decision.get('reviewer', reviewer_role)}"
            ),
        }

    def prepare_summary(state: ProjectState) -> dict:
        return {
            "approved": None,
            "review_status": "Ready for normal approval - no conflicts or missing evidence detected.",
        }

    workflow = StateGraph(ProjectState)
    for key, agent in agents.items():
        workflow.add_node(key, make_node(key, agent))
    workflow.add_node("compare_findings", compare_findings)
    workflow.add_node("human_review", human_review)
    workflow.add_node("prepare_summary", prepare_summary)

    keys = list(agents)
    if parallel:
        for key in keys:
            workflow.add_edge(START, key)
            workflow.add_edge(key, "compare_findings")
    else:
        workflow.add_edge(START, keys[0])
        for first, second in zip(keys, keys[1:]):
            workflow.add_edge(first, second)
        workflow.add_edge(keys[-1], "compare_findings")

    workflow.add_conditional_edges(
        "compare_findings",
        lambda state: state["route"],
        {"human_review": "human_review", "prepare_summary": "prepare_summary"},
    )
    workflow.add_edge("human_review", END)
    workflow.add_edge("prepare_summary", END)

    if pause_for_review:
        return workflow.compile(checkpointer=checkpointer or MemorySaver(),
                                interrupt_before=["human_review"])
    return workflow.compile()


class AECOOrchestrator:
    """Build the graph once and run design-change reviews through it."""

    def __init__(
        self,
        context: AgentContext,
        specialists: Optional[Mapping[str, Type[BaseAECOAgent]]] = None,
        *,
        parallel: bool = False,
        pause_for_review: bool = False,
        checkpointer=None,
    ) -> None:
        self.context = context
        self.specialists = dict(specialists or DEFAULT_SPECIALISTS)
        self.pause_for_review = pause_for_review
        self.app = build_graph(
            context, self.specialists, parallel=parallel,
            pause_for_review=pause_for_review, checkpointer=checkpointer,
        )

    @staticmethod
    def _flatten(state: Dict[str, Any]) -> Dict[str, Any]:
        """Expose each finding at the top level (``result["cost"]``) as well as
        under ``result["findings"]``, which keeps the demo code short."""
        result = dict(state)
        for key, finding in state.get("findings", {}).items():
            result[key] = finding
        return result

    def _record(self, request_id: str, result: Dict[str, Any]) -> None:
        self.context.audit_log.record(
            agent="AECO Orchestrator",
            task=f"Design change review for {request_id}",
            sources=[s for f in result.get("findings", {}).values() for s in f.get("sources", [])],
            reviewer=(result.get("decision") or {}).get("reviewer"),
            decision_status=result.get("review_status"),
            output_summary=f"route={result.get('route')}; conflicts={len(result.get('conflicts', []))}",
        )

    def run_change_review(self, request_id: str = "DCR-0007", thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Run the review. With ``pause_for_review`` the run stops before the
        human review node; call :meth:`record_decision` to resume."""
        if self.pause_for_review:
            config = {"configurable": {"thread_id": thread_id or request_id}}
            self.app.invoke({"request": request_id}, config)
            state = self.app.get_state(config)
            result = self._flatten(state.values)
            result["paused_at"] = list(state.next)
            if not state.next:
                self._record(request_id, result)
            return result
        result = self._flatten(self.app.invoke({"request": request_id}))
        self._record(request_id, result)
        return result

    def record_decision(
        self, request_id: str, approved: bool, reviewer: str, comments: str = "", thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Write the reviewer's decision into the paused run and resume it."""
        if not self.pause_for_review:
            raise RuntimeError("record_decision() needs an orchestrator built with pause_for_review=True")
        config = {"configurable": {"thread_id": thread_id or request_id}}
        self.app.update_state(
            config, {"decision": {"approved": approved, "reviewer": reviewer, "comments": comments}}
        )
        result = self._flatten(self.app.invoke(None, config))
        self._record(request_id, result)
        return result

    def trade_off_summary(self, result: Dict[str, Any], request_title: str) -> str:
        """Render the chapter's "practical output" block from a run's result."""
        lines = [f"Design change: {request_title}"]
        for key in self.specialists:
            finding = result.get("findings", {}).get(key)
            if finding:
                lines.append(f"{LABELS.get(key, key)}: {finding['recommended_action']}")
        lines.append(f"Human review status: {result.get('review_status')}")
        lines.append("Trace log: Sources, agents, assumptions, and reviewer decision recorded")
        return "\n".join(lines)
