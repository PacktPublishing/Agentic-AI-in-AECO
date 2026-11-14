"""Generate a small, realistic-looking planning report PDF for Horizon One Tower.

This stands in for the kind of consultant PDF a real project would have in its
CDE. It is deliberately short (one "clause" per page) so that Chapter 2's
PyMuPDF parsing example in ``horizon_core.tools.pdf_tools`` and ``ch2`` has a
genuine PDF to open, rather than a mocked string.

Run with:
    python scripts/generate_sample_pdf.py
"""
from __future__ import annotations

import json
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "horizon_one_tower"
OUTPUT_PDF = DATA_DIR / "planning_report_P03.pdf"
POLICY_JSON = DATA_DIR / "planning_policy.json"


def build_pdf() -> None:
    policies = json.loads(POLICY_JSON.read_text())

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cover page. Note: fpdf2 leaves the cursor at the right margin after a
    # full-width multi_cell, so we call ln() before every subsequent multi_cell
    # to bring x back to the left margin - otherwise the next call has zero
    # horizontal space to work with.
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, "Horizon One Tower")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 14)
    pdf.multi_cell(0, 8, "Planning Report - Pre-Application Submission")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        6,
        "Revision: P03\nStatus: Approved for pre-application review\n"
        "Stage: Pre-Application\nDate: 2026-06-12\nPrepared for: Horizon One Tower project team\n"
        "Prepared by: (fictional) planning consultant, for teaching purposes only.",
    )

    # One page per policy clause, in the source style a planning consultant report
    # would actually use, so the extraction pipeline in Chapter 2 has real
    # multi-page structure with section headings and body text to parse.
    for i, policy in enumerate(policies, start=1):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 8, f"Section {i}: {policy['topic']}")
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 6, f"Clause reference: {policy['clause_reference']}")
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, policy["description"])
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 10)
        req_label = (
            "Hard requirement"
            if policy["requirement_type"] == "hard_requirement"
            else "Subject to design justification"
        )
        pdf.multi_cell(0, 6, f"Status: {req_label}")
        if policy.get("value"):
            pdf.ln(1)
            pdf.multi_cell(0, 6, f"Reference value: {policy['value']}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_PDF))
    print(f"Wrote {OUTPUT_PDF} ({OUTPUT_PDF.stat().st_size} bytes)")


if __name__ == "__main__":
    build_pdf()
