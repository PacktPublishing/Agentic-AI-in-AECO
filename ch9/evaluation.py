"""Chapter 9 supplier evaluation: the listings as reusable functions.

``Bid`` validates every supplier response before any score is calculated.
``evaluate`` applies the published weights and anchors; a bid with an
unresolved flag gets no score at all rather than a penalised one, so it cannot
be ranked above a complete bid by accident.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class Bid(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)
    vendor: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    baseline_id: str = Field(min_length=1)
    rate_gbp_m2: float = Field(gt=0)
    extras_gbp: float = Field(ge=0)
    lead_weeks: int = Field(ge=0)
    carbon_kg_m2: float | None = Field(ge=0)
    reliability: int = Field(ge=1, le=5)
    supply_risk: int = Field(ge=1, le=5)
    technical_scope: Literal["accepted", "pending", "rejected"]
    quote_ref: str = Field(min_length=1)
    review_ref: str | None = Field(default=None, min_length=1)


WEIGHTS = {"cost": 0.40, "time": 0.25, "carbon": 0.20, "reliability": 0.10, "supply": 0.05}


def anchors_for(package: dict) -> dict:
    # Each pair is (100-point anchor, zero-point anchor).
    return {"cost": (900_000.0, package["budget_gbp"]),
            "time": (12.0, float(package["max_lead_weeks"])),
            "carbon": (60.0, 100.0)}


def lower_is_better(value: float, best: float, worst: float) -> float:
    if worst <= best:
        raise ValueError("Scoring anchors must increase.")
    return max(0.0, min(100.0, 100 * (worst - value) / (worst - best)))


def load_bids(project) -> tuple[dict, list[Bid], pd.DataFrame]:
    package = project.chapter_json("procurement", "package.json")
    raw = project.chapter_csv("procurement", "bids.csv", keep_default_na=False)
    bids = []
    for row in raw.to_dict("records"):
        bids.append(Bid(
            vendor=row["vendor"], package_id=package["package_id"], baseline_id=package["baseline_id"],
            rate_gbp_m2=float(row["rate_gbp_m2"]), extras_gbp=float(row["extras_gbp"]),
            lead_weeks=int(row["lead_weeks"]),
            carbon_kg_m2=float(row["carbon_kg_m2"]) if row["carbon_kg_m2"] != "" else None,
            reliability=int(row["reliability"]), supply_risk=int(row["supply_risk"]),
            technical_scope=row["technical_scope"], quote_ref=row["quote_ref"], review_ref=row["review_ref"] or None,
        ))
    return package, bids, raw


def evaluate(bid: Bid, package: dict, weights: dict = WEIGHTS) -> dict:
    anchors = anchors_for(package)
    total = package["quantity_m2"] * bid.rate_gbp_m2 + bid.extras_gbp
    flags = []
    if (bid.package_id, bid.baseline_id) != (package["package_id"], package["baseline_id"]):
        flags.append("Package or baseline mismatch")
    if bid.technical_scope != "accepted" or not bid.review_ref:
        flags.append("Technical/scope review unresolved")
    if bid.carbon_kg_m2 is None:
        flags.append("Carbon evidence missing")
    if total > package["budget_gbp"]:
        flags.append("Above budget boundary")
    if bid.lead_weeks > package["max_lead_weeks"]:
        flags.append("Beyond delivery window")
    components, score = {}, None
    if not flags:
        components = {
            "cost": lower_is_better(total, *anchors["cost"]),
            "time": lower_is_better(bid.lead_weeks, *anchors["time"]),
            "carbon": lower_is_better(bid.carbon_kg_m2, *anchors["carbon"]),
            "reliability": 25.0 * (bid.reliability - 1),
            "supply": 25.0 * (5 - bid.supply_risk),
        }
        score = sum(weights[k] * v for k, v in components.items())
    return {"vendor": bid.vendor, "total_gbp": total, "score": score, "components": components,
            "flags": flags, "quote_ref": bid.quote_ref, "review_ref": bid.review_ref}


def evaluate_all(bids: list[Bid], package: dict) -> list[dict]:
    matrix = [evaluate(b, package) for b in bids]
    ranked = [r for r in matrix if r["score"] is not None]
    for row in matrix:
        row["rank"] = (1 + sum(o["score"] > row["score"] for o in ranked)) if row["score"] is not None else None
    return matrix


def review_pack(package: dict, bids: list[Bid], matrix: list[dict]) -> dict:
    return deepcopy({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "package": package, "evaluation_version": "DEMO-EVAL-01",
        "weights": WEIGHTS, "anchors": anchors_for(package),
        "inputs": [b.model_dump() for b in bids], "matrix": matrix,
        "review_status": "awaiting_commercial_review", "approved_supplier": None,
    })
