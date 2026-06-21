#!/usr/bin/env python3
"""Generate interactive documentation graph (doc/doc_graph.html).

Scans doc/ for markdown/yaml files, extracts cross-references via regex,
categorizes documents, and produces a standalone HTML file with a D3.js
force-directed graph.

Usage:
    python scripts/generate_doc_graph.py              # regenerate HTML
    python scripts/generate_doc_graph.py --dry-run     # print stats only
    python scripts/generate_doc_graph.py --json        # dump graph data as JSON
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DOC_DIR = ROOT / "doc"
OUTPUT_HTML = DOC_DIR / "doc_graph.html"

# ── category rules ─────────────────────────────────────────────────
# Order matters: first match wins.  Paths are relative to doc/.
CATEGORY_RULES: list[tuple[str, str]] = [
    # Entry points
    ("index.md", "entry"),
    ("readme.md", "entry"),
    ("conventions.md", "entry"),
    # Vision
    ("vision.md", "vision"),
    ("roadmap.md", "vision"),
    ("product_idea.md", "vision"),
    ("pitch.md", "vision"),
    ("cjm.md", "vision"),
    ("smart_study_router.md", "vision"),
    ("future_roadmap.md", "vision"),
    ("roadmap_governance.md", "vision"),
    ("glossary.md", "vision"),
    # UX
    ("user_guide", "ux"),
    ("user_scenarios", "ux"),
    ("quickstart", "ux"),
    ("local_llm", "ux"),
    ("expert_controls", "ux"),
    # Architecture
    ("architecture.md", "arch"),
    ("technical_specification", "arch"),
    ("api_reference", "arch"),
    ("adr", "arch"),
    ("personalized_learner_model", "arch"),
    ("observability_slo", "arch"),
    ("index_lifecycle", "arch"),
    ("data_governance", "arch"),
    ("ssr_", "arch"),
    ("eval_experimenter", "arch"),
    # Conventions
    ("conventions_architecture", "conventions"),
    ("conventions_reference", "conventions"),
    # Backlog
    ("backlog_registry", "backlog"),
    ("tasklist", "backlog"),
    ("current_task", "backlog"),
    ("tail_sweep", "backlog"),
    # User stories
    ("user_stories", "user-stories"),
    # Workflow
    ("agent_workflow", "workflow"),
    ("team_workflow/", "workflow"),
    # Token safety
    ("token_safety", "token"),
    ("kilo_budget", "token"),
    ("kilo_proxy", "token"),
    ("TOKEN_", "token"),
    ("QUICK_READSET", "token"),
    ("MICROPLAN", "token"),
    ("VALIDATOR_FLOWCHART", "token"),
    ("loop_metrics", "token"),
    # History
    ("changelog", "history"),
    ("closed_iterations", "history"),
    ("epochs/", "history"),
    # Prompts
    ("prompts_catalog", "prompts"),
    ("prompts_usage", "prompts"),
    # Next breakthrough
    ("next/", "next"),
    # Scenarios
    ("scenarios/", "scenarios"),
    # Presentations
    ("presentations/", "presentations"),
    ("presenter_script", "presentations"),
    # Archive
    ("archive/", "archive"),
]

CATEGORIES_META = {
    "entry":         {"label": "📍 Точки входа",           "color": "#fbbf24"},
    "vision":        {"label": "🌟 Продуктовое видение",    "color": "#8b5cf6"},
    "ux":            {"label": "📚 Пользовательский опыт",   "color": "#ec4899"},
    "arch":          {"label": "🏛️ Архитектура и спеки",     "color": "#4a9eff"},
    "conventions":   {"label": "🛠️ Конвенции",              "color": "#06b6d4"},
    "backlog":       {"label": "📋 Бэклог и планирование",   "color": "#f59e0b"},
    "workflow":      {"label": "🤖 Workflow и агенты",       "color": "#10b981"},
    "token":         {"label": "🛡️ Token Safety",           "color": "#ef4444"},
    "history":       {"label": "📜 История и эволюция",      "color": "#6366f1"},
    "prompts":       {"label": "📚 Промпты",                "color": "#f97316"},
    "next":          {"label": "🚀 Следующий прорыв",        "color": "#a855f7"},
    "scenarios":     {"label": "🎬 Сценарии",               "color": "#14b8a6"},
    "presentations": {"label": "🎤 Презентации",            "color": "#fb7185"},
    "user-stories":  {"label": "📖 User Stories",           "color": "#c084fc"},
    "archive":       {"label": "🗄️ Архив",                  "color": "#555570"},
    "other":         {"label": "📄 Прочее",                 "color": "#888"},
}

READING_PATHS = {
    "newcomer":  {"label": "🆕 Путь новичка",
                  "path": ["readme.md", "quickstart.md", "vision.md",
                           "user_guide.md", "architecture.md"]},
    "user":      {"label": "👤 Путь пользователя",
                  "path": ["user_guide.md", "user_scenarios.md",
                           "quickstart_demo.md", "user_guide_details.md"]},
    "po":        {"label": "📊 Путь PO/Аналитика",
                  "path": ["vision.md", "cjm.md", "user_stories.md",
                           "backlog_registry.yaml", "roadmap.md"]},
    "architect": {"label": "🏗️ Путь архитектора",
                  "path": ["architecture.md", "adr.md",
                           "conventions_architecture.md",
                           "smart_study_router.md", "observability_slo.md"]},
    "developer": {"label": "💻 Путь разработчика",
                  "path": ["conventions.md", "technical_specification.md",
                           "api_reference.md", "agent_workflow.md",
                           "conventions_reference.md"]},
    "tester":    {"label": "🧪 Путь тестировщика",
                  "path": ["user_scenarios.md", "scenarios/README.md",
                           "agent_workflow_test_bundles.md",
                           "quickstart_demo.md"]},
    "agent":     {"label": "🤖 Путь AI-агента",
                  "path": ["CLAUDE.md", "token_safety.md",
                           "agent_workflow.md", "team_workflow/README.md",
                           "agent_workflow_rules.md"]},
    "devops":    {"label": "🚀 Путь DevOps",
                  "path": ["observability_slo.md", "index_lifecycle.md",
                           "kilo_budget_system.md", "local_llm_runbook.md"]},
}

# Files to always include even if they are outside doc/
EXTRA_NODES = ["CLAUDE.md"]

# ── skip patterns ──────────────────────────────────────────────────
SKIP_PATTERNS = [
    re.compile(r"\.obsidian"),
    re.compile(r"screenshots/"),
    re.compile(r"cost_logs/"),
    re.compile(r"perf/"),
    re.compile(r"eval/"),
    re.compile(r"kilo_budget_probes/"),
]

# Link patterns: markdown [text](path) and wiki [[path]]
MD_LINK_RE = re.compile(
    r"""\[(?:[^\]]*)\]        # [link text]
        \(                    # (
        (?!https?://|mailto:) # skip external URLs
        ([^)\s#]+)            # capture path (stop at ), space, #)
        (?:\#[^)]*)?          # optional #anchor
        \)                    # )
    """,
    re.VERBOSE,
)
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)")


def should_skip(rel: str) -> bool:
    """Return True if the file should be excluded from the graph."""
    return any(p.search(rel) for p in SKIP_PATTERNS)


def categorize(rel: str) -> str:
    """Assign a category to a doc-relative path."""
    rel_lower = rel.lower().replace("\\", "/")
    for pattern, cat in CATEGORY_RULES:
        if pattern.lower() in rel_lower:
            return cat
    return "other"


def make_description(rel: str, first_line: str) -> str:
    """Build a short description from the file's first heading or path."""
    # Try to extract first markdown heading
    m = re.match(r"#+ (.+)", first_line.strip())
    if m:
        return m.group(1).strip()
    return rel


def scan_documents() -> tuple[dict[str, dict], list[dict]]:
    """Scan doc/ and return (nodes_dict, edges_list).

    nodes_dict: {rel_path: {id, label, cat, desc}}
    edges_list: [{source, target}]
    """
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    # Collect all relevant files
    all_files: list[Path] = []
    for ext in ("*.md", "*.yaml", "*.json"):
        all_files.extend(DOC_DIR.rglob(ext))

    # Add CLAUDE.md from root
    claude = ROOT / "CLAUDE.md"
    if claude.exists():
        all_files.append(claude)

    # Also check AGENTS.md
    agents = ROOT / "AGENTS.md"
    if agents.exists():
        all_files.append(agents)

    for fpath in sorted(set(all_files)):
        # Compute relative path
        try:
            rel = fpath.relative_to(DOC_DIR).as_posix()
        except ValueError:
            # Files outside doc/ (e.g. CLAUDE.md)
            rel = fpath.relative_to(ROOT).as_posix()

        if should_skip(rel):
            continue

        # Skip binary files
        if fpath.suffix in (".pdf", ".png", ".jpg", ".gif"):
            continue

        # Skip individual user story files (too many), keep index
        if re.match(r"user_stories/us-\d", rel):
            continue

        # Skip individual scenario YAML files, keep README
        if re.match(r"scenarios/scenario_", rel):
            continue

        # Skip individual epoch files, keep as cluster
        if re.match(r"epochs/e\d", rel):
            continue

        # Skip team_workflow audit subdirectories detail files
        if re.match(r"team_workflow/audit_groups_.*/.+", rel) and "README" not in rel:
            continue

        # Skip archive detail files
        if rel.startswith("archive/") and rel.count("/") > 1:
            continue

        # Read first line for description
        first_line = ""
        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        first_line = stripped
                        break
        except OSError:
            pass

        cat = categorize(rel)
        desc = make_description(rel, first_line)
        label = rel
        # Shorten long labels
        if len(label) > 35:
            label = "…/" + Path(rel).name

        nodes[rel] = {
            "id": rel,
            "label": label,
            "cat": cat,
            "desc": desc,
            "broken_refs": 0,
        }

    # Extract edges from links
    seen_edges: set[tuple[str, str]] = set()
    for fpath in all_files:
        try:
            rel_source = fpath.relative_to(DOC_DIR).as_posix()
        except ValueError:
            rel_source = fpath.relative_to(ROOT).as_posix()

        if rel_source not in nodes:
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Find all markdown links
        for m in MD_LINK_RE.finditer(content):
            raw_target = m.group(1)
            target_rel = _resolve_link(rel_source, raw_target)
            if target_rel and target_rel != rel_source:
                if target_rel in nodes:
                    edge_key = (rel_source, target_rel)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({"source": rel_source, "target": target_rel})
                else:
                    # Check if file actually doesn't exist on disk (genuine broken ref)
                    cand = (DOC_DIR / target_rel)
                    if not cand.exists() and not (ROOT / target_rel).exists():
                        if rel_source in nodes:
                            nodes[rel_source]["broken_refs"] += 1

        # Find wiki-links
        for m in WIKI_LINK_RE.finditer(content):
            raw_target = m.group(1).strip()
            target_rel = _resolve_wiki_link(raw_target, nodes)
            if target_rel and target_rel != rel_source:
                edge_key = (rel_source, target_rel)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({"source": rel_source, "target": target_rel})

    return nodes, edges


def _resolve_link(source_rel: str, raw_target: str) -> str | None:
    """Resolve a relative markdown link to a doc-relative path."""
    # Clean up
    target = raw_target.strip()
    if not target or target.startswith("http") or target.startswith("mailto"):
        return None

    # Handle ../CLAUDE.md style
    source_dir = Path(source_rel).parent
    resolved = (source_dir / target).as_posix()

    # Normalize
    parts = []
    for part in resolved.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    resolved = "/".join(parts)

    return resolved if resolved else None


def _resolve_wiki_link(raw: str, nodes: dict[str, dict]) -> str | None:
    """Resolve an Obsidian [[wiki-link]] to a node id."""
    target = raw.strip()
    if not target:
        return None
    # Direct match
    if target in nodes:
        return target
    # Try adding .md
    if target + ".md" in nodes:
        return target + ".md"
    # Search by filename
    for node_id in nodes:
        if Path(node_id).stem == target or Path(node_id).name == target:
            return node_id
    return None


# ── Analysis helpers ───────────────────────────────────────────────

SNAPSHOT_FILE = DOC_DIR / "doc_graph_snapshot.json"


def get_git_mtimes_bulk() -> dict[str, str]:
    """One git-log call → {posix_rel_path: YYYY-MM-DD} (most-recent commit)."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%x00%ai", "--name-only", "--no-merges"],
            capture_output=True, text=True, cwd=ROOT, timeout=30,
        )
        if result.returncode != 0:
            return {}
        mtimes: dict[str, str] = {}
        current_date: str | None = None
        for line in result.stdout.splitlines():
            if line.startswith("\x00"):
                parts = line[1:].strip().split()
                current_date = parts[0] if parts else None
            elif line.strip() and current_date:
                rel = line.strip().replace("\\", "/")
                if rel not in mtimes:
                    mtimes[rel] = current_date
        return mtimes
    except Exception:
        return {}


def days_since(date_str: str) -> int:
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(date_str)).days
    except Exception:
        return 9999


def compute_betweenness(node_ids: list[str], edges: list[dict]) -> dict[str, float]:
    """Normalized betweenness centrality via Brandes algorithm."""
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        s, t = e["source"], e["target"]
        if s in adj and t in adj:
            adj[s].append(t)
            adj[t].append(s)

    n = len(node_ids)
    centrality = {nid: 0.0 for nid in node_ids}

    for s in node_ids:
        stack: list[str] = []
        pred: dict[str, list[str]] = {nid: [] for nid in node_ids}
        sigma: dict[str, int] = {nid: 0 for nid in node_ids}
        sigma[s] = 1
        dist: dict[str, int] = {nid: -1 for nid in node_ids}
        dist[s] = 0
        queue: deque[str] = deque([s])
        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in adj[v]:
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta: dict[str, float] = {nid: 0.0 for nid in node_ids}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                centrality[w] += delta[w]

    if n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        for nid in centrality:
            centrality[nid] = round(centrality[nid] * scale, 6)

    return centrality


def compute_clusters(node_ids: list[str], edges: list[dict]) -> dict[str, int]:
    """Connected-component IDs via path-compressed union-find."""
    parent = {nid: nid for nid in node_ids}

    def find(x: str) -> str:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for e in edges:
        s, t = e["source"], e["target"]
        if s in parent and t in parent:
            union(s, t)

    root_to_id: dict[str, int] = {}
    return {nid: root_to_id.setdefault(find(nid), len(root_to_id)) for nid in node_ids}


def load_snapshot() -> tuple[dict[str, dict], list[dict]] | None:
    if not SNAPSHOT_FILE.exists():
        return None
    try:
        data = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        return {n["id"]: n for n in data["nodes"]}, data["edges"]
    except Exception:
        return None


def save_snapshot(nodes: dict[str, dict], edges: list[dict]) -> None:
    data = {
        "generated": datetime.date.today().isoformat(),
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    SNAPSHOT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   Snapshot saved: {SNAPSHOT_FILE}")


def apply_diff(
    nodes: dict[str, dict],
    edges: list[dict],
    snap_nodes: dict[str, dict],
    snap_edges: list[dict],
) -> tuple[dict[str, dict], list[dict], dict]:
    snap_ids = set(snap_nodes)
    curr_ids = set(nodes)
    snap_edge_set = {(e["source"], e["target"]) for e in snap_edges}
    curr_edge_set = {(e["source"], e["target"]) for e in edges}

    new_nodes, removed_nodes, new_edges, removed_edges = 0, 0, 0, 0

    for nid, n in nodes.items():
        if nid not in snap_ids:
            n["diff"] = "new"
            new_nodes += 1

    for e in edges:
        if (e["source"], e["target"]) not in snap_edge_set:
            e["diff"] = "new"
            new_edges += 1

    for nid in snap_ids - curr_ids:
        ghost = snap_nodes[nid].copy()
        ghost["diff"] = "removed"
        nodes[nid] = ghost
        removed_nodes += 1

    for se in snap_edges:
        if (se["source"], se["target"]) not in curr_edge_set:
            edges.append({**se, "diff": "removed"})
            removed_edges += 1

    stats = {
        "new_nodes": new_nodes, "removed_nodes": removed_nodes,
        "new_edges": new_edges, "removed_edges": removed_edges,
    }
    return nodes, edges, stats


# ── HTML template ──────────────────────────────────────────────────

def generate_html(
    nodes: dict[str, dict],
    edges: list[dict],
    diff_stats: dict | None = None,
) -> str:
    """Generate the full HTML file content."""

    # ── Enrich nodes with git mtime ──
    print("   [enrich] git mtimes...", end=" ", flush=True)
    git_mtimes = get_git_mtimes_bulk()
    for nid, n in nodes.items():
        # git log paths are relative to repo root; doc files stored as "doc/<id>"
        key = nid if nid in git_mtimes else f"doc/{nid}"
        date = git_mtimes.get(key)
        n["mtime_days"] = days_since(date) if date else 9999
    print("done")

    # ── Betweenness centrality ──
    print("   [enrich] betweenness centrality...", end=" ", flush=True)
    node_ids = list(nodes.keys())
    bw = compute_betweenness(node_ids, edges)
    max_bw = max(bw.values()) if bw else 1.0
    for nid in nodes:
        nodes[nid]["centrality"] = round(bw.get(nid, 0.0) / (max_bw or 1), 4)
    print("done")

    # ── Cluster detection ──
    print("   [enrich] cluster detection...", end=" ", flush=True)
    clusters = compute_clusters(node_ids, edges)
    for nid in nodes:
        nodes[nid]["cluster"] = clusters.get(nid, 0)
    print("done")

    # Filter reading paths to only include existing nodes
    filtered_paths = {}
    for role, rp in READING_PATHS.items():
        valid_steps = [s for s in rp["path"] if s in nodes]
        if valid_steps:
            filtered_paths[role] = {"label": rp["label"], "path": valid_steps}

    nodes_json = json.dumps(list(nodes.values()), ensure_ascii=False, indent=2)
    edges_json = json.dumps(edges, ensure_ascii=False, indent=2)
    categories_json = json.dumps(CATEGORIES_META, ensure_ascii=False, indent=2)
    paths_json = json.dumps(filtered_paths, ensure_ascii=False, indent=2)
    diff_stats_json = json.dumps(diff_stats or {}, ensure_ascii=False)

    root_path = ROOT.as_posix()
    diff_mode = "true" if diff_stats else "false"

    return HTML_TEMPLATE.replace("__NODES_JSON__", nodes_json) \
                        .replace("__EDGES_JSON__", edges_json) \
                        .replace("__CATEGORIES_JSON__", categories_json) \
                        .replace("__PATHS_JSON__", paths_json) \
                        .replace("__PROJECT_ROOT__", root_path) \
                        .replace("__DIFF_MODE__", diff_mode) \
                        .replace("__DIFF_STATS__", diff_stats_json)


HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>hometutor — Граф Документации</title>
<style>
  :root {
    --bg-primary: #0a0a0f; --bg-glass: rgba(255,255,255,0.04);
    --border-glass: rgba(255,255,255,0.08); --text-primary: #e8e8f0;
    --text-secondary: #8888a0; --text-muted: #555570;
    --accent-purple: #8b5cf6; --accent-blue: #4a9eff;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Inter',sans-serif; background:var(--bg-primary); color:var(--text-primary); overflow:hidden; height:100vh; }
  .header { position:fixed; top:0; left:0; right:0; z-index:100; display:flex; align-items:center; gap:16px; padding:12px 24px; background:rgba(10,10,15,0.92); backdrop-filter:blur(20px); border-bottom:1px solid var(--border-glass); }
  .header h1 { font-size:18px; font-weight:700; background:linear-gradient(135deg,var(--accent-purple),var(--accent-blue)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; white-space:nowrap; }
  .header .subtitle { font-size:12px; color:var(--text-muted); white-space:nowrap; }
  .header .gen-badge { font-size:10px; color:var(--text-muted); background:var(--bg-glass); padding:2px 8px; border-radius:6px; border:1px solid var(--border-glass); white-space:nowrap; }
  .search-wrap { position:relative; flex:1; max-width:360px; margin-left:auto; }
  .search-wrap input { width:100%; padding:8px 12px 8px 36px; background:var(--bg-glass); border:1px solid var(--border-glass); border-radius:10px; color:var(--text-primary); font-family:inherit; font-size:13px; outline:none; transition:border-color 0.2s; }
  .search-wrap input:focus { border-color:var(--accent-purple); }
  .search-wrap::before { content:'🔍'; position:absolute; left:10px; top:50%; transform:translateY(-50%); font-size:14px; pointer-events:none; }
  .stats { font-size:11px; color:var(--text-muted); white-space:nowrap; }
  /* search dropdown */
  .search-drop { position:fixed; top:56px; right:0; left:300px; z-index:160; background:rgba(8,8,14,0.98); backdrop-filter:blur(20px); border-bottom:1px solid var(--border-glass); max-height:220px; overflow-y:auto; display:none; }
  .search-drop.visible { display:block; }
  .sd-item { display:flex; align-items:center; gap:8px; padding:7px 20px; font-size:12px; cursor:pointer; color:var(--text-secondary); transition:background 0.1s; }
  .sd-item:hover,.sd-item.active { background:rgba(139,92,246,0.14); color:var(--text-primary); }
  .sd-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
  /* sidebar */
  .sidebar { position:fixed; top:56px; left:0; bottom:0; width:300px; z-index:90; background:rgba(10,10,15,0.95); backdrop-filter:blur(20px); border-right:1px solid var(--border-glass); overflow-y:auto; padding:16px; transition:transform 0.3s ease; }
  .sidebar.collapsed { transform:translateX(-300px); }
  .sidebar-toggle { position:fixed; top:68px; left:8px; z-index:91; width:32px; height:32px; border-radius:8px; background:var(--bg-glass); border:1px solid var(--border-glass); color:var(--text-secondary); cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:16px; transition:all 0.2s; }
  .sidebar-toggle:hover { background:rgba(255,255,255,0.08); color:var(--text-primary); }
  .sidebar.collapsed ~ .sidebar-toggle { left:8px; }
  .sidebar:not(.collapsed) ~ .sidebar-toggle { left:308px; }
  .section-title { font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:var(--text-muted); margin:16px 0 8px; padding-bottom:4px; border-bottom:1px solid var(--border-glass); }
  .section-title:first-child { margin-top:0; }
  .role-btn { display:flex; align-items:center; gap:8px; width:100%; padding:8px 10px; margin:3px 0; background:var(--bg-glass); border:1px solid transparent; border-radius:8px; color:var(--text-secondary); font-family:inherit; font-size:12px; cursor:pointer; transition:all 0.2s; text-align:left; }
  .role-btn:hover { background:rgba(255,255,255,0.06); color:var(--text-primary); }
  .role-btn.active { border-color:var(--accent-purple); background:rgba(139,92,246,0.12); color:var(--text-primary); }
  .role-btn .emoji { font-size:16px; width:24px; text-align:center; }
  .cat-item { display:flex; align-items:center; gap:8px; padding:5px 8px; margin:2px 0; border-radius:6px; cursor:pointer; font-size:11px; color:var(--text-secondary); transition:all 0.15s; }
  .cat-item:hover { background:rgba(255,255,255,0.04); color:var(--text-primary); }
  .cat-item.dimmed { opacity:0.3; }
  .cat-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
  .cat-count { margin-left:auto; font-size:10px; background:rgba(255,255,255,0.06); padding:1px 6px; border-radius:8px; }
  .fresh-row { display:flex; align-items:center; gap:6px; font-size:10px; color:var(--text-muted); margin:2px 0; }
  .fresh-dot { width:9px; height:9px; border-radius:50%; flex-shrink:0; }
  /* graph */
  #graph-container { position:fixed; top:56px; left:300px; right:0; bottom:0; transition:left 0.3s ease; }
  .sidebar.collapsed ~ #graph-container { left:0; }
  #graph-container svg { width:100%; height:100%; }
  /* tooltip */
  .tooltip { position:fixed; z-index:200; pointer-events:none; max-width:380px; padding:14px 18px; background:rgba(18,18,28,0.96); backdrop-filter:blur(24px); border:1px solid rgba(255,255,255,0.1); border-radius:12px; box-shadow:0 8px 32px rgba(0,0,0,0.5); opacity:0; transition:opacity 0.15s; font-size:12px; line-height:1.5; }
  .tooltip.visible { opacity:1; }
  .tooltip h3 { font-size:14px; font-weight:600; margin-bottom:4px; }
  .tooltip .cat-label { display:inline-block; padding:2px 8px; border-radius:6px; font-size:10px; font-weight:600; margin-bottom:6px; }
  .tooltip .desc { color:var(--text-secondary); margin-bottom:6px; }
  .tooltip .links-label { color:var(--text-muted); font-size:10px; font-weight:600; letter-spacing:0.5px; text-transform:uppercase; }
  .tooltip .link-list { color:var(--accent-blue); margin-top:2px; }
  /* diff banner */
  .diff-banner { position:fixed; top:56px; left:0; right:0; z-index:85; padding:5px 20px; background:rgba(16,185,129,0.1); border-bottom:1px solid rgba(16,185,129,0.2); font-size:11px; color:#6ee7b7; display:none; }
  /* detail panel */
  .detail-panel { position:fixed; top:56px; right:0; bottom:0; width:360px; z-index:95; background:rgba(10,10,15,0.97); backdrop-filter:blur(20px); border-left:1px solid var(--border-glass); overflow-y:auto; padding:20px; transform:translateX(360px); transition:transform 0.3s ease; }
  .detail-panel.open { transform:translateX(0); }
  .detail-close { position:absolute; top:12px; right:12px; width:28px; height:28px; border-radius:8px; background:var(--bg-glass); border:1px solid var(--border-glass); color:var(--text-secondary); cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:14px; transition:all 0.2s; }
  .detail-close:hover { background:rgba(255,255,255,0.08); color:var(--text-primary); }
  .detail-panel h2 { font-size:16px; font-weight:700; margin-bottom:4px; padding-right:36px; }
  .detail-panel .meta { font-size:11px; color:var(--text-muted); margin-bottom:10px; }
  .detail-panel .desc-full { font-size:13px; color:var(--text-secondary); line-height:1.6; margin-bottom:16px; }
  .detail-panel .conn-title { font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:var(--text-muted); margin-bottom:6px; }
  .detail-panel .conn-item { display:flex; align-items:center; gap:8px; padding:6px 8px; margin:2px 0; background:var(--bg-glass); border-radius:6px; font-size:12px; cursor:pointer; transition:background 0.15s; }
  .detail-panel .conn-item:hover { background:rgba(255,255,255,0.06); }
  /* action buttons */
  .detail-actions { display:flex; gap:5px; margin-bottom:14px; flex-wrap:wrap; }
  .action-btn { flex:1; min-width:80px; display:flex; align-items:center; justify-content:center; gap:4px; padding:7px 6px; border-radius:8px; font-family:inherit; font-size:11px; font-weight:600; cursor:pointer; transition:all 0.2s; text-decoration:none; border:1px solid; white-space:nowrap; }
  .action-btn.obs { background:rgba(99,102,241,0.1); border-color:rgba(99,102,241,0.28); color:#a5b4fc; }
  .action-btn.obs:hover { background:rgba(99,102,241,0.22); border-color:rgba(99,102,241,0.55); color:#c7d2fe; }
  .action-btn.vsc { background:rgba(0,122,204,0.1); border-color:rgba(0,122,204,0.28); color:#60b0f4; }
  .action-btn.vsc:hover { background:rgba(0,122,204,0.22); border-color:rgba(0,122,204,0.55); color:#93c5fd; }
  .action-btn.cpy { background:rgba(16,185,129,0.1); border-color:rgba(16,185,129,0.28); color:#6ee7b7; }
  .action-btn.cpy:hover { background:rgba(16,185,129,0.22); border-color:rgba(16,185,129,0.55); color:#a7f3d0; }
  /* badges */
  .node-badge { display:inline-flex; align-items:center; gap:3px; padding:1px 6px; border-radius:4px; font-size:10px; font-weight:600; margin-left:4px; }
  .bdg-orphan { background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.3); }
  .bdg-broken { background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3); }
  .bdg-new { background:rgba(16,185,129,0.15); color:#6ee7b7; border:1px solid rgba(16,185,129,0.3); }
  .bdg-removed { background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3); opacity:0.7; }
  /* onboarding bar */
  .onboarding-bar { position:fixed; bottom:52px; left:50%; transform:translateX(-50%); z-index:120; display:flex; align-items:center; gap:12px; padding:10px 20px; background:rgba(18,18,28,0.95); backdrop-filter:blur(20px); border:1px solid var(--border-glass); border-radius:16px; box-shadow:0 8px 32px rgba(0,0,0,0.4); opacity:0; pointer-events:none; transition:opacity 0.3s; }
  .onboarding-bar.visible { opacity:1; pointer-events:auto; }
  .onboarding-bar .path-label { font-size:12px; font-weight:600; color:var(--accent-purple); white-space:nowrap; }
  .onboarding-bar .path-steps { display:flex; align-items:center; gap:4px; font-size:12px; }
  .path-step { padding:4px 10px; border-radius:6px; background:var(--bg-glass); border:1px solid var(--border-glass); color:var(--text-secondary); cursor:pointer; transition:all 0.2s; white-space:nowrap; }
  .path-step.active { background:rgba(139,92,246,0.2); border-color:var(--accent-purple); color:var(--text-primary); }
  .path-step:hover { background:rgba(255,255,255,0.06); }
  .path-arrow { color:var(--text-muted); font-size:14px; }
  .onboarding-dismiss { margin-left:8px; width:24px; height:24px; border-radius:6px; border:none; background:rgba(255,255,255,0.06); color:var(--text-muted); cursor:pointer; font-size:12px; display:flex; align-items:center; justify-content:center; transition:all 0.15s; }
  .onboarding-dismiss:hover { background:rgba(255,255,255,0.1); color:var(--text-primary); }
  /* keyboard hint bar */
  .kbd-bar { position:fixed; bottom:16px; left:310px; z-index:70; display:flex; gap:10px; padding:5px 14px; background:rgba(18,18,28,0.82); backdrop-filter:blur(12px); border:1px solid var(--border-glass); border-radius:10px; font-size:10px; color:var(--text-muted); pointer-events:none; }
  .kbd { display:inline-block; padding:1px 5px; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.14); border-radius:4px; font-family:monospace; font-size:9px; color:var(--text-secondary); }
  /* minimap */
  .minimap { position:fixed; bottom:16px; right:16px; z-index:80; width:160px; height:120px; background:rgba(18,18,28,0.8); border:1px solid var(--border-glass); border-radius:10px; overflow:hidden; }
  .minimap canvas { width:100%; height:100%; }
  ::-webkit-scrollbar { width:5px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.1); border-radius:3px; }
</style>
</head>
<body>
<header class="header">
  <h1>🧭 Граф Документации</h1>
  <span class="subtitle">hometutor</span>
  <span class="gen-badge">auto-generated</span>
  <div class="search-wrap"><input type="text" id="search" placeholder="Поиск... (/ или ↑↓Enter)" autocomplete="off"></div>
  <div class="stats" id="stats"></div>
</header>
<div class="search-drop" id="search-drop"></div>
<div class="diff-banner" id="diff-banner"></div>
<aside class="sidebar" id="sidebar">
  <div class="section-title">🎯 Онбординг по роли</div>
  <div id="role-buttons"></div>
  <button class="role-btn" data-role="all"><span class="emoji">🌐</span> Показать всё</button>
  <div class="section-title">📂 Категории</div>
  <div id="category-legend"></div>
  <div class="section-title">🕐 Свежесть (кольцо)</div>
  <div id="freshness-legend"></div>
  <div class="section-title">📊 Статистика</div>
  <div id="sidebar-stats" style="font-size:11px;color:var(--text-secondary);line-height:1.9;"></div>
</aside>
<button class="sidebar-toggle" id="sidebar-toggle" title="Свернуть/развернуть">☰</button>
<div id="graph-container"></div>
<div class="tooltip" id="tooltip"></div>
<div class="detail-panel" id="detail-panel">
  <button class="detail-close" id="detail-close">✕</button>
  <div id="detail-content"></div>
</div>
<div class="onboarding-bar" id="onboarding-bar">
  <span class="path-label" id="path-label"></span>
  <div class="path-steps" id="path-steps"></div>
  <button class="onboarding-dismiss" id="onboarding-dismiss">✕</button>
</div>
<div class="minimap" id="minimap"><canvas id="minimap-canvas"></canvas></div>
<div class="kbd-bar">
  <span><span class="kbd">/</span> поиск</span>
  <span><span class="kbd">↑↓</span> выбор</span>
  <span><span class="kbd">Enter</span> фокус</span>
  <span><span class="kbd">O</span> Obsidian</span>
  <span><span class="kbd">2×клик</span> Obsidian</span>
  <span><span class="kbd">Esc</span> сброс</span>
</div>

<script src="assets/d3.v7.min.js"></script>
<script>
const CATEGORIES = __CATEGORIES_JSON__;
const NODES = __NODES_JSON__;
const EDGES = __EDGES_JSON__;
const READING_PATHS = __PATHS_JSON__;
const PROJECT_ROOT = '__PROJECT_ROOT__';
const DIFF_MODE = __DIFF_MODE__;
const DIFF_STATS = __DIFF_STATS__;

// ── URI / clipboard helpers ──
const _ROOT_FILES = new Set(['CLAUDE.md','AGENTS.md']);
function _absPath(id){const rel=_ROOT_FILES.has(id)?id:'doc/'+id;return PROJECT_ROOT+'/'+rel;}
function _obsidianUri(id){return 'obsidian://open?path='+encodeURIComponent(_absPath(id).replace(/\//g,'\\'));}
function _vscodeUri(id){return 'vscode://file/'+_absPath(id).replace(/\//g,'\\');}
function _copyPath(id,btn){navigator.clipboard.writeText(_absPath(id)).then(()=>{const t=btn.textContent;btn.textContent='✓ Готово';setTimeout(()=>btn.textContent=t,1500);});}

// ── Freshness color ──
function freshnessColor(days){
  if(days==null||days>=9999)return null;
  if(days<=7)return'#22c55e';
  if(days<=30)return'#84cc16';
  if(days<=90)return'#f59e0b';
  if(days<=180)return'#ef4444';
  return'#6b7280';
}

// ── Freshness legend ──
document.getElementById('freshness-legend').innerHTML=[
  ['#22c55e','до 7 дней'],['#84cc16','7–30 дней'],
  ['#f59e0b','1–3 месяца'],['#ef4444','3–6 месяцев'],['#6b7280','>6 месяцев']
].map(([c,l])=>`<div class="fresh-row"><span class="fresh-dot" style="background:${c}"></span>${l}</div>`).join('');

// ── Diff banner ──
if(DIFF_MODE&&DIFF_STATS){
  const b=document.getElementById('diff-banner');
  b.style.display='block';
  b.textContent=`🔄 Diff: +${DIFF_STATS.new_nodes||0} новых, -${DIFF_STATS.removed_nodes||0} удалённых документов  |  +${DIFF_STATS.new_edges||0} новых, -${DIFF_STATS.removed_edges||0} удалённых связей`;
}

// ── Role buttons ──
const roleContainer = document.getElementById('role-buttons');
Object.entries(READING_PATHS).forEach(([role, rp]) => {
  const btn = document.createElement('button');
  btn.className = 'role-btn'; btn.dataset.role = role;
  btn.innerHTML = `<span class="emoji">${rp.label.slice(0,2)}</span> ${rp.label.slice(2).trim()}`;
  roleContainer.appendChild(btn);
});

// ── Graph engine ──
const nodeMap = new Map(NODES.map(n => [n.id, n]));
const validEdges = EDGES.filter(e => nodeMap.has(e.source) && nodeMap.has(e.target) && e.diff !== 'removed');
const degreeMap = new Map();
NODES.forEach(n => degreeMap.set(n.id, 0));
validEdges.forEach(e => {
  degreeMap.set(e.source, (degreeMap.get(e.source)||0)+1);
  degreeMap.set(e.target, (degreeMap.get(e.target)||0)+1);
});
const adjacency = new Map();
NODES.forEach(n => adjacency.set(n.id, new Set()));
validEdges.forEach(e => { adjacency.get(e.source)?.add(e.target); adjacency.get(e.target)?.add(e.source); });

// stats
const catCounts = {};
NODES.forEach(n => { catCounts[n.cat] = (catCounts[n.cat]||0)+1; });
const orphanCount = NODES.filter(n=>(degreeMap.get(n.id)||0)===0&&n.diff!=='removed').length;
const clusterCount = new Set(NODES.map(n=>n.cluster)).size;
const brokenTotal = NODES.reduce((s,n)=>s+(n.broken_refs||0),0);
document.getElementById('stats').textContent = `${NODES.length} документов · ${validEdges.length} связей`;
document.getElementById('sidebar-stats').innerHTML =
  `<div>📄 Документов: <strong>${NODES.length}</strong></div>`+
  `<div>🔗 Связей: <strong>${validEdges.length}</strong></div>`+
  `<div>📂 Категорий: <strong>${Object.keys(CATEGORIES).length}</strong></div>`+
  `<div>🎯 Ролей: <strong>${Object.keys(READING_PATHS).length}</strong></div>`+
  `<div>🔵 Кластеров: <strong>${clusterCount}</strong></div>`+
  (orphanCount?`<div>⚪ Изолированных: <strong>${orphanCount}</strong></div>`:'') +
  (brokenTotal?`<div>❌ Битых ссылок: <strong>${brokenTotal}</strong></div>`:'');

const legendEl = document.getElementById('category-legend');
Object.entries(CATEGORIES).forEach(([key, cat]) => {
  const count = catCounts[key]||0; if(!count) return;
  const item = document.createElement('div');
  item.className = 'cat-item'; item.dataset.cat = key;
  item.innerHTML = `<span class="cat-dot" style="background:${cat.color}"></span><span>${cat.label}</span><span class="cat-count">${count}</span>`;
  item.addEventListener('click', () => toggleCategory(key));
  legendEl.appendChild(item);
});

// ── D3 simulation ──
const container = document.getElementById('graph-container');
const width = container.clientWidth, height = container.clientHeight;
const svg = d3.select('#graph-container').append('svg').attr('width','100%').attr('height','100%').attr('viewBox',[0,0,width,height]);
const defs = svg.append('defs');
const glow = defs.append('filter').attr('id','glow');
glow.append('feGaussianBlur').attr('stdDeviation',3).attr('result','blur');
const fm = glow.append('feMerge'); fm.append('feMergeNode').attr('in','blur'); fm.append('feMergeNode').attr('in','SourceGraphic');
// green glow for new nodes
const glowNew = defs.append('filter').attr('id','glow-new');
glowNew.append('feGaussianBlur').attr('stdDeviation',5).attr('result','blur');
const fmn = glowNew.append('feMerge'); fmn.append('feMergeNode').attr('in','blur'); fmn.append('feMergeNode').attr('in','SourceGraphic');

const g = svg.append('g');
const zoom = d3.zoom().scaleExtent([0.1,4]).on('zoom',e=>{g.attr('transform',e.transform);updateMinimap();});
svg.call(zoom);

const simNodes = NODES.filter(n=>n.diff!=='removed').map(n=>({...n}));
const allSimNodes = NODES.map(n=>({...n})); // includes removed for diff rendering
const simLinks = validEdges.map(e=>({source:e.source,target:e.target,diff:e.diff}));

function getR(d){
  const deg=degreeMap.get(d.id)||0;
  const base=Math.max(5,Math.min(18,4+deg*1.2));
  return base + (d.centrality||0)*8;
}
function getC(d){return CATEGORIES[d.cat]?.color||'#555';}

const simulation = d3.forceSimulation(simNodes)
  .force('link',d3.forceLink(simLinks).id(d=>d.id).distance(80).strength(0.3))
  .force('charge',d3.forceManyBody().strength(-280).distanceMax(500))
  .force('center',d3.forceCenter(width/2,height/2))
  .force('collision',d3.forceCollide().radius(d=>getR(d)+8))
  .force('x',d3.forceX(width/2).strength(0.03))
  .force('y',d3.forceY(height/2).strength(0.03));

// cluster hull layer (drawn first, under links)
const hullG = g.append('g').attr('class','hull-layer');
const CLUSTER_COLORS=['#8b5cf6','#4a9eff','#10b981','#f59e0b','#ef4444','#ec4899','#06b6d4','#a855f7','#14b8a6','#fb7185','#f97316','#6366f1'];

function drawClusters(){
  const byCluster={};
  simNodes.forEach(n=>{(byCluster[n.cluster]=byCluster[n.cluster]||[]).push([n.x,n.y]);});
  hullG.selectAll('path').data(Object.entries(byCluster)).join('path')
    .attr('d',([cid,pts])=>{
      if(pts.length<3)return null;
      const hull=d3.polygonHull(pts); if(!hull)return null;
      const cx=pts.reduce((s,p)=>s+p[0],0)/pts.length;
      const cy=pts.reduce((s,p)=>s+p[1],0)/pts.length;
      const exp=hull.map(([x,y])=>{const dx=x-cx,dy=y-cy,len=Math.sqrt(dx*dx+dy*dy)||1;return[x+dx/len*22,y+dy/len*22];});
      return 'M'+exp.join('L')+'Z';
    })
    .attr('fill',([cid])=>CLUSTER_COLORS[+cid%CLUSTER_COLORS.length])
    .attr('fill-opacity',0.035)
    .attr('stroke',([cid])=>CLUSTER_COLORS[+cid%CLUSTER_COLORS.length])
    .attr('stroke-opacity',0.07).attr('stroke-width',2);
}

const linkG = g.append('g');
const link = linkG.selectAll('line').data(simLinks).join('line')
  .attr('stroke',l=>l.diff==='new'?'rgba(34,197,94,0.35)':'rgba(255,255,255,0.06)')
  .attr('stroke-width',l=>l.diff==='new'?1.5:0.8)
  .attr('stroke-dasharray',l=>l.diff==='new'?'4,2':null);
const pathG = g.append('g');
const nodeG = g.append('g');
const node = nodeG.selectAll('g').data(simNodes).join('g').attr('class','node')
  .call(d3.drag().on('start',(e,d)=>{if(!e.active)simulation.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;})
    .on('drag',(e,d)=>{d.fx=e.x;d.fy=e.y;}).on('end',(e,d)=>{if(!e.active)simulation.alphaTarget(0);d.fx=null;d.fy=null;}));

// freshness ring (behind main circle)
node.append('circle').attr('class','fresh-ring')
  .attr('r',d=>getR(d)+3).attr('fill','none')
  .attr('stroke',d=>freshnessColor(d.mtime_days)||'transparent')
  .attr('stroke-width',2).attr('stroke-opacity',d=>freshnessColor(d.mtime_days)?0.55:0)
  .style('pointer-events','none');

// main node circle
node.append('circle').attr('class','main-circle')
  .attr('r',d=>getR(d))
  .attr('fill',d=>d.diff==='removed'?'#444':getC(d))
  .attr('stroke',d=>d.diff==='new'?'#22c55e':d.diff==='removed'?'#555':getC(d))
  .attr('stroke-width',d=>d.diff?3:1.5)
  .attr('stroke-dasharray',d=>(degreeMap.get(d.id)||0)===0?'4,3':null)
  .attr('stroke-opacity',d=>d.diff==='new'?0.9:d.diff==='removed'?0.3:0.3)
  .attr('fill-opacity',d=>d.diff==='removed'?0.2:0.85)
  .attr('filter',d=>d.diff==='new'?'url(#glow-new)':null)
  .style('cursor','pointer');

// broken-refs red dot
node.filter(d=>(d.broken_refs||0)>0).append('circle')
  .attr('r',3.5).attr('cx',d=>getR(d)*0.7).attr('cy',d=>-getR(d)*0.7)
  .attr('fill','#ef4444').attr('stroke','#0a0a0f').attr('stroke-width',1)
  .style('pointer-events','none');

node.append('text').text(d=>d.label.replace(/\.md$/,'').replace(/\.yaml$/,'').replace(/\.json$/,''))
  .attr('dy',d=>getR(d)+14).attr('text-anchor','middle')
  .attr('fill','rgba(255,255,255,0.5)')
  .attr('font-size',d=>{const deg=degreeMap.get(d.id)||0;return deg>8?11:deg>4?10:9;})
  .attr('font-weight',d=>(degreeMap.get(d.id)||0)>8?600:400)
  .style('pointer-events','none').style('user-select','none');

simulation.on('tick',()=>{
  link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
  node.attr('transform',d=>`translate(${d.x},${d.y})`);
  drawClusters();
  updateMinimap();
});

// ── Tooltip ──
const tooltip = document.getElementById('tooltip');
node.on('mouseenter',(e,d)=>{
  const nb=adjacency.get(d.id)||new Set();
  const cat=CATEGORIES[d.cat]||{label:'?',color:'#555'};
  const deg=degreeMap.get(d.id)||0;
  const names=[...nb].slice(0,8).map(id=>{const n=nodeMap.get(id);return n?n.label:id;});
  const freshStr=d.mtime_days<9999?` · ${d.mtime_days}д назад`:'';
  tooltip.innerHTML=`<h3>${d.label}</h3><span class="cat-label" style="background:${cat.color}22;color:${cat.color};border:1px solid ${cat.color}44">${cat.label}</span>${freshStr}<div class="desc">${d.desc}</div><div class="links-label">Связи (${deg})</div><div class="link-list">${names.join(' · ')}${nb.size>8?' …':''}</div>`;
  tooltip.classList.add('visible'); highlightNode(d);
}).on('mousemove',e=>{tooltip.style.left=Math.min(e.clientX+16,innerWidth-400)+'px';tooltip.style.top=Math.min(e.clientY-10,innerHeight-200)+'px';})
.on('mouseleave',()=>{tooltip.classList.remove('visible');resetHL();})
.on('click',(e,d)=>{e.stopPropagation();showDetail(d);})
.on('dblclick',(e,d)=>{e.stopPropagation();window.location.href=_obsidianUri(d.id);});

function highlightNode(d){
  const nb=adjacency.get(d.id)||new Set();
  node.select('.main-circle').attr('fill-opacity',n=>n.id===d.id||nb.has(n.id)?1:0.1).attr('stroke-opacity',n=>n.id===d.id||nb.has(n.id)?0.8:0.05);
  node.select('text').attr('fill',n=>n.id===d.id||nb.has(n.id)?'rgba(255,255,255,0.9)':'rgba(255,255,255,0.08)');
  link.attr('stroke',l=>(l.source.id===d.id||l.target.id===d.id)?getC(d):'rgba(255,255,255,0.02)').attr('stroke-width',l=>(l.source.id===d.id||l.target.id===d.id)?2:0.5).attr('stroke-opacity',l=>(l.source.id===d.id||l.target.id===d.id)?0.7:0.3);
}
function resetHL(){
  node.select('.main-circle').attr('fill-opacity',d=>d.diff==='removed'?0.2:0.85).attr('stroke-opacity',d=>d.diff==='new'?0.9:d.diff==='removed'?0.3:0.3);
  node.select('text').attr('fill','rgba(255,255,255,0.5)');
  link.attr('stroke',l=>l.diff==='new'?'rgba(34,197,94,0.35)':'rgba(255,255,255,0.06)').attr('stroke-width',l=>l.diff==='new'?1.5:0.8).attr('stroke-opacity',1);
}

// ── Detail panel ──
const detailPanel=document.getElementById('detail-panel'),detailContent=document.getElementById('detail-content');
document.getElementById('detail-close').addEventListener('click',()=>{detailPanel.classList.remove('open');history.replaceState(null,'',location.pathname+location.search);});
let _currentNode=null;

function showDetail(d){
  _currentNode=d;
  const cat=CATEGORIES[d.cat]||{label:'?',color:'#555'};
  const nb=[...adjacency.get(d.id)||[]];
  const deg=degreeMap.get(d.id)||0;
  const isOrphan=(degreeMap.get(d.id)||0)===0;
  const badges=(isOrphan?'<span class="node-badge bdg-orphan">изолирован</span>':'')+
    ((d.broken_refs||0)>0?`<span class="node-badge bdg-broken">${d.broken_refs} битых ссылок</span>`:'')+
    (d.diff==='new'?'<span class="node-badge bdg-new">новый</span>':'')+
    (d.diff==='removed'?'<span class="node-badge bdg-removed">удалён</span>':'');
  const freshStr=d.mtime_days<9999?`<span style="color:${freshnessColor(d.mtime_days)||'var(--text-muted)'}"> · ${d.mtime_days}д назад</span>`:'';
  detailContent.innerHTML=
    `<div class="detail-actions">
       <a class="action-btn obs" href="${_obsidianUri(d.id)}">🔮 Obsidian</a>
       <a class="action-btn vsc" href="${_vscodeUri(d.id)}">⌨️ VS Code</a>
       <button class="action-btn cpy" id="_cpybtn">📋 Путь</button>
     </div>
     <h2>${d.label}${badges}</h2>
     <div class="meta"><span class="cat-label" style="background:${cat.color}22;color:${cat.color};border:1px solid ${cat.color}44;display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600">${cat.label}</span>${freshStr} · ${deg} связей · centrality ${((d.centrality||0)*100).toFixed(1)}%</div>
     <div class="desc-full">${d.desc}</div>
     ${nb.length?`<div class="conn-title">Связанные документы (${nb.length})</div>${nb.map(id=>{const n=nodeMap.get(id);if(!n)return'';const nc=CATEGORIES[n.cat]||{color:'#555'};return`<div class="conn-item" data-id="${id}"><span class="cat-dot" style="background:${nc.color};width:8px;height:8px;border-radius:50%;flex-shrink:0"></span><span>${n.label}</span></div>`;}).join('')}`:''}`;
  document.getElementById('_cpybtn').addEventListener('click',function(){_copyPath(d.id,this);});
  detailContent.querySelectorAll('.conn-item').forEach(el=>{el.addEventListener('click',()=>{const t=simNodes.find(n=>n.id===el.dataset.id);if(t){zoomTo(t);showDetail(t);}});});
  detailPanel.classList.add('open');
  history.replaceState(null,'','#node='+encodeURIComponent(d.id));
}

function zoomTo(d){const s=1.5;svg.transition().duration(600).call(zoom.transform,d3.zoomIdentity.translate(-d.x*s+width/2,-d.y*s+height/2).scale(s));}

// ── Permalink on load ──
simulation.on('end.permalink',()=>{
  const hash=location.hash;
  if(hash.startsWith('#node=')){
    const id=decodeURIComponent(hash.slice(6));
    const n=simNodes.find(n=>n.id===id);
    if(n){zoomTo(n);showDetail(n);}
  }
  simulation.on('end.permalink',null);
});

// ── Search with dropdown ──
let _srResults=[], _srIdx=-1;
const searchDrop=document.getElementById('search-drop');
const searchInput=document.getElementById('search');

searchInput.addEventListener('input',e=>{
  const q=e.target.value.toLowerCase().trim();
  if(!q){searchDrop.classList.remove('visible');_srResults=[];resetHL();return;}
  _srResults=simNodes.filter(n=>n.label.toLowerCase().includes(q)||n.id.toLowerCase().includes(q)||n.desc.toLowerCase().includes(q)).slice(0,12);
  _srIdx=-1; renderDrop();
  const ms=new Set(_srResults.map(n=>n.id));
  node.select('.main-circle').attr('fill-opacity',n=>ms.has(n.id)?0.95:0.06);
  node.select('text').attr('fill',n=>ms.has(n.id)?'rgba(255,255,255,0.9)':'rgba(255,255,255,0.04)');
  link.attr('stroke','rgba(255,255,255,0.015)');
  if(_srResults.length===1)zoomTo(_srResults[0]);
});

function renderDrop(){
  if(!_srResults.length){searchDrop.classList.remove('visible');return;}
  searchDrop.innerHTML=_srResults.map((n,i)=>{
    const cat=CATEGORIES[n.cat]||{color:'#555'};
    return`<div class="sd-item${i===_srIdx?' active':''}" data-idx="${i}"><span class="sd-dot" style="background:${cat.color}"></span><span>${n.label}</span></div>`;
  }).join('');
  searchDrop.classList.add('visible');
  searchDrop.querySelectorAll('.sd-item').forEach(el=>{el.addEventListener('click',()=>{const n=_srResults[+el.dataset.idx];if(n){zoomTo(n);showDetail(n);searchDrop.classList.remove('visible');searchInput.value='';resetHL();}});});
}

// ── Role paths ──
let activeRole=null;const oBar=document.getElementById('onboarding-bar'),pLabel=document.getElementById('path-label'),pSteps=document.getElementById('path-steps');
document.querySelectorAll('.role-btn').forEach(btn=>{btn.addEventListener('click',()=>{
  const role=btn.dataset.role;
  document.querySelectorAll('.role-btn').forEach(b=>b.classList.remove('active'));
  if(role==='all'||activeRole===role){activeRole=null;resetHL();oBar.classList.remove('visible');pathG.selectAll('*').remove();node.select('.main-circle').attr('r',d=>getR(d));node.select('text').attr('font-weight',d=>(degreeMap.get(d.id)||0)>8?600:400);return;}
  activeRole=role;btn.classList.add('active');const rp=READING_PATHS[role];if(!rp)return;const ps=new Set(rp.path);
  node.select('.main-circle').attr('fill-opacity',n=>ps.has(n.id)?1:0.06).attr('r',n=>ps.has(n.id)?getR(n)*1.4:getR(n));
  node.select('text').attr('fill',n=>ps.has(n.id)?'rgba(255,255,255,0.95)':'rgba(255,255,255,0.04)').attr('font-weight',n=>ps.has(n.id)?700:400);
  link.attr('stroke',l=>(ps.has(l.source.id)&&ps.has(l.target.id))?(CATEGORIES[nodeMap.get(l.source.id)?.cat]?.color||'#fff'):'rgba(255,255,255,0.01)').attr('stroke-width',l=>(ps.has(l.source.id)&&ps.has(l.target.id))?2.5:0.5);
  pLabel.textContent=rp.label;
  pSteps.innerHTML=rp.path.map((id,i)=>{const n=nodeMap.get(id);const lbl=n?n.label.replace(/\.md$/,'').replace(/\.yaml$/,''):id;return`${i>0?'<span class="path-arrow">→</span>':''}<span class="path-step" data-id="${id}">${i+1}. ${lbl}</span>`;}).join('');
  oBar.classList.add('visible');
  pSteps.querySelectorAll('.path-step').forEach(s=>{s.addEventListener('click',()=>{const t=simNodes.find(n=>n.id===s.dataset.id);if(t){zoomTo(t);showDetail(t);pSteps.querySelectorAll('.path-step').forEach(x=>x.classList.remove('active'));s.classList.add('active');}});});
});});
document.getElementById('onboarding-dismiss').addEventListener('click',()=>{oBar.classList.remove('visible');activeRole=null;document.querySelectorAll('.role-btn').forEach(b=>b.classList.remove('active'));resetHL();pathG.selectAll('*').remove();node.select('.main-circle').attr('r',d=>getR(d));node.select('text').attr('font-weight',d=>(degreeMap.get(d.id)||0)>8?600:400);});

// ── Category toggle ──
const hiddenCats=new Set();
function toggleCategory(cat){
  hiddenCats.has(cat)?hiddenCats.delete(cat):hiddenCats.add(cat);
  document.querySelectorAll('.cat-item').forEach(el=>{el.classList.toggle('dimmed',hiddenCats.has(el.dataset.cat));});
  node.select('.main-circle').attr('fill-opacity',n=>hiddenCats.has(n.cat)?0.04:0.85);
  node.select('text').attr('fill',n=>hiddenCats.has(n.cat)?'rgba(255,255,255,0.02)':'rgba(255,255,255,0.5)');
  link.attr('stroke',l=>{const sh=hiddenCats.has(nodeMap.get(l.source.id)?.cat);const th=hiddenCats.has(nodeMap.get(l.target.id)?.cat);return(sh||th)?'rgba(255,255,255,0.008)':'rgba(255,255,255,0.06)';});
}

// ── Sidebar toggle ──
document.getElementById('sidebar-toggle').addEventListener('click',()=>{document.getElementById('sidebar').classList.toggle('collapsed');});

// ── Minimap ──
const mc=document.getElementById('minimap-canvas').getContext('2d');
document.getElementById('minimap-canvas').width=320;document.getElementById('minimap-canvas').height=240;
function updateMinimap(){
  const w=320,h=240;mc.clearRect(0,0,w,h);
  let mnX=Infinity,mxX=-Infinity,mnY=Infinity,mxY=-Infinity;
  simNodes.forEach(n=>{if(n.x<mnX)mnX=n.x;if(n.x>mxX)mxX=n.x;if(n.y<mnY)mnY=n.y;if(n.y>mxY)mxY=n.y;});
  const p=40,s=Math.min((w-p*2)/(mxX-mnX||1),(h-p*2)/(mxY-mnY||1)),ox=(w-(mxX-mnX)*s)/2,oy=(h-(mxY-mnY)*s)/2;
  mc.strokeStyle='rgba(255,255,255,0.05)';mc.lineWidth=0.5;
  simLinks.forEach(l=>{mc.beginPath();mc.moveTo((l.source.x-mnX)*s+ox,(l.source.y-mnY)*s+oy);mc.lineTo((l.target.x-mnX)*s+ox,(l.target.y-mnY)*s+oy);mc.stroke();});
  simNodes.forEach(n=>{mc.fillStyle=getC(n);mc.globalAlpha=0.7;mc.beginPath();mc.arc((n.x-mnX)*s+ox,(n.y-mnY)*s+oy,Math.max(1.5,getR(n)*s*0.3),0,Math.PI*2);mc.fill();});
  mc.globalAlpha=1;
  const tr=d3.zoomTransform(svg.node());mc.strokeStyle='rgba(139,92,246,0.5)';mc.lineWidth=1;mc.strokeRect((-tr.x/tr.k-mnX)*s+ox,(-tr.y/tr.k-mnY)*s+oy,(width/tr.k)*s,(height/tr.k)*s);
}

// ── Fit on end ──
simulation.on('end',()=>{
  let mnX=Infinity,mxX=-Infinity,mnY=Infinity,mxY=-Infinity;
  simNodes.forEach(n=>{if(n.x<mnX)mnX=n.x;if(n.x>mxX)mxX=n.x;if(n.y<mnY)mnY=n.y;if(n.y>mxY)mxY=n.y;});
  const p=60,dx=mxX-mnX+p*2,dy=mxY-mnY+p*2,s=Math.min(width/dx,height/dy)*0.9,cx=(mnX+mxX)/2,cy=(mnY+mxY)/2;
  svg.transition().duration(800).call(zoom.transform,d3.zoomIdentity.translate(width/2,height/2).scale(s).translate(-cx,-cy));
});

svg.on('click',()=>{detailPanel.classList.remove('open');searchDrop.classList.remove('visible');});

// ── Keyboard navigation ──
document.addEventListener('keydown',e=>{
  const inSearch=document.activeElement===searchInput;
  if(e.key==='ArrowDown'&&_srResults.length){e.preventDefault();_srIdx=Math.min(_srIdx+1,_srResults.length-1);renderDrop();}
  else if(e.key==='ArrowUp'&&_srResults.length){e.preventDefault();_srIdx=Math.max(_srIdx-1,0);renderDrop();}
  else if(e.key==='Enter'&&_srIdx>=0&&_srResults.length){
    e.preventDefault();const n=_srResults[_srIdx];if(n){zoomTo(n);showDetail(n);searchDrop.classList.remove('visible');searchInput.value='';resetHL();}
  }else if((e.key==='o'||e.key==='O')&&!inSearch&&_currentNode&&detailPanel.classList.contains('open')){
    window.location.href=_obsidianUri(_currentNode.id);
  }else if(e.key==='Escape'){
    detailPanel.classList.remove('open');
    oBar.classList.remove('visible');
    activeRole=null;
    searchDrop.classList.remove('visible');
    _srResults=[];
    searchInput.value='';
    document.querySelectorAll('.role-btn').forEach(b=>b.classList.remove('active'));
    resetHL();
    pathG.selectAll('*').remove();
    node.select('.main-circle').attr('r',d=>getR(d));
    node.select('text').attr('font-weight',d=>(degreeMap.get(d.id)||0)>8?600:400);
    history.replaceState(null,'',location.pathname+location.search);
  }else if(e.key==='/'&&!inSearch){e.preventDefault();searchInput.focus();}
});
</script>
</body>
</html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without writing HTML")
    parser.add_argument("--json", action="store_true",
                        help="Dump graph data as JSON to stdout")
    parser.add_argument("--diff", action="store_true",
                        help="Compare with saved snapshot and highlight changes")
    parser.add_argument("--save-snapshot", action="store_true",
                        help="Save current graph as snapshot for future --diff runs")
    args = parser.parse_args()

    log_stream = sys.stderr if args.json else sys.stdout

    def log(message: str = "") -> None:
        print(message, file=log_stream)

    log("[scan] Scanning doc/ for documents and cross-references...")
    nodes, edges = scan_documents()

    log(f"   Documents: {len(nodes)}")
    log(f"   Edges:     {len(edges)}")

    # Category breakdown
    cat_counts: dict[str, int] = {}
    for n in nodes.values():
        cat_counts[n["cat"]] = cat_counts.get(n["cat"], 0) + 1
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        log(f"   {cat}: {count}")

    # Top hubs
    degree: dict[str, int] = {}
    for e in edges:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1
    top = sorted(degree.items(), key=lambda x: -x[1])[:10]
    log()
    log("   Top hubs:")
    for node_id, deg in top:
        log(f"      {deg:3d} <- {node_id}")

    if args.json:
        data = {"nodes": list(nodes.values()), "edges": edges}
        print(json.dumps(data, ensure_ascii=True, indent=2))
        return

    if args.dry_run:
        log()
        log("   Dry run complete. No files written.")
        return

    diff_stats: dict | None = None
    if args.diff:
        snap = load_snapshot()
        if snap is None:
            log("   [diff] No snapshot found — run with --save-snapshot first.")
        else:
            snap_nodes, snap_edges = snap
            nodes, edges, diff_stats = apply_diff(nodes, edges, snap_nodes, snap_edges)
            log(f"   [diff] +{diff_stats['new_nodes']} nodes  -{diff_stats['removed_nodes']} nodes"
                f"  +{diff_stats['new_edges']} edges  -{diff_stats['removed_edges']} edges")

    if args.save_snapshot:
        save_snapshot(nodes, edges)

    html = generate_html(nodes, edges, diff_stats)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    log()
    log(f"   Written: {OUTPUT_HTML}")
    log(f"   Size: {len(html):,} bytes")


if __name__ == "__main__":
    main()
