"""One-line construction of the shared ``AgentContext`` used by every demo."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .agent_base import AgentContext
from .audit import AuditLog
from .knowledge_base import AgentKnowledgeBase
from .project import HorizonOneTowerProject


def default_context(audit_path: Optional[Path | str] = None,
                    knowledge_base: Optional[AgentKnowledgeBase] = None) -> AgentContext:
    return AgentContext(
        project=HorizonOneTowerProject(),
        knowledge_base=knowledge_base or AgentKnowledgeBase(),
        audit_log=AuditLog(audit_path),
    )
