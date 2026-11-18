"""Shared data models for the Horizon One Tower agentic AI codebase.

These are the structured records referenced throughout the book:

- ``DocumentRecord`` is the "adding context to a document" example from
  Chapter 2 (project/file/discipline/revision/status/stage/date/source).
- ``ConstraintRecord`` is what a Zoning Compliance Agent (Chapter 4) extracts
  from planning policy: a constraint tied to a clause reference, flagged as a
  hard requirement or subject to design justification.
- ``AgentFinding`` is the standardised specialist-agent output from Chapter 3
  ("Standardising Specialist Agent Outputs") - every micro-agent in Chapter 3
  and Chapter 4 returns one of these so the orchestrator can compare them.
- ``FeasibilityRiskItem`` is one row of the Chapter 4 feasibility risk table.
- ``MassingOption`` is one row of the Chapter 5 massing options table (A-E).

Keeping these in one place means every chapter's agents speak the same
structured language, which is exactly the point the book makes: a well
written paragraph is easy to read, but structured information is easier to
compare, trace, and review.
"""
from __future__ import annotations

from datetime import date  # noqa: F401 - used in DocumentRecord.date; needed
# at runtime for Pydantic to resolve the annotation because this file uses
# `from __future__ import annotations` (postponed evaluation), which is why
# static linters may flag this import as unused even though removing it
# breaks DocumentRecord at class-definition time.
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Confidence = Literal["Low", "Medium", "High"]
DocumentStatus = Literal["Draft", "Approved", "Superseded", "Archived", "For Coordination"]
RequirementType = Literal["hard_requirement", "subject_to_justification"]
# Chapter 14's information classes. Defined here so any agent can declare
# the class of data it handles, and the governance gate can route on it.
DataClass = Literal["public", "internal", "confidential", "restricted"]


class DocumentRecord(BaseModel):
    """A single piece of project information with the metadata an agent needs
    before it can decide whether the content is safe to use (Chapter 2)."""

    project: str
    file: str
    discipline: str
    revision: str
    status: DocumentStatus
    stage: str
    date: date
    source: str
    text: str = ""
    page: Optional[int] = None
    topic: Optional[str] = None
    owner: Optional[str] = None
    document_id: Optional[str] = None

    def citation(self) -> str:
        """A short human-readable source reference, e.g. for an audit log."""
        page_part = f", p.{self.page}" if self.page is not None else ""
        return f"{self.file} (Rev {self.revision}, {self.status}{page_part})"


class ConstraintRecord(BaseModel):
    """A single planning/zoning constraint extracted from a planning
    document, in the shape the Chapter 4 Zoning Compliance Agent produces."""

    topic: str
    description: str
    clause_reference: str
    source_document: str
    requirement_type: RequirementType
    value: Optional[str] = None

    @property
    def is_hard_requirement(self) -> bool:
        return self.requirement_type == "hard_requirement"


class AgentFinding(BaseModel):
    """The standard specialist-agent output shape from Chapter 3.

    Every micro-agent (Cost, Sustainability, BIM Audit, Procurement, Planning
    Risk, Operations, Zoning Compliance, GIS, Environmental Risk, Market
    Intelligence, ...) returns one of these so the orchestrator can compare
    findings without having to parse free text.
    """

    agent: str
    finding: str
    sources: List[str]
    assumptions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    confidence: Confidence
    recommended_action: str
    # Optional fields added for Chapters 7-15. They default to values that
    # keep every earlier chapter's findings valid without changes.
    chapter: Optional[int] = None
    data_class: Optional[DataClass] = None
    evidence_tier: Optional[int] = None
    requires_human_approval: bool = True


class FeasibilityRiskItem(BaseModel):
    """One row of the Chapter 4 feasibility risk report table."""

    risk_area: str
    finding: str
    evidence_source: str
    confidence: Confidence
    human_reviewer: str


PlotEfficiency = Literal["Low", "Medium-low", "Medium", "Medium-high", "High"]
# Daylight impact, planning compliance, and embodied carbon direction are
# kept as free text rather than a tight Literal: Chapter 5's table pairs each
# category with a short parenthetical reason (e.g. "Marginal (close to
# threshold)", "Breach (height/daylight)", "Favourable (regular grid)"), and
# that reason is exactly the evidence a reviewer needs - collapsing it to a
# bare enum would throw away the part of the finding that makes it useful.


class MassingOption(BaseModel):
    """One row of the Chapter 5 massing options table (Options A-E)."""

    option_id: str
    label: str
    tower_footprint_m2: float
    podium_footprint_m2: float
    setback_strategy: str
    podium_setback_m: float
    storeys: int
    core_count: int
    requires_transfer_structure: bool
    floorplate_regularity: str
    gross_internal_area_m2: float

    plot_efficiency: Optional[PlotEfficiency] = None
    daylight_impact: Optional[str] = None
    planning_compliance: Optional[str] = None
    embodied_carbon_direction: Optional[str] = None
    structural_practicality: Optional[str] = None
    breaches: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    """The outcome of a Human Review Authority gate (Chapter 1 / Chapter 3)."""

    reviewer_role: str
    status: Literal["Approved", "Rejected", "Awaiting Review"]
    comments: Optional[str] = None


class InformationRequirement(BaseModel):
    """One row of the Chapter 6 BIM Execution Plan: what a given object
    category is required to carry, and which downstream process depends on
    it - "design coordination, cost estimation, or facilities handover",
    per the book's own sample prompt."""

    object_category: str
    parameter: str
    required: bool
    affects: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    applies_to: Optional[str] = None


class ComplianceLogEntry(BaseModel):
    """One row of Chapter 6's BIMGUARD compliance log - "structured as a
    compliance log, not a narrative report", with a category, finding,
    source, severity, and named responsible discipline."""

    category: str
    finding: str
    source: str
    severity: Literal["Low", "Medium", "High"]
    responsible_discipline: str
    object_ids: List[str] = Field(default_factory=list)
