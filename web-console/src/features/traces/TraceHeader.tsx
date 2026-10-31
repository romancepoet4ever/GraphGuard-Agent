import { Button, Space, Typography } from 'antd'
import { ArrowLeftOutlined, ExportOutlined } from '@ant-design/icons'
import { Link } from 'react-router-dom'
import type { TraceDetailVM } from '../../api/types'
import { MetricStrip } from '../../components/MetricStrip'
import { StatusBadge, RiskBadge } from '../../components/StatusBadge'
import { reportExportUrl } from '../../api/client'
import { normalizeSeverity } from '../../utils/risk'

export function TraceHeader({ detail }: { detail: TraceDetailVM }) {
  const score = Number(detail.riskReport.risk_score || 0)
  const severity = normalizeSeverity(detail.riskReport.severity, score)
  return (
    <div className="panel">
      <div className="page-title">
        <Space direction="vertical" size={4}>
          <Link to="/traces"><ArrowLeftOutlined /> Back to Trace List</Link>
          <Typography.Title level={3}>{detail.traceId}</Typography.Title>
          <Space><StatusBadge value={detail.status} /><RiskBadge severity={severity} score={score} /></Space>
        </Space>
        <Button icon={<ExportOutlined />} href={reportExportUrl(detail.traceId, 'markdown')}>Export Report</Button>
      </div>
      <MetricStrip
        items={[
          { label: 'Risk Level', value: severity },
          { label: 'Duration', value: detail.durationText },
          { label: 'Policy', value: detail.policyVersion },
          { label: 'Nodes', value: detail.graphStats.nodes },
          { label: 'Events', value: detail.graphStats.events },
        ]}
      />
    </div>
  )
}
