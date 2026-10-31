import { Tag } from 'antd'
import { riskColor, statusColor } from '../utils/risk'
import type { RiskSeverity } from '../api/types'

export function StatusBadge({ value }: { value: string }) {
  return <Tag color={statusColor(value)}>{value || 'unknown'}</Tag>
}

export function RiskBadge({ severity, score }: { severity: RiskSeverity; score?: number }) {
  const label = score === undefined ? severity : `${severity} ${Math.round(score * 100)}%`
  return <Tag color={riskColor(severity)}>{label}</Tag>
}
