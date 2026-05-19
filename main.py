"""
main.py
-------
LifeOS CLI — Phase 3
Now supports health logging and shows live data in responses.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from core.orchestrator import Orchestrator
from tools.health_input import HealthInput

console = Console()
health = HealthInput()


def print_banner():
    console.print(Panel(
        Text("LifeOS v0.3 — Personal AI Operating System", justify="center"),
        style="bold blue"
    ))
    console.print(
        "[dim]Commands: 'exit' quit | '+'/'-' feedback | "
        "'scores' trust scores | 'log health' log today's health data[/dim]\n"
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
    """Interactive health logging wizard."""
    console.print("\n[bold cyan]Health Log — Today[/bold cyan]")
    console.print("[dim]Press Enter to skip any field.[/dim]\n")

    data = {}

    fields = [
        ("sleep_hours",   "Sleep hours (e.g. 7.5):",   float),
        ("sleep_quality", "Sleep quality 1-10:",        int),
        ("mood",          "Mood 1-10:",                 int),
        ("energy",        "Energy 1-10:",               int),
        ("water_ml",      "Water intake (ml):",         int),
        ("exercise_min",  "Exercise (minutes):",        int),
        ("notes",         "Any notes (free text):",     str),
    ]

    for key, label, cast in fields:
        val = console.input(f"  {label} ").strip()
        if val:
            try:
                data[key] = cast(val)
            except ValueError:
                console.print(f"  [red]Invalid input, skipping {key}[/red]")

    if data:
        result = health.log(**data)
        console.print(f"\n[green]✓ Health data logged for today.[/green]")
        console.print(f"[dim]{result}[/dim]\n")
    else:
        console.print("[yellow]No data entered.[/yellow]\n")


def main():
    print_banner()
    console.print("[dim]Starting LifeOS...[/dim]")
    orchestrator = Orchestrator()
    console.print("[green]✓ LifeOS v0.3 online. Tools active.[/green]\n")

    last_matches = []

    while True:
        try:
            user_input = console.input("[bold cyan]You → [/bold cyan]").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("\n[yellow]LifeOS shutting down. Goodbye.[/yellow]")
                break

            if user_input.lower() == "scores":
                console.print(orchestrator.get_trust_scores())
                continue

            if user_input.lower() == "log health":
                log_health()
                continue

            if user_input == "+" and last_matches:
                dept = last_matches[0]["name"]
                orchestrator.record_feedback(dept, +1, "User gave reward")
                console.print(f"[green]✓ Reward recorded for {dept}[/green]")
                continue

            if user_input == "-" and last_matches:
                dept = last_matches[0]["name"]
                orchestrator.record_feedback(dept, -1, "User gave penalty")
                console.print(f"[red]✗ Penalty recorded for {dept}[/red]")
                continue

            console.print("\n[dim]Fetching data and routing...[/dim]")
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