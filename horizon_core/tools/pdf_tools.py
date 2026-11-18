"""PDF parsing tool - Chapter 2's "Preparing a planning document" example.

The book's code is:

    import fitz  # PyMuPDF
    pdf = fitz.open("planning_report_P03.pdf")
    pages = []
    for page_number, page in enumerate(pdf):
        pages.append({
            "page": page_number + 1,
            "text": page.get_text(),
            "source": "planning_report_P03.pdf",
            "revision": "P03",
            "status": "Approved",
        })

This module runs that same idea against the real, generated
``planning_report_P03.pdf`` in ``data/horizon_one_tower/`` (see
``scripts/generate_sample_pdf.py``), and adds a light "tag by topic" step
because Chapter 2 is explicit that raw page text is not enough - the useful
form is text tagged by topic so an agent can retrieve the right clause
rather than a whole 250-page document.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pymupdf as fitz

# A small controlled vocabulary used to tag extracted text by planning topic,
# matching the topics that appear in Horizon One Tower's planning_policy.json
# (Height, Setback, Daylight, Land Use, Parking and Servicing, Public Realm,
# Sustainability, Pre-Application Advice). This is deliberately simple
# keyword tagging - Chapter 2's point is that *some* topic structure beats
# none, not that the tagging needs to be clever.
_TOPIC_KEYWORDS = {
    "Height": ["height", "storeys", "townscape", "skyline", "tall building"],
    "Setback": ["setback", "podium massing", "step back"],
    "Daylight": ["daylight", "sunlight", "vsc", "overshadowing"],
    "Land Use": ["active frontage", "ground floor", "retail street"],
    "Parking and Servicing": ["servicing", "parking", "pedestrian flow"],
    "Public Realm": ["public realm", "open space"],
    "Sustainability": ["net zero", "embodied carbon", "operational carbon"],
    "Pre-Application Advice": ["pre-application", "meeting note"],
}


def parse_pdf(path: Path | str, source: str, revision: str, status: str) -> List[Dict[str, Any]]:
    """Extract per-page text and metadata from a PDF (Chapter 2, "parsing").

    Returns a list of page dicts in the same shape as the book's example,
    plus a best-guess ``topic`` tag per page so downstream ingestion into the
    :class:`~horizon_core.knowledge_base.AgentKnowledgeBase` has something
    more useful to index than an anonymous page of text.
    """
    pdf = fitz.open(str(path))
    pages: List[Dict[str, Any]] = []
    for page_number, page in enumerate(pdf):
        text = page.get_text()
        pages.append(
            {
                "page": page_number + 1,
                "text": text,
                "source": source,
                "revision": revision,
                "status": status,
                "topic": _guess_topic(text),
            }
        )
    pdf.close()
    return pages


def _guess_topic(text: str) -> str:
    lowered = text.lower()
    best_topic, best_hits = "General", 0
    for topic, keywords in _TOPIC_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in lowered)
        if hits > best_hits:
            best_topic, best_hits = topic, hits
    return best_topic
