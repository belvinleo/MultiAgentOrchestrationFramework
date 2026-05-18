"""
main.py
-------
Run this to start LifeOS.
This is your command-line interface for now.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from core.orchestrator import Orchestrator

console = Console()


def print_banner():
    console.print(Panel(
        Text("LifeOS v0.1 — Your Personal AI Operating System", justify="center"),
        style="bold blue"
    ))
    console.print("[dim]Type your message and press Enter. Type 'exit' to quit.[/dim]\n")


def main():
    print_banner()
    orchestrator = Orchestrator()
    console.print("[green]✓ Orchestrator online. Constitution loaded.[/green]\n")

    while True:
        try:
            user_input = console.input("[bold cyan]You → [/bold cyan]").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "bye"]:
                console.print("\n[yellow]LifeOS shutting down. Goodbye.[/yellow]")
                break

            console.print("\n[dim]Thinking...[/dim]")
            response = orchestrator.process(user_input)

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