"""Claude API client — the single swap-point for the LLM behind every role.

Every node in graph.py calls call_claude() instead of touching the Anthropic
SDK directly, so the model, key source, or provider can change in one place.

No API key is committed to this repo. Set ANTHROPIC_API_KEY in your
environment (e.g. a local .env loaded by your shell, or your OS's secret
manager) before running main.py. This module is authored but not executed
as part of this scaffold — see README.md.
"""

from __future__ import annotations

import os
from typing import Optional

import anthropic

# SWAP-POINT: change the model id here to move the whole team to a different
# Claude model. All four roles currently share one model; nothing prevents
# giving each role its own model or temperature if a use case calls for it.
DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_MAX_TOKENS = 2048


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it in your shell before "
            "running main.py — see README.md's 'Running it yourself' section."
        )
    return anthropic.Anthropic(api_key=api_key)


def call_claude(
    system_prompt: str,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: Optional[float] = None,
) -> str:
    """Send one turn to Claude and return the assistant's text reply.

    system_prompt: the role's system prompt from prompt_library/.
    messages: Anthropic-format message list ([{"role": "user"|"assistant", "content": str}, ...]).
    """
    client = _client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
        **({"temperature": temperature} if temperature is not None else {}),
    )
    return "".join(block.text for block in response.content if block.type == "text")
