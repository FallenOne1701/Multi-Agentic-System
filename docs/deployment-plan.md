# Deployment Plan — Multi-Agent Support Reply (Render + Vercel + Stitch)

Deploy the **FastAPI support API** on [Render](https://render.com) and the **Next.js support UI** on [Vercel](https://vercel.com). Design the UI in [Google Stitch](https://stitch.withgoogle.com/), then rebuild it as `web/` (same pattern as [Zomato-Project](https://github.com/FallenOne1701/Zomato-Project) and [Groww-and-MCP](https://github.com/FallenOne1701/Groww-and-MCP)).

```
Browser  →  Vercel (Support UI, Next.js from Stitch)
                │
                │  POST /v1/complaints  (rewrite or direct)
                ▼
            Render (FastAPI + groww_support + data/ + Groq/Gemini)
```

**Why this split**

| Service | Platform | Role |
|---------|----------|------|
| Backend | Render | Python 3.11+, long-lived process, parallel LLM classifiers (10–30s), corpus on disk (`data/`) |
| Frontend | Vercel | Next.js App Router, CDN, preview deploys per branch/PR |
| Design | Stitch | Visual contract (`stitch_*/DESIGN.md` + `code.html`) — not the production host |

**Facts-only. No investment advice. No auto-send.** Approve still only appends a support record and writes an email draft.

Repo: https://github.com/FallenOne1701/Multi-Agentic-System

`railway.toml` remains in the repo as an optional alternate host; **Render is the primary backend** (`render.yaml`).

---

## Current gaps (must fix before first deploy)

Same idea as the MCP-Server-1 deploy plan: ship transport + wiring; keep agent logic as-is.

| Gap | Why it blocks | Required change |
|---|---|---|
| **CLI-only** (`groww-support`) | Host needs an HTTP process on `$PORT` | Add FastAPI (`src/groww_support/api.py`) wrapping `handle_complaint` / `refine` / `approve` |
| **No `web/` app** | Vercel Root Directory expects Next.js | Rebuild Stitch export as `web/` (do **not** host `code.html`) |
| **No `render.yaml` / `Procfile`** | Repeatable start + healthcheck | uvicorn on `0.0.0.0:$PORT`, `/health` |
| **Ephemeral `output/`** | Approve artifacts vanish on restart | Render disk for `OUTPUT_DIR`, or object storage |
| **No CORS** | Browser → Render blocked | `CORS_ORIGINS` + `CORS_ORIGIN_REGEX` for `*.vercel.app` |

Orchestrator, specialists, reviewer, and ingress stay in `src/groww_support/` — API is a thin shell.

---

## Prerequisites

- GitHub repo connected (this project: `FallenOne1701/Multi-Agentic-System`).
- **Groq API key** — [console.groq.com](https://console.groq.com) (specialist classifiers).
- **Gemini API key** (optional) — reviewer assist; hard-fail rules still apply without it.
- **Corpus in git** — `data/parsed/`, `data/analyzed_themes.json`, `data/normalized_reviews.json` (already committed).
- Stitch project exported into something like `stitch_groww_support_reply/` (`DESIGN.md`, `code.html`, `screen.png`) + optional `docs/stitch-prompt.md`.

---

## Pre-deploy checklist

- [ ] Corpus present under `data/` and in git.
- [ ] `.env` is **not** committed (only `.env.example`).
- [ ] FastAPI app exists and `GET /health` works locally.
- [ ] Local smoke:
  ```powershell
  .\.venv\Scripts\python.exe -m pytest -q
  .\.venv\Scripts\python.exe scripts/verify_e2e.py
  cd web; npm run build
  ```
- [ ] Production URLs (fill after first deploy):
  - Render API: `https://<service>.onrender.com`
  - Vercel app: `https://<project>.vercel.app`

---

## Part 0 — Design with Stitch (before / while building `web/`)

Use Stitch as the **visual contract**, then rebuild in Next.js — do not deploy Stitch HTML.

| File (after export) | Role |
|---------------------|------|
| `stitch_groww_support_reply/DESIGN.md` | Tokens, type, chrome, components |
| `stitch_groww_support_reply/code.html` | High-fidelity screen(s) |
| `docs/stitch-prompt.md` | IA, sample copy, route map (optional, like Groww-and-MCP) |

**Suggested screens**

| Screen | Route (target) | Shows |
|--------|----------------|--------|
| New complaint | `/` | Textarea + Run |
| Result | `/sessions/[id]` | Draft, citation, last-checked, routing note, specialists, reviewer |
| Refine | same + pushback | Updated draft + `agents_fired` |
| Approve | gated CTA | Only if `review.status == "pass"` → record + email draft paths |

**Do not**

- Host `code.html` / CDN Tailwind as production
- Put `GROQ_API_KEY` / `GEMINI_API_KEY` in the browser or Stitch copy
- Add a “Send email” button (draft only)

**Do**

- Extract shared chrome, then typed React routes under `web/`
- Bind real session JSON from the Render API
- Keep Approve disabled until reviewer pass

---

## Part 1 — Backend on Render

### 1.1 Create the service

**Option A — Blueprint (recommended)**

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
2. Connect `FallenOne1701/Multi-Agentic-System` (repo root has `render.yaml`).
3. Fill prompted secrets (`GROQ_API_KEY`, optional `GEMINI_API_KEY`, `CORS_ORIGINS`).
4. Apply → wait for first deploy.

**Option B — Manual Web Service**

1. **New** → **Web Service** → deploy from GitHub.
2. Select `FallenOne1701/Multi-Agentic-System`.
3. **Root directory:** repository root (not `web/`).
4. **Runtime:** Python. **Branch:** `main`.
5. **Build command:** `pip install .`
6. **Start command:** `uvicorn groww_support.api:app --host 0.0.0.0 --port $PORT`
7. **Health check path:** `/health`

Python version comes from `runtime.txt` (`python-3.11.11`). `Procfile` matches the same start command.

### 1.2 Configure build & start

Render injects **`PORT`**. Uvicorn must listen on `0.0.0.0` and that port.

Blueprint (`render.yaml`):

```yaml
services:
  - type: web
    name: groww-support-api
    runtime: python
    plan: free
    buildCommand: pip install .
    startCommand: uvicorn groww_support.api:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
```

Install from `pyproject.toml`. Ensure `data/` is in the image (it is in git today).

**Free tier notes:** cold starts after idle; multi-agent runs can take 15–45s. If requests time out, upgrade the instance (e.g. Starter) in the Render dashboard.

### 1.3 Minimum API surface

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/health` | Liveness (`{"status":"ok"}`) |
| `POST` | `/v1/complaints` | `{ "text": "..." }` → session (fan-out + draft + review) |
| `POST` | `/v1/sessions/{id}/refine` | `{ "pushback": "..." }` → updated session |
| `POST` | `/v1/sessions/{id}/approve` | Record + email draft if reviewer pass; **404/403 if not pass** |

### 1.4 Environment variables (Render)

Set in **Environment** (never commit). Blueprint marks secrets as `sync: false` so you enter them in the dashboard:

| Variable | Required | Example / notes |
|----------|----------|-----------------|
| `GROQ_API_KEY` | Yes | Specialist classifiers |
| `GROQ_MODEL` | No | `openai/gpt-oss-120b` |
| `GEMINI_API_KEY` | No | Reviewer assist |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` |
| `GROWW_USE_LLM` | No | `1` in prod |
| `CORS_ORIGINS` | Yes (prod) | `https://<project>.vercel.app,http://localhost:3000` |
| `CORS_ORIGIN_REGEX` | No | `https://.*\.vercel\.app` (previews) |
| `DATA_DIR` | No | Default `data` |
| `OUTPUT_DIR` | No | Durable path on a disk, e.g. `/var/data/output` |

Render injects `PORT` — do not hardcode `8000` in production.

### 1.5 Health check

Blueprint sets `healthCheckPath: /health`, or Settings → **Health Check Path** → `/health`.

### 1.6 Public URL

After deploy, copy the service URL, e.g. `https://groww-support-api.onrender.com`, for Vercel.

### 1.7 Verify backend

```bash
curl https://<render-host>/health
curl -X POST https://<render-host>/v1/complaints \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"why was I charged an exit load on HDFC Gold Mutual Fund?\"}"
```

---

## Part 2 — Frontend on Vercel

### 2.1 Import project

1. Vercel → **Add New** → **Project** → import the same GitHub repo.
2. **Root Directory:** `web` (important — Next.js lives in `web/`).
3. Framework preset: **Next.js**.

### 2.2 Environment variables (Vercel)

| Variable | Required | Value |
|----------|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | **Yes (Hobby)** | `https://<render-host>` (no trailing slash) |
| `API_BASE_URL` | Optional | Same URL — used only by `/api/*` rewrite (Option A) |

`NEXT_PUBLIC_API_BASE_URL` lets the **browser** call Render directly (Option B) and avoids Vercel Hobby’s ~10s proxy timeout on multi-agent runs (often 15–45s).

After changing either variable, **Redeploy** on Vercel.

Add `web/vercel.json` (Next.js + security headers) like Palate when `web/` exists.

### 2.3 Build settings

| Setting | Value |
|---------|-------|
| Root Directory | `web` |
| Build Command | `npm run build` (default) |
| Output Directory | `.next` (default) |
| Install Command | `npm install` (default) |
| Node.js version | 24.x (pin via `engines` / `.nvmrc` like Palate) |

### 2.4 Deploy

Deploy from `main` → `https://<project>.vercel.app`.  
Previews: `https://<project>-<branch>.vercel.app` — allowed via Render `CORS_ORIGIN_REGEX`.

---

## Part 3 — Wire backend and frontend

### 3.1 Option A — Next.js rewrite (local default)

When `NEXT_PUBLIC_API_BASE_URL` is **unset**, the UI calls relative `/api/*`; Next rewrites to FastAPI via `API_BASE_URL`.

**Pros:** Same-origin.  
**Cons:** Hobby ~10s proxy limit — multi-agent + reviewer often needs Option B or Pro.

### 3.2 Option B — Direct browser → Render (recommended for Hobby)

**Render**

```env
CORS_ORIGINS=https://<project>.vercel.app,http://localhost:3000
CORS_ORIGIN_REGEX=https://.*\.vercel\.app
```

**Vercel**

```env
NEXT_PUBLIC_API_BASE_URL=https://<render-host>
```

### 3.3 Final CORS matrix

| Client calls | Render CORS needed? |
|--------------|---------------------|
| `your-app.vercel.app/api/*` (rewrite) | No |
| `*.onrender.com/v1/complaints` directly | Yes — prod in `CORS_ORIGINS`; previews via `CORS_ORIGIN_REGEX` |

---

## Part 4 — Post-deploy verification

1. Open `https://<project>.vercel.app`.
2. Submit: *“why was I charged an exit load on HDFC Gold Mutual Fund?”*
3. Confirm draft cites Gold FoF exit load (1% within 15 days), routing note, reviewer pass.
4. Confirm Approve stays off unless `review.status == "pass"`.
5. Submit an advice ask (*“Should I redeem…?”*) → refuse, no citation invent.
6. Check Render logs for Groq/Gemini errors.

**Common failures**

| Symptom | Fix |
|---------|-----|
| API unreachable | Wrong `NEXT_PUBLIC_API_BASE_URL` / Render sleeping (wake with a request) |
| Facts always not_covered | `data/` missing from deploy image |
| 502 / empty specialists | Missing `GROQ_API_KEY` or `GROWW_USE_LLM=0` unexpectedly |
| Hangs then fails | Vercel proxy timeout — use Option B; or Render free cold start / upgrade plan |
| CORS error in console | Add origin to `CORS_ORIGINS` / regex |
| Approve always disabled | Reviewer fail — check draft length / citation / compliance |

---

## Part 5 — Secrets & security

- **Never** set `GROQ_API_KEY` or `GEMINI_API_KEY` on Vercel — only on Render.
- **Never** commit `.env` or `web/.env.local`.
- Rotate keys if they were ever pasted into chat.
- No outbound email send from approve — record + draft file only.
- PII redacted at ingress; do not log raw complaints with PAN/phone/email.

---

## Part 6 — Optional hardening (later)

- **`Dockerfile`** at repo root for reproducible builds.
- **GitHub Actions** — `pytest` + `npm run build` on PR.
- **Persistent disk** for `OUTPUT_DIR` approval artifacts.
- **Custom domains** — `api.…` (Render), app on Vercel.
- Latency fields on the API response (as in `scripts/verify_e2e.py`) for demos.
- **Railway** — `railway.toml` still works if you switch hosts again.

---

## Quick reference — deploy order

1. Land FastAPI + `render.yaml` / `Procfile` + Stitch → `web/` rebuild → push to GitHub.
2. Deploy **Render** → set env vars → confirm `/health`.
3. Copy Render public URL.
4. Deploy **Vercel** (`web/`) → set `NEXT_PUBLIC_API_BASE_URL` → redeploy.
5. Confirm Render `CORS_ORIGIN_REGEX` / `CORS_ORIGINS`.
6. Smoke-test complaint → draft → refine → approve end-to-end.

---

## Local vs production env

| | Local | Render | Vercel |
|---|-------|--------|--------|
| API URL | `http://127.0.0.1:8000` | `https://*.onrender.com` | — |
| UI URL | `http://localhost:3000` | — | `https://*.vercel.app` |
| Groq / Gemini | `.env` | Render Environment | — |
| Browser API origin | `/api/*` or public URL unset | — | `NEXT_PUBLIC_API_BASE_URL` |

**Local dev** (once API + `web/` exist):

```powershell
# Terminal 1 — API
.\.venv\Scripts\python.exe -m uvicorn groww_support.api:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — UI
cd web
npm run dev
```

CLI still works without the web stack:

```powershell
groww-support run "Why was I charged an exit load on HDFC Large Cap Fund?"
.\.venv\Scripts\python.exe scripts/verify_e2e.py
```

---

## Doc map

| Doc | Use |
|---|---|
| [`problemStatement.md`](problemStatement.md) | Product constraints |
| [`architecture.md`](architecture.md) | Agents, contracts, fan-out |
| [`eval.md`](eval.md) | Acceptance before submit |
| This file | Stitch → Render → Vercel deploy path |
