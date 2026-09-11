"""Comments, API mappings, chain-scenario text, and enum-value usage sites."""
from __future__ import annotations

import re
from pathlib import Path

from discover import keyword_variants

_HTTP_METHOD = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": "HTTP",
}
_ROUTE_RE = re.compile(
    r"@(?:app|router|bp)\.(?:get|post|put|delete|patch)\(\s*[\"']([^\"']+)",
    re.IGNORECASE,
)
_CS_ROUTE_RE = re.compile(
    r"\[Http(Get|Post|Put|Delete|Patch)(?:\s*\(\s*\"([^\"]+)\")?",
    re.IGNORECASE,
)
_JAVADOC_RE = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"^\s*//\s*(.+)$")
_HASH_COMMENT_RE = re.compile(r"^\s*#\s*(.+)$")
_TRIPLE_RE = re.compile(r'^\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', re.DOTALL)
_XML_SUMMARY_RE = re.compile(r"<summary>\s*(.*?)\s*</summary>", re.DOTALL | re.IGNORECASE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_VERB_ZH = (
    ("query", "查询"), ("find", "查询"), ("get", "获取"), ("list", "列表查询"),
    ("search", "搜索"), ("select", "查询"), ("load", "加载"), ("read", "读取"),
    ("create", "创建"), ("add", "新增"), ("insert", "新增"), ("save", "保存"),
    ("update", "更新"), ("modify", "修改"), ("patch", "更新"), ("edit", "编辑"),
    ("delete", "删除"), ("remove", "删除"), ("cancel", "取消"),
    ("mark", "标记"), ("set", "设置"), ("change", "变更"),
)
_NOUN_ZH = (
    ("order", "订单"), ("store", "门店"), ("user", "用户"), ("status", "状态"),
    ("entry", "条目"), ("ticket", "工单"), ("item", "明细"),
)
def _first_cjk_line(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"^\s*\*\s?", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\{@\w+[^}]*\}", "", cleaned)
    cleaned = re.sub(r"@\w+.*", "", cleaned)
    for line in cleaned.splitlines():
        line = line.strip(" /*#")
        if _CJK_RE.search(line):
            return line[:80]
    return ""


def _comment_before(lines: list[str], line_no: int) -> str:
    """Best-effort doc comment immediately above 1-indexed line_no."""
    i = max(0, line_no - 2)
    # skip annotations / attributes / blank / decorators
    while i >= 0:
        raw = lines[i].strip()
        if not raw or raw.startswith("@") or raw.startswith("[") or raw.startswith("#"):
            if raw.startswith("#") and _CJK_RE.search(raw):
                break
            i -= 1
            continue
        break
    if i < 0:
        return ""
    chunk = "\n".join(lines[max(0, i - 16): i + 1])
    for rx in (_JAVADOC_RE, _XML_SUMMARY_RE, _TRIPLE_RE):
        matches = list(rx.finditer(chunk))
        if matches:
            zh = _first_cjk_line(matches[-1].group(1))
            if zh:
                return zh
    for j in range(i, max(-1, i - 6), -1):
        m = _LINE_COMMENT_RE.match(lines[j]) or _HASH_COMMENT_RE.match(lines[j])
        if m and _CJK_RE.search(m.group(1)):
            return m.group(1).strip()[:80]
        if lines[j].strip() and not lines[j].strip().startswith(("@", "[", "#", "//", "*")):
            break
    return ""


def _http_mapping(prefix: str) -> str:
    method = ""
    path = ""
    for name, verb in _HTTP_METHOD.items():
        if not re.search(rf"@(?:[\w.]+\.)?{name}\b", prefix):
            continue
        if name != "RequestMapping" or not method:
            method = verb
        m = re.search(
            rf"@(?:[\w.]+\.)?{name}\s*\(\s*(?:(?:value|path)\s*=\s*)?\"([^\"]+)\"",
            prefix,
        )
        if m and m.group(1) and (name != "RequestMapping" or not path):
            path = m.group(1)
    if method:
        return f"{method} {path}".strip()
    m = _ROUTE_RE.search(prefix)
    if m:
        return m.group(0).split("(")[0].split(".")[-1].upper() + " " + m.group(1)
    m = _CS_ROUTE_RE.search(prefix)
    if m:
        return f"{m.group(1).upper()} {m.group(2) or ''}".strip()
    return ""


def _purpose_from_name(label: str) -> str:
    method = (label or "").rsplit(".", 1)[-1]
    compact = method.replace("_", "").lower()
    verb = next((zh for en, zh in _VERB_ZH if compact.startswith(en)), "")
    nouns = [zh for en, zh in _NOUN_ZH if en in compact]
    if verb and nouns:
        return verb + "".join(dict.fromkeys(nouns))
    if verb:
        return verb
    if nouns:
        return "处理" + "".join(dict.fromkeys(nouns))
    return ""


def _read_lines(path: str) -> list[str]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def annotate_units(graph: dict) -> None:
    cache: dict[str, list[str]] = {}
    for node in graph.get("nodes", []):
        if node.get("kind") != "unit":
            continue
        path = node.get("file") or ""
        line = int(node.get("line") or 0)
        if path and path not in cache:
            cache[path] = _read_lines(path)
        lines = cache.get(path) or []
        comment = _comment_before(lines, line) if line else ""
        if not comment and path.endswith(".py") and line:
            after = "\n".join(lines[line: line + 6])
            dm = _TRIPLE_RE.search(after)
            if dm:
                comment = _first_cjk_line(dm.group(1))
        prefix = "\n".join(lines[max(0, line - 12): max(0, line)]) if line else ""
        api = _http_mapping(prefix)
        purpose = comment or _purpose_from_name(node.get("label") or "")
        if comment:
            node["title_zh"] = comment
        if api:
            node["api"] = api
        if purpose:
            node["purpose"] = purpose
        display = api or (node.get("label") or "").rsplit(".", 1)[-1]
        node["display_name"] = display
        if comment:
            node["summary"] = f"{display}：{comment}"
        elif purpose:
            node["summary"] = f"{display}：{purpose}"


def _path_purpose(graph: dict, path: dict) -> str:
    node_by_id = {n["id"]: n for n in graph.get("nodes", [])}
    parts: list[str] = []
    entry = ""
    for nid, layer in zip(path.get("nodes") or [], path.get("layers") or []):
        node = node_by_id.get(nid) or {}
        if layer == "Controller" and not entry:
            entry = node.get("api") or node.get("display_name") or node.get("label") or ""
        zh = node.get("title_zh") or node.get("purpose") or ""
        if zh and zh not in parts:
            parts.append(zh)
    table = path.get("table") or ""
    if not parts:
        labels = path.get("labels") or []
        if labels:
            parts.append(_purpose_from_name(labels[0]) or "字段沿调用链传递")
    action = "；".join(parts[:3])
    if table:
        action = f"{action}，最终访问表 {table}" if action else f"访问表 {table}"
    title = parts[0] if parts else "字段调用链"
    return title, action, entry


def annotate_paths(graph: dict, keyword: str) -> None:
    scenarios: list[dict] = []
    for i, path in enumerate(graph.get("main_paths") or [], 1):
        title, purpose, entry = _path_purpose(graph, path)
        path["title"] = title
        path["purpose"] = purpose
        path["entry"] = entry
        path["keyword"] = keyword
        scenarios.append({
            "id": f"path-{i}",
            "title": title,
            "purpose": purpose,
            "entry": entry,
            "chain": " → ".join(path.get("labels") or []),
            "table": path.get("table") or "",
            "nodes": path.get("nodes") or [],
        })
    if not scenarios:
        units = [n for n in graph.get("nodes", []) if n.get("kind") == "unit" and n.get("usages")]
        for i, node in enumerate(units[:6], 1):
            title = node.get("title_zh") or node.get("purpose") or _purpose_from_name(node.get("label") or "")
            scenarios.append({
                "id": f"use-{i}",
                "title": title or (node.get("label") or ""),
                "purpose": node.get("purpose") or title,
                "entry": node.get("api") or node.get("label") or "",
                "chain": node.get("label") or "",
                "table": "",
                "nodes": [node["id"]],
            })
    graph["scenarios"] = scenarios


def _trigger_of(snippet: str) -> str:
    s = snippet or ""
    low = s.lower()
    if re.search(r"\bswitch\b|\bcase\b", s):
        return "switch 分支"
    if re.search(r"\bif\s*\(|elif\s|\bwhen\b", s, re.I) or "==" in s or ".equals(" in low:
        return "条件判断"
    if "=" in s and "==" not in s:
        return "赋值"
    if "(" in s:
        return "方法调用"
    return "引用"


def _scenario_of(method_label: str, comment: str, trigger: str) -> str:
    bits = [p for p in (comment, _purpose_from_name(method_label), trigger) if p]
    return "，".join(dict.fromkeys(bits))


def annotate_enum_usages(graph: dict, index, keyword: str) -> None:
    variants = keyword_variants(keyword)
    groups = graph.get("field_enums") or []
    if not groups:
        return
    files = list(getattr(index, "files", {}) or {})
    texts: dict[str, tuple[str, list[str]]] = {}
    for raw in files:
        path = Path(raw)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        texts[str(path)] = (text, text.splitlines())
    kw_rx = re.compile("|".join(rf"(?<![\w$]){re.escape(v)}(?![\w$])" for v in variants[:8]) or r"(?!)")

    for group in groups:
        enum_name = group.get("name") or ""
        enum_rx = re.compile(rf"(?<![\w$]){re.escape(enum_name)}(?![\w$])") if enum_name else None
        for item in group.get("values") or []:
            usages: list[dict] = []
            seen: set[tuple[str, int]] = set()
            name = str(item.get("name") or "")
            value = str(item.get("value") or "")
            patterns: list[re.Pattern[str]] = []
            if enum_name and name:
                patterns.append(re.compile(
                    rf"(?<![\w$]){re.escape(enum_name)}\s*\.\s*{re.escape(name)}(?![\w$])"))
            if name:
                patterns.append(re.compile(rf"\bcase\s+{re.escape(name)}\b"))
            if value:
                patterns.append(re.compile(rf"\bcase\s+[\"']{re.escape(value)}[\"']"))
            for path_s, (text, lines) in texts.items():
                rel = Path(path_s).as_posix()
                enum_file = str(group.get("file") or "").replace("\\", "/")
                if enum_file and rel.endswith(enum_file) and f"enum {enum_name}" in text:
                    continue
                for i, line in enumerate(lines, 1):
                    hit = any(p.search(line) for p in patterns)
                    if not hit and value:
                        quoted = re.search(rf"[\"']{re.escape(value)}[\"']", line)
                        hit = bool(quoted and (kw_rx.search(line) or (enum_rx and enum_rx.search(line))))
                    if not hit or (path_s, i) in seen:
                        continue
                    seen.add((path_s, i))
                    method = None
                    if index is not None and hasattr(index, "enclosing_method"):
                        method = index.enclosing_method(path_s, i)
                    label = method.qual if method else ""
                    comment = _comment_before(lines, method.start_line if method else i)
                    snippet = line.strip()
                    trigger = _trigger_of(snippet)
                    usages.append({
                        "file": path_s,
                        "line": i,
                        "method": label,
                        "layer": (getattr(index, "layers", {}) or {}).get(path_s, ""),
                        "snippet": snippet[:200],
                        "trigger": trigger,
                        "scenario": _scenario_of(label, comment, trigger),
                    })
                    if len(usages) >= 12:
                        break
                if len(usages) >= 12:
                    break
            item["usages"] = usages
            if not item.get("label"):
                for u in usages:
                    if _CJK_RE.search(u.get("scenario") or ""):
                        zh = (u.get("scenario") or "").split("，")[0]
                        if zh and zh not in {"条件判断", "switch 分支", "赋值", "方法调用", "引用"}:
                            item["label"] = zh
                            break


def attach_semantics(graph: dict, index, keyword: str) -> dict:
    annotate_units(graph)
    annotate_paths(graph, keyword)
    annotate_enum_usages(graph, index, keyword)
    return graph
