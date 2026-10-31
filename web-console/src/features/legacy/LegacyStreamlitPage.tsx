import { Button, Card, Typography } from 'antd'
import { STREAMLIT_URL } from '../../api/client'

export function LegacyStreamlitPage() {
  return (
    <div className="page">
      <Typography.Title level={2}>Legacy Streamlit Console</Typography.Title>
      <Card className="panel">
        <Typography.Paragraph>
          The Streamlit app is retained as a fallback and emergency demo entry. It should remain runnable while this Web Console is the primary competition display.
        </Typography.Paragraph>
        <pre className="code-block">streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501</pre>
        <Button href={STREAMLIT_URL}>Open Legacy Console</Button>
      </Card>
    </div>
  )
}
