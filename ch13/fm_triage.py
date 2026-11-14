"""Chapter 13: FM fault triage, with identifier mapping and O&M retrieval.

Extends the chapter listing in the two ways the text says a full workflow
needs:

* ``resolve_asset`` maps the BMS point (AHU_19_1) and register ID
  (MEP-AHU-019A) to the canonical asset ID before anything is compared;
* ``retrieve_om_guidance`` queries O&M sections through the Chapter 2
  Agent Knowledge Base and returns the citation with the text.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.schemas import DocumentRecord

THRESHOLDS = {"fan_speed_pct": 85, "airflow_m3s": 8.0, "filter_dp_pa": 280}


class FMData:
    def __init__(self, project):
        get = lambda n, **k: project.chapter_csv("operations", n, **k)  # noqa: E731
        self.assets = get("asset_register.csv")
        self.telemetry = get("bms_iot.csv", parse_dates=["timestamp"])
        self.maintenance = get("maintenance_history.csv")
        self.warranties = get("warranties.csv")
        self.kb = AgentKnowledgeBase()
        self.kb.ingest([
            DocumentRecord(project="Horizon One Tower", file=s["doc_id"], discipline="MEP", revision=s["revision"],
                           status="Approved", stage="Operation", date=date(2028, 6, 1), source="O&M manual",
                           text=s["text"], topic=s["section"], owner="FM Lead")
            for s in project.chapter_json("operations", "om_guidance.json")
        ])

    def resolve_asset(self, any_id: str) -> str:
        for column in ("asset_id", "register_id", "bms_point"):
            match = self.assets.loc[self.assets[column].eq(any_id), "asset_id"]
            if not match.empty:
                return match.iloc[0]
        raise KeyError(f"No asset mapping for {any_id!r}; resolve the identifier before triage")

    def recent_average(self, asset_id: str, field: str, readings: int = 12) -> float:
        data = self.telemetry[self.telemetry["asset_id"] == asset_id].sort_values("timestamp").tail(readings)
        return float(data[field].mean())

    def retrieve_om_guidance(self, query: str):
        hits = self.kb.query(query, top_k=1, status_in=["Approved"])
        if not hits:
            return None, None
        record, _ = hits[0]
        return record.text, f"{record.file} §{record.topic} (Rev {record.revision})"


def triage_hvac_fault(fm: FMData, any_id: str) -> dict:
    asset_id = fm.resolve_asset(any_id)
    asset = fm.assets[fm.assets["asset_id"] == asset_id].iloc[0]
    readings = {f: fm.recent_average(asset_id, f) for f in THRESHOLDS}
    evidence = []
    if readings["fan_speed_pct"] > THRESHOLDS["fan_speed_pct"]:
        evidence.append("Fan speed is above review threshold")
    if readings["airflow_m3s"] < THRESHOLDS["airflow_m3s"]:
        evidence.append("Airflow is below expected range")
    if readings["filter_dp_pa"] > THRESHOLDS["filter_dp_pa"]:
        evidence.append("Filter differential pressure is high")
    open_tasks = fm.maintenance[(fm.maintenance["asset_id"] == asset_id) & (fm.maintenance["status"] == "Open")]
    warranty = fm.warranties[fm.warranties["asset_id"] == asset_id].iloc[0]
    guidance, citation = fm.retrieve_om_guidance("filter differential pressure airflow fan demand")
    likely = "Possible airflow restriction or loaded filters" if len(evidence) == 3 else "Further investigation required"
    return {
        "asset_id": asset_id, "location": asset["location"], "readings": {k: round(v, 2) for k, v in readings.items()},
        "evidence": evidence, "working_hypothesis": likely, "om_guidance": guidance, "om_citation": citation,
        "open_maintenance_tasks": open_tasks["task_id"].tolist(), "warranty_status": warranty["status"],
        "warranty_conditions": warranty["conditions"],
        "recommended_action": "Inspect filters and airflow path before component replacement",
        "approval_required": "FM Lead",
    }
