import { ConfigProvider } from 'antd'
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { useMemo, useState } from 'react'
import { AppShell } from './components/AppShell'
import { AppRoutes } from './routes'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 800,
    },
  },
})

function AppFrame() {
  const [autoRefresh, setAutoRefresh] = useState(true)
  const client = useQueryClient()
  return (
    <AppShell
      autoRefresh={autoRefresh}
      onAutoRefreshChange={setAutoRefresh}
      onRefresh={() => client.invalidateQueries()}
    >
      <AppRoutes autoRefresh={autoRefresh} />
    </AppShell>
  )
}

export default function App() {
  const theme = useMemo(() => ({
    token: {
      colorPrimary: '#0b63f6',
      borderRadius: 8,
      colorBgLayout: '#f8fbff',
      fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    },
    components: {
      Card: { borderRadiusLG: 8 },
      Button: { borderRadius: 6 },
    },
  }), [])
  return (
    <ConfigProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppFrame />
        </BrowserRouter>
      </QueryClientProvider>
    </ConfigProvider>
  )
}
