import type { RiskSeverity } from '../api/types'

export function normalizeSeverity(value: unknown, score = 0): RiskSeverity {
  const text = String(value || '').toLowerCase()
  if (['critical', 'high', 'medium', 'low', 'none'].includes(text)) return text as RiskSeverity
  if (score >= 0.85) return 'critical'
  if (score >= 0.65) return 'high'
  if (score >= 0.4) return 'medium'
  if (score > 0) return 'low'
  return 'none'
}

export function riskColor(severity: RiskSeverity) {
  if (severity === 'critical' || severity === 'high') return 'red'
  if (severity === 'medium') return 'orange'
  if (severity === 'low') return 'blue'
  if (severity === 'none') return 'green'
  return 'default'
}

export function statusColor(status: string) {
  if (status === 'completed' || status === 'allowed') return 'green'
  if (status === 'running') return 'blue'
  if (status === 'sanitized') return 'orange'
  if (status === 'blocked' || status === 'failed') return 'red'
  return 'default'
}
