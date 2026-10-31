import { Button, Descriptions, List, Space, Table, Tag, Typography } from 'antd'
import { ExportOutlined } from '@ant-design/icons'
import type { TraceDetailVM } from '../../api/types'
import { reportExportUrl } from '../../api/client'
import { RiskBadge } from '../../components/StatusBadge'
import { normalizeSeverity } from '../../utils/risk'

export function RiskReportPanel({ detail }: { detail?: TraceDetailVM }) {
  if (!detail) return null
  const report = detail.riskReport
  const score = Number(report.risk_score || 0)
  const rules = (report.matched_rules || []) as Record<string, unknown>[]
  const path = (report.risk_path || []) as unknown[]
  return (
    <div className="panel">
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4}>Risk Report</Typography.Title>
        <Space>
          <RiskBadge severity={normalizeSeverity(report.severity, score)} score={score} />
          <Button icon={<ExportOutlined />} href={reportExportUrl(detail.traceId, 'markdown')}>Markdown</Button>
          <Button icon={<ExportOutlined />} href={reportExportUrl(detail.traceId, 'pdf')}>PDF</Button>
        </Space>
      </Space>
      <Descriptions bordered size="small" column={2}>
        <Descriptions.Item label="Risk Type">{String(report.risk_type || 'none')}</Descriptions.Item>
        <Descriptions.Item label="Recommended Action">{String(report.recommended_action || 'allow')}</Descriptions.Item>
        <Descriptions.Item label="Severity">{String(report.severity || 'none')}</Descriptions.Item>
        <Descriptions.Item label="Attack">{String(report.is_attack ?? false)}</Descriptions.Item>
        <Descriptions.Item label="Explanation" span={2}>{String(report.explanation || 'No explanation yet.')}</Descriptions.Item>
      </Descriptions>
      <Typography.Title level={5}>Risk Path</Typography.Title>
      <Space wrap>{path.length ? path.map((item) => <Tag color="red" key={String(item)}>{String(item)}</Tag>) : <Tag>none</Tag>}</Space>
      <Typography.Title level={5}>Matched Rules</Typography.Title>
      <Table
        size="small"
        rowKey={(row) => String(row.id || row.rule_id)}
        dataSource={rules}
        pagination={false}
        columns={[
          { title: 'Rule', render: (_, row) => String(row.id || row.rule_id || 'n/a') },
          { title: 'Name', render: (_, row) => String(row.name || '') },
          { title: 'Severity', render: (_, row) => <Tag>{String(row.severity || 'n/a')}</Tag> },
          { title: 'Action', render: (_, row) => String(row.action || '') },
        ]}
      />
    </div>
  )
}

export function RawEventsPanel({ detail }: { detail?: TraceDetailVM }) {
  if (!detail) return null
  return <pre className="json-block">{JSON.stringify({ trace: detail.trace, report: detail.report, events: detail.events }, null, 2)}</pre>
}

export function PolicyEvidencePanel({ detail }: { detail?: TraceDetailVM }) {
  const evidence = ((detail?.riskReport.policy_evidence || []) as unknown[]) || []
  return (
    <List
      size="small"
      dataSource={evidence}
      locale={{ emptyText: 'No policy evidence attached to this report.' }}
      renderItem={(item) => <List.Item>{JSON.stringify(item)}</List.Item>}
    />
  )
}
