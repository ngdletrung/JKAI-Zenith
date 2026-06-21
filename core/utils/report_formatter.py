"""
📋 JKAI Report Formatter — Standardized report format utility.
Mọi báo cáo trong hệ thống dùng utility này để đảm bảo format đồng nhất.
"""


def header(title: str, subtitle: str = None) -> str:
    parts = [f"# {title}"]
    if subtitle:
        parts.append(f"> {subtitle}")
    parts.append("")
    return "\n".join(parts)


def section(title: str, level: int = 2) -> str:
    return f"{'#' * level} {title}"


def table(headers: list, rows: list) -> str:
    if not headers or not rows:
        return ""
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    hdr = "| " + " | ".join(headers) + " |"
    lines = [hdr, sep]
    for row in rows:
        vals = [str(v) if v is not None else "" for v in row]
        # Ensure row has same length as headers
        while len(vals) < len(headers):
            vals.append("")
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def kvdict(data: dict, key_label: str = "Key", val_label: str = "Value") -> str:
    return table([key_label, val_label], [[k, v] for k, v in data.items()])


def bullet(items: list, indent: int = 0) -> str:
    prefix = "  " * indent + "- "
    return "\n".join(f"{prefix}{item}" for item in items)


def separator(char: str = "—", length: int = 48) -> str:
    return char * length


def status_badge(ok: bool, text_ok: str = "ON DINH", text_fail: str = "THAT BAI") -> str:
    return f"{'✅' if ok else '❌'} {text_ok if ok else text_fail}"


def count_badge(count: int, label: str) -> str:
    return f"**{count}** {label}"


def build(parts: list, joiner: str = "\n\n") -> str:
    return joiner.join(p for p in parts if p)


def summary_box(items: list, title: str = "TONG QUAN") -> str:
    rows = []
    for item in items:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            rows.append([str(item[0]), str(item[1])])
        else:
            rows.append(["", str(item)])
    t = table(["Chi tiet", "Gia tri"], rows)
    return f"### {title}\n{t}"
