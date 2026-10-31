from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SDK = Path(__file__).resolve().parents[2] / "sdk" / "python"
sys.path.insert(0, str(SDK))

from graphguard import GraphGuardClient, traceable
from graphguard.context import call_stack


def test_async_tasks_keep_separate_call_stacks(tmp_path):
    async def run(name: str):
        client = GraphGuardClient(name, output_path=str(tmp_path / name))

        @traceable(client=client, node_type="tool_call")
        async def child():
            await asyncio.sleep(0)

        @traceable(client=client, node_type="strategy_decision")
        async def parent():
            await child()

        await parent()
        return client.finish_trace()

    async def both():
        return await asyncio.gather(run("one"), run("two"))

    traces = asyncio.run(both())
    assert all(len(trace["nodes"]) == 2 and len(trace["edges"]) == 1 for trace in traces)
    assert traces[0]["trace_id"] != traces[1]["trace_id"]


def test_cancelled_async_span_releases_call_stack(tmp_path):
    async def run():
        client = GraphGuardClient("cancelled", output_path=str(tmp_path))
        started = asyncio.Event()

        @traceable(client=client, node_type="tool_call")
        async def blocked():
            started.set()
            await asyncio.Future()

        task = asyncio.create_task(blocked())
        await started.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert call_stack.get() == []
        trace = client.finish_trace()
        assert len(trace["nodes"]) == 1
        assert trace["nodes"][0]["metadata"]["runtime_status"] == "failed"

    asyncio.run(run())

