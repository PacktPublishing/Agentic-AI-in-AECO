"""The "model core" from Chapter 1's anatomy of an AECO agent.

Chapter 1 is explicit that the model core "may be a cloud model, an
enterprise model, or a local model depending on the project's security
requirements. The model is powerful, but it does not automatically know your
project." In this codebase, agents never depend directly on any particular
provider. They depend on the small ``LLMClient`` protocol below, so the
underlying model can be swapped without touching agent code.

Two implementations are provided:

``MockLLM``
    Deterministic, offline, and free. It does not call any API - it turns a
    structured prompt (goal + retrieved evidence) into readable prose using
    simple templating. This is what every test in this repo runs against, so
    the whole codebase works out of the box with no API key.

``AnthropicLLM``
    A thin wrapper around the real Claude API, used automatically if
    ``ANTHROPIC_API_KEY`` is set in the environment. Swap it in for a more
    fluent narrative layer once you are ready to move past the teaching
    default - the agent code itself does not change.

This mirrors the book's own point directly: "the specific tools may change
... but the professional principle remains the same."
"""
from __future__ import annotations

import os
import textwrap
from typing import Protocol


class LLMClient(Protocol):
    """Minimal interface every agent's model core depends on."""

    def complete(self, prompt: str) -> str:
        ...


class MockLLM:
    """A deterministic stand-in for a real language model.

    It does not "reason" in any deep sense - it reformats whatever structured
    evidence the agent already assembled (from the Agent Knowledge Base and
    deterministic tools) into a short, readable paragraph. This keeps the
    codebase testable and free to run, while keeping faith with the book's
    own repeated warning: agents should retrieve and ground their answers in
    structured evidence rather than have the model "guess."
    """

    def complete(self, prompt: str) -> str:
        # A very small amount of "narrative" formatting: wrap long lines,
        # strip the instruction scaffolding the caller used to build the
        # prompt, and return the evidence block as the "finding" text.
        # Wrapping is done per input line rather than across the whole
        # block, so an agent's bulleted evidence (one issue per line) stays
        # bulleted instead of being collapsed into a single run-on
        # paragraph - the point of MockLLM is to reformat minimally, not to
        # restructure what the caller already organised.
        body = prompt.strip()
        if "EVIDENCE:" in body:
            body = body.split("EVIDENCE:", 1)[1].strip()
        wrapped_lines = [
            textwrap.fill(line, width=100, subsequent_indent="    ") if line.strip() else line
            for line in body.splitlines()
        ]
        return "\n".join(wrapped_lines)


class AnthropicLLM:
    """Optional real model core, used only if an API key is configured.

    Kept intentionally thin: agents call ``.complete(prompt)`` and never know
    which backend answered. Import of the ``anthropic`` package is deferred
    to ``__init__`` so that installing this package is only required for
    people who actually want to use it.
    """

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:  # pragma: no cover - exercised only if used
            raise ImportError(
                "AnthropicLLM requires the 'anthropic' package. "
                "Install it with: pip install anthropic"
            ) from exc
        self._client = anthropic.Anthropic()
        self._model = model

    def complete(self, prompt: str) -> str:  # pragma: no cover - network call
        response = self._client.messages.create(
            model=self._model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )


class OllamaLLM:
    """Optional local model core (Chapter 14's local route).

    Calls an Ollama server on this machine, so prompts never leave
    it. Standard library only; start Ollama and pull a model first.
    """

    def __init__(self, model: str = "llama3.1",
                 host: str = "http://localhost:11434") -> None:
        self._model, self._host = model, host.rstrip("/")

    def complete(self, prompt: str) -> str:  # pragma: no cover
        import json
        import urllib.request

        payload = {"model": self._model, "prompt": prompt,
                   "stream": False}
        body = json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{self._host}/api/generate", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=120) as r:
            return json.loads(r.read())["response"]


def get_default_llm() -> LLMClient:
    """Return ``AnthropicLLM`` if ``ANTHROPIC_API_KEY`` is set, else ``MockLLM``.

    This is the single place agent code should call to pick up a model core,
    so switching every agent in the book from the teaching default to a real
    model is a one-line change here rather than an edit per agent.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicLLM()
        except ImportError:
            pass
    return MockLLM()
