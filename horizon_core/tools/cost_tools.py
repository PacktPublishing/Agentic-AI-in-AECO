"""Cost/quantity calculator tool.

Chapter 1: "if a cost agent needs to compare façade quantities, it should
not guess the numbers. It should retrieve the model quantity export, compare
it with the cost plan, and show the difference." This module is that
deterministic comparison, kept separate from the Cost Agent itself so the
arithmetic is easy to unit-test independently of any LLM narrative layer.
"""
from __future__ import annotations

from typing import Any, Dict


def facade_cost_movement(cost_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the cost movement between the current and proposed façade
    options recorded in the Horizon One Tower cost plan.

    Returns the absolute and percentage movement plus whether the rate for
    the proposed option has actually been confirmed by a supplier - the
    distinction Chapter 4 insists on between a "hard" figure and an
    unconfirmed assumption.
    """
    facade = cost_plan["facade_package"]
    current_total = facade["current_option"]["total"]
    proposed_total = facade["proposed_option"]["total"]
    movement = proposed_total - current_total
    return {
        "current_option": facade["current_option"]["name"],
        "proposed_option": facade["proposed_option"]["name"],
        "quantity_m2": facade["quantity_m2"],
        "movement_gbp": movement,
        "movement_pct": round(movement / current_total * 100, 1) if current_total else None,
        "direction": "increase" if movement > 0 else "decrease" if movement < 0 else "no change",
        "rate_confirmed": facade["proposed_option"].get("rate_confirmed", False),
        "quantity_assumption": facade["quantity_assumption"],
    }
