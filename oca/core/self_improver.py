from pathlib import Path
from typing import Optional

from rich.console import Console

from .self_analysis import SelfAnalyzer
from .self_modifier import SelfModifier
from .improvement_ui import ImprovementUI
from .ollama import OllamaClient
from .editor import CodeEditor
from .memory import MemorySystem

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
        self.memory = MemorySystem(memory_file=self.root_path / ".oca" / "memory.jsonl")

    def run_improvement_cycle(self, auto: bool, improvement_type: Optional[str], dry_run: bool):
        """Main entry point for a self-improvement cycle."""
        self.console.print("🤖 [bold green]OCA Self-Improvement Mode[/bold green] 🤖")

        try:
            self.console.print("\n🔍 Analyzing codebase for improvement opportunities...")
            opportunities = self.analyzer.identify_improvement_opportunities()

            # Prioritize opportunities based on past success
            self.console.print("💡 Analyzing past performance to prioritize tasks...")
            success_patterns = self.memory.get_success_patterns()

            def get_priority_score(opportunity):
                imp_type = opportunity['type']
                # Default to 50% success rate if no history exists
                return success_patterns.get(imp_type, {}).get('success_rate', 50.0)

            opportunities.sort(key=get_priority_score, reverse=True)

            if improvement_type:
                opportunities = [opp for opp in opportunities if opp['type'] == improvement_type]

            if not opportunities:
                self.console.print("✅ No improvement opportunities found.")
                return

            if auto:
                selected_opportunities = [opportunities[0]]
                self.console.print(f"🤖 Auto-selecting highest priority task: [bold yellow]'{opportunities[0]['description']}'[/bold yellow]")
            else:
                selected_opportunities = self.ui.present_opportunities(opportunities)

            if not selected_opportunities:
                self.console.print("No improvements selected. Exiting.")
                return

            if dry_run:
                self.console.print("\n--dry-run enabled. Would apply the following changes:")
                self.ui.present_opportunities(selected_opportunities, is_dry_run=True)
                return

            for opp in selected_opportunities:
                self.console.print(f"\n🤖 Applying improvement [bold yellow]'{opp['description']}'[/bold yellow]...")

                import time
                start_time = time.time()

                result = self.modifier.apply_self_improvement(opp)

                execution_time = time.time() - start_time

                # Record the attempt in memory
                self.memory.record_improvement_attempt(opp, result, execution_time)

                if not result['success']:
                    self.console.print(f"\n[bold red]Self-improvement failed: {result['reason']}[/bold red]")

        except Exception as e:
            self.console.print(f"[bold red]An error occurred during self-improvement cycle: {e}[/bold red]")
