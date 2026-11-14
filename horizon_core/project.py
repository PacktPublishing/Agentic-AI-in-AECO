"""``HorizonOneTowerProject`` - the shared case study every chapter works on.

This is deliberately not a "real" enterprise data platform. It is the small,
structured, traceable dataset the book keeps returning to: a federated BIM
extract, planning policy constraints, GIS layers, a cost plan, a procurement
tracker, a sustainability workbook, an issue log, RFIs, meeting notes, a
drawing register, a decision log, and a massing brief - each with the
metadata (source, revision, status, date) Chapter 2 argues an agent actually
needs.

Every chapter's agents read from this one object. That mirrors the book's
argument directly: agents are only as good as the project memory behind them,
so we build that memory once and reuse it everywhere, rather than
re-inventing ad hoc fixtures per chapter.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .schemas import ConstraintRecord, InformationRequirement

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "horizon_one_tower"


class HorizonOneTowerProject:
    """Loads and caches every data source for the Horizon One Tower case study.

    Parameters
    ----------
    data_dir:
        Directory containing the project's JSON/PDF/IFC files. Defaults to
        the ``data/horizon_one_tower`` folder shipped with this repository.
    """

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self._cache: Dict[str, Any] = {}

    # -- internal helpers ---------------------------------------------------
    def _load_json(self, filename: str) -> Any:
        if filename not in self._cache:
            path = self.data_dir / filename
            if not path.exists():
                raise FileNotFoundError(
                    f"Expected Horizon One Tower data file at {path}. "
                    "Run the scripts in scripts/ to (re)generate the dataset."
                )
            self._cache[filename] = json.loads(path.read_text())
        return self._cache[filename]

    # -- generic loaders for chapter datasets (Chapters 7-15) ---------------
    def chapter_path(self, folder: str, filename: str) -> Path:
        """Path to a file in a chapter dataset folder, e.g.
        ``chapter_path("cost", "rates.csv")``."""
        path = self.data_dir / folder / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Expected {path}. Run scripts/generate_chapter_data.py to rebuild it."
            )
        return path

    def chapter_csv(self, folder: str, filename: str, **kwargs):
        """Load a chapter CSV as a pandas DataFrame (not cached: callers
        often modify the frame to test failure cases)."""
        import pandas as pd

        return pd.read_csv(self.chapter_path(folder, filename), **kwargs)

    def chapter_json(self, folder: str, filename: str) -> Any:
        return self._load_json(f"{folder}/{filename}")

    def identifiers(self) -> Dict[str, Any]:
        """Identifiers shared across chapters (packages, activities, zones,
        assets, change requests), so every agent refers to the same objects."""
        return self._load_json("identifiers.json")

    # -- project-wide facts ---------------------------------------------------
    def overview(self) -> Dict[str, Any]:
        """High-level project facts: storeys, GIA targets, client priorities."""
        return self._load_json("project_overview.json")

    # -- feasibility inputs (Chapter 4) ---------------------------------------
    def planning_constraints(self) -> List[ConstraintRecord]:
        """Planning/zoning constraints, as if extracted by a Zoning Compliance
        Agent from ``planning_report_P03.pdf`` (see ``ch2.data_pipeline`` and
        ``ch4.agents.ZoningComplianceAgent`` for the extraction pipeline)."""
        raw = self._load_json("planning_policy.json")
        return [ConstraintRecord(**item) for item in raw]

    def gis_constraints(self) -> Dict[str, Any]:
        """Simplified, queryable GIS layers: site boundary, flood risk,
        transport, neighbouring buildings, utilities, protected views."""
        return self._load_json("gis_constraints.json")

    def environmental_guidance(self) -> Dict[str, Any]:
        """Daylight/overshadowing, contamination, noise, and wind guidance."""
        return self._load_json("environmental_guidance.json")

    def market_comparables(self) -> List[Dict[str, Any]]:
        """Comparable scheme data for the Market Intelligence Agent."""
        return self._load_json("market_comparables.json")

    # -- design coordination inputs (Chapter 1) -------------------------------
    def issue_log(self) -> List[Dict[str, Any]]:
        return self._load_json("issue_log.json")

    def rfis(self) -> List[Dict[str, Any]]:
        return self._load_json("rfis.json")

    def meeting_notes(self) -> List[Dict[str, Any]]:
        return self._load_json("meeting_notes.json")

    def drawing_register(self) -> List[Dict[str, Any]]:
        return self._load_json("drawing_register.json")

    # -- design-change review inputs (Chapter 3) ------------------------------
    def cost_plan(self) -> Dict[str, Any]:
        return self._load_json("cost_plan.json")

    def procurement_tracker(self) -> Dict[str, Any]:
        return self._load_json("procurement_tracker.json")

    def sustainability_workbook(self) -> Dict[str, Any]:
        return self._load_json("sustainability_workbook.json")

    def decision_log(self) -> List[Dict[str, Any]]:
        return self._load_json("decision_log.json")

    def design_change_requests(self) -> List[Dict[str, Any]]:
        """The concrete design-change scenarios the Chapter 3 orchestrator
        reviews (e.g. the podium facade material substitution)."""
        return self._load_json("design_change_requests.json")

    def design_change_request(self, request_id: str) -> Dict[str, Any]:
        matches = [r for r in self.design_change_requests() if r["request_id"] == request_id]
        if not matches:
            raise KeyError(f"No design change request with id {request_id!r}")
        return matches[0]

    # -- generative design inputs (Chapter 5) ---------------------------------
    def massing_brief(self) -> Dict[str, Any]:
        return self._load_json("massing_brief.json")

    # -- raw source files (Chapter 2 parsing demos) ---------------------------
    def planning_report_pdf_path(self) -> Path:
        path = self.data_dir / "planning_report_P03.pdf"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run scripts/generate_sample_pdf.py first."
            )
        return path

    def architecture_ifc_path(self) -> Path:
        path = self.data_dir / "HorizonOne_Architecture.ifc"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run scripts/generate_sample_ifc.py first."
            )
        return path

    def ifc_spaces_fallback_extract(self) -> List[Dict[str, Any]]:
        """A pre-computed IFC space extract, used as a fallback if
        ``ifcopenshell`` is not installed (see ``horizon_core.tools.ifc_tools``)."""
        return self._load_json("ifc_spaces_extract.json")

    # -- semantic auditing inputs (Chapter 6) ---------------------------------
    def bim_execution_plan(self) -> List[InformationRequirement]:
        """The information requirements the Chapter 6 Audit Agent checks
        every model object against - not a generic checklist, but what
        Horizon One Tower's own BEP actually committed to delivering."""
        raw = self._load_json("bim_execution_plan.json")
        return [InformationRequirement(**item) for item in raw["requirements"]]

    def bim_objects(self) -> Dict[str, Any]:
        """Doors, walls, mechanical assets, and rooms from the federated
        model / IFC export, with the parameter data (and gaps) the Audit
        Agent checks against the BIM Execution Plan."""
        return self._load_json("bim_objects.json")

    def facade_document_set(self) -> Dict[str, Any]:
        """The specification / drawing / model three-way comparison used in
        Chapter 6's "Reviewing Drawings and Specifications Together"."""
        return self._load_json("facade_document_set.json")
