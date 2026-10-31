import { Alert, Typography } from 'antd'
import { API_BASE_URL } from '../api/client'

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error || 'Unknown error')
  return (
    <Alert
      type="error"
      showIcon
      message="GraphGuard API is unavailable"
      description={
        <Typography.Text>
          {message}. Start API with <code>uvicorn api.main:app --host 127.0.0.1 --port 8001</code>. Current API URL: {API_BASE_URL}
        </Typography.Text>
      }
    />
  )
}
