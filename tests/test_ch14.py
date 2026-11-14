import pytest

from ch9.agent import SupplierEvaluationAgent
from ch14.governance import GovernanceState, GovernedAgent, governance_gate

SOURCES = ["FAC-SPEC-R06", "SUP-A-RETURN", "SUP-B-RETURN", "SUP-C-RETURN"]


def test_gate_matches_chapter():
    s = governance_gate(GovernanceState(task_id="HOT-GOV-014", project="Horizon One Tower", user_role="Commercial Manager",
                                        task="t", data_class="confidential", action="recommend", source_ids=SOURCES,
                                        route="", approval_required=False, reviewer=None, status="new"))
    assert (s["route"], s["approval_required"], s["reviewer"]) == ("enterprise_private_ai", True, "commercial_or_digital_lead")


def test_held_until_approved_then_runs(context):
    g = GovernedAgent(SupplierEvaluationAgent(context))
    kw = dict(task_id="HOT-GOV-014", user_role="Commercial Manager", action="recommend", source_ids=SOURCES)
    held = g.run("compare", **kw)
    assert held.finding.startswith("Held by the governance gate")
    done = g.run("compare", approved_by="Digital Lead", **kw)
    assert "Supplier B: rank 1" in done.finding
    assert context.audit_log.entries_for("Governance Gate")[-1].reviewer == "Digital Lead"


def test_role_without_permission_is_refused(context):
    with pytest.raises(PermissionError):
        GovernedAgent(SupplierEvaluationAgent(context)).run(
            "compare", task_id="t", user_role="Design Manager", action="recommend", source_ids=["SUP-A-RETURN"])


def test_alias_resolves_to_confidential(context):
    assert GovernedAgent(SupplierEvaluationAgent(context)).classify(["DEMO-QUOTE-A-R1"]) == "confidential"
