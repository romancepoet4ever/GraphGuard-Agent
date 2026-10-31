from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from typing import Any


def normalized_text(text: str | None) -> str:
    value = unicodedata.normalize("NFKC", text or "").lower().strip()
    value = re.sub(r"\d+(?:\.\d+)?", "<number>", value)
    return re.sub(r"\s+", " ", value)


def normalized_hash(text: str | None) -> str:
    return hashlib.sha256(normalized_text(text).encode("utf-8")).hexdigest()


def topology_signature(case: dict[str, Any]) -> str:
    spec = case.get("scenario_spec") or {}
    value = {
        "path": spec.get("path") or [],
        "variant": spec.get("structure_variant") or "baseline",
        "tool": spec.get("tool_name") or "",
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def audit_splits(cases: list[dict[str, Any]]) -> dict[str, Any]:
    indexes: dict[str, dict[str, set[str]]] = {
        "normalized_text_hash": defaultdict(set),
        "external_content_hash": defaultdict(set),
        "topology_signature": defaultdict(set),
        "family": defaultdict(set),
    }
    duplicate_case_ids: list[str] = []
    seen_ids: set[str] = set()
    for case in cases:
        case_id = str(case["case_id"])
        if case_id in seen_ids:
            duplicate_case_ids.append(case_id)
        seen_ids.add(case_id)
        split = str(case["split"])
        indexes["normalized_text_hash"][normalized_hash(case.get("input_text"))].add(split)
        external = case.get("external_content")
        if external:
            indexes["external_content_hash"][normalized_hash(str(external))].add(split)
        indexes["topology_signature"][topology_signature(case)].add(split)
        indexes["family"][str(case.get("family") or "")].add(split)

    overlaps = {
        name: sorted(key for key, splits in values.items() if len(splits) > 1)
        for name, values in indexes.items()
    }
    passed = not duplicate_case_ids and all(not values for values in overlaps.values())
    return {
        "unique_cases": len(seen_ids),
        "duplicate_cases": sorted(set(duplicate_case_ids)),
        "cross_split_overlap": overlaps,
        "passed": passed,
    }
