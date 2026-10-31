import { useMutation } from '@tanstack/react-query'
import { Button, Card, List, Space, Tag, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { runManualDetection } from '../../api/graphguard'
import { demoScenarios } from './scenarios'

export function DemoScenariosPage() {
  const navigate = useNavigate()
  const mutation = useMutation({ mutationFn: runManualDetection })
  const run = async (key: string) => {
    const scenario = demoScenarios.find((item) => item.key === key)
    if (!scenario) return
    try {
      const result = await mutation.mutateAsync({
        user_input: scenario.userInput,
        external_data: scenario.externalData,
        external_data_source: scenario.key,
        external_data_filename: `${scenario.key}.demo`,
        model_provider: 'openrouter',
        require_model_api: false,
      })
      message.success(`Detection complete: ${result.trace_id}`)
      navigate('/manual-detection', { state: { detectionResult: result } })
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Demo failed')
    }
  }
  return (
    <div className="page">
      <div className="page-title">
        <Typography.Title level={2}>Demo Scenarios</Typography.Title>
        <Typography.Text type="secondary">Run parity scenarios migrated from the Streamlit demo page.</Typography.Text>
      </div>
      <List
        grid={{ gutter: 12, column: 3 }}
        dataSource={demoScenarios}
        renderItem={(scenario) => (
          <List.Item>
            <Card
              title={scenario.title}
              actions={[<Button type="primary" loading={mutation.isPending} onClick={() => run(scenario.key)}>Run</Button>]}
            >
              <Space direction="vertical">
                <Tag color={scenario.expectedScore >= 0.8 ? 'red' : scenario.expectedScore >= 0.5 ? 'orange' : 'green'}>{scenario.riskType}</Tag>
                <Typography.Text>{scenario.notes}</Typography.Text>
                <Typography.Text type="secondary">Expected score: {Math.round(scenario.expectedScore * 100)}%</Typography.Text>
              </Space>
            </Card>
          </List.Item>
        )}
      />
    </div>
  )
}
