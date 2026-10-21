import { IntakeForm } from "@/components/IntakeForm";

export default function HomePage() {
  return (
    <main className="flex flex-1 justify-center overflow-y-auto px-6 py-8">
      <div className="flex w-full max-w-[820px] flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-text-tertiary">
            <span>Workbench</span>
            <span>›</span>
            <span>Intake</span>
            <span>›</span>
            <span className="font-medium text-text-primary">
              New Complaint Intake
            </span>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded border border-state-pass-border bg-state-pass-bg px-2 py-0.5 text-[11px] font-semibold tracking-wide text-state-pass-text uppercase">
            <span className="h-1.5 w-1.5 rounded-full bg-state-pass-dot" />
            PII ENGINE: ONLINE
          </span>
        </div>
        <IntakeForm />
      </div>
    </main>
  );
}
