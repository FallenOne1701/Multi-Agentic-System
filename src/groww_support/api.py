"""HTTP API shell for Railway: health + complaint / refine / approve."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from groww_support.approval import approve
from groww_support.contracts import SessionState
from groww_support.orchestrator import handle_complaint
from groww_support.orchestrator import refine as refine_session

def _resolve_dir(env_key: str, leaf: str) -> Path:
    """Prefer env, then cwd (Render/Railway checkout), then source-tree fallback."""
    if raw := os.environ.get(env_key):
        return Path(raw)
    cwd_candidate = Path.cwd() / leaf
    if cwd_candidate.is_dir() or leaf == "output":
        # output/ may not exist yet; create under cwd when that is the checkout root
        if leaf == "output" and (Path.cwd() / "data").is_dir():
            return cwd_candidate
        if cwd_candidate.is_dir():
            return cwd_candidate
    # Editable/local: src/groww_support/api.py -> repo root
    return Path(__file__).resolve().parents[2] / leaf


DEFAULT_DATA_DIR = _resolve_dir("DATA_DIR", "data")
DEFAULT_OUTPUT_DIR = _resolve_dir("OUTPUT_DIR", "output")

app = FastAPI(title="Groww Support Reply API", version="0.1.0")

_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]
_origin_regex = os.environ.get("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComplaintIn(BaseModel):
    text: str = Field(min_length=1)


class RefineIn(BaseModel):
    pushback: str = Field(min_length=1)


class SessionOut(BaseModel):
    id: str
    session: SessionState


class ApproveOut(BaseModel):
    record_id: str
    record_path: str
    email_path: str


def _sessions_dir() -> Path:
    path = DEFAULT_OUTPUT_DIR / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _session_path(session_id: str) -> Path:
    return _sessions_dir() / f"{session_id}.json"


def _load(session_id: str) -> SessionState:
    path = _session_path(session_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="session not found")
    return SessionState.model_validate_json(path.read_text(encoding="utf-8"))


def _save(session_id: str, session: SessionState) -> None:
    path = _session_path(session_id)
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/complaints", response_model=SessionOut)
async def create_complaint(body: ComplaintIn) -> SessionOut:
    if not (DEFAULT_DATA_DIR / "parsed").is_dir():
        raise HTTPException(
            status_code=500,
            detail=(
                f"Corpus not found at {DEFAULT_DATA_DIR}. "
                "Set DATA_DIR to the repo data/ folder on the host."
            ),
        )
    session = await handle_complaint(body.text, DEFAULT_DATA_DIR)
    session_id = str(uuid.uuid4())
    _save(session_id, session)
    return SessionOut(id=session_id, session=session)


@app.get("/v1/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: str) -> SessionOut:
    return SessionOut(id=session_id, session=_load(session_id))


@app.post("/v1/sessions/{session_id}/refine", response_model=SessionOut)
async def refine(session_id: str, body: RefineIn) -> SessionOut:
    session = _load(session_id)
    try:
        updated = await refine_session(session, body.pushback, DEFAULT_DATA_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _save(session_id, updated)
    return SessionOut(id=session_id, session=updated)


@app.post("/v1/sessions/{session_id}/approve", response_model=ApproveOut)
async def approve_endpoint(session_id: str) -> ApproveOut:
    session = _load(session_id)
    try:
        artifacts = approve(session, DEFAULT_OUTPUT_DIR)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ApproveOut(
        record_id=artifacts.record_id,
        record_path=str(artifacts.record_path),
        email_path=str(artifacts.email_path),
    )
