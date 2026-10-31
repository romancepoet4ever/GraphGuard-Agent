import { requestJson } from './client'
import type { DetectionRequest, DetectionResponse, GraphData, GraphEdgeVM, GraphNodeVM, LiveEvent, TraceDetailVM, TraceListItemVM } from './types'
import { durationText } from '../utils/format'
import { normalizeSeverity } from '../utils/risk'

const text = (value: unknown, fallback = '') => value === null || value === undefined || value === '' ? fallback : String(value)
const num = (value: unknown, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback

export async function getHealth() {
  return requestJson<Record<string, unknown>>('/health')
}

export async function listLiveTraces(limit = 100): Promise<TraceListItemVM[]> {
  const data = await requestJson<{ items?: unknown[] }>(`/api/v1/live/traces?limit=${limit}`)
  return (data.items || []).map(mapTraceListItem)
}

export async function listOfflineTraces(limit = 100): Promise<TraceListItemVM[]> {
  const data = await requestJson<{ items?: unknown[] }>(`/api/v1/traces?limit=${limit}`)
  return (data.items || []).map((item) => mapTraceListItem({ ...(item as Record<string, unknown>), status: 'completed', risk_type: 'stored_trace' }))
}

export async function getTrace(traceId: string): Promise<TraceDetailVM> {
  const data = await requestJson<Record<string, unknown>>(`/api/v1/live/traces/${encodeURIComponent(traceId)}`)
  return mapTraceDetail(data)
}

export async function getTraceEvents(traceId: string, afterSequence = 0): Promise<LiveEvent[]> {
  const data = await requestJson<{ items?: LiveEvent[] }>(`/api/v1/live/traces/${encodeURIComponent(traceId)}/events?after_sequence=${afterSequence}`)
  return data.items || []
}

export async function runManualDetection(payload: DetectionRequest) {
  return requestJson<DetectionResponse>('/api/detection/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function analyzeStoredTrace(traceId: string) {
  return requestJson<Record<string, unknown>>('/api/v1/analyze', {
    method: 'POST',
    body: JSON.stringify({ trace_id: traceId, model: { provider: 'mock' } }),
  })
}

export async function getReport(traceId: string) {
  return requestJson<Record<string, unknown>>(`/api/v1/reports/${encodeURIComponent(traceId)}`)
}

export function mapTraceListItem(raw: unknown): TraceListItemVM {
  const item = raw as Record<string, unknown>
  const score = num(item.risk_score)
  return {
    traceId: text(item.trace_id, 'unknown'),
    status: normalizeStatus(item.status),
    updatedAt: text(item.updated_at || item.created_at || item.last_event_at),
    riskScore: score,
    riskType: text(item.risk_type, 'none'),
    severity: normalizeSeverity(item.severity, score),
    source: text(item.source || item.ingestion_source, 'sdk'),
    project: text(item.project, 'unknown'),
    scenario: text(item.scenario, 'runtime'),
    policyPack: text(item.policy_pack, 'generic_default'),
    nodeCount: num(item.node_count),
    edgeCount: num(item.edge_count),
  }
}

function mapTraceDetail(raw: Record<string, unknown>): TraceDetailVM {
  const trace = (raw.trace || {}) as Record<string, unknown>
  const metadata = (trace.metadata || {}) as Record<string, unknown>
  const report = (raw.report || {}) as Record<string, unknown>
  const riskReport = ((report.risk_report || report || {}) as Record<string, unknown>)
  const graphData = mapGraphData(raw.graph_data, raw.risk_scores as Record<string, number> | undefined, riskReport)
  const events = (raw.events || []) as LiveEvent[]
  const nodes = (trace.nodes || []) as Record<string, unknown>[]
  const status = normalizeStatus(raw.status || metadata.live_status)
  const startTime = text(metadata.started_at || trace.created_at)
  const endTime = text(metadata.finished_at)
  const score = num(riskReport.risk_score)
  return {
    traceId: text(trace.trace_id || raw.trace_id, 'unknown'),
    status,
    project: text(trace.project, 'unknown'),
    scenario: text(trace.scenario, 'runtime'),
    startTime,
    endTime,
    durationText: durationText(startTime, endTime),
    sessionId: text(trace.session_id),
    model: text(metadata.model || report.model),
    policyVersion: text(metadata.policy_version || metadata.policy_pack, 'generic_default'),
    reportId: text(report.trace_id || trace.trace_id),
    graphStats: {
      nodes: graphData.nodes.length,
      edges: graphData.edges.length,
      toolCalls: nodes.filter((node) => text(node.node_type || node.type).includes('tool')).length,
      sanitized: nodes.filter((node) => text(node.status || node.action || node.metadata).includes('sanitize')).length,
      blocked: nodes.filter((node) => text(node.status || node.action || node.metadata).includes('block')).length,
      events: events.length,
      riskIncrement: score,
      maxRiskLevel: normalizeSeverity(riskReport.severity, score),
    },
    riskReport,
    trace,
    report,
    events,
    graphData,
    riskScores: (raw.risk_scores as Record<string, number>) || {},
  }
}

export function mapGraphData(raw: unknown, riskScores: Record<string, number> = {}, riskReport: Record<string, unknown> = {}): GraphData {
  const data = (raw || {}) as Record<string, unknown>
  const riskPath = new Set(((riskReport.risk_path || []) as unknown[]).map(String))
  const nodes = ((data.nodes || []) as Record<string, unknown>[]).map<GraphNodeVM>((node) => {
    const id = text(node.id)
    const kind = text(node.kind || node.type || node.node_type, 'unknown')
    const riskScore = Math.max(num(node.risk_score), num(riskScores[id]), riskPath.has(id) ? 0.85 : 0)
    return {
      id,
      label: text(node.label || node.name || id, id),
      subtitle: text(node.agent || node.sensitivity || kind),
      kind,
      status: nodeStatus(node, riskScore),
      riskScore,
      sensitivity: text(node.sensitivity, 'public'),
      displayContent: text(node.display_content || node.raw_content || node.content || node.label),
      raw: node,
    }
  })
  const edges = ((data.edges || []) as Record<string, unknown>[]).map<GraphEdgeVM>((edge, index) => {
    const source = text(edge.source || edge.from)
    const target = text(edge.target || edge.to)
    const taint = text(edge.taint)
    const highlighted = Boolean(edge.highlighted) || (riskPath.has(source) && riskPath.has(target))
    return {
      id: text(edge.id, `${source}-${target}-${index}`),
      source,
      target,
      kind: text(edge.kind || edge.edge_type || edge.type, 'control_flow'),
      taint,
      dashed: Boolean(edge.dashed) || Boolean(taint),
      highlighted,
      raw: edge,
    }
  }).filter((edge) => edge.source && edge.target)
  return { nodes, edges, metadata: (data.metadata || {}) as Record<string, unknown> }
}

function normalizeStatus(value: unknown) {
  const status = text(value, 'unknown').toLowerCase()
  if (status === 'running' || status === 'completed' || status === 'failed') return status
  return 'unknown'
}

function nodeStatus(node: Record<string, unknown>, riskScore: number): GraphNodeVM['status'] {
  const status = text(node.status || node.action || (node.metadata as Record<string, unknown> | undefined)?.runtime_status).toLowerCase()
  if (status.includes('block') || status.includes('fail')) return 'blocked'
  if (status.includes('sanitize')) return 'sanitized'
  if (riskScore >= 0.65) return 'blocked'
  if (riskScore >= 0.35) return 'sanitized'
  return status.includes('allow') || status.includes('complete') ? 'allowed' : 'info'
}
