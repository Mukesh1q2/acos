"""
CLI Interface for ACOS Runtime.

Provides an interactive command-line interface for:
- Processing queries
- Inspecting threads and sessions
- Managing memory
- Checking system status
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn

from acos.kernel import CognitiveKernel
from acos.schemas.models import QueryRequest, ThreadType, ThreadPriority


console = Console()


def run_async(coro):
    """Run an async coroutine in a synchronous context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're already in an async context
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


async def _process_query(kernel: CognitiveKernel, query: str, thread_types: list[ThreadType] | None = None):
    """Process a query through the kernel."""
    request = QueryRequest(query=query, thread_types=thread_types)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("ACOS processing query...", total=None)

        response = await kernel.process_query(request)

        progress.update(task, completed=True, total=1)

    return response


async def _interactive_mode(kernel: CognitiveKernel):
    """Run an interactive REPL."""
    console.print(Panel(
        "[bold green]ACOS Runtime v0.1[/bold green]\n"
        "Avadhan Cognitive Operating System\n\n"
        "Commands:\n"
        "  [bold]query <text>[/bold]  - Process a query through ACOS\n"
        "  [bold]stats[/bold]         - Show system statistics\n"
        "  [bold]sessions[/bold]      - List recent sessions\n"
        "  [bold]memory <thread_id>[/bold] - Show thread memory\n"
        "  [bold]models[/bold]        - List available LLM models\n"
        "  [bold]help[/bold]          - Show this help\n"
        "  [bold]quit[/bold]          - Exit\n\n"
        "Or just type a query directly to process it.",
        title="ACOS Interactive Mode",
        border_style="green",
    ))

    while True:
        try:
            user_input = console.input("[bold cyan]acos>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.lower() == "help":
            console.print(Panel(
                "Commands:\n"
                "  query <text>   - Process a query\n"
                "  stats          - System statistics\n"
                "  sessions       - List sessions\n"
                "  memory <tid>   - Show thread memory\n"
                "  models         - List LLM models\n"
                "  quit           - Exit",
                title="Help",
                border_style="blue",
            ))
            continue

        if user_input.lower() == "stats":
            stats = await kernel.get_stats()
            table = Table(title="ACOS Runtime Stats")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Initialized", str(stats.get("initialized", False)))
            table.add_row("Active Threads", str(stats.get("active_threads", 0)))
            table.add_row("Total Sessions", str(stats.get("total_sessions", 0)))
            table.add_row("Available Models", ", ".join(stats.get("available_models", [])))

            memory = stats.get("memory", {})
            table.add_row("Memory Records", str(memory.get("total_records", 0)))
            table.add_row("  Working", str(memory.get("working", 0)))
            table.add_row("  Episodic", str(memory.get("episodic", 0)))
            table.add_row("  Semantic", str(memory.get("semantic", 0)))

            console.print(table)
            continue

        if user_input.lower() == "sessions":
            sessions = await kernel.list_sessions()
            if not sessions:
                console.print("[dim]No sessions yet.[/dim]")
            else:
                table = Table(title="Sessions")
                table.add_column("ID", style="cyan")
                table.add_column("Query", style="white")
                table.add_column("Threads", style="green")
                table.add_column("Created", style="dim")

                for s in sessions[-10:]:
                    table.add_row(
                        s.id[:12],
                        s.query[:50],
                        str(len(s.threads)),
                        s.created_at.strftime("%H:%M:%S"),
                    )
                console.print(table)
            continue

        if user_input.lower().startswith("memory "):
            thread_id = user_input[7:].strip()
            memories = await kernel._memory.retrieve(thread_id)
            if not memories:
                console.print(f"[dim]No memories found for thread {thread_id[:12]}[/dim]")
            else:
                table = Table(title=f"Memory for Thread {thread_id[:12]}")
                table.add_column("Type", style="cyan")
                table.add_column("Content", style="white")
                table.add_column("Importance", style="green")

                for m in memories[:20]:
                    table.add_row(
                        m.memory_type.value,
                        m.content[:80],
                        f"{m.importance:.2f}",
                    )
                console.print(table)
            continue

        if user_input.lower() == "models":
            models = await kernel._router.get_available_models()
            table = Table(title="Available Models")
            table.add_column("Name", style="cyan")
            table.add_column("Provider", style="green")
            table.add_column("Available", style="yellow")
            table.add_column("Context Window", style="dim")

            for m in models:
                table.add_row(
                    m.name,
                    m.provider,
                    "Yes" if m.is_available else "No",
                    str(m.context_window),
                )
            console.print(table)
            continue

        if user_input.lower().startswith("query "):
            query = user_input[6:].strip()
        else:
            query = user_input

        # Process the query
        try:
            response = await _process_query(kernel, query)
            _display_response(response)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


def _display_response(response):
    """Display a query response in a formatted way."""
    # Final synthesis
    console.print(Panel(
        Markdown(response.final_synthesis),
        title="[bold green]ACOS Synthesis[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    # Thread summary
    table = Table(title="Reasoning Threads")
    table.add_column("Type", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Agent", style="yellow")
    table.add_column("Messages", style="dim")

    for thread in response.threads:
        table.add_row(
            thread.type.value,
            thread.status.value,
            thread.agent_type.value if thread.agent_type else "N/A",
            str(len(thread.messages)),
        )
    console.print(table)

    # Verification summary
    if response.verifications:
        passed = sum(1 for v in response.verifications if v.passed)
        total = len(response.verifications)
        avg_conf = sum(v.confidence_score for v in response.verifications) / total
        console.print(f"\n[bold]Verification:[/bold] {passed}/{total} passed, avg confidence: {avg_conf:.2f}")

    # Reflection summary
    if response.reflections:
        avg_quality = sum(r.quality_score for r in response.reflections) / len(response.reflections)
        total_issues = sum(len(r.issues_found) for r in response.reflections)
        console.print(f"[bold]Reflection:[/bold] avg quality: {avg_quality:.2f}, total issues: {total_issues}")

    # Timing
    console.print(f"[dim]Total time: {response.total_time_ms:.1f}ms[/dim]")


@click.group()
@click.version_option(version="0.1.0")
def main():
    """ACOS Runtime v0.1 - Avadhan Cognitive Operating System"""
    pass


@main.command()
@click.argument("query")
@click.option("--threads", "-t", multiple=True, type=click.Choice(["analysis", "planning", "memory", "verification", "creative"]), help="Thread types to spawn")
@click.option("--db", default=None, help="Database path")
def query(query: str, threads: tuple, db: str | None):
    """Process a query through the ACOS pipeline."""
    async def _run():
        kernel = CognitiveKernel(db_path=db)
        await kernel.initialize()
        try:
            thread_types = [ThreadType(t) for t in threads] if threads else None
            response = await _process_query(kernel, query, thread_types)
            _display_response(response)
        finally:
            await kernel.shutdown()

    asyncio.run(_run())


@main.command()
@click.option("--db", default=None, help="Database path")
def interactive(db: str | None):
    """Start interactive ACOS REPL."""
    async def _run():
        kernel = CognitiveKernel(db_path=db)
        await kernel.initialize()
        try:
            await _interactive_mode(kernel)
        finally:
            await kernel.shutdown()

    asyncio.run(_run())


@main.command()
@click.option("--db", default=None, help="Database path")
def stats(db: str | None):
    """Show ACOS runtime statistics."""
    async def _run():
        kernel = CognitiveKernel(db_path=db)
        await kernel.initialize()
        try:
            s = await kernel.get_stats()
            table = Table(title="ACOS Runtime Stats")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Initialized", str(s.get("initialized")))
            table.add_row("Active Threads", str(s.get("active_threads", 0)))
            table.add_row("Total Sessions", str(s.get("total_sessions", 0)))
            table.add_row("Available Models", ", ".join(s.get("available_models", [])))

            mem = s.get("memory", {})
            table.add_row("Total Memory Records", str(mem.get("total_records", 0)))
            table.add_row("  Working", str(mem.get("working", 0)))
            table.add_row("  Episodic", str(mem.get("episodic", 0)))
            table.add_row("  Semantic", str(mem.get("semantic", 0)))

            console.print(table)
        finally:
            await kernel.shutdown()

    asyncio.run(_run())


@main.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, type=int, help="Port to bind")
@click.option("--db", default=None, help="Database path")
def serve(host: str, port: int, db: str | None):
    """Start the ACOS FastAPI server."""
    import uvicorn
    from acos.api.server import app

    console.print(f"[bold green]Starting ACOS Runtime server on {host}:{port}[/bold green]")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
