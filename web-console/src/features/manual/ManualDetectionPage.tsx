import { useMutation } from '@tanstack/react-query'
import { Button, Card, Col, Form, Input, Row, Select, Space, Typography } from 'antd'
import { useLocation } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { runManualDetection, mapGraphData } from '../../api/graphguard'
import type { DetectionResponse } from '../../api/types'
import { ExecutionGraph } from '../graph/ExecutionGraph'
import { MetricStrip } from '../../components/MetricStrip'
import { pct } from '../../utils/format'

export function ManualDetectionPage() {
  const location = useLocation()
  const initial = (location.state as { detectionResult?: DetectionResponse } | null)?.detectionResult
  const [result, setResult] = useState<DetectionResponse | undefined>(initial)
  const [form] = Form.useForm()
  const mutation = useMutation({ mutationFn: runManualDetection })

  useEffect(() => {
    if (initial) setResult(initial)
  }, [initial])

  const graphData = useMemo(() => {
    if (!result?.graph_data) return { nodes: [], edges: [] }
    return mapGraphData(result.graph_data, result.risk_scores || {}, result.result)
  }, [result])

  const onFinish = async (values: Record<string, string | boolean>) => {
    const response = await mutation.mutateAsync({
      user_input: String(values.user_input || ''),
      external_data: String(values.external_data || ''),
      external_data_source: String(values.external_data_source || 'manual'),
      external_data_filename: String(values.external_data_filename || ''),
      model_provider: String(values.model_provider || 'openrouter'),
      model: String(values.model || ''),
      base_url: String(values.base_url || ''),
      require_model_api: Boolean(values.require_model_api),
    })
    setResult(response)
  }

  const riskScore = Number(result?.result?.overall_risk_score || 0)
  return (
    <div className="page">
      <Typography.Title level={2}>Manual Detection</Typography.Title>
      <Row gutter={12}>
        <Col xs={24} lg={9}>
          <Card className="panel" title="Input">
            <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ model_provider: 'openrouter', require_model_api: false }}>
              <Form.Item name="user_input" label="User input" rules={[{ required: true }]}>
                <Input.TextArea rows={5} />
              </Form.Item>
              <Form.Item name="external_data" label="External material">
                <Input.TextArea rows={7} />
              </Form.Item>
              <Form.Item name="external_data_source" label="External data source">
                <Input placeholder="manual / file / web / knowledge-base" />
              </Form.Item>
              <Form.Item name="external_data_filename" label="Filename">
                <Input />
              </Form.Item>
              <Form.Item name="model_provider" label="Model provider">
                <Select options={[{ value: 'openrouter' }, { value: 'openai' }, { value: 'mock' }]} />
              </Form.Item>
              <Form.Item name="model" label="Model">
                <Input placeholder="optional" />
              </Form.Item>
              <Form.Item name="base_url" label="Base URL">
                <Input placeholder="optional OpenAI-compatible URL" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={mutation.isPending}>Analyze</Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={15}>
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <MetricStrip items={[
              { label: 'Trace ID', value: result?.trace_id || 'n/a' },
              { label: 'Overall Risk', value: pct(riskScore) },
              { label: 'Action', value: String(result?.result?.recommended_action || 'n/a') },
              { label: 'Nodes', value: graphData.nodes.length },
            ]} />
            <Card className="panel" title="Execution Graph" style={{ height: 440 }}>
              <ExecutionGraph data={graphData} />
            </Card>
            <Card className="panel" title="Detection Results">
              <pre className="json-block">{JSON.stringify(result?.result || {}, null, 2)}</pre>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  )
}
