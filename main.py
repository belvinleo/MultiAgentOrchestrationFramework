"""
main.py
-------
LifeOS CLI — Phase 4
Now includes High Council governance, audit engine,
cluster governors, and system reporting.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from core.orchestrator import Orchestrator
from core.high_council import HighCouncil
from tools.health_input import HealthInput

console = Console()
health = HealthInput()


def print_banner():
    console.print(Panel(
        Text("LifeOS v0.4 — Personal AI Operating System", justify="center"),
        style="bold blue"
    ))
    console.print(
        "[dim]Commands: exit | + reward | - penalty | scores | "
        "log health | council | report | audit | intel <topic>[/dim]\n"
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
                console.print(f"  [red]Skipping {key} — invalid input[/red]")
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

    console.print("[green]✓ LifeOS v0.4 online. High Council active.[/green]\n")

    # Run startup audit
    findings = council.audit.run_scan()
    if findings:
        console.print(Panel(
            council.audit.format_findings(findings),
            title="[yellow]⚠ Startup Audit[/yellow]",
            border_style="yellow"
        ))

    last_matches = []

    while True:
        try:
            user_input = console.input("[bold cyan]You → [/bold cyan]").strip()

            if not user_input:
                continue

            # Exit
            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("\n[yellow]LifeOS shutting down. Goodbye.[/yellow]")
                break

            # Trust scores
            if user_input.lower() == "scores":
                console.print(orchestrator.get_trust_scores())
                continue

            # High Council overview
            if user_input.lower() == "council":
                console.print(Panel(
                    council.format_overview_table(),
                    title="[bold blue]High Council — System Overview[/bold blue]",
                    border_style="blue"
                ))
                continue

            # Generate full report
            if user_input.lower() == "report":
                console.print("\n[dim]High Council generating report...[/dim]")
                report = council.generate_report()
                console.print(Panel(
                    report,
                    title="[bold blue]High Council — Performance Report[/bold blue]",
                    border_style="blue"
                ))
                continue

            # Run audit
            if user_input.lower() == "audit":
                findings = council.audit.run_scan()
                console.print(Panel(
                    council.audit.format_findings(findings),
                    title="[bold yellow]Audit Engine Results[/bold yellow]",
                    border_style="yellow"
                ))
                continue

            # Cross-department intelligence
            if user_input.lower().startswith("intel "):
                topic = user_input[6:].strip()
                console.print(f"\n[dim]High Council analyzing: {topic}...[/dim]")
                intel = council.cross_department_intelligence(topic)
                console.print(Panel(
                    intel,
                    title=f"[bold blue]Intelligence Report — {topic}[/bold blue]",
                    border_style="blue"
                ))
                continue

            # Health logging
            if user_input.lower() == "log health":
                log_health()
                continue

            # Reward
            if user_input == "+" and last_matches:
                dept = last_matches[0]["name"]
                orchestrator.record_feedback(dept, +1, "User reward")
                console.print(f"[green]✓ Reward recorded for {dept}[/green]")
                continue

            # Penalty
            if user_input == "-" and last_matches:
                dept = last_matches[0]["name"]
                orchestrator.record_feedback(dept, -1, "User penalty")
                console.print(f"[red]✗ Penalty recorded for {dept}[/red]")
                continue

            # Normal message
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