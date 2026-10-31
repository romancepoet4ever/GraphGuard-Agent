from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GovAuditLogger:
    def __init__(self, audit_dir: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        self.audit_dir = Path(audit_dir) if audit_dir else root / "data" / "audit_logs"
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def build_record(self, graph, report: dict[str, Any]) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        audit_id = f"audit_{timestamp}_{str(report.get('trace_id', 'trace'))[-6:]}"
        metadata = graph.graph.get("metadata") or {}
        summary = metadata.get("security_summary") or {}
        return {
            "audit_id": audit_id,
            "trace_id": report.get("trace_id", ""),
            "session_id": report.get("session_id", ""),
            "scenario": report.get("scenario", ""),
            "actor": self._first_actor(graph),
            "risk_type": report.get("risk_type", "none"),
            "severity": report.get("severity", "none"),
            "matched_rules": [rule.get("id", "") for rule in report.get("matched_rules") or []],
            "policy_refs": sorted({ref for rule in report.get("matched_rules") or [] for ref in (rule.get("policy_refs") or [])}),
            "risk_path": report.get("risk_path") or [],
            "mode": summary.get("mode") or metadata.get("graphguard_mode") or metadata.get("mode") or "unknown",
            "action_taken": summary.get("action_taken") or "unknown",
            "recommended_action": report.get("recommended_action", "allow"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "evidence_retention": bool(report.get("is_attack")),
        }

    def write(self, record: dict[str, Any]) -> str:
        path = self.audit_dir / f"{record['audit_id']}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return record["audit_id"]

    @staticmethod
    def _first_actor(graph) -> str:
        for _, data in graph.nodes(data=True):
            if data.get("agent") in {"trainee", "user"}:
                return str(data.get("agent"))
        return "system"
