"""CLI entry point for OCA."""

import click
import re
import os
import subprocess
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from .core.session import SessionManager, SessionError
from .core.self_improver import SelfImprover
from .utils.git_safe import GitSafeError # New import


def _parse_code_from_response(response: str) -> Optional[str]:
    """Extracts the first code block from a markdown-formatted response."""
    pattern = re.compile(r"```(?:\w+)?\n(.*?)\n```", re.DOTALL)
    match = pattern.search(response)
    if match:
        return match.group(1).strip()
    return None


@click.group()
@click.version_option(version='0.1.0', package_name='ollama-code-assistant')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--model', help='Specify Ollama model to use')
@click.option('--branch', help='Custom branch name')
@click.option('--no-commit', is_flag=True, help='Disable auto-commit')
@click.option('--dry-run', is_flag=True, help='Show what would be done without doing it')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, model: Optional[str], 
        branch: Optional[str], no_commit: bool, dry_run: bool) -> None:
    """Ollama Code Assistant - AI-powered coding with Git isolation."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['model'] = model
    ctx.obj['branch'] = branch
    ctx.obj['no_commit'] = no_commit
    ctx.obj['dry_run'] = dry_run


@cli.command()
@click.option('--model', help='Specify default Ollama model')
@click.option('--config', help='Path to config file')
@click.pass_context
def init(ctx: click.Context, model: Optional[str], config: Optional[str]) -> None:
    """Initialize OCA in a project."""
    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        session_manager.init_project(model=model, config_path=config)
        click.echo("✓ OCA initialized successfully")
    except Exception as e:
        click.echo(f"✗ Error initializing OCA: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('prompt')
@click.option('--file', help='Specific file to explain')
@click.pass_context
def explain(ctx: click.Context, prompt: str, file: Optional[str]) -> None:
    """Get explanations about code."""
    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        model=ctx.obj['model'],
        branch=ctx.obj['branch'],
        auto_commit=not ctx.obj['no_commit'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        if file:
            full_file_path = Path(file)
            if not full_file_path.is_absolute():
                full_file_path = Path.cwd() / full_file_path
            if not full_file_path.exists():
                click.echo(f"✗ Error: File not found: {file}", err=True)
                raise click.Abort()
            if not full_file_path.is_file():
                click.echo(f"✗ Error: Path is not a file: {file}", err=True)
                raise click.Abort()

        with session_manager.create_session() as session:
            result = session.explain(prompt, target_file=file)
            click.echo(result)
    except SessionError as e:
        click.echo(f"✗ Error during session: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ An unexpected error occurred: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('prompt', required=False)
@click.option('--error', help='Specific error message to fix')
@click.option('--file', help='Specific file to fix')
@click.pass_context
def fix(ctx: click.Context, prompt: Optional[str], error: Optional[str], file: Optional[str]) -> None:
    """Fix bugs or issues in code."""
    if not prompt and not error:
        click.echo("✗ Error: Either PROMPT or --error must be provided.", err=True)
        raise click.Abort()

    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        model=ctx.obj['model'],
        branch=ctx.obj['branch'],
        auto_commit=not ctx.obj['no_commit'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        if file:
            full_file_path = Path(file)
            if not full_file_path.is_absolute():
                full_file_path = Path.cwd() / full_file_path
            if not full_file_path.exists():
                click.echo(f"✗ Error: File not found: {file}", err=True)
                raise click.Abort()
            if not full_file_path.is_file():
                click.echo(f"✗ Error: Path is not a file: {file}", err=True)
                raise click.Abort()

        with session_manager.create_session() as session:
            result = session.fix(prompt or "", error_message=error, target_file=file) # Pass empty string if prompt is None
            click.echo(result)
    except SessionError as e:
        click.echo(f"✗ Error during session: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ An unexpected error occurred: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('prompt', required=False)
@click.option('--pattern', help='Specific pattern to refactor')
@click.option('--file', help='Specific file to refactor')
@click.pass_context
def refactor(ctx: click.Context, prompt: Optional[str], pattern: Optional[str], file: Optional[str]) -> None:
    """Refactor code."""
    if not prompt and not pattern:
        click.echo("✗ Error: Either PROMPT or --pattern must be provided.", err=True)
        raise click.Abort()

    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        model=ctx.obj['model'],
        branch=ctx.obj['branch'],
        auto_commit=not ctx.obj['no_commit'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        if file:
            full_file_path = Path(file)
            if not full_file_path.is_absolute():
                full_file_path = Path.cwd() / full_file_path
            if not full_file_path.exists():
                click.echo(f"✗ Error: File not found: {file}", err=True)
                raise click.Abort()
            if not full_file_path.is_file():
                click.echo(f"✗ Error: Path is not a file: {file}", err=True)
                raise click.Abort()

        with session_manager.create_session() as session:
            result = session.refactor(prompt or "", pattern=pattern, target_file=file) # Pass empty string if prompt is None
            click.echo(result)
    except SessionError as e:
        click.echo(f"✗ Error during session: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ An unexpected error occurred: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('prompt')
@click.option('--coverage', is_flag=True, help='Generate tests with coverage')
@click.option('--style', help='Test style (pytest, unittest, etc.)')
@click.option('--file', help='Specific file/module to test')
@click.pass_context
def test(ctx: click.Context, prompt: str, coverage: bool, style: Optional[str], file: Optional[str]) -> None:
    """Generate tests for code."""
    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        model=ctx.obj['model'],
        branch=ctx.obj['branch'],
        auto_commit=not ctx.obj['no_commit'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        if file:
            full_file_path = Path(file)
            if not full_file_path.is_absolute():
                full_file_path = Path.cwd() / full_file_path
            if not full_file_path.exists():
                click.echo(f"✗ Error: File not found: {file}", err=True)
                raise click.Abort()
            # For test, it might be a directory, so no is_file() check here

        with session_manager.create_session() as session:
            result = session.generate_tests(prompt, coverage=coverage, style=style, target_file=file)
            click.echo(result)
    except SessionError as e:
        click.echo(f"✗ Error during session: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ An unexpected error occurred: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('message', required=False)
@click.option('--type', 'commit_type', help='Commit type (feat, fix, docs, etc.)')
@click.pass_context
def commit(ctx: click.Context, message: Optional[str], commit_type: Optional[str]) -> None:
    """Create descriptive commits."""
    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        model=ctx.obj['model'],
        branch=ctx.obj['branch'],
        auto_commit=not ctx.obj['no_commit'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        with session_manager.create_session() as session:
            result = session.create_commit(message=message, commit_type=commit_type)
            click.echo(result)
    except SessionError as e:
        click.echo(f"✗ Error during session: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ An unexpected error occurred: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('prompt')
@click.option('--regex', help='Regular expression pattern to search for')
@click.option('--type', 'search_type', help='Search type (comment, function, class, etc.)')
@click.pass_context
def search(ctx: click.Context, prompt: str, regex: Optional[str], search_type: Optional[str]) -> None:
    """Search codebase."""
    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        model=ctx.obj['model'],
        branch=ctx.obj['branch'],
        auto_commit=not ctx.obj['no_commit'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        with session_manager.create_session() as session:
            result = session.search_code(prompt, regex=regex, search_type=search_type)
            click.echo(result)
    except SessionError as e:
        click.echo(f"✗ Error during session: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ An unexpected error occurred: {e}", err=True)
        raise click.Abort()


# TODO: Unit tests for this command are in tests/unit/test_self_improve.py
# due to a persistent issue with modifying tests/unit/test_cli.py.
# This separation is likely a better architecture anyway.
@cli.command("self-improve")
@click.option('--auto', is_flag=True, help="Apply the highest priority safe improvement automatically.")
@click.option('--type', 'improvement_type', help="Focus on a specific improvement type (e.g., documentation).")
@click.option('--dry-run', is_flag=True, help="Show what would be improved without doing it.")
@click.pass_context
def self_improve(ctx: click.Context, auto: bool, improvement_type: Optional[str], dry_run: bool) -> None:
    """Analyzes and improves OCA's own codebase."""
    try:
        improver = SelfImprover(
            root_path=Path.cwd(),
            model_name=ctx.obj.get('model'),
            verbose=ctx.obj.get('verbose', False)
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


@cli.command()
@click.pass_context
def test_ollama(ctx: click.Context) -> None:
    """Test connection to Ollama."""
    from .core.ollama import OllamaClient
    
    model = ctx.obj.get('model')
    client = OllamaClient(model=model)
    
    console = Console()
    console.print("🔍 Testing Ollama connection...")
    result = client.test_connection()
    
    if result.get("connected"):
        console.print(f"✅ Successfully connected to Ollama!")
        console.print(f"📍 API URL: {result.get('api_url')}")
        if result.get('response_time'):
            console.print(f"⏱️  Response time: {result.get('response_time'):.2f}s")
        if result.get('models'):
            console.print(f"🤖 Available models: {', '.join(result.get('models'))}")
        
        if ctx.obj.get('model') and result.get('models') and ctx.obj.get('model') not in result.get('models'):
            console.print(f"⚠️  Warning: Requested model '{ctx.obj.get('model')}' not found!")
            console.print(f"💡 Try one of: {', '.join(result.get('models'))}")
    else:
        console.print(f"❌ Failed to connect to Ollama")
        console.print(f"📍 API URL: {result.get('api_url')}")
        console.print(f"🚨 Error: {result.get('error')}")
        
        console.print("\n💡 Troubleshooting tips:")
        console.print("1. Make sure Ollama is running: ollama serve")
        console.print("2. Check if the API URL is correct")
        console.print("3. Verify firewall/network settings")
        console.print("4. Try: curl http://localhost:11434/api/tags")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()