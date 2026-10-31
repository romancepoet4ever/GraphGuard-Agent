from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .schemas import FORBIDDEN_INPUT_KEYS, assert_no_gold


def static_leakage_scan(root: Path) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if not root.exists():
        return hits
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.lower() in FORBIDDEN_INPUT_KEYS
            ):
                hits.append(
                    {
                        "path": path.as_posix(),
                        "line": getattr(node, "lineno", 0),
                        "token": node.value,
                    }
                )
    return hits


def validate_observables(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        assert_no_gold(row)
