import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { getTrace } from '../../api/graphguard'
import { EmptyState } from '../../components/EmptyState'
import { ErrorState } from '../../components/ErrorState'
import { RiskReportPanel, RawEventsPanel } from './RiskReportPanel'

export function RiskReportRoute() {
  const params = useParams()
  const traceId = params.traceId || ''
  const query = useQuery({ queryKey: ['risk-report-route', traceId], queryFn: () => getTrace(traceId), enabled: Boolean(traceId) })
  if (query.error) return <ErrorState error={query.error} />
  if (!query.data) return <EmptyState title="Loading report" />
  return (
    <div className="page">
      <RiskReportPanel detail={query.data} />
      <RawEventsPanel detail={query.data} />
    </div>
  )
}
