from __future__ import annotations

from io import BytesIO
from typing import Any


def report_to_markdown(report: dict[str, Any]) -> str:
    risk = report.get("risk_report", {}) or {}
    methods = report.get("method_results", {}) or {}
    actions = report.get("recommended_actions", []) or []
    agent_report = str(report.get("agent_report") or "")

    lines = [
        "# GraphGuard-Agent 政务智能体安全报告",
        "",
        "## 总览",
        "",
        f"- Trace ID：{report.get('trace_id', risk.get('trace_id', 'unknown'))}",
        f"- 项目：{report.get('project', 'unknown')}",
        f"- 场景：{report.get('scenario', 'unknown')}",
        f"- 模型接口：{report.get('provider', 'mock')}",
        f"- 风险类型：{risk.get('risk_type', 'none')}",
        f"- 严重级别：{risk.get('severity', 'low')}",
        f"- 风险分数：{float(risk.get('risk_score', 0.0) or 0.0):.2f}",
        f"- 建议动作：{risk.get('recommended_action', 'allow')}",
        "",
        "## 风险路径",
        "",
        " -> ".join(str(x) for x in (risk.get("risk_path") or [])) or "未形成高风险传播路径。",
        "",
        "## 命中规则",
        "",
    ]
    for rule in risk.get("matched_rules") or []:
        if isinstance(rule, dict):
            lines.append(f"- {rule.get('id', '')} {rule.get('name', '')}：{rule.get('severity', '')} / {rule.get('action', '')}")
        else:
            lines.append(f"- {rule}")

    lines.extend(["", "## 四类检测方法", ""])
    for name, item in methods.items():
        lines.append(f"- {name}：{item.get('status', 'unknown')}，score={float(item.get('score', 0.0) or 0.0):.2f}，{item.get('evidence', '')}")

    lines.extend(["", "## 智能检测 Agent 报告", "", agent_report or "未生成智能检测 Agent 报告。"])

    lines.extend(["", "## 修复建议", ""])
    for item in actions:
        lines.append(f"- {item.get('action', '')}：{item.get('description', '')}")

    return "\n".join(lines).strip() + "\n"


def report_to_pdf_bytes(report: dict[str, Any]) -> bytes:
    markdown = report_to_markdown(report)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    except ImportError as exc:  # pragma: no cover - dependency fallback
        raise RuntimeError("reportlab is required for PDF export.") from exc

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "STSong-Light"
    styles["Heading2"].fontName = "STSong-Light"
    styles["BodyText"].fontName = "STSong-Light"
    story = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 8))
            continue
        if line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Title"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading2"]))
        else:
            story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]))
    doc.build(story)
    return buffer.getvalue()
