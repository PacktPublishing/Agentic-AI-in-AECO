"""The Chapter 10 listings, in the order they appear in the chapter.

    python -m ch10.listings
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "horizon_one_tower" / "programme"

# Coding example: compare one progress snapshot
schedule = pd.read_csv(DATA / "schedule.csv")
observations = pd.read_csv(DATA / "progress.csv")
keys = ["activity_id", "zone_id", "data_date"]

report = schedule.merge(observations, on=keys, how="outer", validate="one_to_one", indicator=True)
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
print(report[["activity_id", "planned_pct", "observed_pct", "variance_pp", "finding"]].to_string(index=False))

# Coding example: price a conditional deployment option
crew = 8
blocked_shifts = 3                 # Planner-supplied scenario
standby_per_shift_gbp = 240
proposed_move = 5
alternative_capacity = 5           # Still requires confirmation
transfer_gbp = 600

if not 0 <= proposed_move <= min(crew, alternative_capacity):
    raise ValueError("Proposed move exceeds available capacity.")

hold_allowance = crew * blocked_shifts * standby_per_shift_gbp
redeploy_allowance = ((crew - proposed_move) * blocked_shifts * standby_per_shift_gbp
                      + (transfer_gbp if proposed_move else 0))
comparison = {
    "hold_allowance_gbp": hold_allowance,
    "conditional_redeployment_allowance_gbp": redeploy_allowance,
    "approval_status": "awaiting_human_review",
}
print(comparison)
