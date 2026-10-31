import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { traceIdFromQuery } from './utils/routeCompat'
import { OverviewPage } from './features/overview/OverviewPage'
import { DemoScenariosPage } from './features/demo/DemoScenariosPage'
import { TraceConsolePage } from './features/traces/TraceConsolePage'
import { TraceDetailPage } from './features/traces/TraceDetailPage'
import { ManualDetectionPage } from './features/manual/ManualDetectionPage'
import { ReportsPage } from './features/reports/ReportsPage'
import { RiskReportRoute } from './features/reports/RiskReportRoute'
import { RepairPage } from './features/repair/RepairPage'
import { PoliciesPage } from './features/policies/PoliciesPage'
import { IntegrationsPage } from './features/integrations/IntegrationsPage'
import { LegacyStreamlitPage } from './features/legacy/LegacyStreamlitPage'

function RootRedirect() {
  const location = useLocation()
  const traceId = traceIdFromQuery(location.search)
  return <Navigate to={traceId ? `/traces/${encodeURIComponent(traceId)}` : '/overview'} replace />
}

export function AppRoutes({ autoRefresh }: { autoRefresh: boolean }) {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/overview" element={<OverviewPage />} />
      <Route path="/demo-scenarios" element={<DemoScenariosPage />} />
      <Route path="/traces" element={<TraceConsolePage autoRefresh={autoRefresh} />} />
      <Route path="/traces/:traceId" element={<TraceDetailPage autoRefresh={autoRefresh} />} />
      <Route path="/traces/:traceId/graph" element={<TraceDetailPage autoRefresh={autoRefresh} />} />
      <Route path="/traces/:traceId/report" element={<RiskReportRoute />} />
      <Route path="/traces/:traceId/repair" element={<RepairPage />} />
      <Route path="/manual-detection" element={<ManualDetectionPage />} />
      <Route path="/reports" element={<ReportsPage />} />
      <Route path="/reports/:traceId" element={<RiskReportRoute />} />
      <Route path="/repair" element={<RepairPage />} />
      <Route path="/policies" element={<PoliciesPage />} />
      <Route path="/integrations" element={<IntegrationsPage />} />
      <Route path="/legacy-streamlit" element={<LegacyStreamlitPage />} />
      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  )
}
