import html
import json
from pathlib import Path
from typing import Dict

import streamlit.components.v1 as components


_TYPE_BG = {
    "action": "#3498db",
    "tool": "#2ecc71",
    "observation": "#f39c12",
    "sanitizer": "#9b59b6",
    "user_input": "#1abc9c",
    "strategy_decision": "#3b82f6",
    "evidence_retrieval": "#f59e0b",
    "question_generation": "#60a5fa",
    "suspect_generation": "#10b981",
    "referee_scoring": "#6366f1",
    "memory_read": "#14b8a6",
    "memory_write": "#f97316",
    "final_report": "#8b5cf6",
    "case_material": "#94a3b8",
    "case_document": "#94a3b8",
    "unknown": "#95a5a6",
}


def _risk_border(risk: float) -> str:
    if risk >= 0.70:
        return "#dc2626"
    if risk >= 0.40:
        return "#f59e0b"
    return "#16a34a"


def _risk_size(risk: float) -> int:
    if risk >= 0.70:
        return 42
    if risk >= 0.40:
        return 30
    return 22


def _safe_metadata(metadata: Dict | None) -> str:
    blocked_fragments = {"raw", "content", "prompt", "reasoning", "chain", "thought", "secret", "token", "api_key"}
    safe = {
        str(key): value
        for key, value in dict(metadata or {}).items()
        if not any(fragment in str(key).lower() for fragment in blocked_fragments)
    }
    return html.escape(json.dumps(safe, ensure_ascii=False, default=str)[:1200])


def render_graph(graph_data: Dict, risk_scores: Dict | None = None) -> None:
    risk_scores = risk_scores or {}
    nodes = []
    edges = []

    for node in graph_data.get("nodes", []):
        node_id = node["id"]
        label = node.get("label", node_id)
        node_type = (node.get("type", "unknown") or "unknown").lower()
        tags = node.get("security_tags") or []
        is_source = bool(node.get("is_source", False))
        is_sink = bool(node.get("is_sink", False))
        metadata = dict(node.get("metadata") or {})
        runtime_status = str(metadata.get("runtime_status") or node.get("status") or "unknown")
        blocked = bool(metadata.get("blocked")) or runtime_status == "blocked"
        sanitized = bool(metadata.get("sanitized")) or "sanitized" in tags or node_type == "sanitizer"

        risk = float(risk_scores.get(node_id, 0.0) or 0.0)
        risk = max(0.0, min(1.0, risk))

        bg = _TYPE_BG.get(node_type, _TYPE_BG["unknown"])
        border = _risk_border(risk)
        size = _risk_size(risk)
        shape = "box" if is_sink else ("diamond" if is_source else "dot")
        label_prefix = "SRC " if is_source else ("SINK " if is_sink else "")
        if node_type == "sanitizer":
            label_prefix = "SAN " + label_prefix
            shape = "hexagon"
        if str(node.get("sensitivity", "")).lower() in {"sensitive", "highly_sensitive", "secret_like"}:
            label_prefix = "LOCK " + label_prefix
        if blocked:
            label_prefix = "BLOCKED " + label_prefix
        elif sanitized:
            label_prefix = "SANITIZED " + label_prefix

        safe_metadata = _safe_metadata(metadata)
        detail = (
            f"<b>{html.escape(str(label))}</b><br/>"
            f"Type: {html.escape(node_type)}<br/>"
            f"Status: {html.escape(runtime_status)}<br/>"
            f"Trust: {html.escape(str(node.get('trust_level', 'neutral')))}<br/>"
            f"Sensitivity: {html.escape(str(node.get('sensitivity', 'public')))}<br/>"
            f"Visibility: {html.escape(str(node.get('visibility', 'internal_only')))}<br/>"
            f"Source/Sink: {is_source}/{is_sink}<br/>"
            f"Blocked/Sanitized: {blocked}/{sanitized}<br/>"
            f"Risk: {risk:.0%}<br/>"
            f"Tags: {html.escape(', '.join(map(str, tags)))}<br/>"
            f"Metadata (redacted): <code>{safe_metadata}</code>"
        )

        lane = int(node.get("lane", 0) or 0)
        level = int(node.get("level", 0) or 0)
        x = level * 220
        y = lane * 180

        nodes.append(
            {
                "id": node_id,
                "label": f"{label_prefix}{label}",
                "shape": shape,
                "color": {"background": bg, "border": border},
                "borderWidth": 3,
                "x": x,
                "y": y,
                "size": size,
                "fixed": {"x": True, "y": True},
                "title": detail,
                "detail": detail,
            }
        )

    for edge in graph_data.get("edges", []):
        edge_type = edge.get("type", "default")
        is_risk_path = bool(edge.get("is_risk_path", False))
        dashed = edge_type in {"data_flow", "evidence_flow", "memory_flow"}
        edges.append(
            {
                "from": edge["from"],
                "to": edge["to"],
                "label": edge.get("label", ""),
                "arrows": "to",
                "dashes": dashed,
                "color": "#dc2626" if is_risk_path else "#64748b",
                "width": 4 if is_risk_path else 1,
            }
        )

    project_root = Path(__file__).resolve().parents[2]
    vis_js = (project_root / "lib" / "vis-9.1.2" / "vis-network.min.js").read_text(encoding="utf-8")
    vis_css = (project_root / "lib" / "vis-9.1.2" / "vis-network.css").read_text(encoding="utf-8")

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>{vis_css}</style>
  <style>
    body {{ margin: 0; background: #fff; }}
    #network {{ width: 100%; height: 610px; border: 1px solid #e2e8f0; border-radius: 8px; }}
    #detail {{ min-height: 76px; margin-top: 8px; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; font: 13px Arial; color: #334155; }}
  </style>
  <script>{vis_js}</script>
</head>
<body>
  <div id="network"></div>
  <div id="detail">点击节点查看状态、信任级别、敏感级别、可见性和脱敏 metadata。</div>
  <script>
    const nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
    const edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});
    const container = document.getElementById("network");
    const data = {{ nodes, edges }};
    const options = {{
      physics: {{
        enabled: true,
        hierarchicalRepulsion: {{
          centralGravity: 0.0,
          springLength: 120,
          springConstant: 0.01,
          nodeDistance: 140,
          damping: 0.09
        }},
        solver: "hierarchicalRepulsion",
        stabilization: {{ iterations: 200 }}
      }},
      layout: {{
        hierarchical: {{
          enabled: true,
          direction: "LR",
          sortMethod: "directed",
          levelSeparation: 160,
          nodeSpacing: 140
        }}
      }},
      edges: {{
        smooth: {{ type: "cubicBezier" }},
        arrows: {{ to: {{ enabled: true }} }},
        font: {{ size: 10, align: "middle" }}
      }},
      nodes: {{
        font: {{ size: 14, face: "Arial" }}
      }}
    }};
    const network = new vis.Network(container, data, options);
    network.on("click", function(params) {{
      if (!params.nodes.length) return;
      const selected = nodes.get(params.nodes[0]);
      document.getElementById("detail").innerHTML = selected.detail;
    }});
  </script>
</body>
</html>
"""

    components.html(html_content, height=720, scrolling=True)
