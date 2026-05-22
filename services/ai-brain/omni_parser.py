from __future__ import annotations

import ast
import json          # FIX 1: import bị thiếu trong bản gốc
import logging
import os
import re
from abc import ABC, abstractmethod   # FIX 2: enforce interface đúng cách
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 1. DATA MODEL
# ═══════════════════════════════════════════════

@dataclass
class UniversalNode:
    node_id:         str
    name:            str
    file_type:       str
    file:            str
    content_summary: str            = ""
    links_to:        list[str]      = field(default_factory=list)
    linked_by:       list[str]      = field(default_factory=list)
    metadata:        dict[str, Any] = field(default_factory=dict)
    tags:            list[str]      = field(default_factory=list)

    def to_embed_text(self) -> str:
        parts = [f"[{self.file_type}] {self.name}", self.content_summary]
        if self.tags:
            parts.append("tags: " + ", ".join(self.tags))
        if self.links_to:
            parts.append("refs: " + ", ".join(self.links_to[:8]))
        return " | ".join(filter(None, parts))

    def to_payload(self) -> dict[str, Any]:
        """Tạo từ điển dữ liệu đầy đủ cho Qdrant payload."""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "file_type": self.file_type,
            "file": self.file,
            "content_summary": self.content_summary,
            "links_to": self.links_to,
            "linked_by": self.linked_by,
            "metadata": self.metadata,
            "tags": self.tags,
        }


# ═══════════════════════════════════════════════
# 2. LINK DETECTOR
# ═══════════════════════════════════════════════

