"""The Chapter 13 listing, as printed.

    python -m ch13.listings

Runs from data/horizon_one_tower/operations so the CSV names match the text.
The extended version (identifier mapping, O&M retrieval) is ch13/fm_triage.py.
"""
import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent / "data" / "horizon_one_tower" / "operations")

import pandas as pd

THRESHOLDS = {
    "fan_speed_pct": 85,
    "airflow_m3s": 8.0,
    "filter_dp_pa": 280
}

assets = pd.read_csv("asset_register.csv")
telemetry = pd.read_csv("bms_iot.csv", parse_dates=["timestamp"])
maintenance = pd.read_csv("maintenance_history.csv")
warranties = pd.read_csv("warranties.csv")


def recent_average(asset_id, field, readings=12):
    data = telemetry[
        telemetry["asset_id"] == asset_id
    ].sort_values("timestamp").tail(readings)

    return data[field].mean()


def retrieve_om_guidance(asset_id):
    # In the full workflow, LlamaIndex can retrieve this
    # from O&M documents indexed in Chroma or pgvector.
    return (
        "Inspect filter condition and airflow path where "
        "high differential pressure occurs with reduced airflow."
    )


def triage_hvac_fault(asset_id):
    asset = assets[
        assets["asset_id"] == asset_id
    ].iloc[0]

    fan_speed = recent_average(asset_id, "fan_speed_pct")
    airflow = recent_average(asset_id, "airflow_m3s")
    filter_dp = recent_average(asset_id, "filter_dp_pa")

    evidence = []

    if fan_speed > THRESHOLDS["fan_speed_pct"]:
        evidence.append("Fan speed is above review threshold")

    if airflow < THRESHOLDS["airflow_m3s"]:
        evidence.append("Airflow is below expected range")

    if filter_dp > THRESHOLDS["filter_dp_pa"]:
        evidence.append("Filter differential pressure is high")

    open_tasks = maintenance[
        (maintenance["asset_id"] == asset_id) &
        (maintenance["status"] == "Open")
    ]

    warranty = warranties[
        warranties["asset_id"] == asset_id
    ].iloc[0]["status"]

    likely_cause = "Further investigation required"

    if len(evidence) == 3:
        likely_cause = (
            "Possible airflow restriction or loaded filters"
        )

    return {
        "asset_id": asset_id,
        "location": asset["location"],
        "evidence": evidence,
        "working_hypothesis": likely_cause,
        "om_guidance": retrieve_om_guidance(asset_id),
        "open_maintenance_tasks": len(open_tasks),
        "warranty_status": warranty,
        "recommended_action":
            "Inspect filters and airflow path before component replacement",
        "approval_required": "FM Lead"
    }


ticket = triage_hvac_fault("H1T-AHU-L19-01")

print(ticket)
