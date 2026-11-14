"""The Chapter 2 listings, in the order they appear in the chapter.

    python -m ch2.listings

Each listing is kept close to the printed version so readers can follow the
text line by line. The only additions are the file paths (taken from
``HorizonOneTowerProject`` so the script runs from the repository root) and
a TF-IDF fallback for Listing 2.4 when LlamaIndex or an embedding model is
not configured. The full pipeline lives in ``ch2/data_pipeline.py``.
"""
from __future__ import annotations

from horizon_core.project import HorizonOneTowerProject

project = HorizonOneTowerProject()

# Listing 2.1 - adding context to a Horizon One Tower document
document = {
    "project": "Horizon One Tower",
    "file": "planning_report_P03.pdf",
    "discipline": "Planning",
    "revision": "P03",
    "status": "Approved",
    "stage": "Pre-Application",
    "date": "2026-06-12",
    "source": "Project CDE",
}
print(document)

# Listing 2.2 - extracting each page of the planning report with PyMuPDF
import fitz  # noqa: E402

pdf = fitz.open(project.planning_report_pdf_path())
pages = []
for page_number, page in enumerate(pdf):
    pages.append({
        "page": page_number + 1,
        "text": page.get_text(),
        "source": "planning_report_P03.pdf",
        "revision": "P03",
        "status": "Approved",
    })
print(pages[0]["page"], pages[0]["text"][:80].replace("\n", " "))

# Listing 2.3 - extracting Horizon One Tower spaces from IFC
try:
    import ifcopenshell

    model = ifcopenshell.open(str(project.architecture_ifc_path()))
    spaces = model.by_type("IfcSpace")
    space_data = []
    for space in spaces:
        space_data.append({
            "ifc_id": space.GlobalId,
            "name": space.Name,
            "type": space.ObjectType,
        })
except ImportError:
    space_data = project.ifc_spaces_fallback_extract()
print(space_data[:5])

# Listing 2.4 - indexing the pages and querying the Agent Knowledge Base
QUESTION = "What constraints could affect Horizon One Tower's height?"
try:
    from llama_index.core import Document, VectorStoreIndex

    documents = [
        Document(
            text=item["text"],
            metadata={
                "source": item["source"],
                "revision": item["revision"],
                "status": item["status"],
                "page": item["page"],
            },
        )
        for item in pages
    ]
    index = VectorStoreIndex.from_documents(documents)
    query_engine = index.as_query_engine()
    print(query_engine.query(QUESTION))
except Exception as exc:  # no llama-index, or no embedding model configured
    from ch2.data_pipeline import build_knowledge_base

    print(f"LlamaIndex unavailable ({type(exc).__name__}); using the offline TF-IDF knowledge base.")
    kb = build_knowledge_base(project)
    for record, score in kb.query(QUESTION, top_k=3):
        print(f"{score:.2f}  {record.citation()}  {record.topic}")
