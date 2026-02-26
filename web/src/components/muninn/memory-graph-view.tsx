"use client";

import { useCallback, useEffect, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  ReactFlowProvider,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Memory, MemoryTreeResponse } from "@/lib/types";
import { MemoryGraphNode, CategoryGroupNode } from "@/components/muninn/memory-graph-node";
import { useTreeLayout } from "@/components/muninn/use-graph-layout";

const nodeTypes = {
  memoryNode: MemoryGraphNode,
  categoryGroupNode: CategoryGroupNode,
};

const CATEGORY_COLORS: Record<string, string> = {
  vision: "#8b5cf6",
  product: "#ec4899",
  insight: "#06b6d4",
  status: "#00cc88",
  architecture: "#3b82f6",
  decision: "#f59e0b",
  implementation: "#6366f1",
  issue: "#ef4444",
};

interface MemoryGraphViewProps {
  treeData: MemoryTreeResponse;
  activeMemoryId: string | null;
  onNodeSelect: (shortId: string) => void;
}

function MemoryGraphViewInner({
  treeData,
  onNodeSelect,
}: Omit<MemoryGraphViewProps, "activeMemoryId">) {
  const { nodes, edges } = useTreeLayout(treeData);
  const { fitView } = useReactFlow();
  const fittedRef = useRef(false);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const data = node.data as Record<string, unknown>;
      if (data.isGroup) return;
      const mem = data as unknown as Memory;
      onNodeSelect(mem.short_id);
    },
    [onNodeSelect]
  );

  useEffect(() => {
    if (fittedRef.current || nodes.length === 0) return;
    const timer = setTimeout(() => {
      fitView({ padding: 0.15 });
      fittedRef.current = true;
    }, 100);
    return () => clearTimeout(timer);
  }, [nodes, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={handleNodeClick}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      maxZoom={2}
      nodesDraggable={false}
      nodesConnectable={false}
    >
      <Background color="var(--border-default)" gap={24} size={1} />
      <Controls
        showInteractive={false}
        className="[&>button]:!bg-[var(--bg-200)] [&>button]:!border-[var(--border-default)] [&>button]:!text-[var(--fg-100)]"
      />
      <MiniMap
        nodeColor={(node) => {
          const data = node.data as Record<string, unknown>;
          if (data.isGroup) {
            return CATEGORY_COLORS[data.category as string] ?? "#666666";
          }
          const depth = (data as unknown as Memory)?.depth ?? 1;
          const depthColors: Record<number, string> = {
            0: "#00cc88",
            1: "#3b82f6",
            2: "#f59e0b",
            3: "#666666",
          };
          return depthColors[depth] ?? "#666666";
        }}
        maskColor="rgba(0,0,0,0.7)"
        className="!bg-[var(--bg-100)] !border !border-[var(--border-default)] !rounded"
      />
    </ReactFlow>
  );
}

export function MemoryGraphView({
  treeData,
  activeMemoryId: _activeMemoryId,
  onNodeSelect,
}: MemoryGraphViewProps) {
  return (
    <div className="h-full w-full">
      <ReactFlowProvider>
        <MemoryGraphViewInner
          treeData={treeData}
          onNodeSelect={onNodeSelect}
        />
      </ReactFlowProvider>
    </div>
  );
}
