"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { createComplaint } from "@/lib/api";

const SAMPLE =
  "Hello Groww team, I noticed a 1% exit load deduction on my recent redemption of HDFC Large Cap Fund Direct Plan-Growth. My folio is ABC123 and registered PAN is ABCDE1234F. Can you clarify why this was applied and what the official policy states?";

const SAMPLE_CHIP = "Why was I charged an exit load on HDFC Large Cap?";

export function IntakeForm() {
  const router = useRouter();
  const [text, setText] = useState(SAMPLE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chars = text.length;
  const tokens = useMemo(
    () => (text.trim() ? text.trim().split(/\s+/).length : 0),
    [text],
  );

  async function onRun() {
    const trimmed = text.trim();
    if (!trimmed) {
      setError("Paste a customer complaint first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { id } = await createComplaint(trimmed);
      router.push(`/sessions/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run agents");
      setLoading(false);
    }
  }

  return (
    <section className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-surface-panel p-6 shadow-sm">
      <div className="flex flex-col gap-1 border-b border-border-subtle pb-3">
        <h1 className="font-headline text-xl font-semibold tracking-tight text-text-primary">
          New Customer Complaint
        </h1>
        <p className="text-sm text-text-secondary">
          Paste raw ticket or customer query below to initiate automated factual
          analysis and draft generation.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-text-tertiary">Sample query:</span>
        <button
          type="button"
          onClick={() => setText(SAMPLE)}
          className="rounded border border-border-subtle bg-surface-bg px-2.5 py-1 text-xs text-text-primary transition-colors hover:border-border-strong"
        >
          <span className="italic text-text-secondary">&quot;{SAMPLE_CHIP}&quot;</span>
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs">
          <label
            htmlFor="complaint"
            className="font-medium text-text-primary"
          >
            Customer Query Raw Intake{" "}
            <span className="text-state-danger-text">*</span>
          </label>
          <div className="flex gap-3 font-mono-token text-text-tertiary">
            <span>Tokens: {tokens}</span>
            <span>Chars: {chars}</span>
          </div>
        </div>
        <div className="rounded border border-border-subtle bg-surface-panel transition-all focus-within:border-primary-container focus-within:ring-2 focus-within:ring-primary-container/20">
          <textarea
            id="complaint"
            rows={6}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste customer complaint..."
            className="w-full resize-y border-0 bg-transparent p-3 text-sm leading-relaxed text-text-primary outline-none"
            disabled={loading}
          />
          <div className="flex items-center justify-between border-t border-border-subtle/60 bg-surface-bg/50 px-3 py-2">
            <span className="text-[11px] font-semibold tracking-wide text-text-tertiary uppercase">
              PII redacted at API ingress before agents run
            </span>
            <span className="flex items-center gap-1 text-[11px] font-semibold tracking-wide text-state-pass-text uppercase">
              Masking active
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-start gap-3 rounded-lg border border-border-subtle bg-surface-bg p-3 text-xs text-text-secondary">
        <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-state-pass-dot" />
        <span>
          PII is automatically redacted before running agents (typical wait
          10–30s). Approve creates an email draft only — nothing is sent.
        </span>
      </div>

      {error ? (
        <div className="rounded-lg border border-state-danger-border bg-state-danger-bg px-3 py-2 text-sm text-state-danger-text">
          {error}
        </div>
      ) : null}

      <div className="flex flex-col items-center justify-between gap-3 border-t border-border-subtle pt-3 sm:flex-row">
        <button
          type="button"
          onClick={onRun}
          disabled={loading}
          className="inline-flex w-full items-center justify-center gap-2 rounded bg-primary-container px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#009E77] active:bg-[#008765] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
        >
          {loading ? "Running Facts · Pattern · Compliance…" : "Run agents"}
        </button>
        <button
          type="button"
          onClick={() => {
            setText("");
            setError(null);
          }}
          disabled={loading}
          className="rounded px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-state-danger-bg hover:text-state-danger-text"
        >
          Clear intake
        </button>
      </div>
    </section>
  );
}
