"""``BaseAECOAgent`` - a runnable implementation of Chapter 1.7's "anatomy of
an AECO agent."

Chapter 1 lists ten connected parts: goal, guardrails, model core, memory,
retrieval, knowledge base, tool-use layer, platform connection, audit trail,
human approval gate, and output channel. Every specialist agent in this
codebase (Chapters 1, 3, 4, and 5) is a subclass of ``BaseAECOAgent`` so that
those ten parts are implemented once, consistently, rather than reinvented
per agent.

Chapter 1's reusable "AECO Agent Design Template" (1.8) maps directly onto
the class attributes below: ``name``/``purpose`` (Agent Identity, Purpose),
``can_do``/``cannot_do`` (Agent Capabilities), and the constructor's
``context`` (Inputs, Tools). Subclasses implement ``run()`` (Workflow Logic)
and return an ``AgentFinding`` (Output Definition).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from .audit import AuditLog
from .knowledge_base import AgentKnowledgeBase
from .llm import LLMClient, get_default_llm
from .project import HorizonOneTowerProject
from .schemas import AgentFinding


@dataclass
class AgentContext:
    """Everything a Horizon One Tower agent needs to do its work.

    Bundling these together means every agent gets the same project data,
    the same knowledge base, the same model core, and the same audit log -
    which is exactly what lets the Chapter 3 orchestrator compare their
    outputs on equal footing.
    """

    project: HorizonOneTowerProject
    knowledge_base: AgentKnowledgeBase
    audit_log: AuditLog
    llm: LLMClient = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.llm is None:
            self.llm = get_default_llm()


#: Every concrete agent class in the repository, keyed by its ``name``.
#: Populated automatically by ``BaseAECOAgent.__init_subclass__``. Chapter 15
#: reads this register to build the project's agent portfolio, so an agent
#: added in any chapter appears there without extra wiring.
AGENT_REGISTRY: Dict[str, Type["BaseAECOAgent"]] = {}


class BaseAECOAgent(ABC):
    """Base class for every specialist agent in this book's codebase.

    Subclasses must set:

    - ``name``: the agent's identity, e.g. ``"Cost Agent"``.
    - ``purpose``: one or two sentences, matching template section 2.
    - ``can_do`` / ``cannot_do``: the guardrails from template section 4 and
      Chapter 1.7's second anatomy part. ``cannot_do`` is not decoration -
      :meth:`assert_within_guardrails` actively checks it.

    and implement :meth:`run`.
    """

    name: str = "Unnamed Agent"
    purpose: str = ""
    can_do: List[str] = []
    cannot_do: List[str] = []
    # Portfolio metadata (Chapters 14 and 15). Optional for older agents.
    chapter: Optional[int] = None
    reviewer_role: Optional[str] = None
    data_class: str = "internal"

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # ABCMeta computes __abstractmethods__ after this hook runs, so check
        # the run() method directly.
        if not getattr(cls.run, "__isabstractmethod__", False) and cls.name != "Unnamed Agent":
            AGENT_REGISTRY[cls.name] = cls

    def __init__(self, context: AgentContext) -> None:
        self.context = context

    # -- guardrails -----------------------------------------------------
    def assert_within_guardrails(self, requested_action: str) -> None:
        """Raise if ``requested_action`` matches something this agent must
        not do. This is Chapter 1's point made enforceable: "Guardrails are
        not there to make the system timid. They make it usable."
        """
        lowered = requested_action.lower()
        for forbidden in self.cannot_do:
            if forbidden.lower() in lowered:
                raise PermissionError(
                    f"{self.name} cannot do this: '{forbidden}' is outside its guardrails."
                )

    # -- audit ------------------------------------------------------------
    def _log(
        self,
        task: str,
        sources: List[str],
        tools_used: Optional[List[str]] = None,
        output_summary: Optional[str] = None,
    ) -> None:
        self.context.audit_log.record(
            agent=self.name,
            task=task,
            sources=sources,
            tools_used=tools_used,
            output_summary=output_summary,
        )

    # -- workflow -----------------------------------------------------------
    @abstractmethod
    def run(self, request: str, **kwargs) -> AgentFinding:
        """Execute the agent's narrow task and return a structured finding.

        Subclasses should: retrieve relevant context (memory/retrieval),
        use deterministic tools to compute grounded facts (tool-use layer),
        optionally call ``self.context.llm.complete(...)`` for narrative
        text (model core), and finish by calling ``self._log(...)`` (audit
        trail) before returning an ``AgentFinding`` (output channel).
        """
        raise NotImplementedError
