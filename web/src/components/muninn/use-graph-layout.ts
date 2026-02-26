import { useMemo } from "react";
import dagre from "@dagrejs/dagre";
import type { Node, Edge } from "@xyflow/react";
import type { Memory, MemoryTreeResponse } from "@/lib/types";

const NODE_WIDTH = 280;
const NODE_HEIGHT = 130;

const DEPTH_COLORS: Record<number, string> = {
  0: "#10b981",  // green - identity
  1: "#3b82f6",  // blue - index
  2: "#f59e0b",  // amber - working
  3: "#6b7280",  // gray - archive
};

function buildLayout(treeData: MemoryTreeResponse): {
  initialNodes: Node[];
  initialEdges: Edge[];
} {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 100 });

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Collect all memories: roots + all children
  const allMemories: Memory[] = [...treeData.roots];
  for (const children of Object.values(treeData.children)) {
    allMemories.push(...children);
  }

  // Add all memory nodes
  for (const mem of allMemories) {
    g.setNode(mem.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    nodes.push({
      id: mem.id,
      type: "memoryNode",
      position: { x: 0, y: 0 },
      data: { memory: mem, isGroup: false },
    });
  }

  // Add edges from treeData.edges (parent → child)
  for (const edge of treeData.edges) {
    g.setEdge(edge.source, edge.target);
    const sourceDepth = allMemories.find((m) => m.id === edge.source)?.depth ?? 1;
    edges.push({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "default",
      style: {
        stroke: DEPTH_COLORS[sourceDepth] ?? "#888",
        strokeWidth: 1.5,
      },
    });
  }

  // Run dagre layout
  dagre.layout(g);

  // Map dagre positions back
  const positionedNodes = nodes.map((node) => {
    const dagreNode = g.node(node.id);
    if (!dagreNode) return node;
    return {
      ...node,
      position: {
        x: dagreNode.x - NODE_WIDTH / 2,
        y: dagreNode.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { initialNodes: positionedNodes, initialEdges: edges };
}

export function useTreeLayout(treeData: MemoryTreeResponse): {
  initialNodes: Node[];
  initialEdges: Edge[];
} {
  return useMemo(() => buildLayout(treeData), [treeData]);
}
