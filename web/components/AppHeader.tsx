import Link from "next/link";

export function AppHeader() {
  return (
    <header className="flex w-full shrink-0 items-center justify-between border-b border-border-subtle bg-surface-panel px-6 py-2">
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-primary-container text-on-primary">
            <span className="text-xs font-semibold">G</span>
          </div>
          <span className="font-headline text-base font-semibold text-text-primary">
            Groww Support Reply
          </span>
        </Link>
        <div className="hidden h-4 w-px bg-border-subtle sm:block" />
        <span className="hidden text-xs text-text-tertiary sm:inline">
          Facts-only drafts. Human approve.
        </span>
        <nav className="ml-2 hidden items-center gap-4 lg:flex">
          <Link
            href="/"
            className="border-b-2 border-primary pb-1 text-sm font-semibold text-primary"
          >
            Queue
          </Link>
          <span className="cursor-default pb-1 text-sm font-medium text-text-secondary">
            Cluster Stats
          </span>
          <span className="cursor-default pb-1 text-sm font-medium text-text-secondary">
            Audit Log
          </span>
          <span className="cursor-default pb-1 text-sm font-medium text-text-secondary">
            Policies
          </span>
        </nav>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex flex-col text-left">
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-state-pass-dot" />
            <span className="text-xs font-semibold text-text-primary">
              Agent workbench
            </span>
          </div>
          <span className="text-[11px] font-semibold tracking-wide text-text-tertiary uppercase">
            Tier 2 Mutual Funds
          </span>
        </div>
      </div>
    </header>
  );
}
