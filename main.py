"""
main.py
-------
LifeOS CLI — Phase 7
Now includes Library department (LangGraph RAG),
folder watcher, and proactive book insights.
"""

import os
import threading
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from core.orchestrator import Orchestrator
from core.high_council import HighCouncil
from core.legislature import Legislature
from core.constitution_engine import ConstitutionEngine
from core.proactive_engine import ProactiveEngine
from core.emotion_engine import EmotionEngine
from core.scheduler import Scheduler
from tools.health_input import HealthInput
from departments.library.library_manager import LibraryManager

console = Console()
health = HealthInput()


def print_banner():
    console.print(Panel(
        Text("LifeOS v0.7 — Personal AI Operating System", justify="center"),
        style="bold blue"
    ))
    console.print(
        "[dim]Commands: exit | + reward | - penalty | scores | "
        "log health | council | report | audit | intel <topic> | "
        "laws | propose | approve <id> | reject <id> | "
        "changelog | judiciary | emotion | alerts | schedule | "
        "ingest <path> | library books | summarize <title>[/dim]\n"
    )


def show_routing(matches: list):
    if not matches:
        return
    table = Table(show_header=True, header_style="bold dim", box=None)
    table.add_column("Department", style="cyan")
    table.add_column("Relevance", style="green")
    for m in matches:
        bar = "█" * int(m["score"] * 10)
        table.add_row(m["name"], f"{m['score']:.2f} {bar}")
    console.print(table)


def show_pending_alerts(proactive: ProactiveEngine):
    """Check and display any pending proactive alerts."""
    alerts = proactive.get_pending_alerts()
    for alert in alerts:
        priority_styles = {
            "critical": "bold red",
            "high":     "bold yellow",
            "medium":   "yellow",
            "low":      "cyan",
        }
        style = priority_styles.get(alert["priority"], "white")
        console.print(Panel(
            proactive.format_alert(alert),
            title=f"[{style}]LifeOS Alert[/{style}]",
            border_style=style.replace("bold ", ""),
        ))


def log_health():
    console.print("\n[bold cyan]Health Log — Today[/bold cyan]")
    console.print("[dim]Press Enter to skip any field.[/dim]\n")
    data = {}
    fields = [
        ("sleep_hours",   "Sleep hours (e.g. 7.5):", float),
        ("sleep_quality", "Sleep quality 1-10:",      int),
        ("mood",          "Mood 1-10:",               int),
        ("energy",        "Energy 1-10:",             int),
        ("water_ml",      "Water intake (ml):",       int),
        ("exercise_min",  "Exercise (minutes):",      int),
        ("notes",         "Any notes:",               str),
    ]
    for key, label, cast in fields:
        val = console.input(f"  {label} ").strip()
        if val:
            try:
                data[key] = cast(val)
            except ValueError:
                console.print(f"  [red]Skipping {key}[/red]")
    if data:
        health.log(**data)
        console.print(f"[green]✓ Health data logged.[/green]\n")
    else:
        console.print("[yellow]No data entered.[/yellow]\n")


