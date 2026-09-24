# Salesforce Case Agent Team — Design

**Status:** 🟦 scaffold — placeholder / not deployed or tested.
**Stack:** Python 3.10+ · LangGraph (multi-agent orchestration) · Claude API (Anthropic SDK) behind every role.
**Origin:** implements the author's own `biz-apps-sf-team` skill as a real agent graph.

## What it is

A Team Lead + 3 specialist agents that work a single Salesforce support case from intake to closure — retargeting the skill's "three lenses" into LangGraph nodes. The team only produces diagnosis, draft text, and documentation for a human to review and act on. It never contacts the end user, never makes a production change, never sends anything.

## Multi-agent architecture (LangGraph `StateGraph`)

See [`assets/blueprint.png`](assets/blueprint.png) / [`assets/blueprint.excalidraw`](assets/blueprint.excalidraw).

```
                       ┌──────────────────────┐
   case / turn ───────▶│   Team Lead          │  intake · routes · enforces
                       │   (supervisor)       │  constraints · composes the
                       └──┬────────┬───────┬──┘  3-lens turn output
        ┌─────────────────┘        │       └──────────────────┐
        ▼                          ▼                          ▼
 ┌────────────────┐      ┌──────────────────┐      ┌────────────────────┐
 │ 🔧 Technical    │      │ 🎧 Help Desk     │      │ 📚 Knowledge Base  │
 │ Diagnostics    │      │ Communication    │      │ Builder            │
 └───────┬────────┘      └────────┬─────────┘      └─────────┬──────────┘
         │                        │                          ▼
         │                        │              toolkit/kb_library.py:
         │                        │              search_precedent · write_case ·
         │                        │              update_index  (case-kb/ files)
         └────────────── all three call the Claude API via llm.py ──────────────┘
```

Implemented in [`graph.py`](graph.py): `team_lead_intake` → conditional fan-out (`route_to_specialists`) to the specialists with new work → all converge on `team_lead_compose`, which is the only node whose output the human reads.

### 🔧 Agent 1 — Technical Diagnostics ([`prompt_library/technical_diagnostics.py`](prompt_library/technical_diagnostics.py))
- Produces a **ranked hypothesis list**, ranked by how well each explains the specific symptom — not one guess.
- Grounds in org reference material if present in the workspace; else general Salesforce best practice.
- Names the **cheapest, lowest-risk, read-only diagnostic first** (Field History, debug logs, Flow/trigger inspection) before anything that touches data.
- Reads Flow/Apex/Setup evidence literally; states which node/line confirms or rules out each hypothesis.
- Distinguishes **"automation broken"** vs **"automation working on bad data."**
- **Never proposes or executes a production change** — recommends only.

### 🎧 Agent 2 — Help Desk Communication ([`prompt_library/help_desk.py`](prompt_library/help_desk.py))
- Every output is a **draft for the human to send** — never claims to have sent or notified anyone.
- Audience separation: user-facing text is plain and empathetic; technical internals stay out unless the user needs them to act.
- Keeps an early "we're on it" acknowledgment ready; folds any info request (repro steps, screenshots) into the draft.
- Gated: doesn't draft before there's something worth sending.

### 📚 Agent 3 — Knowledge Base Builder ([`prompt_library/kb_builder.py`](prompt_library/kb_builder.py))
- Maintains a **running scaffold from turn one** (Issue Reported / Root Cause / Action Taken / Resolution Category / Status); `[PENDING]` for unknowns, never fabricated.
- **Checks precedent at intake** — searches `case-kb/index.md` for matching symptom/object/field and flags hits to Agents 1 & 2 before they start.
- On case close, writes the record into the Case KB Library and updates the index.

## Case KB Library (file-based)

```
case-kb/
├── index.md                    — table, newest-appended: Case # | Date Closed | Symptom | Root Cause Category | File
└── cases/
    └── <case-number>-<slug>.md — full record (Issue/Root Cause/Action/Category/Status)
```

