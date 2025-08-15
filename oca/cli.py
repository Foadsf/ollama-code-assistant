"""CLI entry point for OCA."""

import click
import re
import os
import subprocess
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .core.session import SessionManager
from .core.self_analysis import SelfAnalyzer
from .core.self_modifier import SelfModifier
from .core.ollama import OllamaClient
from .core.editor import CodeEditor


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
        with session_manager.create_session() as session:
            result = session.explain(prompt, target_file=file)
            click.echo(result)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('prompt')
@click.option('--error', help='Specific error message to fix')
@click.option('--file', help='Specific file to fix')
@click.pass_context
def fix(ctx: click.Context, prompt: str, error: Optional[str], file: Optional[str]) -> None:
    """Fix bugs or issues in code."""
    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        model=ctx.obj['model'],
        branch=ctx.obj['branch'],
        auto_commit=not ctx.obj['no_commit'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        with session_manager.create_session() as session:
            result = session.fix(prompt, error_message=error, target_file=file)
            click.echo(result)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('prompt')
@click.option('--pattern', help='Specific pattern to refactor')
@click.option('--file', help='Specific file to refactor')
@click.pass_context
def refactor(ctx: click.Context, prompt: str, pattern: Optional[str], file: Optional[str]) -> None:
    """Refactor code."""
    session_manager = SessionManager(
        verbose=ctx.obj['verbose'],
        model=ctx.obj['model'],
        branch=ctx.obj['branch'],
        auto_commit=not ctx.obj['no_commit'],
        dry_run=ctx.obj['dry_run']
    )
    
    try:
        with session_manager.create_session() as session:
            result = session.refactor(prompt, pattern=pattern, target_file=file)
            click.echo(result)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
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
        with session_manager.create_session() as session:
            result = session.generate_tests(prompt, coverage=coverage, style=style, target_file=file)
            click.echo(result)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
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
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
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
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


# TODO: Unit tests for this command are in tests/unit/test_self_improve.py
# due to a persistent issue with modifying tests/unit/test_cli.py.
# This separation is likely a better architecture anyway.
@cli.command("self-improve")
@click.option('--auto', is_flag=True, help="Apply the highest priority safe improvement automatically.")
@click.option('--type', 'improvement_type', help="Focus on a specific improvement type (e.g., documentation).")
@click.option('--dry-run', is_flag=True, help="Show what would be improved without doing it.")
@click.option('--plain-output', is_flag=True, hidden=True) # For testing
@click.pass_context
def self_improve(ctx: click.Context, auto: bool, improvement_type: Optional[str], dry_run: bool, plain_output: bool) -> None:
    """Analyzes and improves OCA's own codebase."""
    console = Console()
    console.print("🤖 [bold green]OCA Self-Improvement Mode[/bold green] 🤖")

    try:
        # Assuming oca is run from the root of its own repository
        oca_root_path = Path.cwd()

        analyzer = SelfAnalyzer(root_path=oca_root_path)

        console.print("\n🔍 Analyzing codebase for improvement opportunities...")
        opportunities = analyzer.identify_improvement_opportunities()

        if not opportunities:
            console.print("\n✅ No improvement opportunities found. Great job!")
            return

        if plain_output:
            console.print(f"Found {len(opportunities)} improvement opportunities:")
            for i, opp in enumerate(opportunities[:10]):
                console.print(f"{i+1}: {opp['type']} - {opp['description']} in {opp['file_path']}:{opp['line_number']}")
        else:
            console.print(f"\nFound [bold yellow]{len(opportunities)}[/bold yellow] improvement opportunities:")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim", width=4)
            table.add_column("Type", width=15)
            table.add_column("Description")
            table.add_column("File", style="cyan")
            table.add_column("Line", style="yellow")
            for i, opp in enumerate(opportunities[:10]):
                table.add_row(str(i + 1), opp['type'], opp['description'], opp['file_path'], str(opp['line_number']))
            console.print(table)

        if dry_run or not auto:
            if dry_run:
                console.print("\n--dry-run enabled. No changes will be made.")
            if not auto:
                console.print("\n--auto not specified. Run with --auto to apply the first safe improvement.")
            return

        # --- Self-Modification Workflow ---
        if improvement_type:
            opportunities = [opp for opp in opportunities if opp['type'] == improvement_type]

        if not opportunities:
            console.print(f"\nNo opportunities of type '{improvement_type}' found.")
            return

        target_opp = opportunities[0]
        console.print(f"\n🤖 Automatically applying first safe improvement:")
        console.print(f"   [yellow]{target_opp['description']}[/yellow] in [cyan]{target_opp['file_path']}:{target_opp['line_number']}[/cyan]")

        modifier = SelfModifier(repo_path=oca_root_path)
        editor = CodeEditor(root_path=oca_root_path)
        ollama = OllamaClient(model=ctx.obj['model'] or 'codellama')
        original_branch = ""
        branch_name = ""

        try:
            original_branch = modifier.git.get_current_branch()
            branch_name = modifier.create_improvement_branch(target_opp)
            console.print(f"✅ Created and checked out new branch: [bold blue]{branch_name}[/bold blue]")

            console.print("🧠 Generating docstring with Ollama...")
            file_path = oca_root_path / target_opp['file_path']
            file_content = file_path.read_text()
            prompt = f"{target_opp['suggested_fix']}\n\nHere is the full content of the file `{target_opp['file_path']}`. Please return the complete, modified file content in a single markdown code block.\n\n```python\n{file_content}\n```"
            new_content_response = ollama.generate(prompt)
            new_content = _parse_code_from_response(new_content_response)

            if not new_content:
                raise Exception("Failed to parse new content from Ollama response.")

            console.print(f"✍️ Applying changes to [cyan]{target_opp['file_path']}[/cyan]...")
            editor.apply_changes(Path(target_opp['file_path']), new_content)

            console.print("🛡️ Running test suite to validate changes...")
            pytest_path = Path(os.path.dirname(os.path.abspath(__file__))).parent / "venv" / "bin" / "pytest"
            result = subprocess.run([str(pytest_path)], cwd=oca_root_path, capture_output=True, text=True)

            if result.returncode == 0:
                console.print("✅ [bold green]All tests passed![/bold green]")
                commit_message = f"docs: {target_opp['description']}"
                modifier.git.commit(commit_message, add_all=True)
                console.print(f"📝 Committed changes with message: \"{commit_message}\"")
                console.print("\n🎉 [bold green]Self-improvement successful![/bold green]")
                console.print(f"Changes are on branch [bold blue]{branch_name}[/bold blue]. Please review and merge.")
                modifier.git._run_git(['checkout', original_branch])
            else:
                console.print("❌ [bold red]Tests failed after applying changes.[/bold red]")
                console.print("--- TEST OUTPUT ---")
                console.print(result.stdout)
                console.print(result.stderr)
                console.print("⏪ Rolling back changes...")
                modifier.git._run_git(['checkout', original_branch])
                modifier.git._run_git(['branch', '-D', branch_name])
                console.print("✅ Rollback complete.")

        except Exception as e:
            console.print(f"[bold red]An error occurred during self-modification: {e}[/bold red]")
            if original_branch and branch_name:
                try:
                    modifier.git._run_git(['checkout', original_branch])
                    modifier.git._run_git(['branch', '-D', branch_name])
                except Exception as rollback_e:
                    console.print(f"[bold red]Rollback also failed: {rollback_e}[/bold red]")

    except Exception as e:
        console.print(f"[bold red]An error occurred during self-improvement: {e}[/bold red]")


@cli.command()
@click.pass_context
def test_ollama(ctx: click.Context) -> None:
    """Test connection to Ollama."""
    from .core.ollama import OllamaClient
    
    model = ctx.obj.get('model') or 'codellama'
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