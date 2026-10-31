import { Controls, MiniMap, ReactFlow, Background, useReactFlow } from '@xyflow/react'
import { Button, Space, Typography } from 'antd'
import { FullscreenOutlined, ZoomInOutlined, ZoomOutOutlined } from '@ant-design/icons'
import { useMemo } from 'react'
import type { GraphData, GraphNodeVM } from '../../api/types'
import { EmptyState } from '../../components/EmptyState'
import { toFlow } from './graphMapping'
import { nodeTypes } from './nodeTypes'

function GraphTools() {
  const flow = useReactFlow()
  return (
    <Space>
      <Button size="small" icon={<FullscreenOutlined />} onClick={() => flow.fitView({ padding: 0.2 })} />
      <Button size="small" icon={<ZoomInOutlined />} onClick={() => flow.zoomIn()} />
      <Button size="small" icon={<ZoomOutOutlined />} onClick={() => flow.zoomOut()} />
    </Space>
  )
}

export function ExecutionGraph({ data, selectedNodeId, onNodeSelect }: {
  data: GraphData
  selectedNodeId?: string
  onNodeSelect?: (node: GraphNodeVM) => void
}) {
  const flow = useMemo(() => toFlow(data, selectedNodeId), [data, selectedNodeId])
  if (!data.nodes.length) {
    return <EmptyState title="No graph nodes yet" detail="Start a business run, upload a trace, or run manual detection." />
  }
  return (
    <div className="graph-shell">
      <div style={{ position: 'absolute', zIndex: 2, padding: 8 }}>
        <Space>
          <Typography.Text strong>Execution Graph</Typography.Text>
          <GraphTools />
        </Space>
      </div>
      <ReactFlow
        nodes={flow.nodes}
        edges={flow.edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.25}
        maxZoom={1.8}
        onNodeClick={(_, node) => onNodeSelect?.(node.data as unknown as GraphNodeVM)}
      >
        <Background />
        <MiniMap pannable zoomable />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
