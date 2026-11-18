"""Chapter 10: progress comparison and the conditional redeployment option."""
from __future__ import annotations

from typing import Optional

import pandas as pd

KEYS = ["activity_id", "zone_id", "data_date"]


def compare_progress(schedule: pd.DataFrame, observations: pd.DataFrame) -> pd.DataFrame:
    report = schedule.merge(observations, on=KEYS, how="outer", validate="one_to_one", indicator=True)
    planned = pd.to_numeric(report["planned_pct"], errors="coerce")
    observed = pd.to_numeric(report["observed_pct"], errors="coerce")
    has_source = report["evidence_ref"].fillna("").astype(str).str.strip().ne("")
    usable = (report["_merge"].eq("both") & report["verified"].eq(True) & has_source
              & planned.between(0, 100) & observed.between(0, 100))
    report["variance_pp"] = (observed - planned).where(usable)
    report["finding"] = "verify_evidence"
    report.loc[usable & (observed < planned), "finding"] = "behind_plan"
    report.loc[usable & (observed >= planned), "finding"] = "at_or_ahead"
    report["approval_status"] = "awaiting_human_review"
    return report.drop(columns="_merge")


def redeployment_option(s: dict) -> dict:
    crew, shifts, rate = s["crew"], s["blocked_shifts"], s["standby_per_shift_gbp"]
    move = s["proposed_move"]
    if not 0 <= move <= min(crew, s["alternative_capacity"]):
        raise ValueError("Proposed move exceeds available capacity.")
    hold = crew * shifts * rate
    redeploy = (crew - move) * shifts * rate + (s["transfer_gbp"] if move else 0)
    return {"hold_allowance_gbp": hold, "conditional_redeployment_allowance_gbp": redeploy,
            "conditions": [] if s.get("alternative_confirmed") else
            ["Construction manager to confirm area release, task suitability, materials, supervision and access"],
            "approval_status": "awaiting_human_review"}


def apply_spatial_observation(report: pd.DataFrame, observation: Optional[dict]) -> pd.DataFrame:
    """Attach a confirmed Chapter 12 inspection result to the matching
    activity. Physical progress is not changed; the quality issue is recorded
    next to it, so the activity reads "complete with an open quality issue"
    once the pour is finished."""
    report = report.copy()
    report["quality_issue"] = ""
    if observation and observation.get("status") == "Confirmed":
        links = observation["links"]
        mask = report["activity_id"].eq(links["activity"]) & report["zone_id"].eq(links["zone"])
        report.loc[mask, "quality_issue"] = f"{observation['title']} (affects {links['package']})"
    return report
