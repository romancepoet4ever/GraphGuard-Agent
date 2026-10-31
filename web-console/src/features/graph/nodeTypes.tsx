import { Handle, Position, type NodeProps, type NodeTypes } from '@xyflow/react'
import { Badge, Tooltip } from 'antd'
import type { GraphNodeVM } from '../../api/types'
import { pct, truncateMiddle } from '../../utils/format'
import { nodeTooltip, type GraphFlowNode } from './graphMapping'

export function GraphGuardNode({ data }: NodeProps<GraphFlowNode>) {
  return (
    <Tooltip title={nodeTooltip(data)}>
      <div className={`graph-node ${data.status}`}>
        <Handle type="target" position={Position.Left} />
        <div className="node-title">{truncateMiddle(data.label, 34)}</div>
        <div className="node-subtitle">{truncateMiddle(data.subtitle || data.kind, 36)}</div>
        <div className="node-score">
          <Badge color={data.riskScore >= 0.65 ? '#dc2626' : data.riskScore >= 0.35 ? '#f59e0b' : '#16a34a'} text={`risk ${pct(data.riskScore)}`} />
        </div>
        <Handle type="source" position={Position.Right} />
      </div>
    </Tooltip>
  )
}

export const nodeTypes: NodeTypes = {
  graphGuardNode: GraphGuardNode,
}
