from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Any

import requests


class JsonTraceExporter:
    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def save(self, trace: dict[str, Any], path: str | Path | None = None) -> str:
        target = Path(path) if path else self.output_path / f"{trace['trace_id']}_{trace.get('scenario', 'default')}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(target)


class HttpEventExporter:
    """Ordered, fail-open HTTP exporter for live GraphGuard events.

    A single worker preserves event order while keeping the business path from
    waiting for the monitoring service.  Network errors are retained in
    ``last_error`` and never crash the instrumented Agent unless ``fail_open``
    is explicitly disabled.
    """

    def __init__(
        self,
        api_url: str,
        api_key: str | None = None,
        *,
        timeout: float = 1.5,
        fail_open: bool = True,
        batch_size: int = 20,
        flush_interval_ms: int = 200,
        max_queue_size: int = 2000,
    ) -> None:
        base = api_url.rstrip("/")
        self.endpoint = base if base.endswith("/api/v1/live/events/batch") else f"{base}/api/v1/live/events/batch"
        self.api_key = api_key
        self.timeout = timeout
        self.fail_open = fail_open
        self.last_error: str | None = None
        self.last_response: dict[str, Any] | None = None
        self.batch_size = max(1, int(batch_size))
        self.flush_interval = max(0.02, int(flush_interval_ms) / 1000)
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=max_queue_size)
        self._stop = threading.Event()
        self._flush_requested = threading.Event()
        self.dropped_event_count = 0
        self._worker = threading.Thread(target=self._run, name="graphguard-export", daemon=True)
        self._worker.start()

    def submit(self, event: dict[str, Any]) -> None:
        if hasattr(event, "to_dict"):
            event = event.to_dict()
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self.dropped_event_count += 1
            # Monitoring must never block the business thread. Preserve final/security events when possible.
            if event.get("event_type") in {
                "trace_completed",
                "trace_failed",
                "trace_cancelled",
                "guard_decision",
            }:
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                    self._queue.put_nowait(event)
                except (queue.Empty, queue.Full):
                    self.last_error = "event queue full"

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    def flush(self, timeout: float = 5.0) -> None:
        self._flush_requested.set()
        deadline = time.monotonic() + timeout
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.01)
        if self._queue.unfinished_tasks and not self.fail_open:
            raise TimeoutError("GraphGuard exporter flush timed out")

    def close(self, timeout: float = 0.05) -> None:
        self._flush_requested.set()
        self._stop.set()
        self._worker.join(timeout=max(0.0, timeout))

    def _run(self) -> None:
        batch: list[dict[str, Any]] = []
        last_send = time.monotonic()
        while not self._stop.is_set() or not self._queue.empty() or batch:
            wait = max(0.01, self.flush_interval - (time.monotonic() - last_send))
            try:
                batch.append(self._queue.get(timeout=wait))
            except queue.Empty:
                pass
            ready = len(batch) >= self.batch_size or (
                batch and (time.monotonic() - last_send >= self.flush_interval or self._flush_requested.is_set() or self._stop.is_set())
            )
            if not ready:
                continue
            self._send(batch)
            for _ in batch:
                self._queue.task_done()
            batch = []
            last_send = time.monotonic()
            self._flush_requested.clear()

    def _send(self, events: list[dict[str, Any]]) -> None:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            for attempt in range(3):
                try:
                    response = requests.post(self.endpoint, json={"events": events}, headers=headers, timeout=self.timeout)
                    response.raise_for_status()
                    self.last_response = response.json()
                    self.last_error = None
                    return
                except Exception as exc:
                    self.last_error = str(exc)
                    if attempt < 2:
                        time.sleep(0.05 * (2 ** attempt))
                    elif not self.fail_open:
                        raise
        except Exception:
            if not self.fail_open:
                raise
