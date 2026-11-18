"""Chapter 5, section 5.3: "Validating Massing Against Planning and
Performance."

"Each generated option then passes through the Planning Validation Agent
and Structural Feasibility Agent before it reaches a person. This is not a
second design pass - it is a fast compliance and practicality check,
reusing the constraint set built in Chapter 4 rather than starting from
scratch": "For each of the five Horizon One Tower massing options, check
compliance against the height, setback, and daylight constraints from the
Chapter 4 feasibility report. Separately, flag any option where the
Structural Feasibility Agent identifies a transfer condition, irregular
core position, or floor-to-floor stacking issue that would materially
affect cost or buildability."

Both agents here work on a *batch* of options rather than a single free-text
request, so ``run()`` takes ``options: List[MassingOption]`` instead of the
usual ``request: str`` - the same batch-style deviation used by
``ch4.feasibility_agent.FeasibilityRiskAgent``. Each agent's real per-option
logic lives in a small helper method (:meth:`PlanningValidationAgent.validate`,
:meth:`StructuralFeasibilityAgent.assess`) that is easy to unit test on its
own.
"""
from __future__ import annotations

from typing import Dict, List

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding, MassingOption


class PlanningValidationAgent(BaseAECOAgent):
    name = "Planning Validation Agent"
    chapter = 5
    reviewer_role = "Planning Consultant"
    data_class = "internal"
    purpose = (
        "Check each massing option against the height, setback, and daylight "
        "constraints from the Chapter 4 feasibility report."
    )
    can_do = ["check storeys against the maximum height", "check podium setback against the Policy D9.2 minimum", "check daylight estimate against the threshold"]
    cannot_do = ["approve a design", "waive a planning constraint", "run a detailed VSC/APSH model"]

    def validate(self, option: MassingOption) -> MassingOption:
        """Set ``planning_compliance`` and ``breaches`` on ``option`` in
        place, and return it, so callers can chain this over a list."""
        brief = self.context.project.massing_brief()
        min_setback = brief["setback_constraint_m"]["podium_min_setback_above_6_storeys"]
        max_storeys = brief["max_storeys"]["tower"]

        breaches: List[str] = []
        if option.storeys > max_storeys:
            breaches.append("height")
        if option.podium_setback_m < min_setback:
            breaches.append("setback")
        if option.daylight_impact == "Fails threshold":
            breaches.append("daylight")

        if breaches:
            compliance = f"Breach ({'/'.join(breaches)})"
        elif option.daylight_impact and option.daylight_impact.startswith("Marginal"):
            compliance = "Conditional (needs daylight verification)"
        else:
            compliance = "Compliant"

        option.planning_compliance = compliance
        option.breaches = breaches
        return option

    def run(self, options: List[MassingOption]) -> AgentFinding:  # type: ignore[override]
        validated = [self.validate(o) for o in options]
        breached = [o for o in validated if o.planning_compliance.startswith("Breach")]
        conditional = [o for o in validated if o.planning_compliance.startswith("Conditional")]

        finding_text = (
            f"{len(validated)} option(s) checked against height, setback, and daylight constraints. "
            f"{len(breached)} breach a hard requirement: "
            + ", ".join(f"Option {o.option_id} ({o.planning_compliance})" for o in breached)
            + ". "
            + f"{len(conditional)} require further verification: "
            + ", ".join(f"Option {o.option_id} ({o.planning_compliance})" for o in conditional)
            + "."
        )
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=["massing_brief.json#setback_constraint_m", "massing_brief.json#daylight_threshold"],
            risks=[f"Option {o.option_id} breaches {o.planning_compliance}" for o in breached],
            confidence="Medium",
            recommended_action=(
                "Eliminate options with a hard breach; route conditional options to the daylight "
                "consultant for a technical model before shortlisting."
            ),
        )
        self._log(
            task="Validate massing options against Chapter 4 constraints",
            sources=result.sources,
            tools_used=["PlanningValidationAgent.validate"],
        )
        return result


class StructuralFeasibilityAgent(BaseAECOAgent):
    name = "Structural Feasibility Agent"
    chapter = 5
    reviewer_role = "Structural Engineer"
    data_class = "internal"
    purpose = (
        "Flag massing options with a transfer condition, irregular core position, or "
        "floor-to-floor stacking issue that would materially affect cost or buildability."
    )
    can_do = ["flag transfer structure requirements", "flag multi-core or irregular floorplate options"]
    cannot_do = ["redesign the structural scheme", "approve a structural strategy", "produce a cost estimate"]

    def assess(self, option: MassingOption) -> List[str]:
        flags = []
        if option.requires_transfer_structure:
            flags.append(
                f"Option {option.option_id}: requires a transfer structure at podium level - "
                "materially affects cost and buildability."
            )
        if option.core_count > 1:
            core_word = "two" if option.core_count == 2 else str(option.core_count)
            flags.append(
                f"Option {option.option_id}: requires {core_word} cores - higher structural "
                "cost and coordination complexity."
            )
        if option.floorplate_regularity in ("extended", "split", "large"):
            flags.append(
                f"Option {option.option_id}: {option.floorplate_regularity} floorplate - review "
                "floor-to-floor stacking before proceeding."
            )
        return flags

    def run(self, options: List[MassingOption]) -> AgentFinding:  # type: ignore[override]
        all_flags: List[str] = []
        for option in options:
            all_flags.extend(self.assess(option))

        finding_text = (
            f"{len(all_flags)} structural flag(s) raised across {len(options)} option(s). "
            + " ".join(all_flags) if all_flags else "No structural flags raised."
        )
        narrative = self.context.llm.complete("EVIDENCE:\n" + finding_text)

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=[f"generative_design_agent#Option {o.option_id}" for o in options],
            risks=all_flags,
            confidence="Medium",
            recommended_action="Structural engineer to confirm cost/buildability impact for every flagged option before shortlisting.",
        )
        self._log(
            task="Assess structural feasibility of massing options",
            sources=result.sources,
            tools_used=["StructuralFeasibilityAgent.assess"],
        )
        return result


def summarise_shortlist(options: List[MassingOption]) -> Dict[str, List[MassingOption]]:
    """Chapter 5's "Option Comparison and Summary": "Option A is eliminated
    immediately - a genuine planning breach, not a judgment call. Option D
    is not eliminated but flagged... The remaining options (B, C, and E)
    form the project shortlist."

    Requires :meth:`PlanningValidationAgent.validate` to have already been
    run over ``options`` (so ``planning_compliance`` is set).
    """
    eliminated = [o for o in options if o.planning_compliance and o.planning_compliance.startswith("Breach")]
    flagged = [o for o in options if o.planning_compliance and o.planning_compliance.startswith("Conditional")]
    shortlisted = [o for o in options if o.planning_compliance == "Compliant"]
    return {"eliminated": eliminated, "flagged": flagged, "shortlisted": shortlisted}
