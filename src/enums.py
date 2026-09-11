"""Extract enum / constant values related to the traced keyword."""
from __future__ import annotations

import re
from pathlib import Path

from discover import keyword_variants

_JAVA_ENUM_HEAD_RE = re.compile(r"\benum\s+(\w+)\b[^{]*\{")
_JAVA_CONST_RE = re.compile(
    r"\b([A-Z][A-Z0-9_]*)\s*(?:\((.*?)\))?(?=\s*[,;}]|\s*\{|\s*$)",
    re.DOTALL,
)
_JAVA_STATIC_RE = re.compile(
    r"(?:public|protected|private)?\s*static\s+final\s+[\w.<>,?]+\s+"
    r"([A-Z][A-Z0-9_]*)\s*=\s*(\"[^\"]*\"|'[^']*'|-?\d+)\s*;",
)
_JAVA_CLASS_RE = re.compile(r"\b(?:class|interface|enum)\s+(\w+)")
_PY_ENUM_CLASS_RE = re.compile(
    r"^class\s+(\w+)\s*\(([^)]*)\)\s*:",
    re.MULTILINE,
)
_PY_MEMBER_RE = re.compile(
    r"^\s{4}([A-Z][A-Z0-9_]*)\s*=\s*(\"[^\"]*\"|'[^']*'|-?\d+)\s*$",
    re.MULTILINE,
)
_CS_ENUM_HEAD_RE = re.compile(r"\benum\s+(\w+)\b(?:\s*:\s*[\w.]+)?\s*\{")
_CS_MEMBER_RE = re.compile(
    r"\b([A-Za-z_]\w*)\s*(?:=\s*(\"[^\"]*\"|'[^']*'|-?\d+))?",
)
_SKIP_ENUM_NAMES = {"optional", "override", "transient", "serializable"}


def _unquote(raw: str) -> str:
    s = (raw or "").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {"'", '"'}:
        return s[1:-1]
    return s


def _compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _related_name(name: str, keyword: str, variants: list[str]) -> bool:
    compact = _compact(name)
    if not compact or compact in _SKIP_ENUM_NAMES:
        return False
    keys = {_compact(keyword), *(_compact(v) for v in variants)}
    keys.discard("")
    if any(k and k in compact for k in keys):
        return True
    # status <-> OrderStatus / StatusEnum
    for suffix in ("enum", "type", "code", "state"):
        if compact.endswith(suffix) and compact[: -len(suffix)] in keys:
            return True
    return False


def _balanced_brace_body(text: str, open_idx: int) -> str:
    depth = 0
    quote = ""
    escape = False
    for i, ch in enumerate(text[open_idx:], open_idx):
        if escape:
            escape = False
            continue
        if quote:
            if ch == "\\":
                escape = True
                continue
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1: i]
    return text[open_idx + 1:]


def _constants_block(body: str) -> str:
    depth = 0
    quote = ""
    for i, ch in enumerate(body):
        if quote:
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            return body[:i]
    return body


