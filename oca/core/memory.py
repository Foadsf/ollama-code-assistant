import json
from pathlib import Path
from datetime import datetime
from typing import TypedDict, List, Dict, Any

from .self_analysis import ImprovementOpportunity
from .self_modifier import ApplyResult

class ImprovementAttempt(TypedDict):
    """Represents the data recorded for each improvement attempt."""
    timestamp: str
    improvement_type: str
    description: str
    file_path: str
    success: bool
    reason: str
    execution_time: float

class MemorySystem:
    """Persistent learning and experience storage for OCA."""

    def __init__(self, memory_file: Path = Path(".oca/memory.jsonl")):
        self.memory_file = memory_file
        self.memory_file.parent.mkdir(exist_ok=True, parents=True)

    def record_improvement_attempt(self, opportunity: ImprovementOpportunity, result: ApplyResult, execution_time: float) -> None:
        """Record detailed outcome of an improvement attempt."""
        record: ImprovementAttempt = {
            "timestamp": datetime.now().isoformat(),
            "improvement_type": opportunity['type'],
            "description": opportunity['description'],
            "file_path": opportunity['file_path'],
            "success": result['success'],
            "reason": result['reason'],
            "execution_time": round(execution_time, 4),
        }

        try:
            with open(self.memory_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
        except IOError as e:
            # In a real application, we might want a more robust logger here
            print(f"Warning: Could not write to memory file {self.memory_file}: {e}")

    def get_success_patterns(self) -> Dict[str, Any]:
        """
        Analyze memory to identify success patterns for each improvement type.
        """
        records = self._load_all_records()
        patterns = {}

        # Group records by improvement type
        by_type: Dict[str, List[ImprovementAttempt]] = {}
        for record in records:
            if record['improvement_type'] not in by_type:
                by_type[record['improvement_type']] = []
            by_type[record['improvement_type']].append(record)

        # Calculate stats for each type
        for imp_type, imp_records in by_type.items():
            total_attempts = len(imp_records)
            successful_attempts = sum(1 for r in imp_records if r['success'])
            success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0

            patterns[imp_type] = {
                "total_attempts": total_attempts,
                "successful_attempts": successful_attempts,
                "success_rate": round(success_rate, 2)
            }

        return patterns

    def _load_all_records(self) -> List[ImprovementAttempt]:
        """Loads all records from the memory file."""
        if not self.memory_file.exists():
            return []

        records = []
        with open(self.memory_file, 'r') as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    # Ignore corrupted lines
                    continue
        return records

    # Keeping the original scaffolded methods as placeholders
    def store_interaction(self, interaction: Any) -> None:
        pass

    def learn_from_feedback(self, feedback: Any) -> None:
        pass

    def retrieve_similar_patterns(self, context: Any) -> List[Any]:
        return []

    def update_knowledge_base(self, knowledge: Any) -> None:
        pass
