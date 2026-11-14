"""Chapter 14: the governance gate, and a wrapper that puts any agent behind it.

``governance_gate`` and ``create_audit_record`` are the chapter's listing.
``GovernedAgent`` applies them to a real agent from an earlier chapter:

1. the data class is the highest class of the sources the task uses (from
   ``governance/source_register.csv``) or of the agent itself;
2. the requesting role must be allowed that action at that class
   (``governance/role_permissions.json``);
3. if approval is required and has not been given, the task is held and no
   model is called;
4. once approved, the agent runs with the model core chosen by the route,
   and the audit record is written with the decision.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, Literal, Optional, TypedDict

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.llm import LLMClient, MockLLM
from horizon_core.schemas import AgentFinding

DataClass = Literal["public", "internal", "confidential", "restricted"]
ActionType = Literal["summarise", "recommend", "write_action"]
CLASS_ORDER = ["public", "internal", "confidential", "restricted"]


class GovernanceState(TypedDict):
    task_id: str
    project: str
    user_role: str
    task: str
    data_class: DataClass
    action: ActionType
    source_ids: list[str]
    route: str
    approval_required: bool
    reviewer: str | None
    status: str


MODEL_POLICY = {
    "public": "approved_external_ai",
    "internal": "enterprise_private_ai",
    "confidential": "enterprise_private_ai",
    "restricted": "local_private_ai",
}


def governance_gate(state: GovernanceState):
    """Apply project policy before data reaches a model."""
    state["route"] = MODEL_POLICY[state["data_class"]]
    state["approval_required"] = (state["data_class"] in {"confidential", "restricted"}
                                  or state["action"] in {"recommend", "write_action"})
    if state["action"] == "write_action":
        state["reviewer"] = "authorised_project_lead"
    elif state["data_class"] == "confidential":
        state["reviewer"] = "commercial_or_digital_lead"
    elif state["data_class"] == "restricted":
        state["reviewer"] = "project_security_owner"
    else:
        state["reviewer"] = None
    state["status"] = "awaiting_approval" if state["approval_required"] else "approved_for_processing"
    return state


def create_audit_record(state: GovernanceState):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": state["task_id"], "project": state["project"], "user_role": state["user_role"],
        "data_class": state["data_class"], "action": state["action"], "model_route": state["route"],
        "source_ids": state["source_ids"], "approval_required": state["approval_required"],
        "reviewer": state["reviewer"], "status": state["status"],
    }


def default_routes() -> Dict[str, Callable[[], LLMClient]]:
    """Map each route to a model core. Offline, all three are MockLLM; in a
    deployment, point them at the approved external, enterprise and local
    (e.g. ``OllamaLLM``) services."""
    return {"approved_external_ai": MockLLM, "enterprise_private_ai": MockLLM, "local_private_ai": MockLLM}


class GovernedAgent:
    def __init__(self, agent: BaseAECOAgent, routes: Optional[Dict[str, Callable[[], LLMClient]]] = None):
        self.agent = agent
        self.routes = routes or default_routes()
        p = agent.context.project
        register = p.chapter_csv("governance", "source_register.csv", keep_default_na=False)
        self.classes = dict(zip(register["source_id"], register["data_class"]))
        self.aliases = {r["alias_of"]: r["source_id"] for r in register.to_dict("records") if r["alias_of"]}
        self.permissions = p.chapter_json("governance", "role_permissions.json")
        self.last_state: Optional[GovernanceState] = None
        self.last_audit: Optional[dict] = None

    def classify(self, source_ids: list[str]) -> str:
        classes = [self.classes.get(self.aliases.get(s, s), "internal") for s in source_ids]
        classes.append(self.agent.data_class)
        return max(classes, key=CLASS_ORDER.index)

    def run(self, request: str, *, task_id: str, user_role: str, action: ActionType,
            source_ids: list[str], approved_by: Optional[str] = None) -> AgentFinding:
        perm = self.permissions.get(user_role)
        data_class = self.classify(source_ids)
        if perm is None or action not in perm["may_request"] or \
                CLASS_ORDER.index(data_class) > CLASS_ORDER.index(perm["max_class"]):
            raise PermissionError(f"{user_role} may not request '{action}' on {data_class} data")
        state = governance_gate(GovernanceState(
            task_id=task_id, project="Horizon One Tower", user_role=user_role, task=request,
            data_class=data_class, action=action, source_ids=source_ids, route="",
            approval_required=False, reviewer=None, status="new"))
        if state["approval_required"] and approved_by:
            state["status"] = f"approved_by:{approved_by}"
        self.last_state, self.last_audit = state, create_audit_record(state)
        self.agent.context.audit_log.record(
            agent="Governance Gate", task=f"{task_id}: {request}", sources=source_ids,
            reviewer=approved_by or state["reviewer"], decision_status=state["status"],
            output_summary=f"class={data_class}; route={state['route']}")
        if state["status"] == "awaiting_approval":
            return AgentFinding(
                agent=self.agent.name, chapter=14, data_class=data_class,
                finding="Held by the governance gate before any model call.",
                sources=source_ids, risks=[f"Approval required from {state['reviewer']}"],
                confidence="High", recommended_action=f"Obtain approval from {state['reviewer']} and resubmit.")
        previous = self.agent.context.llm
        self.agent.context.llm = self.routes[state["route"]]()
        try:
            return self.agent.run(request)
        finally:
            self.agent.context.llm = previous
