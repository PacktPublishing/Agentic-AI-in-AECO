"""The Chapter 14 listing, as printed.

    python -m ch14.listings

``ch14/governance.py`` contains the same gate plus ``GovernedAgent``, which
applies it to the Chapter 9 Supplier Evaluation Agent.
"""
from datetime import datetime, timezone
from typing import Literal, TypedDict

DataClass = Literal[
    "public",
    "internal",
    "confidential",
    "restricted"
]

ActionType = Literal[
    "summarise",
    "recommend",
    "write_action"
]

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
    "restricted": "local_private_ai"
}


def governance_gate(state: GovernanceState):
    """Apply project policy before data reaches a model."""

    state["route"] = MODEL_POLICY[state["data_class"]]

    state["approval_required"] = (
        state["data_class"] in {"confidential", "restricted"}
        or state["action"] in {"recommend", "write_action"}
    )

    if state["action"] == "write_action":
        state["reviewer"] = "authorised_project_lead"
    elif state["data_class"] == "confidential":
        state["reviewer"] = "commercial_or_digital_lead"
    elif state["data_class"] == "restricted":
        state["reviewer"] = "project_security_owner"
    else:
        state["reviewer"] = None

    state["status"] = (
        "awaiting_approval"
        if state["approval_required"]
        else "approved_for_processing"
    )

    return state


def create_audit_record(state: GovernanceState):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": state["task_id"],
        "project": state["project"],
        "user_role": state["user_role"],
        "data_class": state["data_class"],
        "action": state["action"],
        "model_route": state["route"],
        "source_ids": state["source_ids"],
        "approval_required": state["approval_required"],
        "reviewer": state["reviewer"],
        "status": state["status"]
    }


request = GovernanceState(
    task_id="HOT-GOV-014",
    project="Horizon One Tower",
    user_role="Commercial Manager",
    task="Compare façade supplier submissions and draft recommendation",
    data_class="confidential",
    action="recommend",
    source_ids=[
        "FAC-SPEC-R06",
        "SUP-A-RETURN",
        "SUP-B-RETURN",
        "SUP-C-RETURN"
    ],
    route="",
    approval_required=False,
    reviewer=None,
    status="new"
)

controlled_request = governance_gate(request)
audit_record = create_audit_record(controlled_request)

print(controlled_request["route"])
print(controlled_request["approval_required"])
print(controlled_request["reviewer"])
