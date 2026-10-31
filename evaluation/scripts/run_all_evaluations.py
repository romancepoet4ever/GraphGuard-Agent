from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from evaluation.runners.v3_evaluation import run
from evaluation.v3.provenance import EvaluationContext, RepositoryPaths

ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the formal GraphGuard evaluation")
    parser.add_argument("--version", choices=("v3",), required=True)
    parser.add_argument("--split", choices=("test",), required=True)
    parser.add_argument("--freeze-config", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore evaluation_run.json and rerun every V3 stage.",
    )
    return parser


def resolve_output_path(repo_root: Path, requested: Path) -> Path:
    repo_root = Path(repo_root).resolve()
    candidate = (repo_root / requested).resolve() if not requested.is_absolute() else requested.resolve()
    allowed = (repo_root / "evaluation" / "results" / "v3").resolve()
    if not candidate.is_relative_to(allowed):
        raise ValueError("output must resolve under evaluation/results/v3")
    return candidate


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = resolve_output_path(ROOT, args.output)
    except ValueError as exc:
        build_parser().error(str(exc))
    context = EvaluationContext(
        repo_root=ROOT,
        dataset_dir=ROOT / "evaluation" / "datasets" / "v3",
        result_dir=output,
        figure_dir=ROOT / "evaluation" / "figures" / "v3",
        repositories=RepositoryPaths(
            graphguard=ROOT,
            weather=ROOT.parent / "下游气象应用",
            interrogation=ROOT.parent / "下游谈话训练应用",
        ),
    )
    evaluation = run(context, resume=not args.force)
    print(json.dumps(evaluation.to_dict(), ensure_ascii=False, indent=2))
    return 0 if evaluation.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
