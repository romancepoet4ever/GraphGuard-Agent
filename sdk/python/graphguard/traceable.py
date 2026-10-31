from __future__ import annotations

import functools
import inspect
from typing import Any, Callable


def traceable(*, client, node_type: str, agent: str = "system", trust_level: str = "trusted",
              sensitivity: str = "public", visibility: str = "internal_only", stage: str = "runtime",
              security_tags: list[str] | None = None, is_source: bool = False, is_sink: bool = False):
    attributes = dict(agent=agent, trust_level=trust_level, sensitivity=sensitivity, visibility=visibility,
                      stage=stage, security_tags=security_tags or [], is_source=is_source, is_sink=is_sink)

    def decorator(func: Callable):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with client.aspan(func.__name__, node_type, input=_summarize({"args": args, "kwargs": kwargs}), **attributes) as span:
                    result = await func(*args, **kwargs)
                    span.set_output_summary(_summarize(result))
                    return result
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with client.span(func.__name__, node_type, input=_summarize({"args": args, "kwargs": kwargs}), **attributes) as span:
                result = func(*args, **kwargs)
                span.set_output_summary(_summarize(result))
                return result
        return sync_wrapper
    return decorator


def _summarize(value: Any, limit: int = 500) -> str:
    return repr(value)[:limit]
