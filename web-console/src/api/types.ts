export type RiskSeverity = 'none' | 'low' | 'medium' | 'high' | 'critical' | 'unknown'
export type TraceStatus = 'running' | 'completed' | 'failed' | 'unknown'

export interface TraceListItemVM {
  traceId: string
  status: TraceStatus
  updatedAt: string
  riskScore: number
  riskType: string
  severity: RiskSeverity
  source: string
  project: string
  scenario: string
  policyPack: string
  nodeCount: number
  edgeCount: number
}

export interface TraceDetailVM {
  traceId: string
  status: TraceStatus
  project: string
  scenario: string
  startTime: string
  endTime?: string
  durationText: string
  user?: string
  sessionId?: string
  model?: string
  policyVersion: string
  reportId?: string
  graphStats: {
    nodes: number
    edges: number
    toolCalls: number
    sanitized: number
    blocked: number
    events: number
    riskIncrement: number
    maxRiskLevel: string
  }
  riskReport: Record<string, unknown>
  trace: Record<string, unknown>
  report: Record<string, unknown>
  events: LiveEvent[]
  graphData: GraphData
  riskScores: Record<string, number>
}

export interface GraphNodeVM {
  [key: string]: unknown
  id: string
  label: string
  subtitle: string
  kind: string
  status: 'allowed' | 'sanitized' | 'blocked' | 'info'
  riskScore: number
  sensitivity: string
  displayContent: string
  raw: unknown
}

export interface GraphEdgeVM {
  [key: string]: unknown
  id: string
  source: string
  target: string
  kind: string
  taint?: string
  dashed: boolean
  highlighted: boolean
  raw: unknown
}

export interface GraphData {
  nodes: GraphNodeVM[]
  edges: GraphEdgeVM[]
  metadata?: Record<string, unknown>
}

export interface LiveEvent {
  sequence?: number
  event_id?: string
  trace_id?: string
  event_type?: string
  timestamp?: string
  payload?: Record<string, unknown>
  [key: string]: unknown
}

export interface DetectionRequest {
  user_input: string
  external_data?: string
  external_data_source?: string
  external_data_filename?: string
  model_provider?: string
  model?: string
  base_url?: string
  require_model_api?: boolean
}

export interface DetectionResponse {
  trace_id: string
  result: Record<string, unknown>
  graph_data?: unknown
  risk_scores?: Record<string, number>
  metrics?: Record<string, unknown>
}

export interface DemoScenario {
  key: string
  title: string
  riskType: string
  expectedScore: number
  userInput: string
  externalData: string
  notes: string
}
