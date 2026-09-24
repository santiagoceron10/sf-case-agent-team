"""File-based Case KB Library tools.

These are the ONLY tools the graph has — deliberately. There is no email,
ticketing, or Salesforce Setup/data tool anywhere in this repo. The team
can read and write case-kb/ and nothing else in the outside world.

All functions are pure with respect to their inputs (given the same
case-kb/ contents, same result) and merge-safe: writing or updating never
drops or overwrites an existing row or file. Not executed as part of this
scaffold — see README.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CASE_KB_DIR = Path(__file__).resolve().parent.parent / "case-kb"
INDEX_PATH = CASE_KB_DIR / "index.md"
CASES_DIR = CASE_KB_DIR / "cases"

INDEX_HEADER = "| Case # | Date Closed | Symptom | Root Cause Category | File |\n"
INDEX_DIVIDER = "|---|---|---|---|---|\n"


@dataclass
class IndexRow:
    case_number: str
    date_closed: str
    symptom: str
    root_cause_category: str
    file: str


@dataclass
class CaseRecord:
    case_number: str
    slug: str
    issue_reported: str
    root_cause: str
    action_taken: str
    resolution_category: str
    status: str
    date_closed: str


def read_index() -> list[IndexRow]:
    """Parse case-kb/index.md into a list of rows, newest first as stored."""
    if not INDEX_PATH.exists():
        return []

    rows: list[IndexRow] = []
    for line in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or "Case #" in line or set(line.replace("|", "").strip()) <= {"-"}:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 5:
            continue
        rows.append(IndexRow(*cells))
    return rows


def search_precedent(symptom: str = "", object_name: str = "", field: str = "") -> list[IndexRow]:
    """Skim the index for rows whose Symptom text matches any of the given terms.

    Deliberately simple substring matching over the Symptom column — this
    is a precedent *flag* for a human/specialist to weigh, not an authority.
    """
    terms = [t.lower() for t in (symptom, object_name, field) if t]
    if not terms:
        return []

    hits = []
    for row in read_index():
        haystack = row.symptom.lower()
        if any(term in haystack for term in terms):
            hits.append(row)
    return hits


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "case"


def write_case(record: CaseRecord) -> Path:
    """Write a full case record to case-kb/cases/<case-number>-<slug>.md.

    Refuses to overwrite an existing file for the same case number so a
    repeated call can't silently clobber a prior write — callers that
    intend to update a case should read the existing file first.
    """
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{record.case_number}-{_slugify(record.slug)}.md"
    path = CASES_DIR / filename

    if path.exists():
        raise FileExistsError(
            f"{path} already exists — write_case never overwrites; "
            "read the existing record if you need to amend it."
        )

    body = (
        f"# Case {record.case_number}\n\n"
        f"**Date Closed:** {record.date_closed}\n\n"
        f"## Issue Reported\n{record.issue_reported}\n\n"
        f"## Root Cause\n{record.root_cause}\n\n"
        f"## Action Taken\n{record.action_taken}\n\n"
        f"## Resolution Category\n{record.resolution_category}\n\n"
        f"## Status\n{record.status}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def update_index(row: IndexRow) -> None:
    """Append one row to case-kb/index.md, creating the table if needed.

    Merge-safe: existing rows are preserved and the new row is appended
    after them (newest-last on disk; README/index convention lists newest
    first for human reading — callers that want strict newest-first order
    on disk should insert after the header instead of appending).
    """
    CASE_KB_DIR.mkdir(parents=True, exist_ok=True)

    if not INDEX_PATH.exists():
        INDEX_PATH.write_text(INDEX_HEADER + INDEX_DIVIDER, encoding="utf-8")

    existing = INDEX_PATH.read_text(encoding="utf-8")
    new_line = (
        f"| {row.case_number} | {row.date_closed} | {row.symptom} "
        f"| {row.root_cause_category} | {row.file} |\n"
    )
    INDEX_PATH.write_text(existing + new_line, encoding="utf-8")
