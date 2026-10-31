import { Card, Statistic } from 'antd'

interface Metric {
  label: string
  value: string | number
  suffix?: string
}

export function MetricStrip({ items }: { items: Metric[] }) {
  return (
    <div className="metric-strip">
      {items.map((item) => (
        <Card size="small" key={item.label} className="metric-card">
          <Statistic title={item.label} value={item.value} suffix={item.suffix} />
        </Card>
      ))}
    </div>
  )
}
