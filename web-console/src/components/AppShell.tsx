import { DashboardOutlined, ExperimentOutlined, FileSearchOutlined, ForkOutlined, HistoryOutlined, MenuFoldOutlined, MenuUnfoldOutlined, SafetyOutlined, SettingOutlined, ToolOutlined } from '@ant-design/icons'
import { Breadcrumb, Button, Layout, Menu, Space, Switch, Typography } from 'antd'
import { ReactNode, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import dayjs from 'dayjs'

const { Header, Sider, Content } = Layout

const items = [
  { key: '/overview', icon: <DashboardOutlined />, label: <Link to="/overview">Overview</Link> },
  { key: '/demo-scenarios', icon: <ExperimentOutlined />, label: <Link to="/demo-scenarios">Demo Scenarios</Link> },
  { key: '/traces', icon: <ForkOutlined />, label: <Link to="/traces">Live Traces</Link> },
  { key: '/manual-detection', icon: <FileSearchOutlined />, label: <Link to="/manual-detection">Manual Detection</Link> },
  { key: '/reports', icon: <HistoryOutlined />, label: <Link to="/reports">Reports</Link> },
  { key: '/repair', icon: <ToolOutlined />, label: <Link to="/repair">Repair</Link> },
  { key: '/policies', icon: <SafetyOutlined />, label: <Link to="/policies">Policies</Link> },
  { key: '/integrations', icon: <SettingOutlined />, label: <Link to="/integrations">Integrations</Link> },
  { key: '/legacy-streamlit', icon: <SettingOutlined />, label: <Link to="/legacy-streamlit">Legacy Streamlit</Link> },
]

export function AppShell({ children, autoRefresh, onAutoRefreshChange, onRefresh }: {
  children: ReactNode
  autoRefresh: boolean
  onAutoRefreshChange: (value: boolean) => void
  onRefresh: () => void
}) {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith('/traces')) return '/traces'
    if (location.pathname.startsWith('/reports')) return '/reports'
    if (location.pathname.startsWith('/repair')) return '/repair'
    return `/${location.pathname.split('/')[1] || 'overview'}`
  }, [location.pathname])
  const crumb = location.pathname.split('/').filter(Boolean)

  return (
    <Layout className="app-shell">
      <Sider collapsible collapsed={collapsed} trigger={null} width={236} className="app-sider">
        <div className="brand">
          <SafetyOutlined />
          {!collapsed ? <span>AI Guard Console</span> : null}
        </div>
        <Menu mode="inline" selectedKeys={[selectedKey]} items={items} />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
            />
            <Breadcrumb
              items={[
                { title: <Link to="/overview">GraphGuard</Link> },
                ...crumb.map((part) => ({ title: part })),
              ]}
            />
          </Space>
          <Space>
            <Typography.Text type="secondary">Last updated {dayjs().format('HH:mm:ss')}</Typography.Text>
            <Switch size="small" checked={autoRefresh} onChange={onAutoRefreshChange} />
            <Typography.Text type="secondary">Auto refresh</Typography.Text>
            <Button onClick={onRefresh}>Refresh</Button>
          </Space>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  )
}
