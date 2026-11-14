from __future__ import annotations

import pytest

from horizon_core.agent_base import AgentContext
from horizon_core.audit import AuditLog
from horizon_core.knowledge_base import AgentKnowledgeBase
from horizon_core.llm import MockLLM
from horizon_core.project import HorizonOneTowerProject


@pytest.fixture
def project() -> HorizonOneTowerProject:
    return HorizonOneTowerProject()


@pytest.fixture
def context(project: HorizonOneTowerProject) -> AgentContext:
    return AgentContext(
        project=project,
        knowledge_base=AgentKnowledgeBase(),
        audit_log=AuditLog(),
        llm=MockLLM(),
    )