def _split_args(args: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    quote = ""
    for ch in args or "":
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch == "(":
            depth += 1
            buf.append(ch)
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
            continue
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


def _java_values(body: str) -> list[dict]:
    values: list[dict] = []
    seen: set[str] = set()
    for m in _JAVA_CONST_RE.finditer(_constants_block(body)):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        args = _split_args(m.group(2) or "")
        value = _unquote(args[0]) if args else name
        label = _unquote(args[1]) if len(args) > 1 else ""
        values.append({"name": name, "value": value, "label": label})
    return values


def _parse_java_enums(text: str, file: str) -> list[dict]:
    out: list[dict] = []
    for m in _JAVA_ENUM_HEAD_RE.finditer(text):
        values = _java_values(_balanced_brace_body(text, m.end() - 1))
        if values:
            out.append({
                "name": m.group(1),
                "kind": "enum",
                "language": "java",
                "file": file,
                "values": values,
            })
    cls_m = _JAVA_CLASS_RE.search(text)
    cls = cls_m.group(1) if cls_m else Path(file).stem
    statics: list[dict] = []
    seen: set[str] = set()
    for m in _JAVA_STATIC_RE.finditer(text):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        statics.append({"name": name, "value": _unquote(m.group(2)), "label": ""})
    if statics and cls:
        out.append({
            "name": cls,
            "kind": "constants",
            "language": "java",
            "file": file,
            "values": statics,
        })
    return out


def _parse_python_enums(text: str, file: str) -> list[dict]:
    out: list[dict] = []
    for m in _PY_ENUM_CLASS_RE.finditer(text):
        bases = m.group(2).lower()
        if "enum" not in bases:
            continue
        window = text[m.end():]
        nxt = re.search(r"\nclass\s+", window)
        if nxt:
            window = window[: nxt.start()]
        values = []
        seen: set[str] = set()
        for mm in _PY_MEMBER_RE.finditer(window):
            name = mm.group(1)
            if name in seen:
                continue
            seen.add(name)
            values.append({"name": name, "value": _unquote(mm.group(2)), "label": ""})
        if values:
            out.append({
                "name": m.group(1),
                "kind": "enum",
                "language": "python",
                "file": file,
                "values": values,
            })
    return out


def _parse_csharp_enums(text: str, file: str) -> list[dict]:
    out: list[dict] = []
    for m in _CS_ENUM_HEAD_RE.finditer(text):
        values = []
        seen: set[str] = set()
        for mm in _CS_MEMBER_RE.finditer(_balanced_brace_body(text, m.end() - 1)):
            name = mm.group(1)
            if name in seen or name in {"enum"}:
                continue
            seen.add(name)
            raw = mm.group(2)
            values.append({
                "name": name,
                "value": _unquote(raw) if raw else name,
                "label": "",
            })
        if values:
            out.append({
                "name": m.group(1),
                "kind": "enum",
                "language": "csharp",
                "file": file,
                "values": values,
            })
    return out


def _field_type_hits(index, variants: list[str]) -> set[str]:
    names: set[str] = set()
    fields = getattr(index, "fields", None) or {}
    compact_vars = {_compact(v) for v in variants}
    compact_vars.discard("")
    for _cls, fmap in fields.items():
        for fname, ftype in fmap.items():
            if _compact(fname) in compact_vars and ftype:
                names.add(str(ftype).split(".")[-1].split("<")[0].strip())
    return names


def _parse_file(path: Path, rel: str) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    suffix = path.suffix.lower()
    if suffix == ".java":
        return _parse_java_enums(text, rel)
    if suffix == ".py":
        return _parse_python_enums(text, rel)
    if suffix == ".cs":
        return _parse_csharp_enums(text, rel)
    return []


def detect_enums(keyword: str, root: Path, index, extra_variants: list[str] | None = None) -> list[dict]:
    """Return enum/constant groups related to the traced keyword."""
    root = Path(root)
    variants = keyword_variants(keyword, extra_variants)
    type_hits = _field_type_hits(index, variants)
    exclude = {"node_modules", ".git", "target", "build", "bin", "obj",
               ".venv", "venv", "__pycache__", "dist", ".idea"}
    groups: list[dict] = []
    files = list(getattr(index, "files", {}) or {})
    if not files:
        for ext in (".java", ".py", ".cs"):
            files.extend(str(p) for p in root.rglob(f"*{ext}"))
    for raw in files:
        path = Path(raw)
        if any(part in exclude for part in path.parts):
            continue
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = path.as_posix()
        for group in _parse_file(path, rel):
            name = group.get("name") or ""
            if name in type_hits or _related_name(name, keyword, variants):
                groups.append(group)
    groups.sort(key=lambda g: (g.get("kind", ""), g.get("name", ""), g.get("file", "")))
    return groups
