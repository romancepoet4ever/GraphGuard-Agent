import { useQuery } from '@tanstack/react-query'
import { Button, Space, Table, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { listLiveTraces } from '../../api/graphguard'
import { ErrorState } from '../../components/ErrorState'
import { RiskBadge, StatusBadge } from '../../components/StatusBadge'
import { formatTime } from '../../utils/format'

export function ReportsPage() {
  const query = useQuery({ queryKey: ['reports-live-traces'], queryFn: () => listLiveTraces(200) })
  if (query.error) return <ErrorState error={query.error} />
  return (
    <div className="page">
      <div className="page-title">
        <Typography.Title level={2}>Reports</Typography.Title>
      </div>
      <Table
        loading={query.isLoading}
        rowKey="traceId"
        dataSource={query.data || []}
        columns={[
          { title: 'Trace ID', dataIndex: 'traceId' },
          { title: 'Status', render: (_, row) => <StatusBadge value={row.status} /> },
          { title: 'Risk', render: (_, row) => <RiskBadge severity={row.severity} score={row.riskScore} /> },
          { title: 'Type', dataIndex: 'riskType' },
          { title: 'Updated', render: (_, row) => formatTime(row.updatedAt) },
          { title: 'Action', render: (_, row) => <Space><Button size="small"><Link to={`/traces/${row.traceId}/report`}>Open</Link></Button></Space> },
        ]}
      />
    </div>
  )
}
