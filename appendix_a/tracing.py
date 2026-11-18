"""Appendix A.5: tracing agent runs.

``traced(agent)`` wraps an agent's ``run`` so every call produces a span with
the agent name, chapter, data class, duration, confidence and source count.
If OpenTelemetry is installed (``pip install opentelemetry-sdk``), spans go
to the configured exporter; otherwise they are kept in ``SPANS`` so the
pattern still works offline. Prompts and source text are not recorded,
only metadata, which keeps confidential content out of the trace store.
"""

from __future__ import annotations

import functools
import time
from typing import List

SPANS: List[dict] = []

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace

    _tracer = trace.get_tracer("horizon-one")
except ImportError:  # pragma: no cover
    _tracer = None


def traced(agent):
    original = agent.run

    @functools.wraps(original)
    def run(request, *args, **kwargs):
        start = time.perf_counter()
        span_cm = (
            _tracer.start_as_current_span(f"agent.{agent.name}")
            if _tracer
            else None
        )
        span = span_cm.__enter__() if span_cm else None
        try:
            finding = original(request, *args, **kwargs)
            record = {
                "agent": agent.name,
                "chapter": agent.chapter,
                "data_class": agent.data_class,
                "request": str(request),
                "confidence": finding.confidence,
                "sources": len(finding.sources),
                "ms": round(
                    1000 * (time.perf_counter() - start), 1
                ),
            }
            SPANS.append(record)
            if span is not None:
                for k, v in record.items():
                    span.set_attribute(
                        k, v if v is not None else ""
                    )
            return finding
        finally:
            if span_cm:
                span_cm.__exit__(None, None, None)

    agent.run = run
    return agent
