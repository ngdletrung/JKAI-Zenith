"""
JKAI Skill Deck Index — maps Command Deck numbers (#1001, #7001) to registry skill IDs.

Single source: intelligence/MAP_SKILLS.md (STT column **#NNNN**).
Registry ground truth: intelligence/registry_Map_skills.json
"""

from __future__ import annotations

import os
import re
import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.utils import path_manager

logger = logging.getLogger("jkai.skill_deck")

# Deck IDs where MAP_SKILLS row lacks SKILL_* in Skill Con column
_MANUAL_DECK_OVERRIDES: Dict[str, str] = {
    "7001": "SKILL_HUEIC_TAO_SKILL_DE_XUAT_THEO_FORM",
    "1001": "BROWSER_VISION_OPS",
    "1002": "HOI_DONG_CHUYEN_GIA",
    "1006": "OMNI_SEARCH_ENGINE",
}


def _load_file_deck_overrides() -> Dict[str, str]:
    """Merge intelligence/deck_registry_overrides.json (from repair_map_deck_links.py)."""
    import json

    merged = dict(_MANUAL_DECK_OVERRIDES)
    for base in (
        Path(os.getenv("INTELLIGENCE_DIR", "")),
        Path("/intelligence"),
        Path("/workspace/intelligence"),
        Path(path_manager.get_root()) / "intelligence",
    ):
        if not base or not str(base):
            continue
        path = base / "deck_registry_overrides.json"
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged.update({str(k): str(v) for k, v in data.items()})
            except Exception as e:
                logger.debug("[SKILL-DECK] overrides load: %s", e)
            break
    return merged


def _fold_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D").lower()

# skill #7001 | kỹ năng #7001 | dùng skill #123 | /run_skill #09
_DECK_REF_RE = re.compile(
    r"(?:"
    r"(?:skill|kỹ năng|ky nang|run_skill|/run_skill)\s*#(\d{2,5})"
    r"|#(\d{2,5})(?=\s*(?:có|co|là|la|hay|không|khong|\?|$))"
    r"|#(\d{2,5})\b"
    r")",
    re.IGNORECASE,
)

_INSPECT_RE = re.compile(
    r"(rà\s*soát|ra\s*soat|xem|kiểm\s*tra|kiem\s*tra|mô\s*tả|mo\s*ta|"
    r"có\s*gì|co\s*gi|thông\s*tin|thong\s*tin|review|inspect|describe|"
    r"giới\s*thiệu|gioi\s*thieu)",
    re.IGNORECASE,
)


@dataclass
class SkillDeckEntry:
    deck_id: str
    title: str
    registry_id: Optional[str] = None
    keywords: str = ""
    skill_con_raw: str = ""
    category: str = ""
    confidence: float = 0.0

    @property
    def display_id(self) -> str:
        return f"#{self.deck_id}"


