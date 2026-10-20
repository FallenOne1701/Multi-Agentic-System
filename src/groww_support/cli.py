"""Human CLI: run complaints, refine, and approve (no auto-send)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from groww_support.approval import approve
from groww_support.contracts import SessionState
from groww_support.orchestrator import handle_complaint
from groww_support.orchestrator import refine as refine_session

app = typer.Typer(
    name="groww-support",
    help="Groww multi-agent support reply CLI",
    invoke_without_command=True,
)
console = Console()

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"
DEFAULT_SESSION_PATH = DEFAULT_OUTPUT_DIR / "session.json"


def load_session(path: Path) -> SessionState:
    return SessionState.model_validate_json(path.read_text(encoding="utf-8"))


def save_session(session: SessionState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")


def can_approve(session: SessionState) -> bool:
    return session.review is not None and session.review.status == "pass"


def print_session(session: SessionState) -> None:
    facts = session.facts
    pattern = session.pattern
    compliance = session.compliance
    draft = session.draft
    review = session.review

    summary = Table(show_header=False, box=None, padding=(0, 1))
    summary.add_row("Facts", facts.status if facts else "—")
    if facts and facts.scheme_id:
        summary.add_row(
            "Scheme",
            f"{facts.scheme_id} / {facts.section_title or '—'}",
        )
    summary.add_row(
        "Pattern",
        f"{pattern.theme_id} ({pattern.signal})" if pattern else "—",
    )
    if compliance:
        flags = ", ".join(compliance.flags) if compliance.flags else "clean"
        summary.add_row("Compliance", flags)
    console.print(Panel(summary, title="Specialists", border_style="cyan"))

    if draft:
        console.print(
            Panel(
                draft.reply,
                title=f"Draft [{draft.disposition}]",
                border_style="green",
            )
        )
        note = draft.routing_note
        console.print(
            Panel(
                f"team={note.team}  priority={note.priority}\n{note.why}",
                title="Routing note",
                border_style="blue",
            )
        )
        if draft.citation:
            console.print(f"citation: {draft.citation}")
        if draft.last_checked:
            console.print(f"last_checked: {draft.last_checked}")

    if review:
        console.print(f"review.status: {review.status} (round {review.round})")
        for f in review.failures:
            console.print(f"  - {f.check}: {f.detail}")

    if session.agents_fired:
        console.print("agents_fired:")
        for entry in session.agents_fired:
            console.print(
                f"  round={entry.round} kind={entry.kind} "
                f"fired={entry.fired} skipped={entry.skipped}"
            )

    if can_approve(session):
        console.print("[bold]Approve offered[/bold] (reviewer pass).")
    else:
        console.print("[yellow]Approve disabled[/yellow] (reviewer status is not pass).")


@app.callback()
def main(ctx: typer.Context) -> None:
    """Groww support CLI. No subcommand → interactive loop."""
    if ctx.invoked_subcommand is None:
        interactive()


@app.command("run")
def run_cmd(
    complaint: str = typer.Argument(..., help="Complaint text"),
    session_out: Path = typer.Option(
        DEFAULT_SESSION_PATH,
        "--session-out",
        help="Where to write session JSON",
    ),
    data_dir: Path = typer.Option(DEFAULT_DATA_DIR, "--data-dir"),
) -> None:
    """Fan-out specialists and print draft + routing note + review."""
    session = asyncio.run(handle_complaint(complaint, data_dir))
    save_session(session, session_out)
    print_session(session)
    console.print(f"session saved: {session_out}")


@app.command("refine")
def refine_cmd(
    session_path: Path = typer.Argument(..., help="Path to session.json"),
    pushback: str = typer.Argument(..., help="Human pushback text"),
    data_dir: Path = typer.Option(DEFAULT_DATA_DIR, "--data-dir"),
) -> None:
    """Selective refinement from a saved session."""
    session = load_session(session_path)
    session = asyncio.run(refine_session(session, pushback, data_dir))
    save_session(session, session_path)
    print_session(session)
    console.print(f"session saved: {session_path}")


@app.command("approve")
def approve_cmd(
    session_path: Path = typer.Argument(..., help="Path to session.json"),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output-dir"),
) -> None:
    """Append support record and write email draft (no send)."""
    session = load_session(session_path)
    if not can_approve(session):
        console.print(
            "[red]Approve unavailable:[/red] reviewer status is not pass."
        )
        raise typer.Exit(code=1)
    arts = approve(session, output_dir)
    console.print(f"record_id: {arts.record_id}")
    console.print(f"record: {arts.record_path}")
    console.print(f"email draft: {arts.email_path}")


def interactive(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    session_path: Path = DEFAULT_SESSION_PATH,
) -> None:
    """Prompt → show draft → refine / approve / quit."""
    console.print(
        "Interactive mode. Type a complaint, then refine / approve / quit."
    )
    while True:
        complaint = console.input("[bold]Complaint[/bold] (or quit): ").strip()
        if not complaint or complaint.lower() in {"q", "quit", "exit"}:
            break

        session = asyncio.run(handle_complaint(complaint, data_dir))
        save_session(session, session_path)
        print_session(session)

        while True:
            if can_approve(session):
                prompt = "[r]efine / [a]pprove / [q]uit: "
            else:
                prompt = "[r]efine / [q]uit (approve disabled): "
            action = console.input(prompt).strip().lower()
            if action in {"q", "quit", "exit"}:
                return
            if action in {"r", "refine"}:
                pushback = console.input("Pushback: ").strip()
                if not pushback:
                    continue
                try:
                    session = asyncio.run(
                        refine_session(session, pushback, data_dir)
                    )
                except ValueError as exc:
                    console.print(f"[red]{exc}[/red]")
                    continue
                save_session(session, session_path)
                print_session(session)
                continue
            if action in {"a", "approve"}:
                if not can_approve(session):
                    console.print(
                        "[yellow]Approve disabled[/yellow] "
                        "(reviewer status is not pass)."
                    )
                    continue
                arts = approve(session, output_dir)
                console.print(f"Approved. record={arts.record_path}")
                console.print(f"email draft={arts.email_path}")
                return
            console.print("Unknown action. Use r, a, or q.")


if __name__ == "__main__":
    app()
