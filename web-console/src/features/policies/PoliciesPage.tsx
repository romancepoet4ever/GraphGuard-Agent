import { Card, Input, List, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'

const packs = [
  { name: 'generic_default', status: 'active', scope: 'generic agent security', rules: 6 },
]

const rules = [
  { id: 'GG-PI-001', name: 'Prompt injection attempt', type: 'prompt_injection', severity: 'high', refs: 'internal' },
  { id: 'GG-LEAK-001', name: 'Sensitive data reaches a public sink', type: 'sensitive_data_leakage', severity: 'critical', refs: 'internal' },
  { id: 'GG-POISON-001', name: 'Poisoned retrieval material', type: 'knowledge_poisoning', severity: 'high', refs: 'internal' },
  { id: 'GG-OUT-001', name: 'Unverified claim reaches a persistent output', type: 'report_pollution', severity: 'high', refs: 'internal' },
  { id: 'GG-PII-001', name: 'Personal information exposure', type: 'personal_information_leakage', severity: 'high', refs: 'internal' },
  { id: 'GG-ROLE-001', name: 'Role override attempt', type: 'role_escape', severity: 'high', refs: 'internal' },
]

export function PoliciesPage() {
  const [query, setQuery] = useState('')
  const filtered = rules.filter((rule) => `${rule.id} ${rule.name} ${rule.type} ${rule.refs}`.toLowerCase().includes(query.toLowerCase()))
  return (
    <div className="page">
      <Typography.Title level={2}>Policies</Typography.Title>
      <div className="detail-grid">
        <Card className="panel" title="Policy Packs">
          <List
            dataSource={packs}
            renderItem={(pack) => (
              <List.Item>
                <List.Item.Meta
                  title={<Space><Tag color="blue">{pack.name}</Tag><Tag color="green">{pack.status}</Tag></Space>}
                  description={`${pack.scope} / ${pack.rules} rules`}
                />
              </List.Item>
            )}
          />
        </Card>
        <Card className="panel" title="Data Classification / Role Permissions">
          <Space wrap>
            <Tag>public</Tag><Tag>internal</Tag><Tag color="orange">sensitive</Tag><Tag color="red">highly_sensitive</Tag>
            <Tag>user</Tag><Tag>system</Tag><Tag>tool</Tag><Tag>agent</Tag>
          </Space>
        </Card>
      </div>
      <Card className="panel" title="Rule Table">
        <Input.Search placeholder="rule id, type, policy refs" value={query} onChange={(event) => setQuery(event.target.value)} style={{ marginBottom: 12 }} />
        <Table
          size="small"
          rowKey="id"
          dataSource={filtered}
          pagination={false}
          columns={[
            { title: 'Rule ID', dataIndex: 'id' },
            { title: 'Name', dataIndex: 'name' },
            { title: 'Type', dataIndex: 'type' },
            { title: 'Severity', render: (_, row) => <Tag color={row.severity === 'critical' ? 'red' : 'orange'}>{row.severity}</Tag> },
            { title: 'Policy Refs', dataIndex: 'refs' },
          ]}
        />
      </Card>
    </div>
  )
}
