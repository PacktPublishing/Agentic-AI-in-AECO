"""Chapter 2: "The data transformation pipeline" and "Building an Agent
Knowledge Base for Horizon One Tower", implemented end to end.

The pipeline mirrors the book's stages:

1. Ingestion - pull raw files from the project's systems (here: the PDF and
   IFC files in ``data/horizon_one_tower/``, plus the structured logs that
   already function as "already tabular" sources).
2. Parsing - extract text/records with the right tool for each format
   (``horizon_core.tools.pdf_tools`` / ``ifc_tools``).
3. Chunking and tagging - break documents into retrievable, topic-tagged
   pieces (done inside ``pdf_tools.parse_pdf``; each PDF page is already a
   natural chunk here).
4. Embedding/indexing - hand everything to the
   :class:`~horizon_core.knowledge_base.AgentKnowledgeBase`.

Chapter 2 also gives a worked query: *"What constraints could affect
Horizon One Tower's height?"*. :func:`demo_query` reproduces exactly that.
"""
from __future__ import annotations

from typing import List, Tuple

from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.project import HorizonOneTowerProject
from horizon_core.schemas import DocumentRecord
from horizon_core.tools import ifc_tools, pdf_tools

PLANNING_REPORT_DATE = "2026-06-12"


def ingest_planning_report(project: HorizonOneTowerProject) -> List[DocumentRecord]:
    """Parse ``planning_report_P03.pdf`` into per-page ``DocumentRecord``s,
    the shape Chapter 2's "adding context to a document" example describes."""
    pages = pdf_tools.parse_pdf(
        project.planning_report_pdf_path(),
        source="Project CDE",
        revision="P03",
        status="Approved",
    )
    return [
        DocumentRecord(
            project="Horizon One Tower",
            file="planning_report_P03.pdf",
            discipline="Planning",
            revision=page["revision"],
            status=page["status"],  # type: ignore[arg-type]
            stage="Pre-Application",
            date=PLANNING_REPORT_DATE,
            source=page["source"],
            text=page["text"],
            page=page["page"],
            topic=page["topic"],
            owner="Planning Consultant",
            document_id=f"HOT-PLN-RPT-P03-p{page['page']}",
        )
        for page in pages
    ]


def ingest_architecture_model(project: HorizonOneTowerProject) -> List[DocumentRecord]:
    """Extract IFC spaces and represent each as a small, queryable
    ``DocumentRecord`` - Chapter 2's "Extracting Horizon One Tower spaces
    from IFC" example, wired into the same knowledge base as the PDF."""
    spaces = ifc_tools.extract_spaces(
        project.architecture_ifc_path(), project.ifc_spaces_fallback_extract()
    )
    records = []
    for space in spaces:
        text = f"Space {space['name']} ({space['type']}) on {space['storey']}."
        records.append(
            DocumentRecord(
                project="Horizon One Tower",
                file="HorizonOne_Architecture.ifc",
                discipline="Architecture",
                revision="Live model export",
                status="For Coordination",
                stage="Design Development",
                date=PLANNING_REPORT_DATE,
                source="Federated BIM model",
                text=text,
                topic=space["type"],
                owner="Lead Architect",
            )
        )
    return records


def build_knowledge_base(project: HorizonOneTowerProject) -> AgentKnowledgeBase:
    """Run the full pipeline (ingest -> parse -> tag -> index) and return a
    ready-to-query :class:`AgentKnowledgeBase` for Horizon One Tower."""
    kb = AgentKnowledgeBase()
    kb.ingest(ingest_planning_report(project))
    kb.ingest(ingest_architecture_model(project))
    return kb


def demo_query(
    kb: AgentKnowledgeBase,
    question: str = "What constraints could affect Horizon One Tower's height?",
    top_k: int = 3,
) -> List[Tuple[DocumentRecord, float]]:
    """Chapter 2's worked retrieval example, reproduced against the real
    knowledge base built by :func:`build_knowledge_base`."""
    return kb.query(question, top_k=top_k)
