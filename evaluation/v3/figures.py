from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from evaluation.core.io import read_jsonl
from evaluation.v3.provenance import EvaluationContext
from evaluation.v3.reporting import _read_csv

KNOWN_STEMS = (
    "weather_method_task_results",
    "weather_guard_asr_comparison",
    "weather_guard_case_breakdown",
    "weather_policy_pack_ablation",
    "weather_business_non_interference",
    "weather_guard_latency",
    "weather_business_overhead",
    "weather_lifecycle_results",
    "weather_prompt_injection_trace",
    "weather_report_pollution_trace",
)


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _save(fig: Any, figure_dir: Path, stem: str) -> list[Path]:
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    png = figure_dir / f"{stem}.png"
    pdf = figure_dir / f"{stem}.pdf"
    fig.savefig(
        png,
        dpi=160,
        bbox_inches="tight",
        metadata={"Software": "GraphGuard Evaluation V3"},
    )
    fig.savefig(
        pdf,
        bbox_inches="tight",
        metadata={
            "Creator": "GraphGuard Evaluation V3",
            "Producer": "GraphGuard Evaluation V3",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    _pyplot().close(fig)
    return [png, pdf]


def _overall(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    return next((row for row in rows if row.get("scope") == "overall"), rows[0] if rows else {})


def _method_results(context: EvaluationContext) -> list[Path]:
    methods: list[str] = []
    f1_values: list[float] = []
    recall_values: list[float] = []
    for name, filename in (
        ("Rule", "weather_rule_metrics.csv"),
        ("Taint", "weather_taint_path_metrics.csv"),
        ("Anomaly", "weather_anomaly_metrics.csv"),
        ("Fusion", "weather_fusion_metrics.csv"),
    ):
        row = _overall(context.result_dir / filename)
        if row.get("f1") is None:
            continue
        methods.append(name)
        f1_values.append(float(row["f1"]))
        recall_values.append(float(row.get("recall") or 0.0))
    if not methods:
        return []
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    positions = list(range(len(methods)))
    width = 0.36
    ax.bar([x - width / 2 for x in positions], f1_values, width, label="F1", color="#2563eb")
    ax.bar([x + width / 2 for x in positions], recall_values, width, label="Recall", color="#0f766e")
    ax.set_xticks(positions, methods)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Score")
    ax.set_title("Weather controlled detection — executed methods")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, context.figure_dir, "weather_method_task_results")


def _guard_asr(context: EvaluationContext) -> list[Path]:
    rows = _read_csv(context.result_dir / "weather_guard_metrics.csv")
    if not rows:
        return []
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(7, 4.6))
    modes = [str(row["mode"]) for row in rows]
    values = [float(row["attack_success_rate"]) for row in rows]
    bars = ax.bar(modes, values, color=["#64748b", "#f59e0b", "#16a34a"][: len(rows)])
    ax.bar_label(bars, labels=[f"{value:.1%}" for value in values], padding=3)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Attack success rate")
    ax.set_title("Runtime Guard outcome comparison")
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, context.figure_dir, "weather_guard_asr_comparison")


def _guard_breakdown(context: EvaluationContext) -> list[Path]:
    rows = [
        row
        for row in _read_csv(context.result_dir / "weather_guard_case_breakdown.csv")
        if bool(row.get("positive"))
    ]
    if not rows:
        return []
    categories = sorted({str(row["category"]) for row in rows})
    modes = [mode for mode in ("disabled", "observe", "enforce") if any(row["mode"] == mode for row in rows)]
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(11, 5.2))
    width = 0.24
    positions = list(range(len(categories)))
    colors = {"disabled": "#64748b", "observe": "#f59e0b", "enforce": "#16a34a"}
    for index, mode in enumerate(modes):
        lookup = {str(row["category"]): float(row["attack_success_rate"]) for row in rows if row["mode"] == mode}
        offset = (index - (len(modes) - 1) / 2) * width
        ax.bar(
            [x + offset for x in positions],
            [lookup.get(category, 0.0) for category in categories],
            width,
            label=mode,
            color=colors[mode],
        )
    ax.set_xticks(positions, categories, rotation=25, ha="right")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Attack success rate")
    ax.set_title("Runtime Guard attack-category breakdown")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, context.figure_dir, "weather_guard_case_breakdown")


def _policy_ablation(context: EvaluationContext) -> list[Path]:
    rows = _read_csv(context.result_dir / "weather_policy_pack_ablation_metrics.csv")
    if not rows:
        return []
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(7, 4.6))
    labels = [str(row.get("policy_pack")) for row in rows]
    values = [float(row.get("f1") or 0.0) for row in rows]
    bars = ax.bar(labels, values, color=["#94a3b8", "#2563eb"][: len(rows)])
    ax.bar_label(bars, labels=[f"{value:.3f}" for value in values], padding=3)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("F1")
    ax.set_title("Policy Pack ablation on the frozen test set")
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, context.figure_dir, "weather_policy_pack_ablation")


def _non_interference(context: EvaluationContext) -> list[Path]:
    rows = _read_csv(context.result_dir / "weather_non_interference_metrics.csv")
    row = next((item for item in rows if item.get("scope") == "overall"), rows[0] if rows else {})
    fields = (
        ("Business", "observe_business_equivalence_rate"),
        ("Raw/provenance", "raw_provenance_equivalence_rate"),
        ("Tool selection", "tool_selection_preservation_rate"),
        ("Enforce normal", "enforce_normal_pass_rate"),
    )
    if not row:
        return []
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    labels = [label for label, _ in fields]
    values = [float(row.get(field) or 0.0) for _, field in fields]
    bars = ax.bar(labels, values, color="#0f766e")
    ax.bar_label(bars, labels=[f"{value:.1%}" for value in values], padding=3)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Preservation rate")
    ax.set_title("Normal-business non-interference")
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, context.figure_dir, "weather_business_non_interference")


