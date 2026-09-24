"""CLI entry point — a scripted example case, written to be read, not run.

Walks the field-reverts-after-save scenario from the design doc through
intake -> precedent check -> ranked hypotheses -> an early acknowledgment
draft -> a running KB scaffold -> human-confirmed close. This file is not
executed as part of this scaffold; see README.md to run it for real.
"""

from __future__ import annotations

from graph import graph
from state import AgentState

# The human's opening message for a new case. In real use this comes from
# whatever intake surface (chat, ticket import) feeds the team.
INTAKE_MESSAGE = (
    "Case 00123: user says the Stage field on their Opportunity reverts to "
    "the previous value a few seconds after every save. No error shown."
)


def run_example_case() -> None:
    state = AgentState(
        messages=[{"role": "user", "content": INTAKE_MESSAGE}],
        case_number="00123",
        symptom="Field reverts to previous value shortly after every save on Opportunity",
    )

    # --- Turn 1: intake -----------------------------------------------
    # team_lead_intake searches case-kb/index.md and finds Case 00042 —
    # same symptom, same root-cause category (recursive Flow). Technical
    # Diagnostics and Knowledge Base Builder both see the hit before they
    # start; Help Desk drafts the early "we're on it" acknowledgment.
    #
    #   result = graph.invoke(state)
    #
    # Expected shape of the Team Lead's composed reply:
    #
    #   Team Lead: Case 00123 open — checking a known recursion pattern
    #   before asking for evidence.
    #
    #   🔧 Technical Diagnostics
    #   1. Recursive Flow re-firing on its own update (matches Case 00042)
    #      — cheapest check: Field History on Stage for the last 3 saves.
    #   2. Validation rule silently re-setting Stage on a second pass.
    #
    #   🎧 Help Desk Communication
    #   Draft to send to the user: "Thanks for flagging this — we're
    #   looking into why Stage reverts after saving and will update you
    #   shortly."
    #
    #   📚 Knowledge Base Builder
    #   Precedent: Case 00042 (recursive Flow) — same symptom.
    #   Scaffold opened — Issue Reported filled in, everything else
    #   [PENDING], Status: Open.
    #
    #   Next: could you pull Field History on Stage for the last 3 saves
    #   on this Opportunity?

    # --- Turn 2: human supplies Field History -------------------------
    # state.messages grows with the human's reply (the Field History
    # export); state.status stays "diagnosing". Technical Diagnostics
    # reads it literally, confirms hypothesis #1, and recommends the
    # entry-condition-guard fix used in Case 00042. Help Desk has nothing
    # new yet (no confirmed fix to tell the user about) — its section is
    # omitted this turn per the gating rule.

    # --- Turn 3: human confirms the fix was applied --------------------
    # state.status moves to "closing". Knowledge Base Builder finalizes
    # every scaffold field, calls kb_library.write_case() and
    # kb_library.update_index(), and the Team Lead's closing reply tells
    # the human the case-kb/ folder is ready and — if their project files
    # live outside this workspace — needs to be re-uploaded to persist.

    print("This is a scripted walkthrough for reading, not an executed run.")
    print("See the inline comments above for the expected turn-by-turn shape.")
    print(f"Initial state: {state.model_dump()}")


if __name__ == "__main__":
    run_example_case()
