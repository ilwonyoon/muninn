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
import type { Memory, GraphEdge } from "@/lib/types";
import { MemoryGraphNode } from "@/components/muninn/memory-graph-node";
import { useGraphLayout } from "@/components/muninn/use-graph-layout";

const nodeTypes = { memoryNode: MemoryGraphNode };

interface MemoryGraphViewProps {
  memories: Memory[];
  edges: GraphEdge[];
  activeMemoryId: string | null;
  onNodeSelect: (shortId: string) => void;
}

function MemoryGraphViewInner({
  memories,
  edges,
  onNodeSelect,
}: Omit<MemoryGraphViewProps, "activeMemoryId">) {
  const { nodes, edges: rfEdges } = useGraphLayout(memories, edges);
  const { fitView } = useReactFlow();
  const fittedRef = useRef(false);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const mem = node.data as unknown as Memory;
      onNodeSelect(mem.short_id);
    },
    [onNodeSelect]
  );

  // Refit once after nodes are measured (custom nodes need a frame to measure)
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
      edges={rfEdges}
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
          const depth = (node.data as unknown as Memory)?.depth ?? 1;
          const colors: Record<number, string> = {
            0: "#00cc88",
            1: "#3b82f6",
            2: "#f59e0b",
            3: "#666666",
          };
          return colors[depth] ?? "#666666";
        }}
        maskColor="rgba(0,0,0,0.7)"
        className="!bg-[var(--bg-100)] !border !border-[var(--border-default)] !rounded"
      />
    </ReactFlow>
  );
}

export function MemoryGraphView({
  memories,
  edges,
  activeMemoryId: _activeMemoryId,
  onNodeSelect,
}: MemoryGraphViewProps) {
  return (
    <div className="h-full w-full">
      <ReactFlowProvider>
        <MemoryGraphViewInner
          memories={memories}
          edges={edges}
          onNodeSelect={onNodeSelect}
        />
      </ReactFlowProvider>
    </div>
  );
}