Operated on exclusively through [`toolkit/kb_library.py`](toolkit/kb_library.py) — `read_index()`, `search_precedent()`, `write_case()`, `update_index()`. Merge-safe: existing rows and files are never dropped or overwritten. Seeded with one sample row and one fake closed case ([`case-kb/cases/00042-flow-recursion.md`](case-kb/cases/00042-flow-recursion.md)) — no PII. Blank structure at [`references/kb_template.md`](references/kb_template.md).

## Team Lead coordination rules (enforced in `graph.py` / `prompt_library/team_lead.py`)

1. **No direct action** on external systems or people — every deliverable is text or data for the human.
2. **Authorize before advancing** — stop and ask for human-only inputs (screenshot, field-history export, fix confirmation); one clear question at a genuine fork.
3. **Keep the three lenses visibly separate** — the three headers in every turn.
4. **Update the KB scaffold every turn something changes.**
5. **PII discipline** — only names/details the user or ticket provided; never look up or invent.
6. **Check precedent before diagnosing.**

## Project layout

```
sf-case-agent-team/
  graph.py             # LangGraph StateGraph: Team Lead supervisor + 3 role nodes + kb tool nodes
  state.py             # Pydantic AgentState: messages, case_number, symptom, hypotheses,
                        #   kb_scaffold, precedent_hits, pending_question, status
  llm.py                # Claude API client (Anthropic SDK) from ANTHROPIC_API_KEY — SWAP-POINT, no key committed
  main.py               # CLI entry: a scripted example case (for reading; not executed)
  prompt_library/        # one system prompt per role: team_lead, technical_diagnostics, help_desk, kb_builder
  toolkit/
    kb_library.py       # read_index, search_precedent, write_case, update_index (operate on case-kb/ files)
  case-kb/              # seeded with a sample index.md + 1 example closed case (fake, no PII)
  references/
    kb_template.md      # copy-pasteable blank single-case KB structure
  requirements.txt      # langgraph, langchain-core, anthropic, pydantic (pinned)
  README.md DESIGN.md LICENSE (MIT ours) .gitignore
  assets/blueprint.png + blueprint.excalidraw
```

## Per-turn output format (authored into the Team Lead prompt)

One-line Team Lead status → only the role sections with new content this turn (skip empty ones) → close with the next question for the human, or the next step.

## Safety / boundaries (baked in)

- **Read-only to the world:** no email send, no ticket post, no Setup/data change — structurally, there are no such tools in `toolkit/`. The only tools are KB file ops.
- **Drafts only** from Agent 2; **recommendations only** from Agent 1.
- **PII discipline** + fake sample case only; real cases will carry customer PII — handle the working `case-kb/` copy carefully.
- Claude API key is the user's, via `ANTHROPIC_API_KEY`; none in the repo.

## Illustrative behavior (not a test — see `main.py`)

"Field reverts after every save, Case 00123" → precedent check finds Case 00042 (recursive Flow) → Technical Diagnostics ranks recursive/re-firing automation first, names Field History as the cheapest check → Knowledge Base Builder opens the scaffold (Status: Open) → Help Desk holds until there's an acknowledgment worth sending, then drafts one. Once the human confirms the fix, Knowledge Base Builder fills the final scaffold, writes `case-kb/cases/00123-*.md`, appends the index row, and presents the folder for re-upload.

## Success criteria (authoring only)

- Valid LangGraph `StateGraph` in `graph.py`: Team Lead supervisor + 3 role nodes + KB tool usage, coherent conditional edges; Pydantic `AgentState`; per-role prompts; Claude API behind `llm.py`.
- `toolkit/kb_library.py` implements the file-based library (index + cases, merge-safe) — pure functions, not executed.
- Seeded `case-kb/` + `references/kb_template.md`.
- `requirements.txt` pinned; imports coherent; not installed, not run, not tested, no API key.
- Business-framed README, this DESIGN.md, blueprint diagram, MIT LICENSE, `.gitignore`.
- Published as a public repo.

## Out of scope (v1 roadmap)

Live Salesforce API/MCP integration, real ticketing (Cases/Jira) sync, RAG over org docs, auto-send of any draft, multi-case batch — all roadmap.
