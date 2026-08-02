"""
core/utils/semantic_skill_matcher.py
Neural Librarian - tu dong tim va inject skill protocol cho moi goal.

Kien truc:
  1. Build inverted index tu toan bo manifest.json (181 skills)
  2. Nhan goal -> tokenize -> score tung skill
  3. Inject dossier.md cua skill tot nhat vao goal context
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("jkai.ssm")


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class SkillMatchResult:
    skill_id: str
    deck_id: str
    display_id: str
    title: str
    domain: str
    score: float
    dossier_path: Optional[Path] = None
    triggers_matched: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"SkillMatchResult({self.display_id} score={self.score:.3f})"


@dataclass
class SkillEntry:
    skill_id: str
    name: str
    domain: str
    triggers: List[str]
    keywords: List[str]
    skill_dir: Path
    dossier_path: Optional[Path] = None
    _dossier_text: str = ""

    def get_dossier_text(self, max_chars: int = 4000) -> str:
        if self._dossier_text:
            return self._dossier_text[:max_chars]
        for doc in ("dossier.md", "SKILL.md", "manual.md"):
            p = self.skill_dir / doc
            if p.exists():
                self._dossier_text = p.read_text(encoding="utf-8", errors="replace")
                self.dossier_path = p
                return self._dossier_text[:max_chars]
        return ""


# ============================================================
# TEXT UTILITIES
# ============================================================

def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower()


_STOP = {
    "va", "cua", "la", "co", "de", "cho", "khi", "theo", "trong", "tren",
    "duoc", "voi", "cac", "mot", "nhu", "ma", "da", "se", "bi",
    "the", "and", "for", "are", "this", "that", "with", "from", "have",
    "all", "not", "its", "any", "each", "you", "your", "when", "use",
    "can", "will", "should", "must", "may", "more", "also", "into",
}

TECHNICAL_TERMS = {
    "git", "api", "bug", "run", "aws", "sql", "ssl", "ssh", "web", "app", "xml", "css", "dom",
    "docker", "deploy", "pipeline", "test", "build", "debug", "review", "security", "performance",
    "optimization", "shipping", "launch", "migration", "observability", "instrumentation",
    "monitoring", "metrics", "log", "logs", "trace", "triage", "rollback", "commit", "branch",
    "pr", "merge", "push", "pull", "clone", "repo", "github", "gitlab", "bitbucket", "npm", "pip",
    "url", "cmd", "dev", "ops", "ram", "cpu", "db", "dockerfile", "yaml", "json", "rest", "graphql",
    "oauth", "token", "auth", "login", "logout", "signin", "signup", "register", "config", "env",
    "host", "server", "client", "service", "daemon", "process", "thread", "memory", "storage",
    "disk", "network", "port", "ip", "dns", "domain", "route", "gateway", "proxy", "loadbalancer",
    "firewall", "encryption", "decryption", "cipher", "hash", "md5", "sha256", "jwt", "key",
    "secret", "cert", "certificate", "ssl", "tls", "ssh", "keypair", "pem", "pubkey", "privkey",
    "agent", "swarm", "node", "cluster", "replica", "backup", "restore", "recovery", "failure",
    "error", "exception", "fault", "crash", "hang", "freeze", "leak", "overflow", "indexerror",
    "keyerror", "valueerror", "typeerror", "runtimeerror", "syntaxerror", "compilation", "compiler",
    "interpreter", "runtime", "sdk", "library", "framework", "package", "module", "dependency",
    "import", "export", "require", "include", "source", "binary", "exec", "executable", "script",
    "cron", "task", "job", "queue", "worker", "message", "event", "pubsub", "kafka", "rabbitmq",
    "redis", "database", "query", "index", "table", "row", "column", "field", "record", "schema",
    "migration", "seed", "fixture", "mock", "stub", "spy", "assertion", "assert", "expect",
    "fixture", "lint", "linter", "formatter", "format", "prettier", "eslint", "pylint", "flake8",
    "black", "isort", "mypy", "typescript", "javascript", "python", "golang", "rust", "cpp",
    "java", "php", "ruby", "bash", "shell", "powershell", "cmd", "terminal", "console", "stdout",
    "stderr", "stdin", "pipe", "redirect", "stream", "buffer", "cache", "session", "cookie",
    "header", "request", "response", "status", "code", "method", "get", "post", "put", "delete",
    "patch", "options", "head", "payload", "params", "query", "body", "json", "xml", "form",
    "multipart", "boundary", "upload", "download", "transfer", "fetch", "ajax", "axios", "curl",
    "wget", "http", "https", "ftp", "sftp", "ssh", "scp", "rsync", "cronjob", "daemon", "service",
    "systemd", "init", "upstart", "rc", "sysctl", "journalctl", "dmesg", "logs", "logrotate",
    "syslog", "fluentd", "logstash", "elasticsearch", "kibana", "prometheus", "grafana", "sentry",
    "datadog", "newrelic", "dynatrace", "appdynamics", "splunk", "sumologic", "paperduty",
    "pagerduty", "opsgenie", "victorops", "alerta", "sensu", "nagios", "zabbix", "zenoss",
    "monit", "supervisor", "circus", "pm2", "forever", "nodemon", "webpack", "babel", "gulp",
    "grunt", "npm", "yarn", "pnpm", "bun", "deno", "node", "express", "koa", "nest", "fastify",
    "react", "angular", "vue", "svelte", "solid", "preact", "jquery", "bootstrap", "tailwind",
    "sass", "less", "stylus", "postcss", "vite", "rollup", "parcel", "esbuild", "swc", "turbopack",
    "adr", "prd", "spec", "planning"
}


def _tokenize(text: str) -> List[str]:
    folded = _fold(text)
    tokens = re.findall(r"[a-z][a-z0-9_-]{2,}", folded)
    return [t for t in tokens if t not in _STOP and len(t) > 2]


# ============================================================
# CORE ENGINE (SINGLETON)
# ============================================================

class SemanticSkillMatcher:
    _instance: Optional["SemanticSkillMatcher"] = None
    _built_at: float = 0.0
    _CACHE_TTL: float = 300.0  # rebuild index sau 5 phut

    def __init__(self) -> None:
        self._skills: List[SkillEntry] = []
        self._trigger_index: Dict[str, List[SkillEntry]] = {}
        self._skills_root: Optional[Path] = None
        self._built = False

    @classmethod
    def get(cls) -> "SemanticSkillMatcher":
        if cls._instance is None:
            cls._instance = SemanticSkillMatcher()
        if not cls._instance._built or (time.time() - cls._built_at > cls._CACHE_TTL):
            cls._instance._build_index()
        return cls._instance

    def _find_skills_root(self) -> Optional[Path]:
        candidates = []
        env = os.getenv("INTELLIGENCE_DIR", "")
        if env:
            candidates.append(Path(env) / "skills")
        candidates.extend([
            Path("/intelligence/skills"),
            Path("/workspace/intelligence/skills"),
        ])
        try:
            from core.utils import path_manager
            candidates.append(Path(path_manager.get_root()) / "intelligence" / "skills")
        except Exception:
            pass
        for c in candidates:
            if c.is_dir():
                return c
        return None

    def _build_index(self) -> None:
        root = self._find_skills_root()
        if not root:
            logger.warning("[SSM] Cannot find intelligence/skills root. Disabled.")
            self._built = True
            SemanticSkillMatcher._built_at = time.time()
            return

        self._skills_root = root
        self._skills = []
        self._trigger_index = {}
        count = 0

        for domain_dir in sorted(root.iterdir()):
            if not domain_dir.is_dir() or domain_dir.name.startswith("__"):
                continue
            domain = domain_dir.name
            if domain == "templates":
                continue

            for skill_dir in sorted(domain_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                manifest_path = skill_dir / "manifest.json"
                if not manifest_path.exists():
                    continue
                try:
                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                except Exception:
                    continue

                triggers = [_fold(t) for t in data.get("triggers", []) if t]
                keywords = [_fold(k) for k in data.get("keywords", []) if k]
                name_tokens = _tokenize(
                    data.get("name", "") + " " + data.get("description", "")
                )
                keywords = list(dict.fromkeys(keywords + name_tokens))[:30]

                entry = SkillEntry(
                    skill_id=data.get("id", skill_dir.name),
                    name=data.get("name", skill_dir.name),
                    domain=domain,
                    triggers=triggers,
                    keywords=keywords,
                    skill_dir=skill_dir,
                )
                self._skills.append(entry)
                count += 1

                for trigger in triggers:
                    for token in _tokenize(trigger) + [trigger]:
                        if len(token) > 2:
                            if token not in self._trigger_index:
                                self._trigger_index[token] = []
                            if entry not in self._trigger_index[token]:
                                self._trigger_index[token].append(entry)

        self._built = True
        SemanticSkillMatcher._built_at = time.time()
        logger.info(
            "[SSM] Index built: %d skills, %d trigger tokens (root=%s)",
            count, len(self._trigger_index), root,
        )

    def match(
        self,
        goal: str,
        top_k: int = 2,
        min_score: float = 0.30,
    ) -> List[SkillMatchResult]:
        if not self._built:
            self._build_index()
        if not self._skills:
            return []

        goal_tokens = _tokenize(goal)
        if not goal_tokens:
            return []

        scores: Dict[str, list] = {}
        goal_folded = _fold(goal)

        for entry in self._skills:
            sid = entry.skill_id
            raw_score = 0.0
            matched_triggers = []

            # 1. Trigger matching using token overlap logic
            for trigger in entry.triggers:
                trig_toks = _tokenize(trigger)
                if not trig_toks:
                    continue
                hits = [t for t in trig_toks if t in goal_tokens]
                if hits:
                    if len(trig_toks) > 1:
                        if len(hits) >= 2:
                            # Verify bigrams to ensure matched tokens form a contiguous phrase in both trigger and goal
                            trig_bigrams = {(trig_toks[i], trig_toks[i+1]) for i in range(len(trig_toks)-1)}
                            goal_bigrams = {(goal_tokens[j], goal_tokens[j+1]) for j in range(len(goal_tokens)-1)}
                            if any(bg in goal_bigrams for bg in trig_bigrams):
                                raw_score += 1.5 * len(hits)
                                matched_triggers.append(trigger)
                            else:
                                t = hits[0]
                                if t in TECHNICAL_TERMS:
                                    raw_score += 0.5
                                    matched_triggers.append(trigger)
                        else:
                            t = hits[0]
                            if t in TECHNICAL_TERMS:
                                raw_score += 0.5
                                matched_triggers.append(trigger)
                    else:
                        t = hits[0]
                        weight = 1.5
                        if t not in TECHNICAL_TERMS:
                            weight = 0.1
                        raw_score += weight
                        matched_triggers.append(trigger)

            # 2. Keyword matching
            kw_hits = 0
            for t in goal_tokens:
                if t in entry.keywords:
                    weight = 0.4
                    if t not in TECHNICAL_TERMS:
                        weight = 0.05
                    kw_hits += weight
            raw_score += kw_hits

            if raw_score > 0:
                scores[sid] = [raw_score, entry, matched_triggers]

        if not scores:
            return []

        n = max(len(goal_tokens), 1)
        results: List[SkillMatchResult] = []

        for sid, (raw_score, entry, matched) in scores.items():
            normalized = raw_score / n
            domain_boost = 0.08 if entry.domain.lower() in goal_folded else 0.0
            
            # Title match boost (supporting subwords) to resolve ties for specific skills
            name_toks = _tokenize(entry.name)
            title_hits = sum(1 for t in goal_tokens if any(t in nt or nt in t for nt in name_toks if len(nt) >= 3))
            title_ratio = title_hits / max(len(name_toks), 1)
            title_boost = title_hits * 0.20 + title_ratio * 0.15
            
            final = min(normalized + domain_boost + title_boost, 1.5)
            if final < min_score:
                continue

            dossier_path: Optional[Path] = None
            for doc in ("dossier.md", "SKILL.md", "manual.md"):
                p = entry.skill_dir / doc
                if p.exists():
                    dossier_path = p
                    break

            # Resolve deck_id
            deck_id = "????"
            display_id = "#????"
            try:
                from core.utils.skill_deck_index import SkillDeckIndex
                deck = SkillDeckIndex.get()
                deck.ensure_loaded()
                for did, dentry in deck._by_deck.items():
                    if dentry.registry_id == sid:
                        deck_id = did
                        display_id = "#" + did
                        break
            except Exception:
                pass

            results.append(SkillMatchResult(
                skill_id=sid,
                deck_id=deck_id,
                display_id=display_id,
                title=entry.name,
                domain=entry.domain,
                score=final,
                dossier_path=dossier_path,
                triggers_matched=matched[:5],
            ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def inject_dossier(
        self,
        goal: str,
        match: SkillMatchResult,
        max_chars: int = 3500,
    ) -> str:
        if not match.dossier_path or not match.dossier_path.exists():
            return goal
        try:
            dossier = match.dossier_path.read_text(encoding="utf-8", errors="replace")[:max_chars]
        except Exception:
            return goal
        injection = (
            "\n\n<ZENITH_SKILL_ACTIVATED>\n"
            f"Skill: {match.display_id} {match.title}"
            f" (domain={match.domain}, score={match.score:.2f})\n"
            "Ap dung chinh xac giao thuc sau - KHONG bo qua buoc nao:\n\n"
            f"{dossier}\n"
            "</ZENITH_SKILL_ACTIVATED>\n"
        )
        return goal + injection

    def explain(self, goal: str, top_k: int = 5) -> str:
        matches = self.match(goal, top_k=top_k, min_score=0.0)
        lines = [
            f"[SSM] Goal: {goal[:80]!r}",
            f"Tokens: {_tokenize(goal)}",
            "",
        ]
        if not matches:
            lines.append("  No matches above 0.0")
        for m in matches:
            lines.append(
                f"  {m.display_id:8} {m.title[:40]:40}"
                f" score={m.score:.3f} matched={m.triggers_matched}"
            )
        return "\n".join(lines)


# ============================================================
# PUBLIC API
# ============================================================

def get_matcher() -> SemanticSkillMatcher:
    return SemanticSkillMatcher.get()


def auto_match_and_enrich(
    goal: str,
    threshold: float = 0.40,
) -> Optional[str]:
    """
    Entry point chinh duoc goi tu ingress_skill_gate.py.
    Tra ve enriched_goal (goal + dossier) neu co skill match du manh.
    Tra ve None neu khong co match hoac goal qua ngan/chung.
    """
    try:
        matcher = SemanticSkillMatcher.get()
        matches = matcher.match(goal, top_k=2, min_score=threshold)
        if not matches:
            return None
        best = matches[0]
        enriched = matcher.inject_dossier(goal, best)
        logger.info(
            "[SSM] Auto-activated %s %s (score=%.2f matched=%s)",
            best.display_id,
            best.title[:30],
            best.score,
            best.triggers_matched,
        )
        return enriched
    except Exception as exc:
        logger.warning("[SSM] match error: %s", exc)
        return None
