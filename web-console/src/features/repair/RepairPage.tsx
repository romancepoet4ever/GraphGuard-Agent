import { useQuery } from '@tanstack/react-query'
import { Button, Card, List, Space, Tag, Typography } from 'antd'
import { useParams } from 'react-router-dom'
import { getTrace, listLiveTraces } from '../../api/graphguard'
import { EmptyState } from '../../components/EmptyState'
import { ErrorState } from '../../components/ErrorState'
import { ExecutionGraph } from '../graph/ExecutionGraph'

export function RepairPage() {
  const params = useParams()
  const list = useQuery({ queryKey: ['repair-traces'], queryFn: () => listLiveTraces(1), enabled: !params.traceId })
  const traceId = params.traceId || list.data?.[0]?.traceId
  const detail = useQuery({ queryKey: ['repair-detail', traceId], queryFn: () => getTrace(traceId || ''), enabled: Boolean(traceId) })
  if (detail.error) return <ErrorState error={detail.error} />
  if (!detail.data) return <EmptyState title="No trace available for repair" />
  const suggestions = ((detail.data.riskReport.repair_suggestions || detail.data.report.recommended_actions || []) as unknown[])
  return (
    <div className="page">
      <div className="page-title">
        <Typography.Title level={2}>Repair Suggestions</Typography.Title>
        <Typography.Text type="secondary">{detail.data.traceId}</Typography.Text>
      </div>
      <div className="detail-grid">
        <Card className="panel" title="Before / After Graph" style={{ height: 540 }}>
          <ExecutionGraph data={detail.data.graphData} />
        </Card>
        <Card className="panel" title="Recommended Actions">
          <Space wrap style={{ marginBottom: 12 }}>
            {['allow', 'sanitize', 'block', 'audit', 'isolate_context'].map((item) => <Tag key={item}>{item}</Tag>)}
          </Space>
          <List
            dataSource={suggestions.length ? suggestions : ['No explicit repair suggestion yet. Review high-risk nodes and taint edges.']}
            renderItem={(item) => (
              <List.Item actions={[<Button key="audit" size="small">Audit</Button>]}>
                {typeof item === 'string' ? item : JSON.stringify(item)}
              </List.Item>
            )}
          />
        </Card>
      </div>
    </div>
  )
}
