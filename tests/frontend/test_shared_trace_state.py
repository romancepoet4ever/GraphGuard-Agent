from __future__ import annotations

from types import SimpleNamespace

from frontend import government_demo_utils
from frontend import session_state


class _FakeStreamlit(SimpleNamespace):
    def __init__(self) -> None:
        super().__init__(session_state={}, query_params={})


def _result(trace_id: str) -> dict:
    return {"trace": {"trace_id": trace_id}}


def test_demo_result_replaces_stale_live_selection(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.session_state.update(
        {
            "selected_trace_id": "live-old",
            "selected_live_trace_id": "live-old",
            "live_latest_seq": 17,
            "government_demo_result": _result("live-old"),
        }
    )
    fake_st.query_params["trace_id"] = "live-old"
    monkeypatch.setattr(session_state, "st", fake_st)
    monkeypatch.setattr("streamlit.session_state", fake_st.session_state)
    monkeypatch.setattr("streamlit.query_params", fake_st.query_params)

    demo = _result("demo-new")
    government_demo_utils.store_demo_result(demo)

    assert fake_st.session_state["government_demo_result"] is demo
    assert fake_st.session_state["selected_trace_id"] == "demo-new"
    assert "selected_live_trace_id" not in fake_st.session_state
    assert "live_latest_seq" not in fake_st.session_state
    assert fake_st.query_params["trace_id"] == "demo-new"

    def fail_if_live_is_requested(*_args, **_kwargs):
        raise AssertionError("the new Demo result must not be replaced by a Live API lookup")

    monkeypatch.setattr(session_state, "get_live_trace", fail_if_live_is_requested)
    assert session_state.get_shared_trace_result() is demo
