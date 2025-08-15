"""Alternative CLI entry point for self-improvement commands."""

import click
from pathlib import Path
from rich.console import Console

# Add the parent directory to the path so we can import oca modules
# This is necessary when running this file as a script.
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from oca.core.self_improver import SelfImprover

@click.command()
@click.option('--auto', is_flag=True, help="Apply the highest priority safe improvement automatically.")
@click.option('--type', 'improvement_type', help="Focus on a specific improvement type (e.g., documentation).", default=None)
@click.option('--dry-run', is_flag=True, help="Show what would be improved without doing it.")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--model', help='Specify Ollama model to use', default=None)
def self_improve(auto: bool, improvement_type: str, dry_run: bool, verbose: bool, model: str):
    """Analyzes and improves OCA's own codebase."""
    try:
        improver = SelfImprover(
            root_path=Path.cwd(),
            model_name=model,
            verbose=verbose
        )
        improver.run_improvement_cycle(
            auto=auto,
            improvement_type=improvement_type,
            dry_run=dry_run
        )
    except Exception as e:
        console = Console()
        console.print(f"[bold red]An error occurred during self-improvement: {e}[/bold red]")
        raise click.Abort()

if __name__ == '__main__':
    self_improve()
