"use client";

import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { approveSession, refineSession } from "@/lib/api";
import type { ApproveResponse, SessionResponse, SessionState } from "@/lib/types";

function StatusBadge({
  tone,
  label,
}: {
  tone: "pass" | "warn" | "danger";
  label: string;
}) {
  const styles = {
    pass: "bg-state-pass-bg border-state-pass-border text-state-pass-text",
    warn: "bg-state-warn-bg border-state-warn-border text-state-warn-text",
    danger:
      "bg-state-danger-bg border-state-danger-border text-state-danger-text",
  } as const;
  const dot = {
    pass: "bg-state-pass-dot",
    warn: "bg-state-warn-dot",
    danger: "bg-state-danger-dot",
  } as const;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${styles[tone]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot[tone]}`} />
      {label}
    </span>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border-subtle bg-surface-panel p-4">
      <h3 className="mb-2 font-headline text-sm font-semibold text-text-primary">
        {title}
      </h3>
      <div className="space-y-1 text-sm text-text-secondary">{children}</div>
    </div>
  );
}

export function SessionPanel({
  id,
  initial,
}: {
  id: string;
  initial: SessionState;
}) {
  const router = useRouter();
  const [session, setSession] = useState(initial);
  const [pushback, setPushback] = useState("");
  const [busy, setBusy] = useState<"refine" | "approve" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approved, setApproved] = useState<ApproveResponse | null>(null);

  const review = session.review;
  const canApprove = review?.status === "pass" && !approved;
  const reviewTone =
    review?.status === "pass"
      ? "pass"
      : review?.status === "fail"
        ? "danger"
        : "warn";

  async function onRefine() {
    const text = pushback.trim();
    if (!text) {
      setError("Enter pushback before refining.");
      return;
    }
    setBusy("refine");
    setError(null);
    try {
      const res: SessionResponse = await refineSession(id, text);
      setSession(res.session);
      setPushback("");
      setApproved(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refine failed");
    } finally {
      setBusy(null);
    }
  }

  async function onApprove() {
    setBusy("approve");
    setError(null);
    try {
      const res = await approveSession(id);
      setApproved(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex w-full max-w-5xl flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge
          tone={reviewTone}
          label={`Reviewer ${review?.status ?? "—"}`}
        />
        {session.draft ? (
          <StatusBadge
            tone={
              session.draft.disposition === "escalate" ||
              session.draft.disposition === "disagree"
                ? "warn"
                : session.draft.disposition === "refuse"
                  ? "danger"
                  : "pass"
            }
            label={`Disposition: ${session.draft.disposition}`}
          />
        ) : null}
        {session.pattern ? (
          <StatusBadge
            tone={
              session.pattern.signal === "one-off" ? "pass" : "warn"
            }
            label={`Pattern: ${session.pattern.signal}`}
          />
        ) : null}
      </div>

      {approved ? (
        <div className="rounded-lg border border-state-pass-border bg-state-pass-bg p-4 text-sm text-state-pass-text">
          <p className="font-semibold">Approved — support record saved</p>
          <p className="mt-1 font-mono-token text-xs">
            record: {approved.record_path}
          </p>
          <p className="font-mono-token text-xs">
            email draft: {approved.email_path}
          </p>
          <p className="mt-2 text-xs">
            Approve writes record + email draft. Does not send.
          </p>
        </div>
      ) : null}

      <section className="rounded-xl border border-border-subtle bg-surface-panel p-6 shadow-sm">
        <h2 className="font-headline text-lg font-semibold text-text-primary">
          Customer reply draft
        </h2>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-text-primary">
          {session.draft?.reply ?? "No draft yet."}
        </p>
        {session.draft?.citation ? (
          <p className="mt-3 text-xs text-text-secondary">
            Citation:{" "}
            <a
              href={session.draft.citation}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline"
            >
              {session.draft.citation}
            </a>
            {session.draft.last_checked
              ? ` · Last checked: ${session.draft.last_checked}`
              : null}
          </p>
        ) : null}
      </section>

      {session.draft?.routing_note ? (
        <section className="rounded-xl border border-border-subtle bg-surface-panel p-6 shadow-sm">
          <h2 className="font-headline text-lg font-semibold text-text-primary">
            Internal routing note
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            team={session.draft.routing_note.team} · priority=
            {session.draft.routing_note.priority}
          </p>
          <p className="mt-2 text-sm text-text-primary">
            {session.draft.routing_note.why}
          </p>
        </section>
      ) : null}

      <div className="grid gap-3 md:grid-cols-3">
        <Panel title="Facts">
          <p>Status: {session.facts?.status ?? "—"}</p>
          {session.facts?.scheme_id ? (
            <p>
              {session.facts.scheme_id}
              {session.facts.section_title
                ? ` / ${session.facts.section_title}`
                : ""}
            </p>
          ) : null}
          {session.facts?.fact ? <p>{session.facts.fact}</p> : null}
        </Panel>
        <Panel title="Pattern">
          <p>
            {session.pattern
              ? `${session.pattern.theme_id} (${session.pattern.signal})`
              : "—"}
          </p>
          {session.pattern ? (
            <>
              <p>
                count={session.pattern.count} · recent=
                {session.pattern.recent_count}
              </p>
              <p className="text-xs">
                window {session.pattern.window.start} →{" "}
                {session.pattern.window.end}
              </p>
            </>
          ) : null}
        </Panel>
        <Panel title="Compliance">
          <p>
            flags:{" "}
            {session.compliance?.flags?.length
              ? session.compliance.flags.join(", ")
              : "clean"}
          </p>
          {session.pii_types?.length ? (
            <p className="font-mono-token text-xs">
              pii: {session.pii_types.map((t) => `[${t}]`).join(" ")}
            </p>
          ) : null}
        </Panel>
      </div>

      <Panel title="Reviewer">
        <p>
          status={review?.status ?? "—"} · round={review?.round ?? "—"}
        </p>
        {review?.failures?.map((f) => (
          <p key={`${f.check}-${f.detail}`} className="text-state-danger-text">
            {f.check}: {f.detail}
          </p>
        ))}
      </Panel>

      {session.agents_fired?.length ? (
        <Panel title="Agents fired">
          {session.agents_fired.map((e) => (
            <p key={`${e.round}-${e.kind}`}>
              round={e.round} kind={e.kind} fired=[{e.fired.join(", ")}]
            </p>
          ))}
        </Panel>
      ) : null}

      <section className="rounded-xl border border-border-subtle bg-surface-panel p-6 shadow-sm">
        <h2 className="font-headline text-lg font-semibold text-text-primary">
          Refine
        </h2>
        <textarea
          rows={3}
          value={pushback}
          onChange={(e) => setPushback(e.target.value)}
          placeholder="Make the wording shorter / re-check pattern…"
          className="mt-3 w-full rounded border border-border-subtle p-3 text-sm outline-none focus:border-primary-container"
          disabled={busy !== null}
        />
        <p className="mt-1 text-xs text-text-tertiary">
          Refinement {session.refinement_count}/5
        </p>
      </section>

      {error ? (
        <div className="rounded-lg border border-state-danger-border bg-state-danger-bg px-3 py-2 text-sm text-state-danger-text">
          {error}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onRefine}
          disabled={busy !== null}
          className="rounded border border-border-subtle bg-surface-panel px-4 py-2.5 text-sm font-medium text-text-primary hover:bg-surface-bg disabled:opacity-60"
        >
          {busy === "refine" ? "Refining…" : "Refine"}
        </button>
        <button
          type="button"
          onClick={onApprove}
          disabled={!canApprove || busy !== null}
          className="rounded bg-primary-container px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-[#009E77] disabled:cursor-not-allowed disabled:opacity-40"
          title={
            canApprove
              ? "Write support record + email draft"
              : "Approve disabled until reviewer pass"
          }
        >
          {busy === "approve" ? "Approving…" : "Approve draft"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/")}
          className="text-sm text-text-secondary hover:text-text-primary"
        >
          New complaint
        </button>
      </div>
      <p className="text-xs text-text-tertiary">
        Approve writes record + email draft. Does not send.
      </p>
    </div>
  );
}
