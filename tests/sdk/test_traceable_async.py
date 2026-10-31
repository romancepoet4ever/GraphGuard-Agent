from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SDK = Path(__file__).resolve().parents[2] / "sdk" / "python"
sys.path.insert(0, str(SDK))

from graphguard import GraphGuardClient, traceable


def test_traceable_supports_async_functions(tmp_path):
    client = GraphGuardClient("async", output_path=str(tmp_path))

    @traceable(client=client, node_type="agent_generation")
    async def generate(value: str) -> str:
        await asyncio.sleep(0)
        return value.upper()

    assert asyncio.run(generate("ok")) == "OK"
    assert len(client.trace.nodes) == 1
    assert client.trace.nodes[0].metadata["runtime_status"] == "completed"
