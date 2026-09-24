"""Shared graph state for the Salesforce Case Agent Team.

AgentState is the single object threaded through every node in graph.py.
Each node reads what it needs and returns a partial update; LangGraph
merges updates back into the running state between turns.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    """One ranked explanation for the reported symptom, from Technical Diagnostics."""

    rank: int
    summary: str
    evidence_needed: str
    confirmed: Optional[bool] = None  # None = untested, True/False once a human checks


class PrecedentHit(BaseModel):
    """A matching row surfaced from case-kb/index.md at intake."""

    case_number: str
    symptom: str
    root_cause_category: str
    file: str


class KBScaffold(BaseModel):
    """The running Knowledge Base record for the case in progress.

    Fields are '[PENDING]' until a human-confirmed fact fills them in.
    Never fabricated — see Knowledge Base Builder constraints in
    prompt_library/kb_builder.py.
    """

    issue_reported: str = "[PENDING]"
    root_cause: str = "[PENDING]"
    action_taken: str = "[PENDING]"
    resolution_category: str = "[PENDING]"
    status: Literal["Open", "Pending Info", "Resolved", "Closed"] = "Open"


class AgentState(BaseModel):
    """The full state of one Salesforce case as it moves through the graph."""

    messages: list[dict] = Field(default_factory=list)  # chat history, Anthropic message format

    case_number: str
    symptom: str

    hypotheses: list[Hypothesis] = Field(default_factory=list)
    precedent_hits: list[PrecedentHit] = Field(default_factory=list)
    kb_scaffold: KBScaffold = Field(default_factory=KBScaffold)

    pending_question: Optional[str] = None  # the one open question blocking the next turn
    status: Literal["intake", "diagnosing", "awaiting_human", "closing", "closed"] = "intake"
