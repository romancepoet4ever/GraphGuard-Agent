from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import traceback
import networkx as nx

from src.utils.logger import log
from src.core.graph_builder import GraphBuilder
from src.detection.graph_anomaly import GraphAnomalyDetector
from src.detection.node_embedding import NodeEmbeddingDetector
from src.detection.taint_analysis import TaintAnalyzer
from src.detection.rule_engine import RuleEngine
from src.models.detection_result import ComprehensiveDetectionResult, DetectionResult
from src.detection.ipi_detector import detect_ipi

router = APIRouter(prefix="/api/detection", tags=["detection"])

graph_builder = GraphBuilder()
anomaly_detector = GraphAnomalyDetector()
node_detector = NodeEmbeddingDetector(use_semantic_model=False)
taint_analyzer = TaintAnalyzer()
rule_engine = RuleEngine()


class DetectionRequest(BaseModel):
    user_input: str
    external_data: Optional[str] = None
    context: Dict[str, Any] = {}
    external_data_source: Optional[str] = "manual"
    external_data_filename: Optional[str] = None
    model_provider: Optional[str] = "openrouter"
    model: Optional[str] = None
    base_url: Optional[str] = None
    require_model_api: bool = False


class DetectionResponse(BaseModel):
    trace_id: str
    result: ComprehensiveDetectionResult
    graph_data: Optional[Dict[str, Any]] = None
    risk_scores: Dict[str, float] = {}
    metrics: Dict[str, Any] = {}


def _compute_taint_risk(taint_report: Dict[str, Any]) -> float:
    if not taint_report:
        return 0.0
    summary = taint_report.get("summary", {}) or {}
    max_taint = float(summary.get("max_taint", 0.0))
    paths = taint_report.get("paths", []) or []
    path_factor = min(1.0, len(paths) / 3.0)
    return float(max(0.0, min(1.0, max(max_taint, 0.35 * path_factor))))


def _prompt_injection_signal(text: str) -> Dict[str, Any]:
    patterns = [
        "忽略",
        "绕过",
        "不要执行",
        "泄露检测",
        "全部证据",
        "真实结论",
        "system prompt",
        "系统提示",
    ]
    hits = [item for item in patterns if item.lower() in (text or "").lower()]
    score = 0.0
    if hits:
        score = min(1.0, 0.55 + 0.1 * len(hits))
    return {"is_malicious": bool(hits), "risk_score": score, "hits": hits, "risk_type": "prompt_injection"}


def _graph_to_api_data(G: nx.DiGraph) -> Dict[str, Any]:
    levels = {str(node): 0 for node in G.nodes()}
    try:
        order = list(nx.topological_sort(G))
    except Exception:
        order = list(G.nodes())
    for node in order:
        preds = list(G.predecessors(node))
        if preds:
            levels[str(node)] = 1 + max(levels.get(str(pred), 0) for pred in preds)

    nodes = []
    for node_id, data in G.nodes(data=True):
        node_id = str(node_id)
        node_type = str(data.get("type") or "unknown").lower()
        nodes.append(
            {
                "id": node_id,
                "label": str(data.get("label") or data.get("name") or node_id),
                "type": node_type,
                "level": int(levels.get(node_id, 0)),
                "lane": int(data.get("lane", 0) or 0),
                "ipi_source": bool(data.get("ipi_source", False)),
                "ipi_score": float(data.get("ipi_score", 0.0) or 0.0),
                "is_source": bool(data.get("ipi_source", False) or data.get("is_source", False)),
                "is_sink": node_type in {"final_report", "output", "user_visible_sink"},
                "trust_level": str(data.get("trust") or "trusted"),
                "sensitivity": "public",
                "security_tags": list(data.get("security_tags") or (["prompt_injection_candidate"] if data.get("ipi_source") else [])),
                "display_content": str(data.get("content") or data.get("full_desc") or data.get("label") or "")[:240],
            }
        )

    edges = [{"from": str(u), "to": str(v), "type": str(ed.get("type", "control_flow"))} for u, v, ed in G.edges(data=True)]
    return {"nodes": nodes, "edges": edges, "metadata": dict(G.graph)}


