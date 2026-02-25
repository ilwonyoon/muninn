import { useMemo } from "react";
import dagre from "@dagrejs/dagre";
import type { Node, Edge } from "@xyflow/react";
import type { Memory, GraphEdge } from "@/lib/types";

type MemoryNodeData = Memory & Record<string, unknown>;
type MemoryNode = Node<MemoryNodeData>;

const NODE_WIDTH = 280;
const NODE_HEIGHT = 130;
const LAYER_HEIGHT = 200;

export function useGraphLayout(
  memories: Memory[],
  edges: GraphEdge[]
): { nodes: MemoryNode[]; edges: Edge[] } {
  return useMemo(() => {
    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 80 });
    g.setDefaultEdgeLabel(() => ({}));

    // Add nodes
    for (const mem of memories) {
      g.setNode(mem.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    }

    // Add edges
    for (const edge of edges) {
      g.setEdge(edge.source, edge.target);
    }

    dagre.layout(g);

    // Convert to React Flow format
    // Override y with depth-based banding for consistent layers
    const rfNodes: MemoryNode[] = memories.map((mem) => {
      const pos = g.node(mem.id);
      return {
        id: mem.id,
        type: "memoryNode",
        position: {
          x: pos ? pos.x - NODE_WIDTH / 2 : 0,
          y: mem.depth * LAYER_HEIGHT,
        },
        data: { ...mem } as MemoryNodeData,
      };
    });

    // Group by depth and spread orphans (nodes dagre placed all at x=0)
    const depthGroups = new Map<number, MemoryNode[]>();
    for (const node of rfNodes) {
      const d = node.data.depth;
      if (!depthGroups.has(d)) depthGroups.set(d, []);
      depthGroups.get(d)!.push(node);
    }
    for (const [, group] of depthGroups) {
      const xs = group.map((n) => n.position.x);
      const allSame = xs.every((x) => x === xs[0]);
      if (allSame && group.length > 1) {
        const totalWidth = group.length * (NODE_WIDTH + 40) - 40;
        const startX = -totalWidth / 2;
        group.forEach((node, i) => {
          node.position.x = startX + i * (NODE_WIDTH + 40);
        });
      }
    }

    const rfEdges: Edge[] = edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: "smoothstep",
      style: { stroke: "var(--border-hover)", strokeWidth: 1.5 },
      animated: false,
    }));

    return { nodes: rfNodes, edges: rfEdges };
  }, [memories, edges]);
}
