import { Card, Descriptions, Tabs, Typography } from 'antd'
import { CodeExample } from './CodeExample'

const sdkCode = `from graphguard import GraphGuardClient

client = GraphGuardClient(
    project="my-agent",
    policy_pack="generic_default",
    api_url="http://127.0.0.1:8001",
)

client.start_trace(trace_id="trace_demo")
client.record_node(id="user_input", label="User Input", node_type="user_input", raw_content="...")
client.finish_trace(status="completed")`

const callbackCode = `# LangChain / LangGraph callback style
callback = GraphGuardCallback(api_url="http://127.0.0.1:8001")
chain.invoke(input, config={"callbacks": [callback]})`

const uploadCode = `curl -X POST http://127.0.0.1:8001/api/v1/traces \\
  -H "Content-Type: application/json" \\
  -d '{"trace": {"trace_id": "trace_upload", "nodes": [], "edges": []}, "analyze": true}'`

export function IntegrationsPage() {
  return (
    <div className="page">
      <Typography.Title level={2}>Integrations</Typography.Title>
      <Card className="panel" title="Ports">
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="GraphGuard API">8001</Descriptions.Item>
          <Descriptions.Item label="GraphGuard Web Console">5174</Descriptions.Item>
          <Descriptions.Item label="Legacy Streamlit">8501</Descriptions.Item>
        </Descriptions>
      </Card>
      <Tabs
        items={[
          { key: 'sdk', label: 'Python SDK', children: <CodeExample>{sdkCode}</CodeExample> },
          { key: 'callback', label: 'Callback', children: <CodeExample>{callbackCode}</CodeExample> },
          { key: 'upload', label: 'Trace Upload', children: <CodeExample>{uploadCode}</CodeExample> },
          { key: 'otel', label: 'OpenTelemetry', children: <CodeExample>{'POST /api/v1/otel/analyze with span JSON to convert spans into SecurityTrace.'}</CodeExample> },
        ]}
      />
    </div>
  )
}
