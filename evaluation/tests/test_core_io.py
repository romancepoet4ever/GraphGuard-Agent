from __future__ import annotations

from evaluation.core.io import (
    read_json,
    read_jsonl,
    write_csv,
    write_json,
    write_jsonl,
)


def test_json_and_jsonl_round_trip_unicode_atomically(tmp_path) -> None:
    json_path = tmp_path / "nested" / "结果.json"
    jsonl_path = tmp_path / "nested" / "预测.jsonl"
    payload = {"结论": "通过", "count": 2}
    rows = [{"case_id": "气象-1", "文本": "哈尔滨实况"}, {"case_id": "气象-2"}]

    write_json(json_path, payload)
    write_jsonl(jsonl_path, rows)

    assert read_json(json_path) == payload
    assert read_jsonl(jsonl_path) == rows
    assert not list(json_path.parent.glob("*.tmp"))


def test_csv_writes_utf8_bom_and_stable_union_of_fields(tmp_path) -> None:
    path = tmp_path / "metrics.csv"
    write_csv(path, [{"名称": "规则", "score": 1.0}, {"名称": "污点", "status": "ok"}])

    content = path.read_bytes()
    text = content.decode("utf-8-sig")
    assert content.startswith(b"\xef\xbb\xbf")
    assert text.splitlines()[0] == "名称,score,status"
    assert "污点,,ok" in text
