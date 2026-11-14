"""Chapter 6: "BIM Auditing, Compliance and Technical Design Review" - the
Audit Agent, and the BIMGUARD workflow it powers.

"The workflow behind this is called BIMGUARD: an Audit Agent working across
the federated model, IFC exports, drawing set, and specifications, checking
each against the project's own Building Information Requirements - not
against some abstract standard, but against what Horizon One Tower's own
BIM Execution Plan actually committed to delivering."

This module implements all four of the chapter's sections as callable
methods on one :class:`AuditAgent`, each backed by a small pure function so
the underlying logic is easy to test independently of any LLM narrative
layer:

- 6.1 "From Clash Detection to Semantic Auditing" -> :meth:`AuditAgent.run`
  (:func:`find_missing_parameters` scoped to the book's own sample prompt:
  fire rating, asset classification, and maintenance access data).
- 6.2 "Checking BIM Against Project Information Requirements" ->
  :meth:`AuditAgent.run_bep_check` (:func:`find_missing_parameters` run
  across the full BIM Execution Plan, tagged with which downstream process
  each gap affects).
- 6.3 "Reviewing Drawings and Specifications Together" ->
  :meth:`AuditAgent.run_document_consistency_check`
  (:func:`facade_discrepancy_narrative` / :func:`facade_discrepancy_entry`).
- 6.4 "Creating Trusted Design Review Logs" ->
  :meth:`AuditAgent.generate_compliance_log`, assembling 6.2's and 6.3's
  findings into the book's structured table (``ComplianceLogEntry`` rows,
  rendered by ``ch6.compliance_log``).

Nothing here hardcodes the specific findings the book's example table
shows. :func:`find_missing_parameters` reads whatever objects and BEP
requirements ``HorizonOneTowerProject`` hands it and reports whatever gaps
actually exist; the fact that it currently reproduces the book's "batch of
doors with a placeholder fire rating" and "three retail units missing a
classification code" findings is a property of the data in
``data/horizon_one_tower/bim_objects.json``, not of this code. Adding a new
object category or requirement (Chapter 7 or later) means one new entry in
``bim_execution_plan.json`` and one new rule in :data:`FINDING_RULES` -
nothing else here needs to change.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from horizon_core.agent_base import BaseAECOAgent
from horizon_core.schemas import AgentFinding, ComplianceLogEntry, InformationRequirement

# Maps a BIM Execution Plan object category to the key it's stored under in
# ``bim_objects.json``. Adding a new object category (e.g. "Window") is one
# new entry here plus a matching list in the data file.
_CATEGORY_TO_DATA_KEY = {
    "Door": "doors",
    "Wall": "walls",
    "Mechanical Asset": "mechanical_assets",
    "Room": "rooms",
}


def _is_gap(parameter: str, value: Any) -> bool:
    """Whether ``value`` counts as a gap for ``parameter``.

    Most parameters are missing/placeholder-detected the same way: ``None``
    or the literal string ``"PLACEHOLDER"`` (Section 6.2's worked example -
    "a batch of doors carrying a placeholder fire rating value left over
    from an early design template"). ``accessibility_clearance_confirmed``
    is a boolean requirement instead: the gap is that it was never
    confirmed (``False``), not that it is unset.
    """
    if parameter == "accessibility_clearance_confirmed":
        return value is False
    return value is None or value == "PLACEHOLDER"


def find_missing_parameters(
    bim_objects: Dict[str, Any],
    bep: List[InformationRequirement],
    categories: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Section 6.1 / 6.2's core check: for every BEP requirement (optionally
    restricted to ``categories``), scan the matching objects and report every
    instance where the required parameter is missing or a placeholder.

    Returns one dict per gap: ``object_id``, ``object_category``,
    ``location``, ``parameter``, ``affects`` (which downstream process the
    gap threatens), and the object's ``name`` if it has one. Grouping these
    into the book's compliance-log rows is :func:`group_findings`'s job, not
    this function's - this function only reports what it finds.
    """
    gaps: List[Dict[str, Any]] = []
    for requirement in bep:
        if categories is not None and requirement.object_category not in categories:
            continue
        data_key = _CATEGORY_TO_DATA_KEY.get(requirement.object_category)
        if data_key is None:
            continue
        for obj in bim_objects.get(data_key, []):
            if requirement.applies_to and not obj.get("accessible_facility", False):
                # This requirement only applies to a subset of objects in
                # the category (e.g. accessibility clearance only applies to
                # rooms flagged as accessible facilities) - skip the rest.
                continue
            value = obj.get(requirement.parameter)
            if _is_gap(requirement.parameter, value):
                gaps.append(
                    {
                        "object_id": obj["object_id"],
                        "object_category": requirement.object_category,
                        "location": obj.get("location") or obj.get("name", obj["object_id"]),
                        "name": obj.get("name"),
                        "parameter": requirement.parameter,
                        "affects": requirement.affects,
                    }
                )
    return gaps


def _describe_door_fire_rating(records: List[Dict[str, Any]]) -> str:
    return f"Batch of {len(records)} doors carrying placeholder fire rating"


def _describe_wall_fire_rating(records: List[Dict[str, Any]]) -> str:
    return f"{len(records)} fire compartment wall(s) missing a confirmed fire resistance rating"


def _describe_mechanical_maintenance_access(records: List[Dict[str, Any]]) -> str:
    if len(records) == 1:
        return "Mechanical plant missing maintenance access parameter"
    return f"{len(records)} mechanical plant items missing maintenance access parameter"


def _describe_door_asset_classification(records: List[Dict[str, Any]]) -> str:
    return f"{len(records)} door(s) missing asset classification"


def _describe_door_maintenance_access(records: List[Dict[str, Any]]) -> str:
    return f"{len(records)} door(s) missing maintenance access clearance"


def _describe_mechanical_asset_classification(records: List[Dict[str, Any]]) -> str:
    return f"{len(records)} mechanical asset(s) missing asset classification"


def _describe_room_classification(records: List[Dict[str, Any]]) -> str:
    names = [r["name"] for r in records if r.get("name")]
    if names and all("retail" in n.lower() for n in names):
        return f"Room classification code missing for {len(records)} retail units"
    return f"Room classification code missing for {len(records)} room(s)"


def _describe_room_accessibility(records: List[Dict[str, Any]]) -> str:
    if len(records) == 1:
        return "Accessible WC clearance not confirmed against drawing dimensions"
    return f"{len(records)} accessible facilities have clearance not confirmed against drawing dimensions"


# (object_category, parameter) -> how to report a batch of gaps found for
# that combination. This is where "grouped, not one row per object" and the
# book's own severity/responsible-discipline choices live. A pair with no
# entry here still gets reported (see the fallback in ``group_findings``) -
# this table makes the reporting *readable*, it doesn't gate detection.
FINDING_RULES: Dict[tuple, Dict[str, Any]] = {
    ("Door", "fire_rating"): dict(
        category="Fire data", severity="High", responsible_discipline="Fire engineer",
        source="Model / IFC export", describe=_describe_door_fire_rating,
    ),
    ("Wall", "fire_rating"): dict(
        category="Fire data", severity="High", responsible_discipline="Fire engineer",
        source="Model / IFC export", describe=_describe_wall_fire_rating,
    ),
    ("Mechanical Asset", "maintenance_access_clearance_mm"): dict(
        category="Asset data", severity="Medium", responsible_discipline="MEP engineer / FM lead",
        source="Model", describe=_describe_mechanical_maintenance_access,
    ),
    ("Door", "asset_classification"): dict(
        category="Asset data", severity="Medium", responsible_discipline="BIM manager",
        source="Model", describe=_describe_door_asset_classification,
    ),
    ("Door", "maintenance_access_clearance_mm"): dict(
        category="Asset data", severity="Medium", responsible_discipline="Architect / FM lead",
        source="Model", describe=_describe_door_maintenance_access,
    ),
    ("Mechanical Asset", "asset_classification"): dict(
        category="Asset data", severity="Medium", responsible_discipline="MEP engineer / FM lead",
        source="Model", describe=_describe_mechanical_asset_classification,
    ),
    ("Room", "classification_code"): dict(
        category="Room data", severity="Low", responsible_discipline="BIM manager",
        source="Model", describe=_describe_room_classification,
    ),
    ("Room", "accessibility_clearance_confirmed"): dict(
        category="Accessibility", severity="Medium", responsible_discipline="Architect",
        source="Drawing set", describe=_describe_room_accessibility,
    ),
}


def group_findings(gaps: List[Dict[str, Any]]) -> List[ComplianceLogEntry]:
    """Batch raw gap records from :func:`find_missing_parameters` into
    compliance-log rows - "a batch of doors" is one row, not one row per
    door, matching the book's own presentation of this data.
    """
    grouped: Dict[tuple, List[Dict[str, Any]]] = {}
    for gap in gaps:
        key = (gap["object_category"], gap["parameter"])
        grouped.setdefault(key, []).append(gap)

    entries = []
    for key, records in grouped.items():
        rule = FINDING_RULES.get(key)
        if rule is None:
            # A category/parameter combination with no dedicated wording yet
            # (e.g. a requirement added for a future chapter) still gets
            # reported, generically, rather than silently dropped.
            category, parameter = key
            rule = dict(
                category="Other",
                severity="Medium",
                responsible_discipline="BIM manager",
                source="Model",
                describe=lambda r, c=category, p=parameter: (
                    f"{len(r)} {c.lower()} object(s) missing {p.replace('_', ' ')}"
                ),
            )
        entries.append(
            ComplianceLogEntry(
                category=rule["category"],
                finding=rule["describe"](records),
                source=rule["source"],
                severity=rule["severity"],
                responsible_discipline=rule["responsible_discipline"],
                object_ids=[r["object_id"] for r in records],
            )
        )
    return entries


def _facade_values_differ(doc_set: Dict[str, Any]) -> bool:
    values = {doc_set["specification"]["value"], doc_set["drawing"]["value"], doc_set["model"]["value"]}
    return len(values) > 1


def most_recent_facade_source(doc_set: Dict[str, Any]) -> str:
    """Which of the three documents (by issue/update date) appears to hold
    the most recent information - Section 6.3's sample prompt asks for
    exactly this: "identify which document appears to hold the most recent
    information based on issue date."
    """
    dates = {
        doc_set["specification"]["document"]: doc_set["specification"]["date"],
        doc_set["drawing"]["document"]: doc_set["drawing"]["date"],
        doc_set["model"]["object"]: doc_set["model"]["date"],
    }
    return max(dates, key=lambda k: dates[k])


def facade_discrepancy_narrative(doc_set: Dict[str, Any]) -> str:
    spec, drawing, model = doc_set["specification"], doc_set["drawing"], doc_set["model"]
    if not _facade_values_differ(doc_set):
        return f"No discrepancy found: {doc_set['parameter']} is consistent across specification, drawing, and model."
    most_recent = most_recent_facade_source(doc_set)
    return (
        f"{doc_set['parameter']} differs across three sources: {spec['value']} {doc_set['unit']} in "
        f"{spec['document']} (Rev {spec['revision']}, {spec['date']}); {drawing['value']} {doc_set['unit']} in "
        f"drawing {drawing['document']} Rev {drawing['revision']} ({drawing['date']}); {model['value']} "
        f"{doc_set['unit']} in the model ({model['object']}, last updated {model['date']}). "
        f"{spec['note']} {drawing['note']} Based on issue date, {most_recent} appears to hold the most "
        "recent information."
    )


def facade_discrepancy_entry(doc_set: Dict[str, Any]) -> Optional[ComplianceLogEntry]:
    if not _facade_values_differ(doc_set):
        return None
    spec, drawing, model = doc_set["specification"], doc_set["drawing"], doc_set["model"]
    return ComplianceLogEntry(
        category="Document consistency",
        finding="Façade performance value differs across spec, drawing, and model",
        source=f"{spec['document']}, {drawing['document']}, {model['source']}",
        severity="High",
        responsible_discipline="Façade consultant / cost lead",
        object_ids=[spec["document"], drawing["document"], model["object"]],
    )


def regulatory_limit_entry(doc_set: Dict[str, Any]) -> Optional[ComplianceLogEntry]:
    """Check each source value against the regulatory backstop recorded in
    the document set. A document mismatch is a coordination problem; a
    value above the limiting U-value is a compliance problem, and it is the
    more serious of the two."""
    limit = doc_set.get("regulatory_limit")
    if not limit:
        return None
    over = [(k, doc_set[k]) for k in ("specification", "drawing", "model")
            if doc_set.get(k, {}).get("value", 0) > limit["value"]]
    if not over:
        return None
    names = ", ".join(v.get("document", v.get("object", k)) for k, v in over)
    value = over[0][1]["value"]
    return ComplianceLogEntry(
        category="Regulatory limit",
        finding=(f"{doc_set['parameter']} of {value} {doc_set['unit']} in {names} exceeds the "
                 f"{limit['value']} {limit['unit']} limiting value ({limit['reference']})."),
        source=names,
        severity="High",
        responsible_discipline="Façade Engineer and Sustainability Consultant",
    )


class AuditAgent(BaseAECOAgent):
    """The Audit Agent behind the BIMGUARD workflow."""

    name = "Audit Agent"
    chapter = 6
    reviewer_role = "BIM Manager"
    data_class = "internal"
    purpose = (
        "Check the federated model, IFC export, drawings, and specifications for gaps and "
        "contradictions against Horizon One Tower's own Information Requirements."
    )
    can_do = [
        "check objects against the BIM Execution Plan",
        "compare specification, drawing, and model values for the same parameter",
        "produce a structured, sourced compliance log",
    ]
    cannot_do = [
        "resolve or redesign a flagged issue",
        "judge design quality",
        "approve a document for issue",
    ]

    # -- 6.1 "From Clash Detection to Semantic Auditing" ---------------------
    def run(
        self,
        request: str = (
            "Review the Horizon One Tower federated model and associated IFC export for "
            "objects missing required parameters under the project's Information Requirements "
            "- specifically fire rating, asset classification, and maintenance access data. "
            "List each instance by object ID, location, and missing parameter."
        ),
    ) -> AgentFinding:
        bep = self.context.project.bim_execution_plan()
        bim_objects = self.context.project.bim_objects()
        scoped_bep = [
            r for r in bep
            if r.parameter in ("fire_rating", "asset_classification", "maintenance_access_clearance_mm")
        ]
        gaps = find_missing_parameters(bim_objects, scoped_bep, categories=["Door", "Mechanical Asset"])

        lines = [f"{len(gaps)} instance(s) missing a required parameter:"]
        for g in gaps:
            lines.append(f"  - {g['object_id']} ({g['location']}): missing {g['parameter'].replace('_', ' ')}")
        narrative = self.context.llm.complete("EVIDENCE:\n" + "\n".join(lines))

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=["bim_objects.json#doors", "bim_objects.json#mechanical_assets"],
            risks=[f"{g['object_id']}: missing {g['parameter'].replace('_', ' ')}" for g in gaps],
            confidence="High",
            recommended_action="Responsible discipline to confirm or correct each flagged parameter before the model is issued for coordination.",
        )
        self._log(task=request, sources=result.sources, tools_used=["find_missing_parameters"])
        return result

    # -- 6.2 "Checking BIM Against Project Information Requirements" ---------
    def run_bep_check(
        self,
        request: str = (
            "Check all door, wall, and mechanical asset objects in the Horizon One Tower model "
            "against the parameters required by the project's BIM Execution Plan. Report any "
            "object with a missing, placeholder, or inconsistent value, and indicate whether the "
            "issue affects design coordination, cost estimation, or facilities handover."
        ),
    ) -> AgentFinding:
        bep = self.context.project.bim_execution_plan()
        bim_objects = self.context.project.bim_objects()
        gaps = find_missing_parameters(bim_objects, bep, categories=["Door", "Wall", "Mechanical Asset"])
        entries = group_findings(gaps)

        lines = [f"{len(entries)} distinct issue group(s) found across door, wall, and mechanical asset objects:"]
        for e in entries:
            impacts = sorted({a for g in gaps if g["object_category"] and (g["object_id"] in e.object_ids) for a in g["affects"]})
            lines.append(f"  - {e.finding} (affects: {', '.join(impacts) or 'unclear'})")
        narrative = self.context.llm.complete("EVIDENCE:\n" + "\n".join(lines))

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=["bim_execution_plan.json", "bim_objects.json"],
            risks=[e.finding for e in entries],
            confidence="High",
            recommended_action="Route each issue group to its responsible discipline before the model is issued for coordination.",
        )
        self._log(task=request, sources=result.sources, tools_used=["find_missing_parameters", "group_findings"])
        return result

    # -- 6.3 "Reviewing Drawings and Specifications Together" ----------------
    def run_document_consistency_check(
        self,
        request: str = (
            "Compare the Horizon One Tower façade specification against the current drawing set "
            "and the corresponding model objects. Flag any discrepancy in material callouts, "
            "performance values, or revision status, and identify which document appears to hold "
            "the most recent information based on issue date."
        ),
    ) -> AgentFinding:
        doc_set = self.context.project.facade_document_set()
        narrative = self.context.llm.complete("EVIDENCE:\n" + facade_discrepancy_narrative(doc_set))
        entry = facade_discrepancy_entry(doc_set)
        breach = regulatory_limit_entry(doc_set)
        if breach:
            action = (
                "Do not align the drawing and model to the newest value yet: it exceeds "
                "the regulatory limiting value. Façade engineer to confirm a compliant value, "
                "then update the specification, drawing and model together."
            )
        elif entry:
            action = (
                "Update the drawing note and model parameter to match the current specification "
                "value before the façade package is issued for cost planning and procurement."
            )
        else:
            action = "No discrepancy found - no action required."

        result = AgentFinding(
            agent=self.name,
            finding=narrative,
            sources=[doc_set["specification"]["document"], doc_set["drawing"]["document"], doc_set["model"]["object"]],
            risks=[e.finding for e in (entry, breach) if e],
            confidence="High" if entry else "Medium",
            recommended_action=action,
        )
        self._log(task=request, sources=result.sources, tools_used=["facade_discrepancy_narrative"])
        return result

    # -- 6.4 "Creating Trusted Design Review Logs" ----------------------------
    def generate_compliance_log(self, include_regulatory: bool = True) -> List[ComplianceLogEntry]:
        """Assemble Section 6.2's BEP gap scan (across every object category)
        and Section 6.3's document consistency check into the book's
        structured compliance log - "not a narrative report."
        """
        bep = self.context.project.bim_execution_plan()
        bim_objects = self.context.project.bim_objects()
        gaps = find_missing_parameters(bim_objects, bep)  # every category
        entries = group_findings(gaps)

        facade_entry = facade_discrepancy_entry(self.context.project.facade_document_set())
        if facade_entry:
            entries.append(facade_entry)
        if include_regulatory:
            # Section 6.4: a value can be the most recent and still be wrong.
            reg_entry = regulatory_limit_entry(self.context.project.facade_document_set())
            if reg_entry:
                entries.append(reg_entry)

        self._log(
            task="Generate BIMGUARD compliance log",
            sources=["bim_execution_plan.json", "bim_objects.json", "facade_document_set.json"],
            tools_used=["find_missing_parameters", "group_findings", "facade_discrepancy_entry"],
            output_summary=f"{len(entries)} compliance log entries",
        )
        return entries
