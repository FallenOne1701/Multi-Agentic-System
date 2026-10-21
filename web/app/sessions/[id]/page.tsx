import { Suspense } from "react";
import { SessionLoader } from "@/components/SessionLoader";

export const instant = false;

export default async function SessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="flex flex-1 justify-center overflow-y-auto px-6 py-8">
      <Suspense
        fallback={<p className="text-sm text-text-secondary">Loading session…</p>}
      >
        <SessionLoader id={id} />
      </Suspense>
    </main>
  );
}
