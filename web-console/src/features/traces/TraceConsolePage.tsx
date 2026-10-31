import { useQuery } from '@tanstack/react-query'
import { Card, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getTrace, listLiveTraces } from '../../api/graphguard'
import type { GraphNodeVM } from '../../api/types'
import { EmptyState } from '../../components/EmptyState'
import { ErrorState } from '../../components/ErrorState'
import { ExecutionGraph } from '../graph/ExecutionGraph'
import { EventGantt } from '../timeline/EventGantt'
import { EventTimelineTable } from '../timeline/EventTimelineTable'
import { TraceDetailPanel } from './TraceDetailPanel'
import { TraceListPanel } from './TraceListPanel'

export function TraceConsolePage({ autoRefresh }: { autoRefresh: boolean }) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialTrace = searchParams.get('trace_id') || undefined
  const [selectedTraceId, setSelectedTraceId] = useState(initialTrace)
  const [selectedNode, setSelectedNode] = useState<GraphNodeVM>()

  const listQuery = useQuery({
    queryKey: ['live-traces'],
    queryFn: () => listLiveTraces(100),
    refetchInterval: autoRefresh ? 1500 : false,
  })
  const detailQuery = useQuery({
    queryKey: ['live-trace', selectedTraceId],
    queryFn: () => getTrace(selectedTraceId || ''),
    enabled: Boolean(selectedTraceId),
    refetchInterval: autoRefresh ? 1500 : false,
  })

  useEffect(() => {
    if (!selectedTraceId && listQuery.data?.length) {
      setSelectedTraceId(listQuery.data[0].traceId)
    }
  }, [listQuery.data, selectedTraceId])

  const handleSelect = (traceId: string) => {
    setSelectedTraceId(traceId)
    setSelectedNode(undefined)
    navigate(`/traces?selected=${encodeURIComponent(traceId)}`, { replace: true })
  }

  if (listQuery.error) return <ErrorState error={listQuery.error} />

  return (
    <div className="control-grid">
      <TraceListPanel items={listQuery.data || []} selectedTraceId={selectedTraceId} onSelect={handleSelect} />
      <div className="panel panel-fill">
        <Typography.Title level={4}>2. Execution Graph</Typography.Title>
        {detailQuery.error ? <ErrorState error={detailQuery.error} /> : detailQuery.data ? (
          <ExecutionGraph data={detailQuery.data.graphData} selectedNodeId={selectedNode?.id} onNodeSelect={setSelectedNode} />
        ) : <EmptyState title="No trace selected" detail="Select a trace from the list or open /traces/{trace_id}." />}
      </div>
      <TraceDetailPanel detail={detailQuery.data} selectedNode={selectedNode} />
      <Card className="panel" style={{ gridColumn: '1 / -1' }}>
        <Typography.Title level={4}>4. Event Timeline</Typography.Title>
        <div className="timeline-row">
          <EventTimelineTable events={detailQuery.data?.events || []} />
          <EventGantt events={detailQuery.data?.events || []} />
        </div>
      </Card>
    </div>
  )
}
