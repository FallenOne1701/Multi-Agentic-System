# Groww Multi-Agent Support Reply System

Drafts facts-only, citation-backed support replies for Groww user complaints. Three specialist agents (Facts, Pattern, Compliance) run in parallel; an orchestrator merges their outputs; a reviewer hard-fails unsafe drafts; a human approval gate appends a record and creates an email draft (no auto-send).

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"   # Windows
# source .venv/bin/activate && pip install -e ".[dev]"  # macOS/Linux
```

## Tests

```bash
pytest -q
```

## Specs

- `docs/problemStatement.md`
- `docs/architecture.md`
- `docs/superpowers/plans/implementation plan.md`
