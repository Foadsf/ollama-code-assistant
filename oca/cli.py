"""CLI entry point for OCA."""

import click
from typing import Optional
from .core.session import SessionManager


@click.group()
@click.version_option()
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


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()