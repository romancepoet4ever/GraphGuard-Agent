from __future__ import annotations

import sys
import time
from pathlib import Path

SDK = Path(__file__).resolve().parents[2] / "sdk" / "python"
sys.path.insert(0, str(SDK))

from graphguard.events import TraceEvent
from graphguard.exporters import HttpEventExporter


def test_exporter_batches_without_blocking_business(monkeypatch):
    batches = []
    monkeypatch.setattr(HttpEventExporter, "_send", lambda self, events: batches.append(list(events)))
    exporter = HttpEventExporter("http://127.0.0.1:9", batch_size=2, flush_interval_ms=20)
    started = time.perf_counter()
    for seq in range(1, 4):
        exporter.submit(TraceEvent(f"e{seq}", "t1", "s1", 1, seq, "heartbeat", "now"))
    assert time.perf_counter() - started < 0.1
    exporter.flush(1)
    exporter.close()
    assert sum(len(batch) for batch in batches) == 3
