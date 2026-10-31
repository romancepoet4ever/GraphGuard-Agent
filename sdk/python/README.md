# graphguard-agent

Install the GraphGuard Python SDK independently from the GraphGuard server:

```bash
python -m pip install -e ./sdk/python
```

It remains import-compatible with existing integrations:

```python
from graphguard import GraphGuardClient, GraphGuardRuntime, traceable

client = GraphGuardClient(
    project="my-agent",
    scenario="default",
    policy_pack="generic_default",
    api_url="http://127.0.0.1:8001",
)
```

The base package only requires `requests`. LangChain and LangGraph adapters are
optional and do not make their frameworks mandatory SDK dependencies.

Policy packs include `generic_default`, `government_agent` (interrogation_agent) and `government_weather` (MeteorologicalBureau). The two business systems remain independent repositories and use the SDK through their own adapters.

