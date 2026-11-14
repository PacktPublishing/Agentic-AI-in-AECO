from ch11.agent import FabricationMonitoringAgent
from ch11.monitoring import AdjustmentProposal, build_gate, check_proposal, envelope, maturity_c_h, risk_indicators


def _data(project):
    return project.chapter_csv("fabrication", "pavilion_print_log.csv"), project.chapter_json("fabrication", "limits.json")


def test_indicators_and_maturity_match_chapter(project):
    log, limits = _data(project)
    ind = risk_indicators(log, limits).set_index("indicator")
    assert ind["flag"].all() and ind.at["interlayer_ratio", "value"] == 0.89
    assert round(maturity_c_h(log, 1)) == 128


def test_envelope_rejects_and_accepts(project):
    _, limits = _data(project)
    env = envelope(limits)
    draft = AdjustmentProposal(parameter="print_speed_mm_s", current=120, proposed=160, reason="r", evidence=["L048"])
    assert len(check_proposal(draft, env)) == 2
    assert check_proposal(draft.model_copy(update={"proposed": 130}), env) == []


def test_gate_pauses_and_records_no_controller_action(project):
    _, limits = _data(project)
    app = build_gate(envelope(limits))
    cfg = {"configurable": {"thread_id": "t"}}
    proposal = AdjustmentProposal(parameter="print_speed_mm_s", current=120, proposed=130, reason="r", evidence=["L048"])
    app.invoke({"proposal": proposal.model_dump()}, cfg)
    assert app.get_state(cfg).next == ("supervisor",)
    app.update_state(cfg, {"decision": "Declined"})
    assert app.invoke(None, cfg)["audit"][-1]["controller_action"] == "none by agent"


def test_agent_never_acts(context):
    assert "no controller action" in FabricationMonitoringAgent(context).run().recommended_action
