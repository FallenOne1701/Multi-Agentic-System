# Edge Cases: Groww Multi-Agent Support Reply System

Derived from [`docs/superpowers/plans/implementation plan.md`](superpowers/plans/implementation%20plan.md) and [`docs/architecture.md`](architecture.md). Each case lists the input shape, expected behavior, and which component owns the failure mode.

Use this as a test checklist while implementing Tasks 3–12. Cases marked **acceptance** must pass before submit.

---

## 1. Ingress / PII

| ID | Input | Expected | Owner |
|---|---|---|---|
| PII-01 | PAN `ABCDE1234F` in complaint | Replaced with `[PAN]`; raw value absent from session, logs, draft, record | Ingress |
| PII-02 | Phone `9876543210` | `[PHONE]` only; never in output artifacts | Ingress |
| PII-03 | Email `me@example.com` | `[EMAIL]` only | Ingress |
| PII-04 | Aadhaar with spaces `1234 5678 9012` | `[AADHAAR]` only | Ingress |
| PII-05 | Aadhaar without spaces `123456789012` | `[AADHAAR]` only | Ingress |
| PII-06 | Labeled OTP `OTP 482913` | `[OTP]` only; bare 6-digit numbers without OTP label may stay (avoid over-redacting NAV-like digits) | Ingress |
| PII-07 | Account context `account number 1234567890123456` | `[ACCOUNT]` only | Ingress |
| PII-08 | Multiple PII types in one message | All masked; `pii_types` lists each type once, no raw values | Ingress |
| PII-09 | Clean complaint, no PII | Text unchanged; `pii_types == []` | Ingress |
| PII-10 | PII that ingress missed but still matches regex in draft | Compliance flags `pii`; reviewer hard-fails if raw value reaches draft | Compliance + Reviewer |
| PII-11 | Token `[PAN]` already in text | Left as token; not treated as raw PII leak | Ingress / Reviewer |
| PII-12 **acceptance** | Exit-load question + PAN + phone | Agents see tokens only; approve record and email contain no raw PAN/phone | Full path |

---

## 2. Facts Agent

| ID | Input | Expected | Owner |
|---|---|---|---|
| FAC-01 **acceptance** | Exit load on HDFC Large Cap | `covered`, `scheme_id=large_cap`, section Exit load, citation = that file's `source_url`, `last_checked=25-Jun-2026` | Facts |
| FAC-02 | Exit load on Mid / Small Cap | Covered for matching scheme; 1 year exit-load text from that file | Facts |
| FAC-03 | Exit load on Gold / Silver FoF | Covered; 15-day exit-load text (not 1 year) | Facts |
| FAC-04 **acceptance** | Non-HDFC fund or app order failure | `not_covered`; `fact`/`citation` null; `searched` lists schemes/sections opened | Facts |
| FAC-05 | Scheme matched, section not in seven titles | `not_covered` (do not invent) | Facts |
| FAC-06 | Ambiguous "HDFC" with no Large/Mid/Small/Gold/Silver cue | `not_covered` or no scheme_id; never pick a random scheme | Facts |
| FAC-07 | Two schemes named in one complaint | At most one scheme; prefer the one tied to the asked section, else `not_covered` | Facts |
| FAC-08 | Asks for 1Y return / CAGR of a covered scheme | Do not invent returns; `not_covered` (or non-performance section only if corpus text truly answers — corpus has no return figures as answers) | Facts |
| FAC-09 | Stamp duty / tax / NAV / SIP minimum for a named scheme | `covered` from matching section; one citation only | Facts |
| FAC-10 | Empty or whitespace-only complaint | `not_covered`; empty or minimal `searched` | Facts |

---

## 3. Pattern Agent

