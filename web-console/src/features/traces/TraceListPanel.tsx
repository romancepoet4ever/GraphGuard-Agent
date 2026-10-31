import { Input, List, Select, Space, Typography } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useMemo, useState } from 'react'
import type { TraceListItemVM } from '../../api/types'
import { StatusBadge, RiskBadge } from '../../components/StatusBadge'
import { formatTime, truncateMiddle } from '../../utils/format'

export function TraceListPanel({ items, selectedTraceId, onSelect }: {
  items: TraceListItemVM[]
  selectedTraceId?: string
  onSelect: (traceId: string) => void
}) {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<string>('all')
  const filtered = useMemo(() => {
    return items.filter((item) => {
      const hay = `${item.traceId} ${item.status} ${item.project} ${item.scenario} ${item.source}`.toLowerCase()
      return hay.includes(query.toLowerCase()) && (status === 'all' || item.status === status)
    })
  }, [items, query, status])
  return (
    <div className="panel panel-fill">
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={4}>1. Trace List</Typography.Title>
        <Typography.Text type="secondary">{filtered.length}</Typography.Text>
      </Space>
      <Space.Compact style={{ width: '100%', marginBottom: 10 }}>
        <Input prefix={<SearchOutlined />} placeholder="trace id, user, status" value={query} onChange={(event) => setQuery(event.target.value)} />
        <Select
          value={status}
          onChange={setStatus}
          style={{ width: 132 }}
          options={[
            { value: 'all', label: 'All' },
            { value: 'running', label: 'Running' },
            { value: 'completed', label: 'Completed' },
            { value: 'failed', label: 'Failed' },
          ]}
        />
      </Space.Compact>
      <List
        className="trace-list"
        dataSource={filtered}
        renderItem={(item) => (
          <List.Item className={item.traceId === selectedTraceId ? 'active' : ''} onClick={() => onSelect(item.traceId)}>
            <List.Item.Meta
              title={<Space><Typography.Text strong>{truncateMiddle(item.traceId, 26)}</Typography.Text><StatusBadge value={item.status} /></Space>}
              description={
                <Space direction="vertical" size={2}>
                  <Typography.Text type="secondary">{item.project} / {item.scenario}</Typography.Text>
                  <Space>
                    <RiskBadge severity={item.severity} score={item.riskScore} />
                    <Typography.Text type="secondary">{formatTime(item.updatedAt)}</Typography.Text>
                  </Space>
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </div>
  )
}