class LinkDetector:
    _WIKILINK  = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")   # [[page|alias]] / [[page#section]]
    _HASHTAG   = re.compile(r"(?<!\w)#([A-Za-z][A-Za-z0-9_]*)")     # #tag (không match #123)
    _MD_LINK   = re.compile(r"\[[^\]]+\]\(([^)]+)\)")                # [text](path)
    _PY_IMPORT = re.compile(r"^(?:from|import)\s+([\w.]+)", re.M)    # import / from x import

    # FIX 3: Bỏ backtick pattern — quá noisy, code literal không phải link
    # Thay bằng pattern chặt hơn: chỉ nhận dạng skill call dạng tool_name(
    _SKILL_CALL = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+){1,})\s*\(")  # snake_case(

    @classmethod
    def extract(cls, text: str, file_type: str) -> tuple[list[str], list[str]]:
        if not text:
            return [], []

        links: list[str] = []
        tags:  list[str] = []

        links += cls._WIKILINK.findall(text)

        for href in cls._MD_LINK.findall(text):
            if not href.startswith(("http://", "https://", "mailto:")):
                links.append(Path(href).stem)   # lấy tên file không có extension

        tags += cls._HASHTAG.findall(text)

        if file_type == "code":
            links += cls._PY_IMPORT.findall(text)
        elif file_type == "markdown":
            # Skill call trong docs: `tool_name(` pattern
            links += cls._SKILL_CALL.findall(text)

        return list(dict.fromkeys(links)), list(dict.fromkeys(tags))  # dedup, giữ thứ tự


# ═══════════════════════════════════════════════
# 3. PARSER BASE + REGISTRY
# ═══════════════════════════════════════════════

class BaseParser(ABC):
    """FIX 2: Dùng ABC thay vì raise NotImplementedError thủ công."""

    @property
    @abstractmethod
    def supported_extensions(self) -> set[str]:
        ...

    @abstractmethod
    async def parse(self, file_path: str, base_dir: str = "") -> list[UniversalNode]:
        ...

    # Helper: tạo node_id duy nhất dùng relative path để tránh collision
    @staticmethod
    def make_node_id(file_path: str, suffix: str = "", base_dir: str = "") -> str:
        """
        💎 [UNIVERSAL-ID]: Luôn dùng relative path tính từ Gốc Dự án để định danh.
        """
        if base_dir:
            rel = os.path.relpath(file_path, base_dir)
        else:
            rel = os.path.basename(file_path) # Fallback neu khong co base_dir
        
        # Chuan hoa separator thanh '/' de nhat the giua Win/Linux
        rel = rel.replace("\\", "/")
        return f"{rel} - {suffix}" if suffix else rel


class ParserRegistry:
    _parsers: dict[str, BaseParser] = {}

    @classmethod
    def register(cls, *extensions: str):
        def decorator(parser_cls: type[BaseParser]) -> type[BaseParser]:
            instance = parser_cls()
            for ext in extensions:
                key = ext.lower()
                if key in cls._parsers:
                    logger.warning(f"Parser for {key} overwritten by {parser_cls.__name__}")
                cls._parsers[key] = instance
            return parser_cls
        return decorator

    @classmethod
    def get(cls, file_path: str) -> BaseParser | None:
        return cls._parsers.get(Path(file_path).suffix.lower())

    @classmethod
    def all_extensions(cls) -> set[str]:
        return set(cls._parsers)


# ═══════════════════════════════════════════════
# 4. PARSERS
# ═══════════════════════════════════════════════

@ParserRegistry.register(".md", ".mdx", ".txt", ".rst")
class MarkdownParser(BaseParser):
    supported_extensions = {".md", ".mdx", ".txt", ".rst"}

    # FIX: Tách heading thành section riêng — 1 heading = 1 node
    _HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

    async def parse(self, file_path: str, base_dir: str = "") -> list[UniversalNode]:
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            logger.error(f"MarkdownParser: cannot read {file_path}: {e}")
            return []

        links, tags = LinkDetector.extract(content, "markdown")
        nodes: list[UniversalNode] = []

        # Tách sections theo heading
        mtime = os.path.getmtime(file_path)
        sections = self._split_sections(content, file_path)
        # Chuan hoa path de luu tru
        rel_file = os.path.relpath(file_path, base_dir).replace("\\", "/") if base_dir else file_path

        for sec_name, sec_body in sections:
            nodes.append(UniversalNode(
                node_id         = self.make_node_id(file_path, sec_name, base_dir),
                name            = sec_name,
                file_type       = "markdown",
                file            = rel_file,
                content_summary = sec_body[:500].strip(),
                links_to        = links,
                tags            = tags,
                metadata        = {
                    "word_count": len(sec_body.split()),
                    "file_mtime": mtime
                },
            ))

        return nodes

    def _split_sections(self, content: str, file_path: str) -> list[tuple[str, str]]:
        headings = list(self._HEADING.finditer(content))
        if not headings:
            return [(Path(file_path).stem, content)]

        sections: list[tuple[str, str]] = []
        for i, match in enumerate(headings):
            start = match.end()
            end   = headings[i + 1].start() if i + 1 < len(headings) else len(content)
            sections.append((match.group(2).strip(), content[start:end].strip()))
        return sections


@ParserRegistry.register(".json")
class JsonParser(BaseParser):
    supported_extensions = {".json"}

    # Filenames that are machine-generated and useless for the knowledge graph
    _SKIP_NAMES: frozenset[str] = frozenset({
        "package-lock.json",
        "yarn.lock",           # not JSON but just in case
        "vocab.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "merges.txt",          # not JSON, defensive
    })

    # Path fragments that signal machine-generated data directories
    _SKIP_PATH_FRAGMENTS: tuple[str, ...] = (
        "/tokenizer/",
        "/tokenizer_2/",
        "/tokenizer_3/",
        "node_modules/",
    )

    async def parse(self, file_path: str, base_dir: str = "") -> list[UniversalNode]:
        fname = Path(file_path).name

        # --- Guard 1: blocklisted filenames ---
        if fname in self._SKIP_NAMES:
            logger.debug(f"JsonParser: skipping blocklisted file {file_path}")
            return []

        # --- Guard 2: blocklisted path fragments ---
        normalized = file_path.replace("\\", "/")
        if any(frag in normalized for frag in self._SKIP_PATH_FRAGMENTS):
            logger.debug(f"JsonParser: skipping machine-gen path {file_path}")
            return []

        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")

            # FIX: Safer comment stripping.
            # Original regex could eat slashes inside strings (e.g. URLs).
            # New version only strips // at the START of a line (after optional whitespace)
            # and /* */ block comments — safe for all real config files.
            clean_content = re.sub(
                r"^\s*//.*$",           # line comments at line start only
                "",
                content,
                flags=re.MULTILINE,
            )
            clean_content = re.sub(r"/\*[\s\S]*?\*/", "", clean_content)

            data = json.loads(clean_content, strict=False)

        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"JsonParser: {file_path}: {e}")
            return []

        # --- Guard 3: skip if it looks like a flat token/vocab mapping ---
        # vocab.json files are typically {"token": id, ...} with thousands of keys
        if isinstance(data, dict) and len(data) > 500:
            logger.debug(f"JsonParser: skipping oversized dict ({len(data)} keys) {file_path}")
            return []

        links: list[str] = []
        self._extract_string_refs(data, links)
        summary = json.dumps(data, ensure_ascii=False)[:300] if isinstance(data, dict) else content[:300]
        rel_file = os.path.relpath(file_path, base_dir).replace("\\", "/") if base_dir else file_path

        return [UniversalNode(
            node_id         = self.make_node_id(file_path, base_dir=base_dir),
            name            = Path(file_path).stem,
            file_type       = "json",
            file            = rel_file,
            content_summary = summary,
            links_to        = list(dict.fromkeys(links)),
            metadata        = {
                "keys":       list(data.keys()) if isinstance(data, dict) else [],
                "item_count": len(data) if isinstance(data, (dict, list)) else 0,
                "file_mtime": os.path.getmtime(file_path),
            },
        )]

    def _extract_string_refs(self, data: Any, links: list[str], depth: int = 0):
        """Đệ quy tìm giá trị string trông như file path."""
        if depth > 3:
            return
        if isinstance(data, str) and ("/" in data or data.endswith((".py", ".md", ".json"))):
            links.append(Path(data).stem)
        elif isinstance(data, dict):
            for v in data.values():
                self._extract_string_refs(v, links, depth + 1)
        elif isinstance(data, list):
            for item in data[:20]:
                self._extract_string_refs(item, links, depth + 1)


