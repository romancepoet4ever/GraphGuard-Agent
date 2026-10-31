from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class TraceStore:
    def __init__(self, db_path: str | Path = "data/trace_store/graphguard.sqlite") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    project TEXT,
                    scenario TEXT,
                    source TEXT,
                    trace_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    trace_id TEXT PRIMARY KEY,
                    provider TEXT,
                    model TEXT,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(trace_id) REFERENCES traces(trace_id)
                )
                """
            )

    def save_trace(self, trace: dict[str, Any], source: str = "api") -> str:
        trace_id = str(trace.get("trace_id") or "")
        if not trace_id:
            raise ValueError("trace.trace_id is required.")
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO traces(trace_id, project, scenario, source, trace_json, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trace_id) DO UPDATE SET
                    project=excluded.project,
                    scenario=excluded.scenario,
                    source=excluded.source,
                    trace_json=excluded.trace_json,
                    updated_at=excluded.updated_at
                """,
                (
                    trace_id,
                    trace.get("project", "unknown"),
                    trace.get("scenario", "unknown"),
                    source,
                    json.dumps(trace, ensure_ascii=False),
                    trace.get("created_at") or now,
                    now,
                ),
            )
        return trace_id

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT trace_json FROM traces WHERE trace_id = ?", (trace_id,)).fetchone()
        if not row:
            return None
        return json.loads(row["trace_json"])

    def list_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT trace_id, project, scenario, source, created_at, updated_at
                FROM traces
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_report(self, trace_id: str, report: dict[str, Any], provider: str, model: str | None = None) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO reports(trace_id, provider, model, report_json, created_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(trace_id) DO UPDATE SET
                    provider=excluded.provider,
                    model=excluded.model,
                    report_json=excluded.report_json,
                    created_at=excluded.created_at
                """,
                (trace_id, provider, model or "", json.dumps(report, ensure_ascii=False, default=str), now),
            )

    def get_report(self, trace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT report_json FROM reports WHERE trace_id = ?", (trace_id,)).fetchone()
        if not row:
            return None
        return json.loads(row["report_json"])
