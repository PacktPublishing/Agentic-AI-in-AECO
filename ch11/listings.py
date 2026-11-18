"""The Chapter 11 listings, exactly as printed, in chapter order.

    python -m ch11.listings

The listings read their files by name ("pavilion_print_log.csv"),
so this script runs them from data/horizon_one_tower/fabrication.
Reusable versions are in ch11/monitoring.py.
"""
import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent / "data" / "horizon_one_tower" / "fabrication")

# --- Listing 11.1 ---
import pandas as pd

log = pd.read_csv("pavilion_print_log.csv",
                  parse_dates=["timestamp"])

limits = {
    "open_time_min": 15.0,
    "interlayer_ratio_watch": 0.8,
    "target_layer_mm": 15.0,
    "layer_tolerance_mm": 1.0,
    "min_ambient_c": 5.0,
    "pump_rise_bar_per_layer": 0.15,
    "source": "MIX-PAV-02 datasheet Rev B; "
              "printer manual Rev 4",
}

def risk_indicators(log, limits, window=6):
    recent = log.tail(window)
    pump = recent["pump_bar"]
    slope = (pump.iloc[-1] - pump.iloc[0]) / (window - 1)
    latest = log.iloc[-1]
    ratio = latest["interlayer_min"] / limits["open_time_min"]
    deviation = (latest["layer_height_mm"]
                 - limits["target_layer_mm"])
    checks = {
        "interlayer_ratio": (
            ratio, ratio > limits["interlayer_ratio_watch"]),
        "layer_deviation_mm": (
            deviation,
            abs(deviation) > limits["layer_tolerance_mm"]),
        "ambient_c": (
            latest["ambient_c"],
            latest["ambient_c"] < limits["min_ambient_c"]),
        "pump_slope_bar": (
            slope, slope > limits["pump_rise_bar_per_layer"]),
    }
    refs = ", ".join(recent["source"].iloc[[0, -1]])
    return pd.DataFrame(
        [{"indicator": name, "value": round(value, 2),
          "flag": bool(flag), "evidence": refs,
          "limit_source": limits["source"]}
         for name, (value, flag) in checks.items()])

result = risk_indicators(log, limits)
print(result[["indicator", "value", "flag"]])


# --- Listing 11.2 ---
def maturity_c_h(log, layer, datum_c=-10.0):
    rows = log.loc[log["layer"] >= layer,
                   ["timestamp", "layer_temp_c"]]
    hours = (rows["timestamp"].diff()
             .dt.total_seconds().div(3600).fillna(0))
    effective = (rows["layer_temp_c"] - datum_c).clip(lower=0)
    return float((effective * hours).sum())

required = 180.0
achieved = maturity_c_h(log, layer=1)
print(f"Layer 1 maturity: {achieved:.0f} °C·h "
      f"(calibrated requirement {required:.0f} °C·h)")


# --- Listing 11.3 ---
from typing import Literal
from pydantic import BaseModel, Field

class AdjustmentProposal(BaseModel):
    parameter: Literal["print_speed_mm_s",
                       "accelerator_pct",
                       "layer_pause_min"]
    current: float
    proposed: float
    reason: str
    evidence: list[str] = Field(min_length=1)
    proposed_by: str = "Fabrication Monitoring Agent"

ENVELOPE = {
    "print_speed_mm_s": {"min": 80, "max": 150,
                         "max_step_pct": 10},
    "accelerator_pct": {"min": 0.0, "max": 0.8,
                        "max_step_pct": 25},
    "layer_pause_min": {"min": 0, "max": 10,
                        "max_step_pct": 100},
}

def check_proposal(p: AdjustmentProposal) -> list[str]:
    rule = ENVELOPE[p.parameter]
    problems = []
    if not rule["min"] <= p.proposed <= rule["max"]:
        problems.append(f"{p.proposed} is outside "
                        f"{rule['min']}-{rule['max']}")
    if p.current:
        step = abs(p.proposed - p.current) / p.current * 100
        if step > rule["max_step_pct"]:
            problems.append(f"step of {step:.0f}% exceeds "
                            f"{rule['max_step_pct']}%")
    return problems

draft = AdjustmentProposal(
    parameter="print_speed_mm_s", current=120, proposed=160,
    reason="Reduce interlayer interval below 80% of open time",
    evidence=["PRINTLOG-PAV-03-L043", "PRINTLOG-PAV-03-L048"],
)
print(check_proposal(draft))

revised = draft.model_copy(update={"proposed": 130})
print(check_proposal(revised))


# --- Listing 11.4 ---
from datetime import datetime, timezone
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class FabState(TypedDict, total=False):
    proposal: dict
    problems: list
    decision: str
    audit: list

def validate(state):
    proposal = AdjustmentProposal(**state["proposal"])
    return {"problems": check_proposal(proposal)}

def route(state):
    return "rejected" if state["problems"] else "supervisor"

def supervisor(state):
    return {}

def record(state):
    entry = {
        "time": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "proposal": state["proposal"],
        "checker": state.get("problems") or "within envelope",
        "decision": state.get("decision",
                              "rejected by checker"),
        "controller_action": "none by agent",
    }
    return {"audit": state.get("audit", []) + [entry]}

graph = StateGraph(FabState)
graph.add_node("validate", validate)
graph.add_node("supervisor", supervisor)
graph.add_node("record", record)
graph.set_entry_point("validate")
graph.add_conditional_edges(
    "validate", route,
    {"supervisor": "supervisor", "rejected": "record"})
graph.add_edge("supervisor", "record")
graph.add_edge("record", END)
app = graph.compile(checkpointer=MemorySaver(),
                    interrupt_before=["supervisor"])


# --- Listing 11.5 ---
config = {"configurable": {"thread_id": "PAV-03-adjust-01"}}
app.invoke({"proposal": revised.model_dump()}, config)
print(app.get_state(config).next)

decision = (
    "Declined by print supervisor. Hold speed, stop at "
    "layer 50 as a planned joint, apply approved joint "
    "treatment, resume after engineer confirms maturity.")
app.update_state(config, {"decision": decision})
result = app.invoke(None, config)
entry = result["audit"][-1]
print(entry["decision"].split(".")[0])
print(entry["controller_action"])
