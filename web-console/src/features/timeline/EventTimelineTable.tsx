import { Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { LiveEvent } from '../../api/types'
import { formatTime } from '../../utils/format'

const columns: ColumnsType<LiveEvent> = [
  { title: 'Seq', dataIndex: 'sequence', width: 72 },
  { title: 'Time', dataIndex: 'timestamp', width: 170, render: (value) => formatTime(value) },
  { title: 'Event Type', dataIndex: 'event_type', width: 160, render: (value) => <Tag>{String(value || 'unknown')}</Tag> },
  {
    title: 'Node / Edge',
    render: (_, row) => {
      const payload = row.payload || {}
      const node = (payload.node as Record<string, unknown> | undefined)?.id || payload.node_id
      const edge = payload.edge as Record<string, unknown> | undefined
      return String(node || (edge ? `${edge.source || ''} -> ${edge.target || ''}` : 'n/a'))
    },
  },
  {
    title: 'Summary',
    render: (_, row) => {
      const payload = row.payload || {}
      return (
        <Typography.Text ellipsis style={{ maxWidth: 420 }}>
          {String(payload.summary || payload.stage || payload.status || row.event_id || '')}
        </Typography.Text>
      )
    },
  },
]

export function EventTimelineTable({ events, onSelect }: { events: LiveEvent[]; onSelect?: (event: LiveEvent) => void }) {
  return (
    <Table
      rowKey={(row) => String(row.sequence || row.event_id)}
      size="small"
      columns={columns}
      dataSource={events}
      pagination={{ pageSize: 8, size: 'small' }}
      onRow={(record) => ({ onClick: () => onSelect?.(record) })}
    />
  )
}
