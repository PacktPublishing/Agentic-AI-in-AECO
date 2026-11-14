"""The audit trail - the ninth part of the "anatomy of an AECO agent" (1.7).

Chapter 1: "An audit trail records the task, sources, tools, output,
reviewer, decision, and date... Without that record, the workflow becomes
difficult to trust." Chapter 3 repeats the same requirement for the
multi-agent case, listing exactly the fields a practical approval gate
should record.

Every agent in this codebase writes through this one class, so every
chapter's audit trail has the same shape and (optionally) lands in the same
JSONL file for later inspection.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    agent: str
    task: str
    sources: List[str]
    tools_used: List[str] = field(default_factory=list)
    reviewer: Optional[str] = None
    decision_status: Optional[str] = None
    output_summary: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "task": self.task,
            "sources": self.sources,
            "tools_used": self.tools_used,
            "reviewer": self.reviewer,
            "decision_status": self.decision_status,
            "output_summary": self.output_summary,
            "timestamp": self.timestamp,
        }


class AuditLog:
    """Records what an agent did, so the workflow stays reviewable.

    If ``path`` is given, every entry is also appended to that file as JSON
    Lines, giving a persistent, human-inspectable audit trail across runs -
    exactly the kind of record Chapter 3's approval gate calls for.
    """

    def __init__(self, path: Optional[Path | str] = None) -> None:
        self.path = Path(path) if path else None
        self.entries: List[AuditEntry] = []

    def record(
        self,
        *,
        agent: str,
        task: str,
        sources: List[str],
        tools_used: Optional[List[str]] = None,
        reviewer: Optional[str] = None,
        decision_status: Optional[str] = None,
        output_summary: Optional[str] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            agent=agent,
            task=task,
            sources=sources,
            tools_used=tools_used or [],
            reviewer=reviewer,
            decision_status=decision_status,
            output_summary=output_summary,
        )
        self.entries.append(entry)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(entry.as_dict()) + "\n")
        return entry

    def entries_for(self, agent: str) -> List[AuditEntry]:
        return [e for e in self.entries if e.agent == agent]
