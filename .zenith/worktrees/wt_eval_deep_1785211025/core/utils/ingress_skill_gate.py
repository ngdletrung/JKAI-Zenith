"""
Shared ingress helpers: Command Deck inspect/enrich before FAST/DEEP/receptionist.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("jkai.ingress_skill_gate")


def try_skill_deck_run_guide(
    goal: str,
    history: Optional[List[Any]] = None,
    mission_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        from core.utils.skill_deck_run_guide import try_skill_run_guide as _try

        return _try(goal, history, mission_id)
    except Exception as e:
        logger.warning("[INGRESS-SKILL-GATE] run guide failed: %s", e)
    return None


def try_skill_deck_inspect(goal: str) -> Optional[Dict[str, Any]]:
    """
    If goal is inspect intent with deck refs, return completed answer dict.
    Otherwise None (caller continues normal routing).
    """
    try:
        from core.utils.skill_deck_index import SkillDeckIndex

        deck = SkillDeckIndex.get()
        if not deck.parse_refs(goal) or not deck.is_inspect_intent(goal):
            return None
        entries, deck_err = deck.lookup_or_explain(goal)
        if entries:
            return {
                "status": "success",
                "answer": deck.build_inspect_report(entries),
                "task_id": None,
                "source": "skill_deck_inspect",
            }
        if deck_err:
            return {"status": "error", "answer": deck_err, "task_id": None, "source": "skill_deck_inspect"}
    except Exception as e:
        logger.warning("[INGRESS-SKILL-GATE] inspect failed: %s", e)
    return None


def enrich_goal_with_deck(goal: str) -> Tuple[str, List[str], Optional[str]]:
    """Returns (enriched_goal, registry_ids, warning)."""
    try:
        from core.utils.skill_deck_index import SkillDeckIndex

        deck = SkillDeckIndex.get()
        refs = deck.parse_refs(goal)
        if not refs:
            try:
                ssm = try_semantic_skill_match(goal, threshold=0.40)
                if ssm and ssm.get("status") == "success":
                    enriched = ssm.get("enriched_goal")
                    matched_refs = deck.parse_refs(enriched)
                    if matched_refs:
                        entries = [deck.resolve(r) for r in matched_refs if deck.resolve(r)]
                        ids = [e.registry_id for e in entries if e.registry_id]
                        logger.info("[INGRESS-SSM] Auto-matched registry IDs: %s", ids)
                        enriched, _ = _append_skill_references(enriched, ids)
                        return enriched, ids, None
            except Exception as ssm_err:
                logger.warning("[INGRESS-SSM] Auto-activation failed: %s", ssm_err)

            goal, _ = _append_skill_references(goal, [])
            return goal, [], None
        entries, deck_err = deck.lookup_or_explain(goal)
        if entries:
            enriched, _ = deck.enrich_goal(goal)
            ids = [e.registry_id for e in entries if e.registry_id]
            enriched, ref_loaded = _append_skill_references(enriched, ids)
            if ref_loaded:
                logger.info("[INGRESS-SKILL-GATE] references loaded: %s", ref_loaded)
            return enriched, ids, None
        return goal, [], deck_err
    except Exception as e:
        logger.warning("[INGRESS-SKILL-GATE] enrich failed: %s", e)
        return goal, [], str(e)


def _append_skill_references(goal: str, registry_ids: List[str]) -> Tuple[str, List[str]]:
    try:
        from core.utils.skill_references import enrich_goal_with_skill_references

        return enrich_goal_with_skill_references(goal, registry_ids)
    except Exception as e:
        logger.debug("[INGRESS-SKILL-GATE] references: %s", e)
        return goal, []


def try_semantic_skill_match(
    goal: str,
    threshold: float = 0.40,
    skip_if_has_deck_ref: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Semantic Skill Matcher (SSM) hook.
    Tu dong nhan dien intent tu goal va inject dossier.md cua skill phu hop.

    Args:
        goal: Goal text tu Master.
        threshold: Score toi thieu de kich hoat (default 0.40).
        skip_if_has_deck_ref: Neu True, bo qua SSM khi Master da goi #NNNN tuong minh.

    Returns:
        Dict voi enriched_goal va metadata, hoac None neu khong co match.
    """
    if not goal or len(goal.strip()) < 5:
        return None

    # Neu Master da chi dinh #NNNN tuong minh, tin tuong explicit ref
    if skip_if_has_deck_ref:
        try:
            from core.utils.skill_deck_index import SkillDeckIndex
            if SkillDeckIndex.get().parse_refs(goal):
                return None
        except Exception:
            pass

    try:
        from core.utils.semantic_skill_matcher import auto_match_and_enrich
        enriched = auto_match_and_enrich(goal, threshold=threshold)
        if enriched is None:
            return None

        logger.info("[INGRESS-SSM] Goal enriched with skill dossier (%d chars)", len(enriched) - len(goal))
        return {
            "status": "success",
            "enriched_goal": enriched,
            "source": "semantic_skill_matcher",
        }
    except Exception as e:
        logger.warning("[INGRESS-SSM] SSM hook failed: %s", e)
        return None

