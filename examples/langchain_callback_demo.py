from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = ROOT / "sdk" / "python"
if str(SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(SDK_ROOT))

from langchain_core.runnables import RunnableLambda

from graphguard import GraphGuardClient
from graphguard.integrations.langchain import GraphGuardCallbackHandler


def main() -> int:
    client = GraphGuardClient(
        project="langchain-callback-demo",
        scenario="langchain_runnable",
        output_path=str(ROOT / "data" / "uploaded_traces"),
    )
    client.start_trace({"source": "langchain_callback"})
    callback = GraphGuardCallbackHandler(client)

    normalize = RunnableLambda(lambda text: {"normalized": str(text).strip()})
    summarize = RunnableLambda(lambda value: f"安全摘要：{value['normalized']}")
    chain = normalize | summarize
    output = chain.invoke("请按公开材料生成摘要", config={"callbacks": [callback]})

    output_path = Path(client.save())
    trace = json.loads(output_path.read_text(encoding="utf-8"))
    print(output)
    print(output_path)
    print(f"nodes={len(trace['nodes'])} edges={len(trace['edges'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
