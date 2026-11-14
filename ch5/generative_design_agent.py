"""Chapter 5, section 5.2: "Generating Options with Constraints" - the
Generative Design Agent.

"With parameters defined, the Generative Design Agent produces massing
variations - not finished designs, but volumetric studies that respect the
hard constraints and explore different responses to the soft preferences."
"For Horizon One Tower, this stage produced five initial variations, each
taking a different position on the trade-off between plot efficiency,
daylight impact, and podium activation."

This module does not hardcode the book's table of results as strings - it
computes plot efficiency and a first-pass daylight estimate from real
geometric inputs (footprint, setback, storeys, core count), against
thresholds tied to the Chapter 4 feasibility brief
(``data/horizon_one_tower/massing_brief.json``). The five canonical options
(A-E) in :func:`generate_horizon_one_tower_options` reproduce the book's
table because their input parameters were chosen to match the book's
narrative descriptions ("Full footprint tower", "Stepped podium, slim
tower", ...) - but :func:`generate_variation` is the real, reusable
function, and it is exactly how a sixth option ("Option F") would be added
for a future chapter: call it with new numbers, get a consistently-derived
result back.

Planning compliance and structural practicality are deliberately *not* set
here - Chapter 5 is explicit that "each generated option then passes
through the Planning Validation Agent and Structural Feasibility Agent
before it reaches a person." Those two agents live in
``ch5.validation_agents`` and fill in the remaining fields.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from horizon_core.schemas import MassingOption

# Nominal maximum buildable tower footprint used to express "plot
# efficiency" as a percentage of what the site could theoretically support,
# after allowing for the public realm and setback requirements in the
# massing brief. This is a simplifying assumption for a teaching case
# study, not a real capacity model.
MAX_TOWER_FOOTPRINT_M2 = 1750.0

# Daylight clearance model. Canal Walk Residences (see gis_constraints.json)
# is the nearest sensitive residential receptor. A massing option's
# estimated clearance to it is modelled as a small baseline gap, plus twice
# the podium setback (a larger setback helps directly), minus an
# encroachment penalty proportional to how much of the maximum buildable
# footprint the option uses (a fuller footprint pushes the building mass
# closer to the boundary). This is a transparent, tunable proxy for a real
# VSC/APSH daylight study - good enough to separate options at a first
# pass, not a substitute for the technical model Chapter 4's Environmental
# Risk Agent already flags as outstanding.
DAYLIGHT_BASE_GAP_M = 5.8
DAYLIGHT_SETBACK_MULTIPLIER = 2.0
FOOTPRINT_ENCROACHMENT_FACTOR_M = 8.0


def _bucket_plot_efficiency(tower_footprint_m2: float) -> str:
    utilisation = tower_footprint_m2 / MAX_TOWER_FOOTPRINT_M2
    if utilisation >= 0.90:
        return "High"
    if utilisation >= 0.80:
        return "Medium-high"
    if utilisation >= 0.65:
        return "Medium"
    if utilisation >= 0.50:
        return "Medium-low"
    return "Low"


def estimate_daylight_clearance_m(tower_footprint_m2: float, podium_setback_m: float) -> float:
    """A simple, transparent proxy for daylight clearance to the nearest
    sensitive residential receptor: baseline gap, plus setback benefit,
    minus footprint-utilisation encroachment. See the module-level
    constants above for the model this implements.
    """
    utilisation = tower_footprint_m2 / MAX_TOWER_FOOTPRINT_M2
    encroachment = utilisation * FOOTPRINT_ENCROACHMENT_FACTOR_M
    return DAYLIGHT_BASE_GAP_M + DAYLIGHT_SETBACK_MULTIPLIER * podium_setback_m - encroachment


def _bucket_daylight(clearance_m: float) -> str:
    if clearance_m < 2.5:
        return "Fails threshold"
    if clearance_m < 4.5:
        return "Marginal (close to threshold)"
    if clearance_m < 7.0:
        return "Meets threshold"
    return "Meets threshold with margin"


def _embodied_carbon_direction(requires_transfer_structure: bool, floorplate_regularity: str) -> str:
    if requires_transfer_structure:
        return "Higher (larger floorplate, more transfer)"
    if floorplate_regularity == "regular":
        return "Favourable (regular grid)"
    return "Neutral"


def _structural_practicality(requires_transfer_structure: bool, core_count: int) -> str:
    if requires_transfer_structure:
        return "Requires transfer structure at podium"
    if core_count > 1:
        return "Requires two cores, higher cost"
    return "Straightforward"


def _estimate_gia(
    tower_footprint_m2: float,
    podium_footprint_m2: float,
    storeys: int,
    podium_storeys: int,
    core_count: int,
) -> float:
    # The tower rises above the podium, so only the storeys above the podium
    # use the tower footprint; the podium storeys use the podium footprint.
    raw = tower_footprint_m2 * (storeys - podium_storeys) + podium_footprint_m2 * podium_storeys
    # A second core takes net-usable area for its own enclosure/lobbies.
    core_deduction_factor = 0.97 if core_count > 1 else 1.0
    return round(raw * core_deduction_factor, -1)  # round to nearest 10 sqm


def generate_variation(
    option_id: str,
    label: str,
    tower_footprint_m2: float,
    podium_footprint_m2: float,
    setback_strategy: str,
    podium_setback_m: float,
    storeys: int,
    core_count: int,
    requires_transfer_structure: bool,
    floorplate_regularity: str,
    podium_storeys: int = 6,
) -> MassingOption:
    """Generate one massing option from real geometric parameters.

    This is the reusable core of the Generative Design Agent: plot
    efficiency and the first-pass daylight estimate are *computed*, not
    supplied. Structural practicality and embodied carbon direction are
    filled in here too (they follow directly from the structural inputs),
    but planning compliance is deliberately left unset - that is the
    Planning Validation Agent's job (``ch5.validation_agents``), reusing the
    Chapter 4 constraint set rather than being decided at generation time.
    """
    clearance = estimate_daylight_clearance_m(tower_footprint_m2, podium_setback_m)
    gia = _estimate_gia(tower_footprint_m2, podium_footprint_m2, storeys, podium_storeys, core_count)

    return MassingOption(
        option_id=option_id,
        label=label,
        tower_footprint_m2=tower_footprint_m2,
        podium_footprint_m2=podium_footprint_m2,
        setback_strategy=setback_strategy,
        podium_setback_m=podium_setback_m,
        storeys=storeys,
        core_count=core_count,
        requires_transfer_structure=requires_transfer_structure,
        floorplate_regularity=floorplate_regularity,
        gross_internal_area_m2=gia,
        plot_efficiency=_bucket_plot_efficiency(tower_footprint_m2),
        daylight_impact=_bucket_daylight(clearance),
        embodied_carbon_direction=_embodied_carbon_direction(requires_transfer_structure, floorplate_regularity),
        structural_practicality=_structural_practicality(requires_transfer_structure, core_count),
        notes=[f"Estimated daylight clearance to nearest sensitive receptor (Canal Walk Residences): {clearance:.1f}m."],
    )


# The five canonical Horizon One Tower variations from Chapter 5, section
# 5.2 - "A: Full footprint tower", "B: Stepped podium, slim tower",
# "C: Split massing, two cores", "D: Maximised residential, reduced retail
# frontage", "E: Podium-led, reduced tower footprint". Parameters were
# chosen so the *computed* plot efficiency / daylight buckets above land on
# the book's own table; nothing about the labels themselves is hardcoded.
_CANONICAL_OPTION_PARAMS: List[Dict[str, Any]] = [
    dict(
        option_id="A",
        label="Full footprint tower",
        tower_footprint_m2=1700,
        podium_footprint_m2=3000,
        setback_strategy="None - full footprint built to the site boundary",
        podium_setback_m=0.0,
        storeys=36,
        core_count=1,
        requires_transfer_structure=True,
        floorplate_regularity="large",
    ),
    dict(
        option_id="B",
        label="Stepped podium, slim tower",
        tower_footprint_m2=1550,
        podium_footprint_m2=3000,
        setback_strategy="3m stepped setback above the podium, slim tower above",
        podium_setback_m=3.0,
        storeys=30,
        core_count=1,
        requires_transfer_structure=False,
        floorplate_regularity="regular",
    ),
    dict(
        option_id="C",
        label="Split massing, two cores",
        tower_footprint_m2=1300,
        podium_footprint_m2=3000,
        setback_strategy="Split massing with a central light well between two cores",
        podium_setback_m=3.5,
        storeys=30,
        core_count=2,
        requires_transfer_structure=False,
        floorplate_regularity="split",
    ),
    dict(
        option_id="D",
        label="Maximised residential, reduced retail frontage",
        tower_footprint_m2=1650,
        podium_footprint_m2=2400,
        setback_strategy="Extended tower footprint over the podium, minimal additional setback",
        podium_setback_m=3.0,
        storeys=30,
        core_count=1,
        requires_transfer_structure=False,
        floorplate_regularity="extended",
    ),
    dict(
        option_id="E",
        label="Podium-led, reduced tower footprint",
        tower_footprint_m2=1100,
        podium_footprint_m2=3000,
        setback_strategy="Reduced tower footprint, set well back from the podium edge",
        podium_setback_m=6.0,
        storeys=30,
        core_count=1,
        requires_transfer_structure=False,
        floorplate_regularity="regular",
    ),
]


def generate_horizon_one_tower_options() -> List[MassingOption]:
    """Chapter 5's worked prompt, made runnable: "Generate five massing
    variations for Horizon One Tower within the defined parameter set." """
    return [generate_variation(**params) for params in _CANONICAL_OPTION_PARAMS]


@dataclass
class GenerativeDesignAgent:
    """Thin, stateless wrapper so this agent has the same call shape
    (``.run(...)``) as the rest of the book's agents, even though its real
    logic lives in the pure functions above (kept top-level so they are
    trivially unit-testable without constructing an ``AgentContext``).
    """

    def run(self, brief: Dict[str, Any] | None = None) -> List[MassingOption]:
        return generate_horizon_one_tower_options()
