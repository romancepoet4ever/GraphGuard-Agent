import { Button, Space, Typography } from 'antd'
import { CaretRightOutlined, ReloadOutlined, ZoomInOutlined, ZoomOutOutlined } from '@ant-design/icons'
import type { LiveEvent } from '../../api/types'

export function EventGantt({ events }: { events: LiveEvent[] }) {
  const visible = events.slice(0, 12)
  return (
    <div className="panel">
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={5}>Lifecycle</Typography.Title>
        <Space>
          <Button size="small" icon={<CaretRightOutlined />} />
          <Button size="small" icon={<ZoomInOutlined />} />
          <Button size="small" icon={<ZoomOutOutlined />} />
          <Button size="small" icon={<ReloadOutlined />} />
        </Space>
      </Space>
      <div className="gantt">
        {visible.length ? visible.map((event, index) => (
          <div className="gantt-bar" key={String(event.sequence || event.event_id)}>
            <Typography.Text ellipsis>{String(event.event_type || 'event')}</Typography.Text>
            <div className="gantt-track">
              <div className="gantt-fill" style={{ width: `${Math.max(8, ((index + 1) / visible.length) * 100)}%` }} />
            </div>
          </div>
        )) : <Typography.Text type="secondary">No timestamped events.</Typography.Text>}
      </div>
    </div>
  )
}
