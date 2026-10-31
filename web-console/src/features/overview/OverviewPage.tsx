import { useQuery } from '@tanstack/react-query'
import { Button, Card, List, Space, Tag, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { getHealth, listLiveTraces } from '../../api/graphguard'
import { MetricStrip } from '../../components/MetricStrip'
import { RiskBadge, StatusBadge } from '../../components/StatusBadge'
import { demoScenarios } from '../demo/scenarios'

export function OverviewPage() {
  const traces = useQuery({ queryKey: ['overview-traces'], queryFn: () => listLiveTraces(50) })
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: 1 })
  const items = traces.data || []
  const running = items.filter((item) => item.status === 'running').length
  const highRisk = items.filter((item) => item.riskScore >= 0.65).length
  const blockedOrSanitized = items.filter((item) => ['high', 'critical', 'medium'].includes(item.severity)).length
  return (
    <div className="page">
      <div className="page-title">
        <Space direction="vertical" size={2}>
          <Typography.Title level={2}>GraphGuard-Agent / AI Guard Console</Typography.Title>
          <Typography.Text type="secondary">Runtime security observability and guardrails for high-risk business agents.</Typography.Text>
        </Space>
        <Space>
          <Button type="primary"><Link to="/traces">Live Traces</Link></Button>
          <Button><Link to="/demo-scenarios">Run Demo</Link></Button>
        </Space>
      </div>
      <MetricStrip items={[
        { label: 'Recent Traces', value: items.length },
        { label: 'Running', value: running },
        { label: 'High Risk', value: highRisk },
        { label: 'Guard Actions', value: blockedOrSanitized },
        { label: 'API', value: health.data ? 'healthy' : 'unknown' },
      ]} />
      <div className="detail-grid">
        <Card title="Recent Trace Activity" className="panel">
          <List
            size="small"
            dataSource={items.slice(0, 6)}
            locale={{ emptyText: 'No live traces yet.' }}
            renderItem={(item) => (
              <List.Item actions={[<Link key="open" to={`/traces/${item.traceId}`}>Open</Link>]}>
                <List.Item.Meta
                  title={<Space><span>{item.traceId}</span><StatusBadge value={item.status} /></Space>}
                  description={<Space><RiskBadge severity={item.severity} score={item.riskScore} /><span>{item.project}</span></Space>}
                />
              </List.Item>
            )}
          />
        </Card>
        <Card title="Policy Pack Status" className="panel">
          <Space wrap>
            <Tag color="blue">generic_default</Tag>
            <Tag color="green">generic_default</Tag>
            <Tag>data classification</Tag>
            <Tag>role permissions</Tag>
            <Tag>process constraints</Tag>
            <Tag>audit redaction</Tag>
          </Space>
        </Card>
      </div>
      <Card title="Detection Methods" className="panel">
        <div className="metric-strip">
          {['Graph anomaly detection', 'Node embedding / semantic detection', 'Taint propagation analysis', 'Policy Pack rule engine'].map((method) => (
            <Card size="small" key={method}><Typography.Text strong>{method}</Typography.Text></Card>
          ))}
        </div>
      </Card>
      <Card title="Demo Coverage" className="panel">
        <List
          grid={{ gutter: 10, column: 4 }}
          dataSource={demoScenarios}
          renderItem={(item) => <List.Item><Card size="small" title={item.title}>{item.notes}</Card></List.Item>}
        />
      </Card>
    </div>
  )
}
