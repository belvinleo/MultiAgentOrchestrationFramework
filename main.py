"""
main.py
-------
LifeOS CLI — Phase 5
Now includes Judiciary enforcement and Legislature law proposals.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from core.orchestrator import Orchestrator
from core.high_council import HighCouncil
from core.legislature import Legislature
from core.constitution_engine import ConstitutionEngine
from tools.health_input import HealthInput

console = Console()
health = HealthInput()


def print_banner():
    console.print(Panel(
        Text("LifeOS v0.5 — Personal AI Operating System", justify="center"),
        style="bold blue"
    ))
    console.print(
        "[dim]Commands: exit | + reward | - penalty | scores | log health | "
        "council | report | audit | intel <topic> | "
        "laws | propose | approve <id> | reject <id> | "
        "changelog | judiciary[/dim]\n"
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

    orchestrator = Orchestrator()
    council = HighCouncil()
    legislature = Legislature()
    constitution = ConstitutionEngine()

    console.print("[green]✓ LifeOS v0.5 online. Constitution engine active.[/green]\n")

    # Startup audit
    findings = council.audit.run_scan()
    if findings:
        console.print(Panel(
            council.audit.format_findings(findings),
            title="[yellow]⚠ Startup Audit[/yellow]",
            border_style="yellow"
        ))

    # Show pending proposals on startup
    pending = legislature.get_pending_proposals()
    if pending:
        console.print(Panel(
            f"{len(pending)} law proposal(s) awaiting your decision. Type 'propose' to review.",
            title="[cyan]Legislature[/cyan]",
            border_style="cyan"
        ))

    last_matches = []

    while True:
        try:
            user_input = console.input("[bold cyan]You → [/bold cyan]").strip()

            if not user_input:
                continue

            # ── System commands ──────────────────────────────────

            if user_input.lower() in ["exit", "quit", "bye"]:
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
                console.print("\n[dim]Legislature analyzing patterns...[/dim]")
                proposals = legislature.analyze_and_propose()
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
                if success:
                    console.print(f"[green]✓ Proposal {prop_id} approved and enacted.[/green]")
                else:
                    console.print(f"[red]Proposal {prop_id} not found.[/red]")
                continue

            if user_input.lower().startswith("reject "):
                prop_id = user_input[7:].strip()
                success = legislature.reject_proposal(prop_id, "User rejected")
                if success:
                    console.print(f"[yellow]✗ Proposal {prop_id} rejected.[/yellow]")
                else:
                    console.print(f"[red]Proposal {prop_id} not found.[/red]")
                continue

            # ── Judiciary command ─────────────────────────────────

            if user_input.lower() == "judiciary":
                console.print(Panel(
                    orchestrator.get_judiciary_stats(),
                    title="[cyan]Judiciary — Review Stats[/cyan]",
                    border_style="cyan"
                ))
                continue

            # ── Feedback commands ─────────────────────────────────

            if user_input == "+" and last_matches:
                dept = last_matches[0]["name"]
                orchestrator.record_feedback(dept, +1, "User reward")
                console.print(f"[green]✓ Reward recorded for {dept}[/green]")
                continue

            if user_input == "-" and last_matches:
                dept = last_matches[0]["name"]
                orchestrator.record_feedback(dept, -1, "User penalty")
                console.print(f"[red]✗ Penalty recorded for {dept}[/red]")
                continue

            # ── Normal message ────────────────────────────────────

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
            console.print("\n[yellow]LifeOS shutting down. Goodbye.[/yellow]")
            break


if __name__ == "__main__":
    main()