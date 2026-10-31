from __future__ import annotations

from contextvars import ContextVar


current_client: ContextVar[object | None] = ContextVar("graphguard_current_client", default=None)
call_stack: ContextVar[list[str]] = ContextVar("graphguard_call_stack", default=[])


def push_node(node_id: str) -> list[str]:
    stack = list(call_stack.get())
    stack.append(node_id)
    call_stack.set(stack)
    return stack


def pop_node() -> list[str]:
    stack = list(call_stack.get())
    if stack:
        stack.pop()
    call_stack.set(stack)
    return stack


def parent_node() -> str | None:
    stack = call_stack.get()
    return stack[-1] if stack else None
