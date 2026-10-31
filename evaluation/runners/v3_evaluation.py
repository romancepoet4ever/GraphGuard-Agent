from __future__ import annotations

from evaluation.v3.orchestrator import EvaluationRun, run_v3
from evaluation.v3.provenance import EvaluationContext


def run(context: EvaluationContext, *, resume: bool = True) -> EvaluationRun:
    return run_v3(context, resume=resume)