def _guard_latency(context: EvaluationContext) -> list[Path]:
    rows = [
        row
        for row in _read_csv(context.result_dir / "weather_performance_metrics.csv")
        if row.get("scope") == "local_guard_stage"
    ]
    if not rows:
        return []
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    labels = [str(row.get("stage")) for row in rows]
    values = [float(row.get("p95_ms") or 0.0) for row in rows]
    bars = ax.bar(labels, values, color="#7c3aed")
    ax.bar_label(bars, labels=[f"{value:.3f}" for value in values], padding=3)
    ax.set_ylabel("p95 latency (ms)")
    ax.set_title("Local Runtime Guard latency (network/waits excluded)")
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, context.figure_dir, "weather_guard_latency")


def _business_overhead(context: EvaluationContext) -> list[Path]:
    rows = [
        row
        for row in _read_csv(context.result_dir / "weather_performance_metrics.csv")
        if row.get("scope") == "controlled_runtime_flow" and row.get("mode") in {"observe", "enforce"}
    ]
    if not rows:
        return []
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row["mode"])].append(float(row.get("absolute_delta_ms") or 0.0))
    modes = [mode for mode in ("observe", "enforce") if grouped[mode]]
    values = [sum(grouped[mode]) / len(grouped[mode]) for mode in modes]
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    bars = ax.bar(modes, values, color=["#f59e0b", "#16a34a"][: len(modes)])
    ax.bar_label(bars, labels=[f"{value:.3f}" for value in values], padding=3)
    ax.set_ylabel("Mean absolute delta (ms)")
    ax.set_title("Controlled business-flow overhead (not end-to-end)")
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, context.figure_dir, "weather_business_overhead")


def _lifecycle(context: EvaluationContext) -> list[Path]:
    rows = _read_csv(context.result_dir / "weather_lifecycle_metrics.csv")
    if not rows:
        return []
    passed = sum(row.get("status") == "PASS" for row in rows)
    failed = len(rows) - passed
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    bars = ax.bar(["PASS", "non-PASS"], [passed, failed], color=["#16a34a", "#dc2626"])
    ax.bar_label(bars, padding=3)
    ax.set_ylabel("Real service contract cases")
    ax.set_title("Deferred / Resume / Cancellation lifecycle")
    ax.set_ylim(0, max(3, len(rows) + 1))
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, context.figure_dir, "weather_lifecycle_results")


def _trace_figure(context: EvaluationContext, risk_type: str, stem: str) -> list[Path]:
    gold = read_jsonl(context.dataset_dir / "weather_gold_annotations.jsonl")
    case = next(
        (
            row
            for row in gold
            if str(row.get("case_id", "")).startswith("WX-T-")
            and risk_type in (row.get("risk_types") or [])
        ),
        None,
    )
    if case is None:
        return []
    predictions = _read_csv(context.result_dir / "weather_fusion_predictions.csv")
    prediction = next((row for row in predictions if row.get("case_id") == case.get("case_id")), None)
    if prediction is None:
        return []
    path_value = prediction.get("risk_path")
    try:
        nodes = json.loads(path_value) if isinstance(path_value, str) else list(path_value or [])
    except json.JSONDecodeError:
        nodes = []
    if len(nodes) < 2:
        nodes = list((case.get("paths") or [[]])[0])
    if len(nodes) < 2:
        return []
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.axis("off")
    positions = [index / (len(nodes) - 1) for index in range(len(nodes))]
    for index, (position, node) in enumerate(zip(positions, nodes, strict=True)):
        ax.text(
            position,
            0.5,
            str(node).split(":")[-1],
            ha="center",
            va="center",
            transform=ax.transAxes,
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#fee2e2", "edgecolor": "#dc2626"},
        )
        if index:
            ax.annotate(
                "",
                xy=(position - 0.055, 0.5),
                xytext=(positions[index - 1] + 0.055, 0.5),
                xycoords=ax.transAxes,
                arrowprops={"arrowstyle": "->", "color": "#334155", "lw": 1.8},
            )
    ax.set_title(
        f"{risk_type} — {case['case_id']} — observed fusion risk path",
        pad=18,
    )
    return _save(fig, context.figure_dir, stem)


def generate_figures(context: EvaluationContext) -> list[Path]:
    for stem in KNOWN_STEMS:
        for suffix in (".png", ".pdf"):
            (context.figure_dir / f"{stem}{suffix}").unlink(missing_ok=True)
    builders: tuple[Callable[[EvaluationContext], list[Path]], ...] = (
        _method_results,
        _guard_asr,
        _guard_breakdown,
        _policy_ablation,
        _non_interference,
        _guard_latency,
        _business_overhead,
        _lifecycle,
        lambda current: _trace_figure(
            current, "prompt_injection", "weather_prompt_injection_trace"
        ),
        lambda current: _trace_figure(
            current, "report_pollution", "weather_report_pollution_trace"
        ),
    )
    generated: list[Path] = []
    for builder in builders:
        generated.extend(builder(context))
    return generated
