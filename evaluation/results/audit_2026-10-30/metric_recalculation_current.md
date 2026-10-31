# Independent V3 metric recomputation

Date: 2026-10-30 (Asia/Tokyo)

The auditor joined the four prediction CSV files to `evaluation/datasets/v3/weather_gold_annotations.jsonl` by `case_id`, restricted to the 240 prediction rows, and recomputed confusion counts and derived metrics without reading the metric CSV values.

| Method | N | TP | TN | FP | FN | Precision | Recall | F1 | FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Rule | 240 | 100 | 120 | 0 | 20 | 1.0000 | 0.8333 | 0.9091 | 0.0000 |
| Taint | 240 | 60 | 120 | 0 | 60 | 1.0000 | 0.5000 | 0.6667 | 0.0000 |
| Anomaly | 240 | 40 | 120 | 0 | 80 | 1.0000 | 0.3333 | 0.5000 | 0.0000 |
| Fusion | 240 | 100 | 120 | 0 | 20 | 1.0000 | 0.8333 | 0.9091 | 0.0000 |

## Method-overlap signatures

Signature order is Rule/Taint/Anomaly; `1` means predicted positive.

| Signature | Cases |
| --- | ---: |
| 000 | 120 |
| 010 | 20 |
| 100 | 20 |
| 101 | 40 |
| 110 | 40 |

Positive intersections: Rule∩Taint = 40, Rule∩Anomaly = 40, Taint∩Anomaly = 0. The current Fusion positives equal the Rule-positive set on this frozen batch. This is an observed batch relationship, not a general equivalence claim.

## Fusion recall by gold risk type

`knowledge_poisoning`, `missing_provenance`, `prompt_injection`, `report_pollution`, and `sensitive_data_leakage` are each 20/20. `tool_overreach` is 0/20. The gap is retained in formal conclusions.
