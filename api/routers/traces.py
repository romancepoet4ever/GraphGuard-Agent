from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from src.adapters.security_trace_adapter import SecurityTraceAdapter
from src.adapters.opentelemetry_adapter import otel_spans_to_security_trace
from src.agents.detection_agent import GraphGuardDetectionAgent
from src.agents.model_clients import ModelClientConfig
from src.core.trace_store import TraceStore
from src.utils.report_exporter import report_to_markdown, report_to_pdf_bytes


router = APIRouter(prefix="/api/v1", tags=["security-traces"])

store = TraceStore()
adapter = SecurityTraceAdapter()


Provider = Literal["mock", "openai", "openrouter"]


class ModelOptions(BaseModel):
    provider: Provider = "mock"
    model: str | None = None
    api_key: str | None = Field(default=None, repr=False)
    base_url: str | None = None
    temperature: float = 0.2


class TraceIngestionRequest(BaseModel):
    trace: dict[str, Any]
    source: str = "api"
    analyze: bool = False
    model: ModelOptions = Field(default_factory=ModelOptions)


class AnalyzeRequest(BaseModel):
    trace_id: str | None = None
    trace: dict[str, Any] | None = None
    source: str = "api"
    model: ModelOptions = Field(default_factory=ModelOptions)


class OTelAnalyzeRequest(BaseModel):
    spans: dict[str, Any] | list[dict[str, Any]]
    project: str = "otel-import"
    source: str = "otel_api"
    analyze: bool = True
    model: ModelOptions = Field(default_factory=ModelOptions)


class TraceIngestionResponse(BaseModel):
    trace_id: str
    stored: bool
    warnings: list[str]
    report: dict[str, Any] | None = None


class AnalyzeResponse(BaseModel):
    trace_id: str
    provider: Provider
    model: str | None = None
    report: dict[str, Any]


@router.post("/traces", response_model=TraceIngestionResponse)
async def ingest_trace(request: TraceIngestionRequest):
    warnings = adapter.validate_trace(request.trace)
    if warnings:
        raise HTTPException(status_code=400, detail={"message": "Invalid SecurityTrace", "warnings": warnings})

    trace_id = store.save_trace(request.trace, source=request.source)
    report = None
    if request.analyze:
        report = _run_detection_agent_or_raise(request.trace, request.model)
        store.save_report(trace_id, report, provider=request.model.provider, model=request.model.model)
    return TraceIngestionResponse(trace_id=trace_id, stored=True, warnings=[], report=report)


@router.get("/traces")
async def list_traces(limit: int = 100):
    return {"items": store.list_traces(limit=limit)}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_trace(request: AnalyzeRequest):
    trace = request.trace
    if trace is None:
        if not request.trace_id:
            raise HTTPException(status_code=400, detail="Either trace or trace_id is required.")
        trace = store.get_trace(request.trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail=f"Trace not found: {request.trace_id}")

    warnings = adapter.validate_trace(trace)
    if warnings:
        raise HTTPException(status_code=400, detail={"message": "Invalid SecurityTrace", "warnings": warnings})

    trace_id = store.save_trace(trace, source=request.source)
    report = _run_detection_agent_or_raise(trace, request.model)
    store.save_report(trace_id, report, provider=request.model.provider, model=request.model.model)
    return AnalyzeResponse(trace_id=trace_id, provider=request.model.provider, model=request.model.model, report=report)


@router.get("/reports/{trace_id}")
async def get_report(trace_id: str):
    report = store.get_report(trace_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report not found: {trace_id}")
    return report


@router.get("/reports/{trace_id}/export")
async def export_report(trace_id: str, format: Literal["markdown", "pdf"] = "markdown"):
    report = store.get_report(trace_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report not found: {trace_id}")

    if format == "markdown":
        body = report_to_markdown(report)
        return Response(
            content=body,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{trace_id}_risk_report.md"'},
        )

    body = report_to_pdf_bytes(report)
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{trace_id}_risk_report.pdf"'},
    )


@router.post("/otel/analyze", response_model=AnalyzeResponse)
async def analyze_otel_trace(request: OTelAnalyzeRequest):
    trace = otel_spans_to_security_trace(request.spans, project=request.project)
    trace_id = store.save_trace(trace, source=request.source)
    report = _run_detection_agent_or_raise(trace, request.model) if request.analyze else {}
    if report:
        store.save_report(trace_id, report, provider=request.model.provider, model=request.model.model)
    return AnalyzeResponse(trace_id=trace_id, provider=request.model.provider, model=request.model.model, report=report)


def _run_detection_agent(trace: dict[str, Any], options: ModelOptions) -> dict[str, Any]:
    config = ModelClientConfig(
        provider=options.provider,
        model=options.model,
        api_key=options.api_key,
        base_url=options.base_url,
        temperature=options.temperature,
    )
    agent = GraphGuardDetectionAgent(config)
    return agent.analyze(trace)


def _run_detection_agent_or_raise(trace: dict[str, Any], options: ModelOptions) -> dict[str, Any]:
    try:
        return _run_detection_agent(trace, options)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail={"message": "Model provider is not ready.", "error": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Trace analysis failed.", "error": str(exc)}) from exc
