"""Chapter 11: the Fabrication Monitoring Agent's tools, driven by limits.json.

Advisory plane only. Nothing in this module can send a command to a printer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict

import pandas as pd
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


def risk_indicators(log: pd.DataFrame, limits: dict, window: int = 6) -> pd.DataFrame:
    m, pr, w = limits["material"], limits["printer"], limits["watch"]
    recent = log.tail(window)
    pump = recent["pump_bar"]
    slope = (pump.iloc[-1] - pump.iloc[0]) / (window - 1)
    latest = log.iloc[-1]
    ratio = latest["interlayer_min"] / m["open_time_min"]
    deviation = latest["layer_height_mm"] - pr["target_layer_mm"]
    checks = {
        "interlayer_ratio": (ratio, ratio > w["interlayer_ratio"]),
        "layer_deviation_mm": (deviation, abs(deviation) > pr["layer_tolerance_mm"]),
        "ambient_c": (latest["ambient_c"], latest["ambient_c"] < m["min_ambient_c"]),
        "pump_slope_bar": (slope, slope > w["pump_rise_bar_per_layer"]),
    }
    refs = ", ".join(recent["source"].iloc[[0, -1]])
    source = f"{m['id']} datasheet {m['revision']}; printer manual {pr['manual']}"
    return pd.DataFrame([{"indicator": k, "value": round(v, 2), "flag": bool(f), "evidence": refs,
                          "limit_source": source} for k, (v, f) in checks.items()])


def maturity_c_h(log: pd.DataFrame, layer: int, datum_c: float = -10.0) -> float:
    rows = log.loc[log["layer"] >= layer, ["timestamp", "layer_temp_c"]]
    hours = pd.to_datetime(rows["timestamp"]).diff().dt.total_seconds().div(3600).fillna(0)
    return float(((rows["layer_temp_c"] - datum_c).clip(lower=0) * hours).sum())


class AdjustmentProposal(BaseModel):
    parameter: Literal["print_speed_mm_s", "accelerator_pct", "layer_pause_min"]
    current: float
    proposed: float
    reason: str
    evidence: list[str] = Field(min_length=1)
    proposed_by: str = "Fabrication Monitoring Agent"


def envelope(limits: dict) -> dict:
    pr, m = limits["printer"], limits["material"]
    return {
        "print_speed_mm_s": {"min": pr["print_speed_mm_s"][0], "max": pr["print_speed_mm_s"][1],
                             "max_step_pct": pr["max_speed_step_pct"]},
        "accelerator_pct": {"min": m["accelerator_pct"][0], "max": m["accelerator_pct"][1], "max_step_pct": 25},
        "layer_pause_min": {"min": 0, "max": 10, "max_step_pct": 100},
    }


def check_proposal(p: AdjustmentProposal, env: dict) -> list[str]:
    rule = env[p.parameter]
    problems = []
    if not rule["min"] <= p.proposed <= rule["max"]:
        problems.append(f"{p.proposed} is outside {rule['min']}-{rule['max']}")
    if p.current:
        step = abs(p.proposed - p.current) / p.current * 100
        if step > rule["max_step_pct"]:
            problems.append(f"step of {step:.0f}% exceeds {rule['max_step_pct']}%")
    return problems


class FabState(TypedDict, total=False):
    proposal: dict
    problems: list
    decision: str
    audit: list


def build_gate(env: dict):
    """The approval gate: validate, pause before the supervisor, record."""
    def validate(state):
        return {"problems": check_proposal(AdjustmentProposal(**state["proposal"]), env)}

    def record(state):
        entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "proposal": state["proposal"], "checker": state.get("problems") or "within envelope",
                 "decision": state.get("decision", "rejected by checker"), "controller_action": "none by agent"}
        return {"audit": state.get("audit", []) + [entry]}

    g = StateGraph(FabState)
    g.add_node("validate", validate)
    g.add_node("supervisor", lambda state: {})
    g.add_node("record", record)
    g.set_entry_point("validate")
    g.add_conditional_edges("validate", lambda s: "rejected" if s["problems"] else "supervisor",
                            {"supervisor": "supervisor", "rejected": "record"})
    g.add_edge("supervisor", "record")
    g.add_edge("record", END)
    return g.compile(checkpointer=MemorySaver(), interrupt_before=["supervisor"])
