from typing import List
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from .self_analysis import ImprovementOpportunity

class ImprovementUI:
    """Handles the user interface for self-improvement."""

    def __init__(self):
        self.console = Console()

    def present_opportunities(self, opportunities: List[ImprovementOpportunity]) -> List[ImprovementOpportunity]:
        """
        Displays the list of opportunities to the user and gets their selection.
        Returns a list of the opportunities the user selected.
        """
        if not opportunities:
            self.console.print("\n✅ No improvement opportunities found. Great job!")
            return []

        self.console.print(f"\nFound [bold yellow]{len(opportunities)}[/bold yellow] improvement opportunities:")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Type", width=15)
        table.add_column("Description")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="yellow")

        display_opportunities = opportunities[:10]
        for i, opp in enumerate(display_opportunities):
            table.add_row(str(i + 1), opp['type'], opp['description'], opp['file_path'], str(opp['line_number']))

        self.console.print(table)

        choices = [str(i + 1) for i in range(len(display_opportunities))]
        selection_str = Prompt.ask(
            "Which improvement would you like to apply? (e.g., '1', '1,3', 'all', or 'none')",
            choices=choices + ['all', 'none'],
            default="none"
        )

        if selection_str == 'none':
            self.console.print("No improvements selected. Exiting.")
            return []

        selected_opportunities = []
        if selection_str == 'all':
            selected_opportunities = display_opportunities
        else:
            try:
                selected_indices = [int(i.strip()) - 1 for i in selection_str.split(',')]
                selected_opportunities = [display_opportunities[i] for i in selected_indices]
            except (ValueError, IndexError):
                self.console.print("[bold red]Invalid selection.[/bold red]")
                return []

        return selected_opportunities
