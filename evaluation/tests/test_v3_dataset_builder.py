from __future__ import annotations

from collections import Counter

from evaluation.core.dataset_split import audit_splits
from evaluation.core.schemas import assert_no_gold
from evaluation.v3.dataset_builder import build_weather_dataset


def test_v3_dataset_has_required_controlled_and_guard_counts() -> None:
    bundle = build_weather_dataset()
    split_counts = Counter(row["split"] for row in bundle.controlled_cases)
    guard_gold = {row["case_id"]: row for row in bundle.guard_gold}

    assert split_counts == {"validation": 60, "test": 240}
    assert len(bundle.controlled_gold) == 300
    assert len(bundle.guard_cases) == 240
    assert sum(row["positive"] for row in bundle.guard_gold) == 120
    assert sum(not row["positive"] for row in bundle.guard_gold) == 120
    assert {row["category"] for row in bundle.guard_gold if row["positive"]} == {
        "prompt_injection",
        "tainted_valid_high_impact_tool_call",
        "synthetic_secret_leakage",
        "knowledge_poisoning",
        "report_pollution",
        "combined_attack",
    }
    assert all(case["case_id"] in guard_gold for case in bundle.guard_cases)


def test_v3_observables_have_no_gold_or_descriptive_attack_family() -> None:
    bundle = build_weather_dataset()
    for row in [*bundle.controlled_cases, *bundle.guard_cases]:
        assert_no_gold(row)
        assert not any(
            token in row["family"]
            for token in ("attack", "normal", "prompt", "secret", "poison", "pollution")
        )


def test_v3_splits_are_family_isolated_and_deduplicated() -> None:
    bundle = build_weather_dataset()
    audit = audit_splits(bundle.controlled_cases)

    assert audit["passed"] is True
    assert audit["duplicate_cases"] == []
    assert all(not overlaps for overlaps in audit["cross_split_overlap"].values())


def test_v3_build_is_deterministic() -> None:
    first = build_weather_dataset(seed=20261012)
    second = build_weather_dataset(seed=20261012)

    assert first.to_canonical_json() == second.to_canonical_json()


def test_v3_controlled_gold_covers_canonical_weather_rules() -> None:
    bundle = build_weather_dataset()
    positives = [row for row in bundle.controlled_gold if row["positive"]]

    assert {row["rule_ids"][0] for row in positives} == {
        "WX-01",
        "WX-02",
        "WX-03",
        "WX-04",
        "WX-05",
        "WX-06",
    }
    assert {row["risk_types"][0] for row in positives} == {
        "prompt_injection",
        "tool_overreach",
        "sensitive_data_leakage",
        "knowledge_poisoning",
        "report_pollution",
        "missing_provenance",
    }
