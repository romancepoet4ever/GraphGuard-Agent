import type { Edge, Node } from '@xyflow/react'
import type { GraphData, GraphNodeVM } from '../../api/types'
import { pct } from '../../utils/format'
import { layoutGraph } from './graphLayout'

export type GraphFlowNode = Node<GraphNodeVM, 'graphGuardNode'>

export function toFlow(data: GraphData, selectedNodeId?: string) {
  const nodes: GraphFlowNode[] = data.nodes.map((node) => ({
    id: node.id,
    type: 'graphGuardNode',
    position: { x: 0, y: 0 },
    data: node,
    selected: node.id === selectedNodeId,
  }))
  const edges: Edge[] = data.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    animated: edge.highlighted,
    label: edge.taint || edge.kind,
    style: {
      stroke: edge.highlighted ? '#dc2626' : '#64748b',
      strokeWidth: edge.highlighted ? 2.5 : 1.4,
      strokeDasharray: edge.dashed ? '6 4' : undefined,
    },
  }))
  return { nodes: layoutGraph(nodes, edges), edges }
}

export function nodeTooltip(node: GraphNodeVM) {
  return `${node.kind} | ${node.sensitivity} | risk ${pct(node.riskScore)}`
}
