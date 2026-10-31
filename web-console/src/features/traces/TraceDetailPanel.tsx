import { Button, Descriptions, Space, Typography } from 'antd'
import { CopyOutlined, ExportOutlined } from '@ant-design/icons'
import type { GraphNodeVM, TraceDetailVM } from '../../api/types'
import { reportExportUrl } from '../../api/client'
import { StatusBadge, RiskBadge } from '../../components/StatusBadge'
import { formatTime, pct } from '../../utils/format'
import { normalizeSeverity } from '../../utils/risk'

export function TraceDetailPanel({ detail, selectedNode }: { detail?: TraceDetailVM; selectedNode?: GraphNodeVM }) {
  if (!detail) return null
  const severity = normalizeSeverity(detail.riskReport.severity, Number(detail.riskReport.risk_score || 0))
  return (
    <div className="panel panel-fill">
      <Typography.Title level={4}>3. Trace Details</Typography.Title>
      <Space style={{ marginBottom: 10 }}>
        <StatusBadge value={detail.status} />
        <RiskBadge severity={severity} score={Number(detail.riskReport.risk_score || 0)} />
      </Space>
      <Descriptions size="small" column={1} bordered>
        <Descriptions.Item label="Trace ID">
          <Space>
            <Typography.Text copyable>{detail.traceId}</Typography.Text>
            <Button size="small" icon={<CopyOutlined />} onClick={() => navigator.clipboard?.writeText(detail.traceId)} />
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="Project">{detail.project}</Descriptions.Item>
        <Descriptions.Item label="Scenario">{detail.scenario}</Descriptions.Item>
        <Descriptions.Item label="Start">{formatTime(detail.startTime)}</Descriptions.Item>
        <Descriptions.Item label="End">{formatTime(detail.endTime)}</Descriptions.Item>
        <Descriptions.Item label="Duration">{detail.durationText}</Descriptions.Item>
        <Descriptions.Item label="Session">{detail.sessionId || 'n/a'}</Descriptions.Item>
        <Descriptions.Item label="Policy">{detail.policyVersion}</Descriptions.Item>
      </Descriptions>
      <Typography.Title level={5} style={{ marginTop: 14 }}>Graph Statistics</Typography.Title>
      <Descriptions size="small" column={2} bordered>
        <Descriptions.Item label="Nodes">{detail.graphStats.nodes}</Descriptions.Item>
        <Descriptions.Item label="Edges">{detail.graphStats.edges}</Descriptions.Item>
        <Descriptions.Item label="Tool Calls">{detail.graphStats.toolCalls}</Descriptions.Item>
        <Descriptions.Item label="Events">{detail.graphStats.events}</Descriptions.Item>
        <Descriptions.Item label="Sanitized">{detail.graphStats.sanitized}</Descriptions.Item>
        <Descriptions.Item label="Blocked">{detail.graphStats.blocked}</Descriptions.Item>
      </Descriptions>
      {selectedNode ? (
        <>
          <Typography.Title level={5} style={{ marginTop: 14 }}>Selected Node</Typography.Title>
          <Descriptions size="small" column={1} bordered>
            <Descriptions.Item label="Node">{selectedNode.label}</Descriptions.Item>
            <Descriptions.Item label="Kind">{selectedNode.kind}</Descriptions.Item>
            <Descriptions.Item label="Risk">{pct(selectedNode.riskScore)}</Descriptions.Item>
            <Descriptions.Item label="Content">{selectedNode.displayContent || 'n/a'}</Descriptions.Item>
          </Descriptions>
        </>
      ) : null}
      <Button style={{ marginTop: 14 }} icon={<ExportOutlined />} href={reportExportUrl(detail.traceId, 'markdown')}>
        Export Report
      </Button>
    </div>
  )
}