class SkillDeckIndex:
    _instance: Optional["SkillDeckIndex"] = None

    def __init__(self) -> None:
        self._by_deck: Dict[str, SkillDeckEntry] = {}
        self._registry: Dict[str, dict] = {}
        self._loaded = False

    @classmethod
    def get(cls) -> "SkillDeckIndex":
        if cls._instance is None:
            cls._instance = SkillDeckIndex()
        return cls._instance

    def _intel_dir_candidates(self) -> List[Path]:
        raw: List[Path] = []
        env_intel = os.getenv("INTELLIGENCE_DIR", "").strip()
        if env_intel:
            raw.append(Path(env_intel))
        raw.extend([
            Path("/intelligence"),
            Path("/workspace/intelligence"),
            Path(path_manager.get_root()) / "intelligence",
        ])
        pm_intel = path_manager.get("INTELLIGENCE_DIR", None)
        if pm_intel:
            raw.append(Path(pm_intel))
        seen: set[str] = set()
        out: List[Path] = []
        for p in raw:
            key = str(p.resolve()) if p.exists() else str(p)
            if key not in seen:
                seen.add(key)
                out.append(p)
        return out

    def _intel_dir(self) -> Path:
        for candidate in self._intel_dir_candidates():
            if candidate.is_dir():
                return candidate
        return Path(path_manager.get_root()) / "intelligence"

    def _find_file(self, name: str) -> Optional[Path]:
        for base in self._intel_dir_candidates():
            path = base / name
            if path.is_file():
                return path
        return None

    def _map_path(self) -> Optional[Path]:
        return self._find_file("MAP_SKILLS.md")

    def _registry_path(self) -> Optional[Path]:
        return self._find_file("registry_Map_skills.json")

    def ensure_loaded(self, force: bool = False) -> None:
        if self._loaded and not force and self._by_deck:
            return
        self._by_deck.clear()
        self._load_registry()
        self._parse_map_skills()
        self._loaded = True
        map_p = self._map_path()
        logger.info(
            "[SKILL-DECK] Indexed %d deck entries (map=%s, intel=%s)",
            len(self._by_deck),
            map_p,
            self._intel_dir(),
        )

    def _load_registry(self) -> None:
        import json

        self._registry = {}
        path = self._registry_path()
        if not path or not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._registry = data.get("skills", {}) or {}
        except Exception as e:
            logger.warning("[SKILL-DECK] Registry load failed: %s", e)

    def _parse_map_skills(self) -> None:
        path = self._map_path()
        if not path or not path.exists():
            logger.warning(
                "[SKILL-DECK] MAP_SKILLS.md not found (tried: %s)",
                [str(p / "MAP_SKILLS.md") for p in self._intel_dir_candidates()],
            )
            return

        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if "**#" not in line or not line.strip().startswith("|"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            m = re.search(r"#(\d{2,5})", parts[1])
            if not m:
                continue

            deck_id = m.group(1)
            title = re.sub(r"\*+", "", parts[2]).strip()
            keywords = parts[3] if len(parts) > 3 else ""
            skill_con = parts[4] if len(parts) > 4 else ""
            category = parts[5] if len(parts) > 5 else ""

            registry_ids = re.findall(r"\b(SKILL_[A-Z0-9_]+)\b", line)
            registry_id = registry_ids[0] if registry_ids else None
            confidence = 0.95 if registry_id else 0.0

            if not registry_id:
                overrides = _load_file_deck_overrides()
                registry_id = overrides.get(deck_id)
                confidence = 0.99 if registry_id else 0.0
            if not registry_id:
                registry_id, confidence = self._fuzzy_registry_match(title, keywords)

            self._by_deck[deck_id] = SkillDeckEntry(
                deck_id=deck_id,
                title=title,
                registry_id=registry_id,
                keywords=keywords[:500],
                skill_con_raw=skill_con,
                category=category,
                confidence=confidence,
            )

        file_overrides = _load_file_deck_overrides()
        for deck_id, entry in self._by_deck.items():
            if entry.registry_id:
                continue
            oid = file_overrides.get(deck_id)
            if oid and oid in self._registry:
                entry.registry_id = oid
                entry.confidence = 0.99

    def _fuzzy_registry_match(self, title: str, keywords: str) -> Tuple[Optional[str], float]:
        if not self._registry:
            return None, 0.0

        title_f = _fold_text(title)
        title_tokens = set(re.findall(r"[a-z0-9_]+", title_f))
        kw_tokens = set(re.findall(r"[a-z0-9_]+", _fold_text(keywords)))
        query_tokens = {t for t in (title_tokens | kw_tokens) if len(t) > 2}

        best_id: Optional[str] = None
        best_score = 0.0

        for sid, data in self._registry.items():
            name = _fold_text(data.get("name_vn") or data.get("name") or "")
            aliases = _fold_text(" ".join(data.get("aliases_vn") or []))
            blob = f"{name} {aliases} {sid.lower()}"
            blob_tokens = set(re.findall(r"[a-z0-9_]+", blob))
            if not query_tokens:
                continue
            overlap = len(query_tokens & blob_tokens)
            score = overlap / max(len(query_tokens), 1)
            if "hueic" in title_f and "hueic" in blob:
                score += 0.5
            if title_f[:24] and title_f[:24] in name:
                score += 0.35
            if score > best_score:
                best_score = score
                best_id = sid

        if best_score >= 0.25:
            return best_id, min(0.85, best_score)
        return None, 0.0

    def resolve(self, ref: str) -> Optional[SkillDeckEntry]:
        self.ensure_loaded()
        clean = ref.strip().lstrip("#")
        if not clean.isdigit():
            return None
        entry = self._by_deck.get(clean)
        if entry:
            return entry
        # Zero-pad attempts: 09 -> search keys
        for key in (clean, clean.lstrip("0") or clean):
            if key in self._by_deck:
                return self._by_deck[key]
        # After registry sync: deck_number on skill JSON
        rid = self.resolve_registry_by_deck(clean)
        if rid:
            data = self._registry.get(rid, {})
            return SkillDeckEntry(
                deck_id=clean,
                title=data.get("name_vn") or data.get("name") or rid,
                registry_id=rid,
                confidence=0.99,
            )
        return None

    def parse_refs(self, text: str) -> List[str]:
        if not text:
            return []
        ids: List[str] = []
        for m in _DECK_REF_RE.finditer(text):
            g = m.group(1) or m.group(2) or m.group(3)
            if g and g not in ids:
                ids.append(g)
        return ids

    def resolve_all_in_text(self, text: str) -> List[SkillDeckEntry]:
        refs = self.parse_refs(text)
        entries = [e for rid in refs if (e := self.resolve(rid))]
        if refs and not entries and not self._by_deck:
            self.ensure_loaded(force=True)
            entries = [e for rid in refs if (e := self.resolve(rid))]
        return entries

    def lookup_or_explain(self, text: str) -> Tuple[List[SkillDeckEntry], str]:
        """Resolve deck refs; return entries and human-readable error if any ref failed."""
        self.ensure_loaded()
        refs = self.parse_refs(text)
        if not refs:
            return [], ""
        entries = self.resolve_all_in_text(text)
        missing = [f"#{r}" for r in refs if not self.resolve(r)]
        if missing:
            hint = (
                f"Không tìm thấy {', '.join(missing)} trong MAP_SKILLS "
                f"(đã index {len(self._by_deck)} mục). "
                f"MAP: `{self._map_path() or 'NOT FOUND'}`. "
                "Thử `/search_skill từ_khóa` hoặc dùng đúng số 4 chữ số (VD: #1002, #7001)."
            )
            return entries, hint
        return entries, ""

    def format_resolution_block(self, entries: List[SkillDeckEntry]) -> str:
        if not entries:
            return ""
        lines = [
            "<ZENITH_SKILL_DECK_RESOLVE>",
            "Master dùng số thứ tự Command Deck (MAP_SKILLS.md). Đã ánh xạ sang Registry ID thực thi:",
        ]
        for e in entries:
            lines.append(f"- {e.display_id}: {e.title}")
            if e.registry_id:
                lines.append(f"  → registry_id / tool / skill_id: `{e.registry_id}`")
            else:
                lines.append("  → ⚠️ Chưa khớp registry — dùng /search_skill hoặc cập nhật MAP_SKILLS.")
        lines.append(
            "Khi gọi tool/plan: dùng registry_id ở trên, KHÔNG dùng số # trong field tool."
        )
        lines.append("</ZENITH_SKILL_DECK_RESOLVE>")
        return "\n".join(lines)

    def enrich_goal(self, goal: str) -> Tuple[str, List[SkillDeckEntry]]:
        entries = self.resolve_all_in_text(goal)
        if not entries:
            return goal, []
        block = self.format_resolution_block(entries)
        return f"{goal}\n\n{block}", entries

    def is_inspect_intent(self, goal: str) -> bool:
        return bool(_INSPECT_RE.search(goal)) and bool(self.parse_refs(goal))

    def build_inspect_report(self, entries: List[SkillDeckEntry]) -> str:
        self.ensure_loaded()
        intel = self._intel_dir()
        parts = ["🏛️ **BÁO CÁO KỸ NĂNG (Command Deck → Registry)**\n"]

        for e in entries:
            parts.append(f"## {e.display_id} — {e.title}\n")
            if not e.registry_id:
                parts.append(
                    "⚠️ **Catalog-only** (có trên MAP_SKILLS, chưa có SKILL_* trong registry). "
                    "Chạy `python scripts/repair_map_deck_links.py` hoặc sửa cột Skill Con / đúc skill mới.\n"
                )
                if e.title:
                    parts.append(f"- **Mô tả MAP**: {e.title[:500]}")
                if e.keywords:
                    parts.append(f"- **Keywords**: {e.keywords[:300]}")
                parts.append("")
                continue
            data = self._registry.get(e.registry_id, {})
            parts.append(f"- **Registry ID**: `{e.registry_id}`")
            parts.append(f"- **Tên**: {data.get('name_vn', e.registry_id)}")
            if data.get("description"):
                parts.append(f"- **Mô tả**: {data['description'][:800]}")
            rel = data.get("rel_path", "")
            if rel:
                skill_dir = intel / Path(rel.replace("\\", "/")).parent
                for name in ("dossier.md", "SKILL.md", "manual.md"):
                    p = skill_dir / name
                    if p.exists():
                        snippet = p.read_text(encoding="utf-8")[:2500]
                        parts.append(f"\n### Tài liệu ({name})\n{snippet}\n")
                        break
            parts.append("")
        return "\n".join(parts)

    def list_for_prompt(self, limit: int = 40) -> str:
        self.ensure_loaded()
        lines = ["Command Deck index (STT → registry_id):"]
        for i, (deck_id, entry) in enumerate(sorted(self._by_deck.items(), key=lambda x: int(x[0]))):
            if i >= limit:
                lines.append(f"... và {len(self._by_deck) - limit} kỹ năng khác (xem MAP_SKILLS.md)")
                break
            rid = entry.registry_id or "?"
            lines.append(f"  #{deck_id} → `{rid}` | {entry.title[:60]}")
        return "\n".join(lines)

    def search(self, query: str, limit: int = 10) -> List[SkillDeckEntry]:
        self.ensure_loaded()
        q = query.lower().strip()
        if not q:
            return list(self._by_deck.values())[:limit]

        if q.startswith("#"):
            e = self.resolve(q)
            return [e] if e else []

        results: List[Tuple[float, SkillDeckEntry]] = []
        for entry in self._by_deck.values():
            blob = f"{entry.title} {entry.keywords} {entry.registry_id or ''}".lower()
            score = 0.0
            if q in blob:
                score += 2.0
            for tok in q.split():
                if len(tok) > 2 and tok in blob:
                    score += 0.5
            if q.isdigit() and entry.deck_id == q.lstrip("#"):
                score += 5.0
            if score > 0:
                results.append((score, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:limit]]

    def sync_registry_deck_numbers(self, write: bool = True) -> Dict[str, int]:
        """
        Write deck_number / command_deck_id from MAP index into registry_Map_skills.json.
        """
        import json

        self.ensure_loaded(force=True)
        path = self._registry_path()
        if not path or not path.exists():
            return {"updated": 0, "deck_entries": len(self._by_deck), "error": "registry not found"}

        data = json.loads(path.read_text(encoding="utf-8"))
        skills: Dict[str, dict] = data.get("skills", {}) or {}
        updated = 0
        unmapped = 0

        # One registry_id may appear on multiple deck rows (fuzzy); keep highest-confidence deck.
        best_for_registry: Dict[str, SkillDeckEntry] = {}
        for entry in self._by_deck.values():
            if not entry.registry_id:
                unmapped += 1
                continue
            prev = best_for_registry.get(entry.registry_id)
            if prev is None or entry.confidence > prev.confidence:
                best_for_registry[entry.registry_id] = entry
            elif entry.confidence == prev.confidence and int(entry.deck_id) < int(prev.deck_id):
                best_for_registry[entry.registry_id] = entry

        for entry in best_for_registry.values():
            sk = skills.get(entry.registry_id)
            if not sk:
                continue
            deck_num = entry.deck_id
            display = entry.display_id
            if sk.get("deck_number") == deck_num and sk.get("command_deck_id") == display:
                continue
            sk["deck_number"] = deck_num
            sk["command_deck_id"] = display
            updated += 1

        if write and updated > 0:
            path.write_text(
                json.dumps(data, indent=4, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            logger.info("[SKILL-DECK] Registry sync: updated %d skills at %s", updated, path)

        return {
            "updated": updated,
            "unmapped_deck_rows": unmapped,
            "deck_entries": len(self._by_deck),
            "registry_path": str(path),
        }

    @classmethod
    def resolve_registry_by_deck(cls, deck_ref: str) -> Optional[str]:
        """Lookup registry skill id by deck_number field (after sync). Does not call resolve()."""
        inst = cls.get()
        inst.ensure_loaded()
        clean = deck_ref.strip().lstrip("#")
        if not clean.isdigit():
            return None
        for sid, data in inst._registry.items():
            if str(data.get("deck_number", "")) == clean:
                return sid
        return None


def resolve_skill_deck_refs(text: str) -> Tuple[str, List[SkillDeckEntry]]:
    return SkillDeckIndex.get().enrich_goal(text)


def parse_skill_deck_refs(text: str) -> List[str]:
    return SkillDeckIndex.get().parse_refs(text)