| ID | Input | Expected | Owner |
|---|---|---|---|
| PAT-01 **acceptance** | Fee / brokerage / exit-load complaint | `theme_id=fees_brokerage` even though not in `topThemes`; `count=136` | Pattern |
| PAT-02 | Withdrawal / deposit stuck | `money_movement` | Pattern |
| PAT-03 | App crash / lag | `reliability` | Pattern |
| PAT-04 | Chart / order / trade UI | `trading_charts` | Pattern |
| PAT-05 | Generic praise / unmatched | `other`, signal `one-off` | Pattern |
| PAT-06 | Theme count &lt; 20 (if such theme existed) | `one-off` | Pattern |
| PAT-07 | Recent 7-day count ≥ 40 | `rising` | Pattern |
| PAT-08 | Recent count ≥ 2× earlier weekly rate, count ≥ 20, not other | `rising` | Pattern |
| PAT-09 | Count ≥ 20, not other, not rising | `recurring` | Pattern |
| PAT-10 | Window dates always | Full `2026-04-12`→`2026-07-04`; recent `2026-06-28`→`2026-07-04` | Pattern |
| PAT-11 | Must not read Facts or Compliance output | Same result whether other agents succeed or fail | Pattern |

---

## 4. Compliance Agent

| ID | Input | Expected | Owner |
|---|---|---|---|
| COM-01 **acceptance** | "Should I redeem…?" | `advice` flag; `advice_refusal=True` | Compliance |
| COM-02 **acceptance** | "Is this scheme good?" / "worth it?" | `advice` | Compliance |
| COM-03 **acceptance** | "What returns / CAGR should I expect?" | `performance_claim`; `advice_refusal=True` | Compliance |
| COM-04 | Clean exit-load question | `flags=[]`, `advice_refusal=False` | Compliance |
| COM-05 | Ingress reports `pii_types` | `pii` in flags; types echoed, no raw values | Compliance |
| COM-06 | Buy/sell/hold in investment context | `advice` | Compliance |
| COM-07 | Does not see draft or other agents | Flags based only on redacted complaint + `pii_types` | Compliance |

---

## 5. Orchestrator — disposition and draft

| ID | Input mix | Expected disposition | Owner |
|---|---|---|---|
| ORC-01 | Covered + one-off + clean | `reply`; citation + last_checked in ≤3 sentences | Orchestrator |
| ORC-02 | Covered + recurring/rising | `escalate`; routing note keeps ticket open | Orchestrator |
| ORC-03 | Covered + rising / high recent on same issue | `disagree`; `disagreement=True`; note cites fact **and** N recent reviews | Orchestrator |
| ORC-04 | Facts `not_covered` | `handoff`; no citation; no invented fact; names what was searched | Orchestrator |
| ORC-05 | Advice or performance flag (or sticky refusal) | `refuse`; fixed refusal copy; **no** exit-load recommendation even if Facts covered | Orchestrator |
| ORC-06 | Refuse vs covered conflict | Covered fact does **not** overwrite `refuse` | Orchestrator |
| ORC-07 | Reply sentence budget | User reply ≤ 3 sentences; routing note separate and unlimited by that budget | Orchestrator |
| ORC-08 | Covered reply missing last_checked | Must include `25-Jun-2026` (or scheme `nav_date`) before reviewer | Orchestrator |
| ORC-09 | Exactly one citation when covered | URL must be Facts `source_url`, never a second link | Orchestrator |
| ORC-10 | Team map | `fees_brokerage` → Fees and mutual fund ops; `money_movement` → Payments; etc. | Orchestrator |
| ORC-11 | Priority | `rising`→P1; `recurring`→P2; `one-off`→P3; escalate/disagree at least P2 | Orchestrator |
| ORC-12 **acceptance** | Parallel fan-out | All three agents started before any result read; reviewer only after merge | Orchestrator |

---

## 6. Reviewer

