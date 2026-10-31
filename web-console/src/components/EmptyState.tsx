import { Empty, Typography } from 'antd'

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="state-box">
      <Empty description={<Typography.Text>{title}</Typography.Text>} />
      {detail ? <Typography.Paragraph type="secondary">{detail}</Typography.Paragraph> : null}
    </div>
  )
}
