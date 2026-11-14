"""The Agent Knowledge Base - Chapter 2's "controlled memory layer that
agents can search, query, cite, and use within approved workflows."

Chapter 2's own code example queries a ``llama_index.core.VectorStoreIndex``.
That is a fine choice for a real deployment, but it defaults to calling an
embeddings API, which would mean this teaching codebase only works if every
reader has an OpenAI (or similar) key configured. Chapter 3 makes the
book's actual position on this explicit: "the specific tools may change...
but the professional principle remains the same" - retrieve from trusted,
current, well-described project information rather than guessing.

So ``AgentKnowledgeBase`` here uses a local TF-IDF index (scikit-learn) as
its default retrieval backend: no API key, no network call, fully
deterministic, and good enough to demonstrate the actual pattern the book
cares about - grounded retrieval with source metadata attached. Swapping in
LlamaIndex + Chroma/pgvector later is a drop-in replacement behind the same
``ingest()`` / ``query()`` interface; see ``LlamaIndexKnowledgeBase`` below
for exactly that swap, kept optional so it's never required to run this repo.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .schemas import DocumentRecord

# The project name ("Horizon One Tower") and a handful of boilerplate words
# appear in almost every document regardless of topic (cover pages, section
# headers, footers). With a small corpus like this one, TF-IDF's inverse
# document frequency does not discount them enough on its own, so ubiquitous
# project vocabulary can outrank the actually distinguishing terms in a
# query. Extending the stop-word list with these terms keeps retrieval
# focused on what makes one page topically different from another - which is
# the whole point of the exercise - without changing the ranking algorithm.
_DOMAIN_STOP_WORDS = ENGLISH_STOP_WORDS.union(
    {"horizon", "tower", "project", "report", "section", "page"}
)


class AgentKnowledgeBase:
    """A controlled, searchable, source-traceable memory layer.

    Every document ingested must already carry the metadata Chapter 2 insists
    on: discipline, revision, status, stage, date, and source. Retrieval
    (``query``) always returns documents alongside that metadata, never bare
    text, so a caller can always answer "can I trust this for this task?"
    before using the result.
    """

    def __init__(self) -> None:
        self._documents: List[DocumentRecord] = []
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._matrix = None

    def ingest(self, documents: List[DocumentRecord]) -> None:
        """Add documents to the knowledge base and rebuild the search index.

        Mirrors the book's "ingestion" step from the data transformation
        pipeline (2, "The data transformation pipeline"): only documents
        that already carry approved project metadata should reach here.
        """
        self._documents.extend(documents)
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        if not self._documents:
            self._vectorizer = None
            self._matrix = None
            return
        texts = [doc.text or doc.topic or doc.file for doc in self._documents]
        self._vectorizer = TfidfVectorizer(stop_words=list(_DOMAIN_STOP_WORDS))
        self._matrix = self._vectorizer.fit_transform(texts)

    def query(
        self,
        text: str,
        top_k: int = 5,
        status_in: Optional[List[str]] = None,
    ) -> List[Tuple[DocumentRecord, float]]:
        """Return the ``top_k`` most relevant documents for ``text``.

        Parameters
        ----------
        status_in:
            Optional allow-list of document statuses (e.g. ``["Approved"]``)
            - the retrieval-time equivalent of Chapter 2's point that an
            agent should know "whether the file is current, draft, approved,
            superseded, or archived" before using it.
        """
        candidates = self._documents
        if status_in is not None:
            candidates = [d for d in candidates if d.status in status_in]
        if not candidates or self._vectorizer is None:
            return []

        candidate_indices = [self._documents.index(d) for d in candidates]
        query_vec = self._vectorizer.transform([text])
        sims = cosine_similarity(query_vec, self._matrix[candidate_indices]).flatten()

        ranked = sorted(
            zip(candidates, sims), key=lambda pair: pair[1], reverse=True
        )
        return [(doc, float(score)) for doc, score in ranked[:top_k] if score > 0]

    def __len__(self) -> int:
        return len(self._documents)


class LlamaIndexKnowledgeBase:
    """Optional drop-in replacement matching Chapter 2's exact code example.

    Not imported by default and not required by any test in this repo - it
    is here so the book's own ``llama_index`` example has a home once a
    reader has an embeddings-capable model configured (OpenAI, a local
    embedding model, etc). It implements the same ``ingest`` / ``query``
    shape as :class:`AgentKnowledgeBase` so it can be swapped in without
    touching any agent code.
    """

    def __init__(self) -> None:
        try:
            from llama_index.core import Document, VectorStoreIndex
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "LlamaIndexKnowledgeBase requires the 'llama-index' package "
                "and a configured embedding model. "
                "Install with: pip install llama-index"
            ) from exc
        self._Document = Document
        self._VectorStoreIndex = VectorStoreIndex
        self._documents: List[DocumentRecord] = []
        self._index = None
        self._query_engine = None

    def ingest(self, documents: List[DocumentRecord]) -> None:  # pragma: no cover
        self._documents.extend(documents)
        llama_docs = [
            self._Document(
                text=item.text,
                metadata={
                    "source": item.source,
                    "revision": item.revision,
                    "status": item.status,
                    "page": item.page,
                },
            )
            for item in self._documents
        ]
        self._index = self._VectorStoreIndex.from_documents(llama_docs)
        self._query_engine = self._index.as_query_engine()

    def query(self, text: str, top_k: int = 5):  # pragma: no cover
        if self._query_engine is None:
            return []
        return self._query_engine.query(text)
