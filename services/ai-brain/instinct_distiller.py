import json
from pathlib import Path
from typing import List, Dict
from core.utils.zenith_observer import ZenithObserver

class InstinctDistiller:
    """
    Analyzes neural history and distills repeating successful patterns into skills.
    """
    
    CONFIDENCE_THRESHOLD = 0.8
    
    def __init__(self, zenith_dir: str):
        self.zenith_dir = Path(zenith_dir)
        self.observer = ZenithObserver(zenith_dir)
        self.skills_dir = self.zenith_dir / "evolved" / "skills"
        
    def distill_new_skills(self) -> List[str]:
        """
        Analyzes history and generates skill drafts.
        Currently a placeholder for a more complex LLM-based distillation logic.
        """
        history = self.observer.get_recent_history(limit=50)
        successes = [h for h in history if h["type"] == "task_success"]
        
        if not successes:
            return []
            
        # Group by similarity (placeholder logic)
        # In a real scenario, we would send these to an LLM to find patterns.
        
        proposals = []
        # Example proposal logic
        for success in successes:
            desc = success["data"]["description"]
            if "n8n" in desc.lower():
                proposals.append(self._create_skill_draft("n8n_integration", success["data"]))
                
        return proposals

    def _create_skill_draft(self, skill_name: str, sample_data: Dict) -> str:
        """Creates a markdown skill draft."""
        file_path = self.skills_dir / f"{skill_name}.md"
        if file_path.exists():
            return str(file_path)
            
        content = f"""# Skill: {skill_name}

## Description
Auto-distilled skill from task: {sample_data['description']}

## Patterns Identified
- Tools used: {', '.join(sample_data['tools'])}
- Outcome: {sample_data['outcome']}

## Guidance
[This is an auto-generated draft. Refine it based on project needs.]
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return str(file_path)