@router.post("/analyze", response_model=DetectionResponse)
async def analyze_input(request: DetectionRequest):
    trace_id = str(uuid.uuid4())
    try:
        log.info(f"[analyze] trace_id={trace_id} user_input_len={len(request.user_input or '')} external_len={len(request.external_data or '')}")
        

        # 1) 构图（含 external_data）
        builder = GraphBuilder(
            model_provider=request.model_provider or "openrouter",
            model=request.model,
            base_url=request.base_url,
            allow_fallback=not request.require_model_api,
        ) if request.require_model_api else graph_builder
        G_orig = builder.build_from_prompt(request.user_input, request.external_data)
        G_mask = builder.build_from_prompt(request.user_input, None)
        log.debug(f"[analyze] trace_id={trace_id} G_orig nodes={G_orig.number_of_nodes()} edges={G_orig.number_of_edges()}")
        log.debug(f"[analyze] trace_id={trace_id} G_mask nodes={G_mask.number_of_nodes()} edges={G_mask.number_of_edges()}")
        combined_text = (
            "[USER_INPUT]\n"
            f"{request.user_input}\n\n"
            "[EXTERNAL_DATA]\n"
            f"{request.external_data or ''}"
        )
        prompt_signal = _prompt_injection_signal(request.user_input or "")
        ipi = detect_ipi(combined_text)
        if prompt_signal["is_malicious"]:
            G_orig.nodes["user_input"]["ipi_source"] = True
            G_orig.nodes["user_input"]["is_source"] = True
            G_orig.nodes["user_input"]["ipi_score"] = prompt_signal["risk_score"]
            G_orig.nodes["user_input"]["security_tags"] = ["prompt_injection_candidate"]
        log.debug(f"[analyze] trace_id={trace_id} ipi={ipi}")

       # 2) MELON-style 图异动（注意：orig 在前，mask 在后）
        anomaly_report = anomaly_detector.detect_detailed(G_orig, G_mask)
        log.debug(f"[analyze] trace_id={trace_id} anomaly_report_keys={list(anomaly_report.keys())}")
        graph_anomaly_result = DetectionResult(
            is_attack=bool(anomaly_report.get("is_anomalous", False)),
            confidence=float(anomaly_report.get("score", 0.0)),
            detection_method="graph_anomaly",
            details=anomaly_report,
        )

        # 3) 用户指令 + 外部数据 instruction detection（Spotlighting/Instruction Detection 的 span 证据）
        if combined_text.strip():
            node_det = node_detector.detect(
                combined_text,
                context={"trust": "untrusted", "reachable_sink": True},
            )
            if prompt_signal["is_malicious"]:
                node_det["is_malicious"] = True
                node_det["risk_score"] = max(float(node_det.get("risk_score", 0.0) or 0.0), float(prompt_signal["risk_score"]))
                node_det.setdefault("spans", [])
                node_det["prompt_signal"] = prompt_signal
            log.debug(f"[analyze] trace_id={trace_id} node_det_keys={list(node_det.keys()) if isinstance(node_det, dict) else type(node_det)}")
            node_embedding_result = DetectionResult(
                is_attack=bool(node_det.get("is_malicious", node_det.get("has_instruction", False))),
                confidence=float(node_det.get("risk_score", 0.0)),
                detection_method="node_embedding",
                details=node_det,
            )
        else:
            node_embedding_result = DetectionResult(
                is_attack=False, confidence=0.0, detection_method="node_embedding", details={}
            )

        # 4) 规则引擎（高精度命中你样例）
        rule_result = rule_engine.check(combined_text)
        if prompt_signal["is_malicious"]:
            rule_result["is_malicious"] = True
            rule_result["score"] = max(float(rule_result.get("score", 0.0) or 0.0), float(prompt_signal["risk_score"]))
            rule_result.setdefault("matches", [])
            rule_result["matches"].append({"rule_id": "GOV-PI-001", "name": "用户提示注入", "pattern": "默认实时检测提示注入信号", "hits": prompt_signal["hits"]})
        log.debug(f"[analyze] trace_id={trace_id} rule_result_keys={list(rule_result.keys()) if isinstance(rule_result, dict) else type(rule_result)}")
        rule_score = float(rule_result.get("score", 1.0 if rule_result.get("is_malicious", False) else 0.0))
        rule_engine_result = DetectionResult(
            is_attack=bool(rule_result.get("is_malicious", False)),
            confidence=rule_score,
            detection_method="rule_engine",
            details=rule_result,
        )

        # 5) 污点分析（Not what you’ve signed up for：source→sink）
        taint_report = taint_analyzer.analyze(G_orig)
        log.debug(f"[analyze] trace_id={trace_id} taint_report_keys={list(taint_report.keys()) if isinstance(taint_report, dict) else type(taint_report)}")
        taint_risk = _compute_taint_risk(taint_report)
        taint_analysis_result = DetectionResult(
            is_attack=taint_risk > 0.5,
            confidence=float(taint_risk),
            detection_method="taint_analysis",
            details={**(taint_report or {}), "risk_score": taint_risk},
        )

        # 6) 融合：以 rule/node 为主（你这类 IPI 文本应该直接拉高）
        overall_risk = max(
            graph_anomaly_result.confidence,
            node_embedding_result.confidence,
            rule_engine_result.confidence,
            taint_analysis_result.confidence,
        )
        is_attack = overall_risk > 0.5

        if overall_risk > 0.8:
            recommended_action = "block"
        elif overall_risk > 0.5:
            recommended_action = "sanitize"
        else:
            recommended_action = "allow"

        # ✅ 关键：输出“真实节点ID”的高风险节点（用于前端红色/大小）
        # Spotlighting 的最小可解释对象：Observation 节点
        injection_risk = max(rule_score, float(node_embedding_result.confidence))
        high_risk_nodes: List[str] = []
        if injection_risk >= 0.7:
            for n, d in G_orig.nodes(data=True):
                if str(d.get("type", "")).lower() in {"observation", "user_input"}:
                    high_risk_nodes.append(str(n))

        result = ComprehensiveDetectionResult(
            trace_id=trace_id,
            is_attack=is_attack,
            overall_risk_score=float(overall_risk),
            graph_anomaly_result=graph_anomaly_result,
            node_embedding_result=node_embedding_result,
            taint_analysis_result=taint_analysis_result,
            rule_engine_result=rule_engine_result,
            graph_metrics={"num_nodes": G_orig.number_of_nodes(), "num_edges": G_orig.number_of_edges()},
            high_risk_nodes=high_risk_nodes,
            recommended_action=recommended_action,
            external_data_source=request.external_data_source,
            external_data_filename=request.external_data_filename,
        )

        graph_data = _graph_to_api_data(G_orig)
        risk_scores = {node: float(overall_risk) for node in high_risk_nodes}
        return DetectionResponse(
            trace_id=trace_id,
            result=result,
            graph_data=graph_data,
            risk_scores=risk_scores,
            metrics={"num_nodes": G_orig.number_of_nodes(), "num_edges": G_orig.number_of_edges()},
        )

    # trace_id 可能在异常更早发生时还未赋值
    except Exception as e:
        log.exception(f"[analyze][EXCEPTION] trace_id={trace_id} err={e}")
        raise HTTPException(
            status_code=500,
            detail={
                "trace_id": trace_id,
                "error": str(e),
                "hint": "Check server logs for full traceback (printed by log.exception).",
            },
        )
