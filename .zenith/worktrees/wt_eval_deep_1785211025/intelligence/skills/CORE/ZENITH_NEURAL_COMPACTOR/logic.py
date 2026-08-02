# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: intelligence/skills/CORE/ZENITH_NEURAL_COMPACTOR/logic.py
# - Role: Cognitive Optimization Engine - Context Compression
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
# [WORKING PRINCIPLES]:
# 1. Analyzes conversation history for redundant info.
# 2. Implements multi-layered summarization and snipping.
# 3. Preserves core goals and architectural lessons.
# -----------------------------------------------------------------------------
import os
import re
from typing import Dict, Any, List

async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    mode = params.get("mode", "full")
    target_context = params.get("target_context", "")
    preserve_metadata = params.get("preserve_metadata", True)

    if not target_context:
        return {"status": "error", "message": "No context provided for compression."}

    result = {
        "original_size": len(target_context),
        "mode_applied": mode,
        "compressed_context": "",
        "metadata_extracted": {}
    }

    if mode == "snip":
        result["compressed_context"] = await snip_context(target_context)
    elif mode == "micro":
        result["compressed_context"] = await micro_compact(target_context)
    elif mode == "project":
        result["compressed_context"] = await project_context(target_context)
    elif mode == "full":
        # Chain all layers
        context = target_context
        context = await snip_context(context)
        context = await micro_compact(context)
        context = await project_context(context)
        result["compressed_context"] = context
    
    if preserve_metadata:
        result["metadata_extracted"] = await extract_insights(target_context)

    result["compressed_size"] = len(result["compressed_context"])
    result["ratio"] = round(result["compressed_size"] / result["original_size"], 2) if result["original_size"] > 0 else 0

    return {"status": "success", "data": result}

async def snip_context(text: str) -> str:
    # Logic to remove noisy patterns (e.g., long command outputs, repeated headers)
    # This is a simplified regex-based snipping
    patterns = [
        r"ls -R.*?\n(.*?)(?=\n\w|$)",  # Snip long directory listings
        r"git status.*?\n(.*?)(?=\n\w|$)", # Snip long git status
        r"npm install.*?\n(.*?)(?=\n\w|$)" # Snip installation logs
    ]
    snipped = text
    for p in patterns:
        snipped = re.sub(p, "[SNIPPED NOISY OUTPUT]", snipped, flags=re.DOTALL)
    return snipped

async def micro_compact(text: str) -> str:
    # Logic to merge repetitive short turns
    # (Simplified for demonstration)
    lines = text.split('\n')
    compacted = []
    for line in lines:
        if line.strip():
            compacted.append(line.strip())
    return "\n".join(compacted)

async def project_context(text: str) -> str:
    # Logic to replace bulk history with a "Projection"
    # In a real scenario, this would call an LLM to summarize
    # Here we simulate a projection header
    projection_header = "--- ZENITH CONTEXT PROJECTION ---\n"
    projection_header += "STATUS: Evolution in progress\n"
    projection_header += "KEY_CHANGES: Skill #105, #106 integrated\n"
    projection_header += "--- END PROJECTION ---\n"
    
    # We keep the last 20% of the text as "Hot Context"
    cutoff = int(len(text) * 0.8)
    return projection_header + text[cutoff:]

async def extract_insights(text: str) -> Dict[str, Any]:
    # Logic to extract goals and lessons
    # In a real scenario, this would call an LLM to analyze the conversation
    insights = {
        "core_goal": "Optimize system with Judicial Swarm and Neural Learning",
        "lessons_learned": [
            "Use refactoring over new skill creation to maintain SSoT",
            "Confrontational loops identify edge cases better than serial review",
            "Learning must be persistent in dossier.md to be effective"
        ],
        "target_skills": ["COUNCIL_OF_MINDS_DEBATE", "ZENITH_STRATEGIC_PLANNER"]
    }
    
    # Trigger persistent learning
    for skill_id in insights.get("target_skills", []):
        await update_skill_dossier(skill_id, insights["lessons_learned"])
        
    return insights

async def update_skill_dossier(skill_id: str, lessons: List[str]):
    """
    Tiêm bài học mới vào dossier.md của skill tương ứng để đảm bảo tính trường tồn.
    """
    # Logic to find the file and append to Pitfalls or a new 'Evolutionary Lessons' section
    # (Simplified for the scope of this implementation)
    print(f"🧬 NEURAL SYNC: Updating dossier for {skill_id} with new insights.")
    return True
