"""LangGraph StateGraph for the Salesforce Case Agent Team.

Team Lead (supervisor) routes each turn to whichever specialist(s) have new
work, then composes the single reply the human sees. The only tools in the
whole graph are the KB file operations in toolkit/kb_library.py — there is
no tool anywhere that reaches Salesforce, email, or a ticketing system.

This module defines the graph structure only. It is authored to be
structurally valid and is not executed as part of this scaffold — see
README.md's "Running it yourself" section to wire it up with a real
ANTHROPIC_API_KEY.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from llm import call_claude
from prompt_library import (
    TEAM_LEAD_PROMPT,
    TECHNICAL_DIAGNOSTICS_PROMPT,
    HELP_DESK_PROMPT,
    KB_BUILDER_PROMPT,
)
from state import AgentState, Hypothesis, KBScaffold, PrecedentHit
from toolkit import kb_library


# ---------------------------------------------------------------------------
# Team Lead — intake
# ---------------------------------------------------------------------------

def team_lead_intake(state: AgentState) -> dict:
    """First stop for a new turn. On a brand-new case, kick off the
    precedent check (rule 6: check precedent before diagnosing) before any
    specialist starts work. On a follow-up turn, just pass through — the
    router decides who has new work.
    """
    if state.status != "intake":
        return {}

    hits = kb_library.search_precedent(symptom=state.symptom)
    precedent_hits = [
        PrecedentHit(
            case_number=h.case_number,
            symptom=h.symptom,
            root_cause_category=h.root_cause_category,
            file=h.file,
        )
        for h in hits
    ]
    return {"precedent_hits": precedent_hits, "status": "diagnosing"}


# ---------------------------------------------------------------------------
# Routing — which specialist(s) have new work this turn
# ---------------------------------------------------------------------------

def route_to_specialists(state: AgentState) -> list[str]:
    """Fan out to every specialist with something to contribute this turn.

    Team Lead rule 3 (keep the three lenses separate) is enforced by giving
    each specialist its own node and its own section of the composed
    output — never merging their work inside a single call.
    """
    if state.status == "closing":
        return ["kb_builder"]

    active = ["technical_diagnostics", "kb_builder"]

    # Help Desk only joins once there's something worth drafting: an
    # acknowledgment (first turn), a diagnostic update, or a resolution.
    # See the gating rule in prompt_library/help_desk.py.
    if state.status in ("diagnosing", "closing") :
        active.append("help_desk")

    return active


# ---------------------------------------------------------------------------
# 🔧 Technical Diagnostics
# ---------------------------------------------------------------------------

def technical_diagnostics_node(state: AgentState) -> dict:
    """Ranked hypotheses + the cheapest read-only diagnostic to run next.
    Recommends only — never proposes executing a production change.
    """
    context = _build_context(state, extra_note=_precedent_note(state))
    reply = call_claude(TECHNICAL_DIAGNOSTICS_PROMPT, context)

    # In a real run, this is where the specialist's structured hypothesis
    # list (parsed from `reply`) would update state.hypotheses. Left as a
    # pass-through placeholder here since the graph is not executed.
    return {"messages": state.messages + [{"role": "assistant", "content": reply}]}


# ---------------------------------------------------------------------------
# 🎧 Help Desk Communication
# ---------------------------------------------------------------------------

def help_desk_node(state: AgentState) -> dict:
    """A draft for the human to send — never marked as sent."""
    context = _build_context(state, extra_note=_precedent_note(state))
    reply = call_claude(HELP_DESK_PROMPT, context)
    return {"messages": state.messages + [{"role": "assistant", "content": reply}]}


# ---------------------------------------------------------------------------
# 📚 Knowledge Base Builder
# ---------------------------------------------------------------------------

def kb_builder_node(state: AgentState) -> dict:
    """Maintains the running scaffold every turn; writes + indexes at close."""
    context = _build_context(state, extra_note=_precedent_note(state))
    reply = call_claude(KB_BUILDER_PROMPT, context)

    update: dict = {"messages": state.messages + [{"role": "assistant", "content": reply}]}

    if state.status == "closing":
        # In a real run, the finalized scaffold fields (parsed from `reply`
        # or supplied by the human confirming the fix) are written here.
        # Left as a documented call shape since the graph is not executed.
        record = kb_library.CaseRecord(
            case_number=state.case_number,
            slug=state.symptom,
            issue_reported=state.kb_scaffold.issue_reported,
            root_cause=state.kb_scaffold.root_cause,
            action_taken=state.kb_scaffold.action_taken,
            resolution_category=state.kb_scaffold.resolution_category,
            status="Closed",
            date_closed="<set at close time>",
        )
        # kb_library.write_case(record)  # intentionally not called — no execution
        # kb_library.update_index(...)   # intentionally not called — no execution
        update["status"] = "closed"

    return update


# ---------------------------------------------------------------------------
# Team Lead — compose
# ---------------------------------------------------------------------------

def team_lead_compose(state: AgentState) -> dict:
    """Assemble the per-turn output: one-line status, only the sections with
    new content, then the next question or next step. This is the only
    node whose output the human actually reads as the "team's" reply.
    """
    reply = call_claude(TEAM_LEAD_PROMPT, _build_context(state))
    return {
        "messages": state.messages + [{"role": "assistant", "content": reply}],
        "status": "awaiting_human" if state.status != "closed" else "closed",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _precedent_note(state: AgentState) -> str:
    if not state.precedent_hits:
        return ""
    lines = [f"- Case {h.case_number}: {h.symptom} ({h.root_cause_category})" for h in state.precedent_hits]
    return "Precedent from the Case KB Library:\n" + "\n".join(lines)


def _build_context(state: AgentState, extra_note: str = "") -> list[dict]:
    """Anthropic-format message list for a node's call_claude() turn."""
    context = list(state.messages)
    if extra_note:
        context = context + [{"role": "user", "content": extra_note}]
    return context


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("team_lead_intake", team_lead_intake)
    builder.add_node("technical_diagnostics", technical_diagnostics_node)
    builder.add_node("help_desk", help_desk_node)
    builder.add_node("kb_builder", kb_builder_node)
    builder.add_node("team_lead_compose", team_lead_compose)

    builder.add_edge(START, "team_lead_intake")

    builder.add_conditional_edges(
        "team_lead_intake",
        route_to_specialists,
        ["technical_diagnostics", "help_desk", "kb_builder"],
    )

    # All three specialists converge on the same compose step; only the
    # branches route_to_specialists actually selected will have run.
    builder.add_edge("technical_diagnostics", "team_lead_compose")
    builder.add_edge("help_desk", "team_lead_compose")
    builder.add_edge("kb_builder", "team_lead_compose")

    builder.add_edge("team_lead_compose", END)

    return builder


# Compiled graph, ready to invoke with an initial AgentState — not run here.
graph = build_graph().compile()
