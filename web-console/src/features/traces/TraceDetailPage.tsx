import { useQuery } from '@tanstack/react-query'
import { Tabs } from 'antd'
import { useParams } from 'react-router-dom'
import { getTrace } from '../../api/graphguard'
import { ErrorState } from '../../components/ErrorState'
import { EmptyState } from '../../components/EmptyState'
import { ExecutionGraph } from '../graph/ExecutionGraph'
import { PolicyEvidencePanel, RawEventsPanel, RiskReportPanel } from '../reports/RiskReportPanel'
import { EventGantt } from '../timeline/EventGantt'
import { EventTimelineTable } from '../timeline/EventTimelineTable'
import { TraceHeader } from './TraceHeader'

export function TraceDetailPage({ autoRefresh }: { autoRefresh: boolean }) {
  const params = useParams()
  const traceId = params.traceId || ''
  const query = useQuery({
    queryKey: ['trace-detail-page', traceId],
    queryFn: () => getTrace(traceId),
    enabled: Boolean(traceId),
    refetchInterval: autoRefresh ? 1500 : false,
  })
  if (query.error) return <ErrorState error={query.error} />
  if (!query.data) return <EmptyState title="Loading trace" />
  const detail = query.data
  return (
    <div className="page">
      <TraceHeader detail={detail} />
      <Tabs
        items={[
          {
            key: 'graph',
            label: 'Execution Graph',
            children: (
              <div className="detail-grid">
                <div className="panel" style={{ height: 560 }}><ExecutionGraph data={detail.graphData} /></div>
                <RiskReportPanel detail={detail} />
              </div>
            ),
          },
          {
            key: 'events',
            label: 'Events Timeline',
            children: <div className="timeline-row"><EventTimelineTable events={detail.events} /><EventGantt events={detail.events} /></div>,
          },
          { key: 'report', label: 'Risk Report', children: <RiskReportPanel detail={detail} /> },
          { key: 'policies', label: 'Policies', children: <PolicyEvidencePanel detail={detail} /> },
          { key: 'raw', label: 'Raw Events', children: <RawEventsPanel detail={detail} /> },
        ]}
      />
    </div>
  )
}
