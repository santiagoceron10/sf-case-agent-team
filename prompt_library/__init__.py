"""System prompts for the four roles in the Salesforce Case Agent Team.

Each module exports a single SYSTEM_PROMPT string. graph.py imports these
directly and passes them to llm.call_claude() as the `system_prompt` for
that node's turn.
"""

from .team_lead import SYSTEM_PROMPT as TEAM_LEAD_PROMPT
from .technical_diagnostics import SYSTEM_PROMPT as TECHNICAL_DIAGNOSTICS_PROMPT
from .help_desk import SYSTEM_PROMPT as HELP_DESK_PROMPT
from .kb_builder import SYSTEM_PROMPT as KB_BUILDER_PROMPT

__all__ = [
    "TEAM_LEAD_PROMPT",
    "TECHNICAL_DIAGNOSTICS_PROMPT",
    "HELP_DESK_PROMPT",
    "KB_BUILDER_PROMPT",
]