@ParserRegistry.register(".py")
class PythonParser(BaseParser):
    supported_extensions = {".py"}

    async def parse(self, file_path: str, base_dir: str = "") -> list[UniversalNode]:
        mtime = os.path.getmtime(file_path)
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            tree    = ast.parse(content, filename=file_path)
        except (OSError, SyntaxError) as e:
            logger.warning(f"PythonParser: {file_path}: {e}")
            return []

        nodes: list[UniversalNode] = []
        rel_file = os.path.relpath(file_path, base_dir).replace("\\", "/") if base_dir else file_path

        # Node đại diện toàn bộ file
        file_imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                file_imports += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                file_imports.append(node.module)

        nodes.append(UniversalNode(
            node_id         = self.make_node_id(file_path, base_dir=base_dir),
            name            = Path(file_path).stem,
            file_type       = "python_file",
            file            = rel_file,
            content_summary = content[:300],
            links_to        = list(dict.fromkeys(file_imports)),
            metadata        = {
                "line_count": content.count("\n"),
                "file_mtime": os.path.getmtime(file_path),
            },
        ))

        # FIX: Parse cả class + method + async def
        for item in ast.walk(tree):
            if isinstance(item, ast.ClassDef):
                class_name = item.name
                method_names: list[str] = []

                for child in item.body:
                    # FIX: Bắt cả FunctionDef lẫn AsyncFunctionDef
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_names.append(child.name)
                        calls   = self._collect_calls(child)
                        fn_type = "async_method" if isinstance(child, ast.AsyncFunctionDef) else "method"

                        nodes.append(UniversalNode(
                            node_id         = self.make_node_id(file_path, f"{class_name}.{child.name}", base_dir),
                            name            = f"{class_name}.{child.name}",
                            file_type       = fn_type,
                            file            = rel_file,
                            content_summary = f"{fn_type} at line {child.lineno} in class {class_name}",
                            links_to        = calls,
                            metadata        = {
                                "line": child.lineno, 
                                "class": class_name,
                                "file_mtime": mtime
                            },
                        ))

                nodes.append(UniversalNode(
                    node_id         = self.make_node_id(file_path, class_name, base_dir),
                    name            = class_name,
                    file_type       = "python_class",
                    file            = rel_file,
                    content_summary = f"Class with {len(method_names)} methods: {', '.join(method_names[:8])}",
                    links_to        = method_names,
                    metadata        = {
                        "line": item.lineno, 
                        "methods": method_names,
                        "file_mtime": mtime
                    },
                ))

            # Top-level functions (không nằm trong class)
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not self._is_method(item, tree):
                    calls   = self._collect_calls(item)
                    fn_type = "async_function" if isinstance(item, ast.AsyncFunctionDef) else "function"
                    nodes.append(UniversalNode(
                        node_id         = self.make_node_id(file_path, item.name, base_dir),
                        name            = item.name,
                        file_type       = fn_type,
                        file            = rel_file,
                        content_summary = f"{fn_type} at line {item.lineno}",
                        links_to        = calls,
                        metadata        = {
                            "line": item.lineno,
                            "file_mtime": mtime
                        },
                    ))

        return nodes

    @staticmethod
    def _collect_calls(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        calls: list[str] = []
        for child in ast.walk(func_node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return list(dict.fromkeys(calls))

    @staticmethod
    def _is_method(node: ast.AST, tree: ast.Module) -> bool:
        """Kiểm tra node có nằm trong class không."""
        for item in ast.walk(tree):
            if isinstance(item, ast.ClassDef):
                if node in item.body:
                    return True
        return False

@ParserRegistry.register(".png", ".jpg", ".jpeg")
class ImageParser(BaseParser):
    supported_extensions = {".png", ".jpg", ".jpeg"}

    async def parse(self, file_path: str, base_dir: str = "") -> list[UniversalNode]:
        rel_file = os.path.relpath(file_path, base_dir).replace("\\", "/") if base_dir else file_path
        return [UniversalNode(
            node_id = self.make_node_id(file_path, base_dir=base_dir),
            name = Path(file_path).stem,
            file_type = "image",
            file = rel_file,
            content_summary = "[Vision LLM Caption Placeholder]",
            metadata = {"file_mtime": os.path.getmtime(file_path)},
        )]

@ParserRegistry.register(".html", ".htm")
class HtmlParser(BaseParser):
    supported_extensions = {".html", ".htm"}

    async def parse(self, file_path: str, base_dir: str = "") -> list[UniversalNode]:
        rel_file = os.path.relpath(file_path, base_dir).replace("\\", "/") if base_dir else file_path
        return [UniversalNode(
            node_id = self.make_node_id(file_path, base_dir=base_dir),
            name = Path(file_path).stem,
            file_type = "html",
            file = rel_file,
            content_summary = "HTML parser placeholder",
            metadata = {"file_mtime": os.path.getmtime(file_path)},
        )]

# ═══════════════════════════════════════════════
# 5. OMNI SCANNER
# ═══════════════════════════════════════════════

# Thư mục cần bỏ qua
_IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules", ".mypy_cache", "dist", "build", ".gemini"}

async def scan_omni_directory(
    directory: str,
    *,
    max_concurrency: int = 20,
) -> list[UniversalNode]:
    """
    Quét toàn bộ directory với mọi parser đã đăng ký.
    FIX: asyncio.gather + semaphore thay vì sequential await.
    """
    import asyncio

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _safe_parse(file_path: str) -> list[UniversalNode]:
        parser = ParserRegistry.get(file_path)
        if not parser:
            return []
        async with semaphore:
            try:
                # [DYNAMIC-ROOT-INJECTION]: Truyen thu muc goc de chuan hoa
                return await parser.parse(file_path, base_dir=directory)
            except Exception as e:
                # FIX: Log lỗi thay vì nuốt im lặng
                logger.error(f"scan_omni_directory: failed parsing {file_path}: {e}", exc_info=True)
                return []

    # Thu thập tất cả file paths
    def _collect_files():
        paths = []
        for root, dirs, files in os.walk(directory):
            # Prune in-place để os.walk không đi vào thư mục cần bỏ qua
            dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS and not d.startswith(".")]
            for fname in files:
                fpath = os.path.join(root, fname)
                if ParserRegistry.get(fpath):
                    paths.append(fpath)
        return paths

    # 🛡️ [NEURAL-LIBERATION]: Chạy os.walk trong luồng riêng để không treo hệ thống
    file_paths = await asyncio.to_thread(_collect_files)

    # FIX: Parse song song thay vì tuần tự
    # ⚡ [CPU-BREATHER]: Chia nhỏ batch để Event Loop có thể xử lý các request chat
    results = []
    chunk_size = 50
    for i in range(0, len(file_paths), chunk_size):
        chunk = file_paths[i:i+chunk_size]
        res = await asyncio.gather(*[_safe_parse(p) for p in chunk])
        results.extend(res)
        await asyncio.sleep(0.01) # Nhường đường cho Master gõ lệnh
    
    all_nodes: list[UniversalNode] = [n for batch in results for n in batch]

    # Resolve backlinks
    _resolve_backlinks(all_nodes)

    logger.info(
        f"scan_omni_directory: {directory} → {len(all_nodes)} nodes "
        f"from {len(file_paths)} files | "
        f"types: {set(n.file_type for n in all_nodes)}"
    )
    return all_nodes


def _resolve_backlinks(nodes: list[UniversalNode]) -> None:
    """
    FIX: Multi-key inverted index thay vì name_dict bị ghi đè.
    Hỗ trợ lookup theo: node_id, name, stem (tên file không có ext).
    """
    # Build multi-key index: mỗi key → list node (không ghi đè)
    index: dict[str, list[UniversalNode]] = defaultdict(list)
    for node in nodes:
        index[node.node_id].append(node)
        index[node.name].append(node)
        index[Path(node.file).stem].append(node)

    # Tính linked_by
    for node in nodes:
        for ref in node.links_to:
            for target in index.get(ref, []):
                if target.node_id != node.node_id and node.node_id not in target.linked_by:
                    target.linked_by.append(node.node_id)
