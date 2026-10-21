"use client";

import { useEffect, useState } from "react";
import { SessionPanel } from "@/components/SessionPanel";
import { getSession } from "@/lib/api";
import type { SessionState } from "@/lib/types";

export function SessionLoader({ id }: { id: string }) {
  const [session, setSession] = useState<SessionState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await getSession(id);
        if (!cancelled) setSession(res.session);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load session",
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <div className="max-w-xl rounded-lg border border-state-danger-border bg-state-danger-bg p-4 text-sm text-state-danger-text">
        {error}
      </div>
    );
  }

  if (!session) {
    return <p className="text-sm text-text-secondary">Loading session…</p>;
  }

  return <SessionPanel id={id} initial={session} />;
}
