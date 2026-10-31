from __future__ import annotations

import os
from typing import Any

import requests


DEFAULT_GRAPHGUARD_API = os.getenv("GRAPHGUARD_API_URL", "http://127.0.0.1:8001").rstrip("/")
GRAPHGUARD_API_KEY = os.getenv("GRAPHGUARD_API_KEY", "")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {GRAPHGUARD_API_KEY}"} if GRAPHGUARD_API_KEY else {}


def list_live_traces(api_url: str = DEFAULT_GRAPHGUARD_API, limit: int = 100) -> list[dict[str, Any]]:
    response = requests.get(f"{api_url}/api/v1/live/traces", params={"limit": limit}, headers=_headers(), timeout=3)
    response.raise_for_status()
    return list(response.json().get("items") or [])


def get_live_trace(trace_id: str, api_url: str = DEFAULT_GRAPHGUARD_API) -> dict[str, Any]:
    response = requests.get(f"{api_url}/api/v1/live/traces/{trace_id}", headers=_headers(), timeout=3)
    response.raise_for_status()
    return dict(response.json())
