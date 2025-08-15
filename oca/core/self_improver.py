from pathlib import Path
from typing import Optional

from rich.console import Console

from .self_analysis import SelfAnalyzer
from .self_modifier import SelfModifier
from .improvement_ui import ImprovementUI
from .ollama import OllamaClient
from .editor import CodeEditor

class SelfImprover:
    """Orchestrates the complete self-improvement workflow."""

    def __init__(self, root_path: Path, model_name: Optional[str] = None, verbose: bool = False):
        self.root_path = root_path
        self.console = Console()
        self.analyzer = SelfAnalyzer(self.root_path)
        ollama = OllamaClient(model=model_name or 'codellama')
        editor = CodeEditor(root_path=self.root_path)
        self.modifier = SelfModifier(repo_path=self.root_path, ollama=ollama, editor=editor)
        self.ui = ImprovementUI()

    def run_improvement_cycle(self, auto: bool, improvement_type: Optional[str], dry_run: bool):
        """Main entry point for a self-improvement cycle."""
        self.console.print("🤖 [bold green]OCA Self-Improvement Mode[/bold green] 🤖")

        try:
            self.console.print("\n🔍 Analyzing codebase for improvement opportunities...")
            opportunities = self.analyzer.identify_improvement_opportunities()

            if improvement_type:
                opportunities = [opp for opp in opportunities if opp['type'] == improvement_type]

            selected_opportunities = self.ui.present_opportunities(opportunities)

            if not selected_opportunities:
                return

            if dry_run:
                self.console.print("\n--dry-run enabled. No changes will be made.")
                return

            if not auto and selected_opportunities:
                 # In interactive mode, the opportunities are already selected by the UI
                 pass
            elif auto and opportunities:
                selected_opportunities = [opportunities[0]]
            else: # Not auto and no selection from UI
                return

            for opp in selected_opportunities:
                self.console.print(f"\n🤖 Applying improvement [bold yellow]'{opp['description']}'[/bold yellow]...")
                result = self.modifier.apply_self_improvement(opp)

                if not result['success']:
                    self.console.print(f"\n[bold red]Self-improvement failed: {result['reason']}[/bold red]")

        except Exception as e:
            self.console.print(f"[bold red]An error occurred during self-improvement cycle: {e}[/bold red]")
