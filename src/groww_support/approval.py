"""Human approval gate: append redacted record + email draft file (no send)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from pydantic import BaseModel

from groww_support.contracts import SessionState


class ApprovalArtifacts(BaseModel):
    record_id: str
    record_path: Path
    email_path: Path


def approve(session: SessionState, output_dir: Path) -> ApprovalArtifacts:
    if session.review is None or session.review.status != "pass":
        raise PermissionError("approve unavailable: reviewer status is not pass")
    if session.draft is None:
        raise PermissionError("approve unavailable: no draft")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "email_drafts").mkdir(exist_ok=True)

    record_id = str(uuid.uuid4())
    record = {
        "id": record_id,
        "redacted_text": session.redacted_text,
        "disposition": session.draft.disposition,
        "reply": session.draft.reply,
        "citation": session.draft.citation,
        "last_checked": session.draft.last_checked,
        "routing_note": session.draft.routing_note.model_dump(),
        "pattern_signal": session.pattern.signal if session.pattern else None,
        "agents_fired": [e.model_dump() for e in session.agents_fired],
    }
    record_path = output_dir / "support_records.jsonl"
    with record_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    email_path = output_dir / "email_drafts" / f"{record_id}.txt"
    email_path.write_text(
        f"Subject: Regarding your Groww support request\n\n{session.draft.reply}\n",
        encoding="utf-8",
    )
    return ApprovalArtifacts(
        record_id=record_id,
        record_path=record_path,
        email_path=email_path,
    )