| ID | Draft defect | Expected | Owner |
|---|---|---|---|
| REV-01 | Factual claim, no `source_url` | Fail `citation` | Reviewer |
| REV-02 | More than one link, or wrong scheme URL | Fail `citation` | Reviewer |
| REV-03 | `not_covered` draft with a factual claim | Fail `citation` / shape | Reviewer |
| REV-04 | Advice language ("you may want to", "consider staying") | Fail `advice` | Reviewer |
| REV-05 | Return / CAGR / performance figure in draft | Fail `performance` | Reviewer |
| REV-06 | Raw phone/PAN/email in draft or routing note | Fail `pii` | Reviewer |
| REV-07 | Tokens like `[PAN]` in draft | Allowed (not a fail) | Reviewer |
| REV-08 | &gt; 3 sentences, or covered without last-checked | Fail `shape` | Reviewer |
| REV-09 | Round 1 fail | Orchestrator rewrites from same three results; agents do **not** re-run; `agents_fired` kind `reviewer_rework` | Reviewer + Orch |
| REV-10 | Round 2 still fail | `status=blocked`; UI shows draft + flag; **no Approve / Send** | Reviewer |
| REV-11 | Pass | Human sees draft + routing note; Approve enabled only then | Reviewer |

---

## 7. Refinement and session

| ID | Pushback | Expected | Owner |
|---|---|---|---|
| REF-01 | "Shorter" / wording only | Orchestrator only; Facts/Pattern/Compliance skipped | Refinement |
| REF-02 | "Different scheme" | Facts + orchestrator re-run; then reviewer | Refinement |
| REF-03 | "Fee issue from last week" | Pattern + orchestrator; then reviewer | Refinement |
| REF-04 | Scheme + theme both change | Facts + Pattern + orchestrator | Refinement |
| REF-05 | Complaint text itself changes | Compliance also re-runs | Refinement |
| REF-06 | Wording tweak of draft | Compliance does **not** re-run | Refinement |
| REF-07 **acceptance** | Advice then later "is large cap worth it?" | Sticky `advice_refusal`; every turn `refuse` | Session |
| REF-08 | Fifth refinement succeeds | `refinement_count=5`; draft updated | Session |
| REF-09 | Sixth pushback | Rejected; keep last reviewed draft | Session |
| REF-10 | Reviewer rework inside a refinement | Does **not** count toward the five human refinements | Session |
| REF-11 | `agents_fired` each round | Logs fired vs skipped names | Session |
| REF-12 | Raw user string | Never stored as a session field | Session |

---

## 8. Approval gate

| ID | Condition | Expected | Owner |
|---|---|---|---|
| APP-01 | `review.status=pass` + human approve | Append redacted JSONL record; create email draft file | Approval |
| APP-02 | `fail` or `blocked` | Approve absent in UI; programmatic `approve` raises | Approval |
| APP-03 | Record contents | redacted_text, disposition, reply, citation, last_checked, routing_note, pattern signal, agents_fired — no raw PII | Approval |
| APP-04 | Email | Draft body only; **no send** / no SMTP / no mailto auto-fire | Approval |
| APP-05 | Double approve | Safe append (new id) or idempotent policy — must not send email either way | Approval |

---

## 9. Cross-cutting / system

| ID | Scenario | Expected | Owner |
|---|---|---|---|
| SYS-01 | Agent throws / times out | Orchestrator fails closed (no silent empty draft); no partial approve | Orchestrator |
| SYS-02 | Missing `data/parsed` file | Facts `not_covered` or hard error before draft ships with invented facts | Facts |
| SYS-03 | Logger given raw complaint key | Logging util drops banned keys (`raw`, `pan`, etc.) | logging_util |
| SYS-04 **acceptance** | 20 real reviews from `normalized_reviews.json` | Every run: three structured results; reply has citation **or** explicit not_covered | Acceptance |
| SYS-05 **acceptance** | Four demo branches (clean / miss / recurring / PII) | Log agents_fired + reviewer; PII branch tokenized | Acceptance |
| SYS-06 | Single model answering all three roles | Out of scope — must remain three parallel agents | Design |

---

## Priority for implementers

1. **P0 (ship blockers):** PII-01–12, COM-01–03, ORC-05–06, REF-07, REV-10, APP-02, ORC-12  
2. **P1 (acceptance):** FAC-01/04, PAT-01, ORC-02–04, SYS-04–05  
3. **P2 (hardening):** FAC-06–08, PAT-07–08, REF-09–10, SYS-01–03  

Map each P0/P1 case to a pytest in the owning task from the implementation plan before marking that task done.