def main():
    print_banner()
    console.print("[dim]Starting LifeOS...[/dim]")

    # Initialize all systems
    orchestrator = Orchestrator()
    council      = HighCouncil()
    legislature  = Legislature()
    constitution = ConstitutionEngine()
    proactive    = ProactiveEngine()
    emotion      = EmotionEngine()
    library      = LibraryManager()

    # Start Books folder watcher in background
    folder_observer = library.start_folder_watcher()
    if folder_observer:
        console.print(f"[dim]📂 Watching ~/Books/ for new books...[/dim]")

    # Start background scheduler
    scheduler = Scheduler(tick_interval=60)
    scheduler.add_task(
        name="Proactive Monitor",
        func=proactive.run_all_monitors,
        interval_seconds=300,        # every 5 minutes
        run_immediately=True         # run once at startup
    )
    scheduler.add_task(
        name="Legislature Pattern Scan",
        func=lambda: legislature.analyze_and_propose(),
        interval_seconds=1800,       # every 30 minutes
        run_immediately=False
    )
    scheduler.add_task(
        name="Library Insight",
        func=lambda: _queue_library_insight(library, proactive),
        interval_seconds=14400,      # every 4 hours
        run_immediately=False
    )
    scheduler.start()

    console.print("[green]✓ LifeOS v0.7 online. Proactive mode + Library active.[/green]\n")

    # Startup audit
    findings = council.audit.run_scan()
    if findings:
        console.print(Panel(
            council.audit.format_findings(findings),
            title="[yellow]⚠ Startup Audit[/yellow]",
            border_style="yellow"
        ))

    # Show pending proposals
    pending = legislature.get_pending_proposals()
    if pending:
        console.print(Panel(
            f"{len(pending)} law proposal(s) awaiting decision. Type 'propose' to review.",
            title="[cyan]Legislature[/cyan]",
            border_style="cyan"
        ))

    last_matches = []

    while True:
        try:
            # Check for proactive alerts before each prompt
            show_pending_alerts(proactive)

            user_input = console.input("[bold cyan]You → [/bold cyan]").strip()

            if not user_input:
                continue

            # ── System commands ──────────────────────────────────

            if user_input.lower() in ["exit", "quit", "bye"]:
                scheduler.stop()
                if folder_observer:
                    folder_observer.stop()
                    folder_observer.join()
                console.print("\n[yellow]LifeOS shutting down. Goodbye.[/yellow]")
                break

            if user_input.lower() == "scores":
                console.print(orchestrator.get_trust_scores())
                continue

            if user_input.lower() == "council":
                console.print(Panel(
                    council.format_overview_table(),
                    title="[bold blue]High Council — System Overview[/bold blue]",
                    border_style="blue"
                ))
                continue

            if user_input.lower() == "report":
                console.print("\n[dim]Generating report...[/dim]")
                report = council.generate_report()
                console.print(Panel(report,
                    title="[bold blue]High Council Report[/bold blue]",
                    border_style="blue"))
                continue

            if user_input.lower() == "audit":
                findings = council.audit.run_scan()
                console.print(Panel(
                    council.audit.format_findings(findings),
                    title="[bold yellow]Audit Engine[/bold yellow]",
                    border_style="yellow"
                ))
                continue

            if user_input.lower().startswith("intel "):
                topic = user_input[6:].strip()
                console.print(f"\n[dim]Analyzing: {topic}...[/dim]")
                intel = council.cross_department_intelligence(topic)
                console.print(Panel(intel,
                    title=f"[bold blue]Intelligence — {topic}[/bold blue]",
                    border_style="blue"))
                continue

            if user_input.lower() == "log health":
                log_health()
                continue

            # ── Constitution commands ─────────────────────────────

            if user_input.lower() == "laws":
                hard = constitution.get_hard_laws_text()
                soft = constitution.get_soft_laws_text()
                console.print(Panel(
                    f"[bold]HARD LAWS[/bold]\n{hard}\n\n[bold]SOFT LAWS[/bold]\n{soft}",
                    title="[cyan]Constitution — Current Laws[/cyan]",
                    border_style="cyan"
                ))
                continue

            if user_input.lower() == "changelog":
                console.print(Panel(
                    constitution.format_changelog(),
                    title="[cyan]Constitution Changelog[/cyan]",
                    border_style="cyan"
                ))
                continue

            # ── Legislature commands ──────────────────────────────

            if user_input.lower() == "propose":
                console.print("\n[dim]Legislature analyzing...[/dim]")
                legislature.analyze_and_propose()
                pending = legislature.get_pending_proposals()
                console.print(Panel(
                    legislature.format_proposals(pending),
                    title="[cyan]Legislature — Law Proposals[/cyan]",
                    border_style="cyan"
                ))
                continue

            if user_input.lower().startswith("approve "):
                prop_id = user_input[8:].strip()
                success = legislature.approve_proposal(prop_id)
                msg = f"[green]✓ Proposal {prop_id} approved and enacted.[/green]" \
                      if success else f"[red]Proposal {prop_id} not found.[/red]"
                console.print(msg)
                continue

            if user_input.lower().startswith("reject "):
                prop_id = user_input[7:].strip()
                success = legislature.reject_proposal(prop_id, "User rejected")
                msg = f"[yellow]✗ Proposal {prop_id} rejected.[/yellow]" \
                      if success else f"[red]Proposal {prop_id} not found.[/red]"
                console.print(msg)
                continue

            # ── Judiciary ─────────────────────────────────────────

            if user_input.lower() == "judiciary":
                console.print(Panel(
                    orchestrator.get_judiciary_stats(),
                    title="[cyan]Judiciary — Review Stats[/cyan]",
                    border_style="cyan"
                ))
                continue

            # ── Emotion engine ────────────────────────────────────

            if user_input.lower() == "emotion":
                state = emotion.infer(recent_message="")
                lines = [
                    f"Current state  : {state['state'].upper()}",
                    f"Confidence     : {state['confidence']:.0%}",
                    f"Signals        : {state['signals']}",
                    f"Tone guidance  : {state['tone_guidance']}",
                ]
                console.print(Panel(
                    "\n".join(lines),
                    title="[cyan]Emotion Engine[/cyan]",
                    border_style="cyan"
                ))
                continue

            # ── Alerts history ────────────────────────────────────

            if user_input.lower() == "alerts":
                history = proactive.get_alert_history(days=7)
                if not history:
                    console.print("[dim]No alerts in the last 7 days.[/dim]")
                else:
                    lines = [f"  {a['timestamp'][:19]} | {a['priority']:<8} | {a['message'][:60]}..."
                             for a in reversed(history[-10:])]
                    console.print(Panel(
                        "\n".join(lines),
                        title="[cyan]Recent Alerts (last 7 days)[/cyan]",
                        border_style="cyan"
                    ))
                continue

            # ── Schedule status ───────────────────────────────────

            if user_input.lower() == "schedule":
                console.print(Panel(
                    scheduler.format_tasks(),
                    title="[cyan]Background Scheduler[/cyan]",
                    border_style="cyan"
                ))
                continue

            # ── Feedback ──────────────────────────────────────────

            if user_input == "+" and last_matches:
                dept = last_matches[0]["name"]
                orchestrator.record_feedback(dept, +1, "User reward")
                console.print(f"[green]✓ Reward for {dept}[/green]")
                continue

            if user_input == "-" and last_matches:
                dept = last_matches[0]["name"]
                orchestrator.record_feedback(dept, -1, "User penalty")
                console.print(f"[red]✗ Penalty for {dept}[/red]")
                continue

            # ── Library commands ──────────────────────────────────

            if user_input.lower().startswith("ingest "):
                file_path = os.path.expanduser(user_input[7:].strip())
                console.print(f"\n[dim]Ingesting: {file_path}...[/dim]")
                result = library._handle_ingestion(file_path)
                console.print(Panel(
                    result,
                    title="[bold cyan]Library — Ingestion[/bold cyan]",
                    border_style="cyan"
                ))
                continue

            if user_input.lower() in ["library books", "my library", "list books"]:
                console.print(Panel(
                    library._handle_list_books(),
                    title="[bold cyan]Library — Your Books[/bold cyan]",
                    border_style="cyan"
                ))
                continue

            if user_input.lower().startswith("summarize "):
                title = user_input[10:].strip()
                console.print(f"\n[dim]Generating summary for: {title}...[/dim]")
                summary = library._handle_summary(title)
                console.print(Panel(
                    summary,
                    title=f"[bold cyan]Library — {title}[/bold cyan]",
                    border_style="cyan"
                ))
                continue

            # ── Normal message ────────────────────────────────────

            # Infer emotion and inject into context
            emotional_context = emotion.format_for_context(user_input)

            console.print("\n[dim]Routing...[/dim]")
            response, matches = orchestrator.process(user_input)
            last_matches = matches

            if matches:
                show_routing(matches)

            console.print(Panel(
                response,
                title="[bold green]LifeOS[/bold green]",
                border_style="green"
            ))
            console.print()

        except KeyboardInterrupt:
            scheduler.stop()
            if folder_observer:
                folder_observer.stop()
                folder_observer.join()
            console.print("\n[yellow]LifeOS shutting down. Goodbye.[/yellow]")
            break


def _queue_library_insight(library: LibraryManager, proactive: ProactiveEngine):
    """
    Called by the Scheduler every 4 hours.
    Gets a library insight and queues it as a proactive alert.
    """
    try:
        insight = library.get_proactive_insight()
        if insight:
            proactive.queue_alert(
                message=insight,
                priority="low",
                source="library",
            )
    except Exception as e:
        pass  # Scheduler swallows errors already, this is a safety net


if __name__ == "__main__":
    main()