"""NexForge v6.0 CLI."""
from __future__ import annotations
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(name="nexforge",
                  help="NexForge v6.0 — AI-Native CPS Engineering Framework",
                  no_args_is_help=True)
console = Console()


def _compile_or_exit(yaml_path):
    from .compiler.pipeline import compile_file, CompilationError
    try: return compile_file(yaml_path)
    except CompilationError as e:
        console.print(f"[red]{e}[/]"); raise typer.Exit(1)


@app.command()
def compile(yaml_path: Path = typer.Argument(..., exists=True),
            output: Path = typer.Option(None, "--output", "-o"),
            caps: Path = typer.Option(None, "--capabilities")):
    """Full compilation pipeline."""
    report = _compile_or_exit(yaml_path)
    ir = report.ir
    console.print(Panel.fit(
        f"[bold green]✅ Compiled:[/] {ir.metadata.domain_name} v{ir.metadata.version}\n"
        f"IR hash: [cyan]{ir.content_hash()}[/]\n"
        f"Schedulable: {'✅' if ir.timing.schedulable else '❌'}  U={ir.timing.utilization:.3f}\n"
        f"Hardware OK: {'✅' if report.hardware_ok else '❌'}  "
        f"Budget OK: {'✅' if report.budget_ok else '❌'}",
        border_style="green"))
    if output: output.write_text(ir.to_json(), encoding="utf-8")
    if caps and report.capabilities_md:
        caps.parent.mkdir(parents=True, exist_ok=True)
        caps.write_text(report.capabilities_md, encoding="utf-8")
        console.print(f"[dim]Capabilities → {caps}[/]")


@app.command()
def simulate(yaml_path: Path = typer.Argument(..., exists=True),
             duration: float = typer.Option(30.0, "-d"),
             scenario: str = typer.Option(None, "--scenario", "-s"),
             record: Path = typer.Option(None, "--record")):
    """Run simulator with optional scenario and session recording."""
    report = _compile_or_exit(yaml_path)
    from .backends.python_sim import SimulatorBackend
    from .scenarios.base import LIBRARY
    from .replay.recorder import Recorder

    sim = SimulatorBackend(report.ir, duration_s=duration, realtime=True)
    if scenario:
        sc = LIBRARY.get(scenario)
        for d in sc.disturbances(duration):
            sim.schedule_disturbance(d.at_seconds, {d.channel: d.value})
        console.print(f"[yellow]Scenario '{sc.name}': {sc.description}[/]")

    recorder = None
    if record:
        recorder = Recorder(name=yaml_path.stem, ir_hash=report.ir.content_hash())
        sim.kernel.on_telemetry(recorder.on_telemetry)

    history = sim.run()
    console.print(f"[green]✅ {len(history)} frames[/]")
    if recorder:
        session = recorder.to_session()
        session.save(record)
        console.print(f"[dim]Session → {record}[/]")


@app.command()
def replay(session_path: Path = typer.Argument(..., exists=True),
           yaml_path: Path = typer.Option(..., "--domain", exists=True)):
    """Replay a recorded session deterministically."""
    report = _compile_or_exit(yaml_path)
    from .replay.player import replay_session
    result = replay_session(report.ir, session_path)
    color = "green" if result.ok else "red"
    console.print(Panel.fit(
        f"[{color}]Replay: {result.summary}[/]\n"
        f"Total events: {result.total_events}",
        border_style=color))


@app.command(name="list-scenarios")
def list_scenarios(domain: str = typer.Option(None, "--domain", "-d")):
    """List available fault scenarios."""
    from .scenarios.base import LIBRARY
    scs = LIBRARY.applicable_to(domain) if domain else LIBRARY.list()
    for s in scs:
        console.print(f"  • [cyan]{s.name}[/] — {s.description}")


@app.command(name="ai-contract")
def ai_contract(out: Path = typer.Option(Path("docs/AI_CONTRACT.md"), "-o")):
    """Generate the AI Contract document."""
    from .compiler.ai_contract import CONTRACT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(CONTRACT.to_markdown(), encoding="utf-8")
    console.print(f"[green]AI Contract → {out}[/]")


@app.command(name="list-domains")
def list_domains(dir_: Path = typer.Option(Path("domains"), "--dir", exists=True)):
    """List bundled YAML domains."""
    from .compiler.pipeline import compile_file, CompilationError
    for p in sorted(dir_.glob("*.yaml")):
        try:
            report = compile_file(p, generate_caps=False)
            ir = report.ir
            console.print(
                f"  • [cyan]{ir.metadata.domain_name}[/] v{ir.metadata.version}  "
                f"[{len(ir.sensors)} sensors, {len(ir.safety.contracts)} contracts, "
                f"hash [dim]{ir.content_hash()}[/]]")
        except CompilationError:
            console.print(f"  • [red]{p.name}[/] — invalid")


@app.command()
def plugins():
    """List discovered plugins."""
    from .plugins.registry import PluginRegistry
    reg = PluginRegistry()
    n1 = reg.discover_entrypoints()
    n2 = reg.discover_directory(Path("./plugins"))
    console.print(f"Discovered {n1 + n2} plugins: {reg.summary()}")


if __name__ == "__main__":
    app()
