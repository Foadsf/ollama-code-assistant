"""CLI entry point for OCA."""

import click
from typing import Optional
from .core.session import SessionManager


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


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()