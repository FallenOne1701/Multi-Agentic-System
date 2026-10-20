# Groww Multi-Agent Support Reply System

Drafts facts-only, citation-backed support replies for Groww user complaints. Three specialist agents (Facts, Pattern, Compliance) run in parallel; an orchestrator merges their outputs; a reviewer hard-fails unsafe drafts; a human approval gate appends a record and creates an email draft (no auto-send).

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"   # Windows
# source .venv/bin/activate && pip install -e ".[dev]"  # macOS/Linux
```

Optional classifier LLM: copy `.env.example` to `.env` and set `GROQ_API_KEY` / `GROQ_MODEL`. Set `GROWW_USE_LLM=0` for offline keyword/regex fallbacks (default in tests).

## CLI

```bash
# One-shot fan-out (writes output/session.json)
groww-support run "Why was I charged an exit load on HDFC Large Cap Fund?"

# Selective refinement
groww-support refine output/session.json "make it shorter"

# Approve only when reviewer status is pass (appends record + email draft; no send)
groww-support approve output/session.json

# Interactive: complaint → refine / approve / quit
groww-support
```

Approve is disabled when `review.status != "pass"`.

## Tests

```bash
pytest -q
```

## Specs

- `docs/problemStatement.md`
- `docs/architecture.md`
- `docs/superpowers/plans/implementation plan.md`
