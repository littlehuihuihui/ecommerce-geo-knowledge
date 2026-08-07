# -*- coding: utf-8 -*-
"""从 metrics / methodology / interview 抽取知识图谱数据，关联仅来自正文名称匹配。"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent
OUT_JS = ROOT / "knowledge-graph-data.js"
OUT_JSON = ROOT / "knowledge-graph-data.json"


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        if tag in ("li", "p", "br", "div", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    if not html or not html.strip():
        return ""
    p = _TextExtractor()
    try:
        p.feed(html)
        return p.get_text()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)


def extract_array_block(text: str, var_name: str) -> str:
    m = re.search(rf"const {var_name} = \[", text)
    if not m:
        raise ValueError(f"cannot find const {var_name}")
    start = m.end() - 1
    depth = 0
    in_str = None
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'", "`"):
            in_str = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i]
    raise ValueError(f"unterminated array for {var_name}")


def parse_js_string(s: str) -> str:
    s = s.strip()
    if s.startswith("`") and s.endswith("`"):
        return s[1:-1]
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        inner = s[1:-1]
        return (
            inner.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\'", "'")
            .replace("\\\\", "\\")
        )
    return s


def split_top_level_objects(block: str) -> list[str]:
    objs: list[str] = []
    depth = 0
    start = None
    in_str = None
    escape = False
    i = 0
    while i < len(block):
        ch = block[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
        else:
            if ch in ('"', "'", "`"):
                in_str = ch
            elif ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    objs.append(block[start : i + 1])
                    start = None
        i += 1
    return objs


def get_field(obj: str, key: str) -> str | None:
    # string / template
    m = re.search(
        rf"(?:^|[{{,;\n])\s*{re.escape(key)}\s*:\s*((?:`(?:\\.|[^`])*`)|(?:\"(?:\\.|[^\"])*\")|(?:'(?:\\.|[^'])*'))",
        obj,
        re.S,
    )
    if m:
        return parse_js_string(m.group(1))
    # number
    m = re.search(rf"(?:^|[{{,;\n])\s*{re.escape(key)}\s*:\s*(\d+(?:\.\d+)?)", obj)
    if m:
        return m.group(1)
    return None


def get_string_array(obj: str, key: str) -> list[str]:
    m = re.search(rf"(?:^|[{{,;\n])\s*{re.escape(key)}\s*:\s*\[(.*?)\]", obj, re.S)
    if not m:
        return []
    return re.findall(r'["\']([^"\']+)["\']', m.group(1))


def slug(prefix: str, name: str, extra: str = "") -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name).strip("_")
    if extra:
        base = f"{base}_{extra}"
    return f"{prefix}_{base}"


def extract_metrics() -> list[dict]:
    text = (ROOT / "metrics.html").read_text(encoding="utf-8")
    block = extract_array_block(text, "metrics")
    nodes = []
    seen = set()
    for i, obj in enumerate(split_top_level_objects(block)):
        name = get_field(obj, "name")
        if not name:
            continue
        cat = get_field(obj, "category") or "other"
        cat_name = get_field(obj, "categoryName") or cat
        nid = slug("metric", name, cat)
        if nid in seen:
            nid = f"{nid}_{i}"
        seen.add(nid)
        nodes.append(
            {
                "id": nid,
                "name": name,
                "type": "metric",
                "description": get_field(obj, "desc") or "",
                "level": 2,
                "category": cat,
                "categoryName": cat_name,
                "icon": get_field(obj, "icon") or "",
                "tags": get_string_array(obj, "tags"),
                "detail": {
                    "definition": get_field(obj, "desc") or "",
                    "formula": get_field(obj, "formula") or "",
                    "notes": get_string_array(obj, "tags"),
                },
                "crossRefs": [],
            }
        )
    return nodes


def extract_methods() -> list[dict]:
    text = (ROOT / "methodology.html").read_text(encoding="utf-8")
    block = extract_array_block(text, "methods")
    nodes = []
    seen = set()
    for i, obj in enumerate(split_top_level_objects(block)):
        name = get_field(obj, "name")
        if not name:
            continue
        cat = get_field(obj, "category") or "other"
        cat_name = get_field(obj, "categoryName") or cat
        nid = slug("method", name, cat)
        if nid in seen:
            nid = f"{nid}_{i}"
        seen.add(nid)
        scenarios = get_string_array(obj, "scenarios")
        nodes.append(
            {
                "id": nid,
                "name": name,
                "type": "methodology",
                "description": get_field(obj, "desc") or "",
                "level": 2,
                "category": cat,
                "categoryName": cat_name,
                "icon": get_field(obj, "icon") or "",
                "subtitle": get_field(obj, "subtitle") or "",
                "detail": {
                    "definition": get_field(obj, "desc") or "",
                    "formula": get_field(obj, "formula") or "",
                    "applicableScenarios": scenarios,
                    "notes": [],
                },
                "crossRefs": [],
                "_search_text": " ".join(
                    [
                        name,
                        get_field(obj, "subtitle") or "",
                        get_field(obj, "desc") or "",
                        get_field(obj, "formula") or "",
                        " ".join(scenarios),
                    ]
                ),
            }
        )
    return nodes


def extract_questions() -> list[dict]:
    text = (ROOT / "interview.html").read_text(encoding="utf-8")
    block = extract_array_block(text, "questions")
    cat_objs = split_top_level_objects(block)
    nodes = []
    seen = set()

    def add_question(title, answer_text, cat, cat_name, icon, difficulty, qi=0):
        steps = [ln.strip(" -•\t") for ln in answer_text.split("\n") if ln.strip()]
        if len(steps) > 40:
            steps = steps[:40]
        nid = slug("problem", title[:40], cat)
        if nid in seen:
            nid = f"{nid}_{qi}"
        seen.add(nid)
        nodes.append(
            {
                "id": nid,
                "name": title,
                "type": "business_problem",
                "description": (answer_text[:120] + "…") if len(answer_text) > 120 else answer_text,
                "level": 2,
                "category": cat,
                "categoryName": cat_name,
                "icon": icon,
                "difficulty": difficulty or "",
                "detail": {
                    "definition": answer_text,
                    "steps": steps,
                    "notes": [],
                },
                "crossRefs": [],
                "_search_text": title + "\n" + answer_text,
            }
        )

    for cat_obj in cat_objs:
        # Alternate schema: { id, category, question: { title, desc, answer: [...] } }
        if re.search(r"(?:^|[{,;\n])\s*question\s*:\s*\{", cat_obj):
            cat = get_field(cat_obj, "category") or "other"
            cat_name = get_field(cat_obj, "categoryName") or cat
            difficulty = get_field(cat_obj, "difficulty") or ""
            qm = re.search(r"question\s*:\s*\{", cat_obj)
            if not qm:
                continue
            # extract question object
            start = qm.end() - 1
            depth = 0
            end = start
            in_str = None
            escape = False
            for i in range(start, len(cat_obj)):
                ch = cat_obj[i]
                if in_str:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == in_str:
                        in_str = None
                    continue
                if ch in ('"', "'", "`"):
                    in_str = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            qobj = cat_obj[start : end + 1]
            title = get_field(qobj, "title")
            if not title:
                continue
            desc = get_field(qobj, "desc") or ""
            # answer may be string array
            ans_arr = get_string_array(qobj, "answer")
            if ans_arr:
                answer_text = "\n".join(ans_arr)
            else:
                answer_html = get_field(qobj, "answer") or ""
                answer_text = html_to_text(answer_html) if answer_html else desc
            if desc and desc not in answer_text:
                answer_text = desc + "\n" + answer_text
            add_question(title, answer_text, cat, cat_name, "", difficulty)
            continue

        cat = get_field(cat_obj, "category") or "other"
        cat_name = get_field(cat_obj, "categoryName") or cat
        icon = get_field(cat_obj, "icon") or ""
        m = re.search(r"list\s*:\s*\[", cat_obj)
        if not m:
            continue
        start = m.end() - 1
        depth = 0
        end = start
        in_str = None
        escape = False
        for i in range(start, len(cat_obj)):
            ch = cat_obj[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_str:
                    in_str = None
                continue
            if ch in ('"', "'", "`"):
                in_str = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        list_block = cat_obj[start + 1 : end]
        for qi, qobj in enumerate(split_top_level_objects(list_block)):
            title = get_field(qobj, "title")
            if not title:
                continue
            answer_html = get_field(qobj, "answer") or ""
            answer_text = html_to_text(answer_html)
            add_question(
                title,
                answer_text,
                cat,
                cat_name,
                icon,
                get_field(qobj, "difficulty") or "",
                qi,
            )
    return nodes


def build_alias_map(metrics: list[dict], methods: list[dict]) -> list[tuple[str, str, str]]:
    """Return list of (alias_lower_or_raw, node_id, type) sorted by alias length desc."""
    aliases: list[tuple[str, str, str]] = []
    for n in methods:
        names = {n["name"]}
        sub = n.get("subtitle") or ""
        if sub:
            # take first english chunk before ·
            for part in re.split(r"[·|/]", sub):
                part = part.strip()
                if len(part) >= 3:
                    names.add(part)
        # short aliases for common methods
        short = n["name"]
        for suffix in ("模型", "分析", "方法"):
            if short.endswith(suffix) and len(short) > len(suffix) + 1:
                core = short[: -len(suffix)]
                if len(core) >= 3:
                    names.add(core)
        for name in names:
            aliases.append((name, n["id"], "methodology"))

    for n in metrics:
        names = {n["name"]}
        # extract Chinese core before （ or (
        m = re.match(r"^([^（(]+)", n["name"])
        if m:
            core = m.group(1).strip()
            if len(core) >= 2:
                names.add(core)
        # english acronym in parentheses
        for ac in re.findall(r"[（(]([A-Za-z][A-Za-z0-9 /_-]{1,20})[）)]", n["name"]):
            ac = ac.strip()
            if len(ac) >= 2:
                names.add(ac)
                names.add(ac.upper())
        for name in names:
            aliases.append((name, n["id"], "metric"))

    # longer first to prefer specific matches
    aliases.sort(key=lambda x: len(x[0]), reverse=True)
    return aliases


def find_mentions(text: str, aliases: list[tuple[str, str, str]], self_id: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    seen = {self_id}
    # mark occupied spans to avoid overlapping weaker matches
    occupied = [False] * len(text)
    lower = text  # Chinese case-sensitive; for ascii compare both
    text_lower = text.lower()

    for alias, nid, _ in aliases:
        if nid in seen:
            continue
        if len(alias) < 2:
            continue
        # ascii aliases: case-insensitive
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _/-]*", alias):
            pattern = re.compile(re.escape(alias), re.I)
            search_in = text
        else:
            pattern = re.compile(re.escape(alias))
            search_in = text
        for m in pattern.finditer(search_in):
            a, b = m.start(), m.end()
            if any(occupied[a:b]):
                continue
            for i in range(a, b):
                occupied[i] = True
            seen.add(nid)
            found.append(nid)
            break
    return found


def wire_cross_refs(problems, methods, metrics):
    aliases = build_alias_map(metrics, methods)
    # reverse map id -> node
    by_id = {n["id"]: n for n in problems + methods + metrics}
    # also allow methods to mention metrics and vice versa
    for n in problems:
        text = n.pop("_search_text", n["name"] + "\n" + (n["detail"].get("definition") or ""))
        refs = find_mentions(text, aliases, n["id"])
        n["crossRefs"] = refs

    method_aliases_for_metrics = [
        (a, i, t) for a, i, t in aliases if t == "methodology"
    ]
    metric_aliases = [(a, i, t) for a, i, t in aliases if t == "metric"]

    for n in methods:
        text = n.pop("_search_text", "")
        refs = find_mentions(text, metric_aliases, n["id"])
        # also related questions that already point here — filled later
        n["crossRefs"] = refs

    for n in metrics:
        text = "\n".join(
            [
                n["name"],
                n["detail"].get("definition") or "",
                n["detail"].get("formula") or "",
            ]
        )
        refs = find_mentions(text, method_aliases_for_metrics, n["id"])
        n["crossRefs"] = refs

    # bidirectional: if A refs B, add A to B
    for n in problems + methods + metrics:
        for rid in list(n["crossRefs"]):
            other = by_id.get(rid)
            if other and n["id"] not in other["crossRefs"]:
                other["crossRefs"].append(n["id"])


def build_categories(nodes: list[dict], type_name: str, root_id: str, root_name: str) -> tuple[list[dict], list[dict]]:
    """Return (category_nodes + root, parent_edges within plate)."""
    cats: dict[str, dict] = {}
    edges = []
    root = {
        "id": root_id,
        "name": root_name,
        "type": type_name,
        "description": root_name,
        "level": 0,
        "isRoot": True,
        "detail": {"definition": f"{root_name}入口，点击分类节点展开具体内容。"},
        "crossRefs": [],
        "childrenIds": [],
    }
    for n in nodes:
        key = n["category"]
        cid = f"cat_{type_name}_{key}"
        if key not in cats:
            cats[key] = {
                "id": cid,
                "name": n.get("categoryName") or key,
                "type": type_name,
                "description": n.get("categoryName") or key,
                "level": 1,
                "isCategory": True,
                "category": key,
                "categoryName": n.get("categoryName") or key,
                "icon": n.get("icon") or "",
                "detail": {"definition": f"「{n.get('categoryName') or key}」下的{root_name}条目。"},
                "crossRefs": [],
                "childrenIds": [],
            }
            root["childrenIds"].append(cid)
            edges.append(
                {
                    "id": f"e_{root_id}_{cid}",
                    "source": root_id,
                    "target": cid,
                    "label": "包含",
                    "style": "solid",
                    "plate": type_name,
                }
            )
        cats[key]["childrenIds"].append(n["id"])
        n["parentId"] = cats[key]["id"]
        edges.append(
            {
                "id": f"e_{cid}_{n['id']}",
                "source": cid,
                "target": n["id"],
                "label": "包含",
                "style": "solid",
                "plate": type_name,
            }
        )
    cat_list = list(cats.values())
    root["childrenIds"] = [c["id"] for c in cat_list]
    return [root] + cat_list, edges


def relation_label(src_type: str, tgt_type: str) -> str:
    mapping = {
        ("business_problem", "methodology"): "分析方法",
        ("business_problem", "metric"): "使用指标",
        ("methodology", "metric"): "使用指标",
        ("methodology", "business_problem"): "解决业务问题",
        ("metric", "methodology"): "分析方法",
        ("metric", "business_problem"): "解决业务问题",
        ("business_problem", "business_problem"): "相关问题",
        ("methodology", "methodology"): "相关方法",
        ("metric", "metric"): "相关指标",
    }
    return mapping.get((src_type, tgt_type), "关联")


def build_cross_edges(nodes: list[dict]) -> list[dict]:
    by_id = {n["id"]: n for n in nodes}
    edges = []
    seen = set()
    for n in nodes:
        if n.get("isRoot") or n.get("isCategory"):
            continue
        for rid in n.get("crossRefs") or []:
            if rid not in by_id:
                continue
            a, b = sorted([n["id"], rid])
            key = (a, b)
            if key in seen:
                continue
            seen.add(key)
            other = by_id[rid]
            edges.append(
                {
                    "id": f"x_{a}_{b}",
                    "source": n["id"],
                    "target": rid,
                    "label": relation_label(n["type"], other["type"]),
                    "style": "dashed",
                    "cross": True,
                }
            )
    return edges


def main():
    metrics = extract_metrics()
    methods = extract_methods()
    problems = extract_questions()
    wire_cross_refs(problems, methods, metrics)

    bp_struct, bp_edges = build_categories(
        problems, "business_problem", "root_business_problem", "业务问题拆解"
    )
    md_struct, md_edges = build_categories(
        methods, "methodology", "root_methodology", "方法论"
    )
    mt_struct, mt_edges = build_categories(
        metrics, "metric", "root_metric", "指标字典"
    )

    all_nodes = bp_struct + problems + md_struct + methods + mt_struct + metrics
    # strip internal fields
    for n in all_nodes:
        n.pop("_search_text", None)

    plate_edges = bp_edges + md_edges + mt_edges
    cross_edges = build_cross_edges(all_nodes)

    data = {
        "meta": {
            "source": ["interview.html", "methodology.html", "metrics.html"],
            "counts": {
                "business_problems": len(problems),
                "methodologies": len(methods),
                "metrics": len(metrics),
                "cross_edges": len(cross_edges),
            },
            "note": "crossRefs 由正文名称匹配生成，未人工编造关联",
        },
        "plates": {
            "business_problem": {
                "id": "business_problem",
                "name": "业务问题拆解",
                "color": "#4A90D9",
                "rootId": "root_business_problem",
            },
            "methodology": {
                "id": "methodology",
                "name": "方法论",
                "color": "#52C41A",
                "rootId": "root_methodology",
            },
            "metric": {
                "id": "metric",
                "name": "指标字典",
                "color": "#FA8C16",
                "rootId": "root_metric",
            },
        },
        "nodes": all_nodes,
        "edges": plate_edges + cross_edges,
    }

    OUT_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    js = (
        "/* Auto-generated by _build_knowledge_graph_data.py — do not edit by hand */\n"
        "window.KNOWLEDGE_GRAPH_DATA = "
        + json.dumps(data, ensure_ascii=False)
        + ";\n"
    )
    OUT_JS.write_text(js, encoding="utf-8")
    print(
        "OK",
        data["meta"]["counts"],
        "nodes",
        len(all_nodes),
        "edges",
        len(data["edges"]),
    )


if __name__ == "__main__":
    # fix Chinese quotes if any slipped in - use normal
    main()
