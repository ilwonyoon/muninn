import { useMemo } from "react";
import dagre from "@dagrejs/dagre";
import type { Node, Edge } from "@xyflow/react";
import type { MemoryTreeResponse } from "@/lib/types";

const MEMORY_WIDTH = 280;
const MEMORY_HEIGHT = 130;
const GROUP_WIDTH = 200;
const GROUP_HEIGHT = 60;

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

export function useTreeLayout(
  treeData: MemoryTreeResponse
): { nodes: Node[]; edges: Edge[] } {
  return useMemo(() => {
    const { roots, groups, edges: treeEdges } = treeData;

    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: "TB", nodesep: 50, ranksep: 100 });
    g.setDefaultEdgeLabel(() => ({}));

    // Add root nodes (depth 0)
    for (const root of roots) {
      g.setNode(root.id, { width: MEMORY_WIDTH, height: MEMORY_HEIGHT });
    }

    // Add category group nodes (virtual)
    const activeCategories = Object.entries(groups).filter(
      ([, mems]) => mems.length > 0
    );
    for (const [cat] of activeCategories) {
      g.setNode(`group:${cat}`, { width: GROUP_WIDTH, height: GROUP_HEIGHT });
    }

    // Add memory nodes under groups
    for (const [, mems] of activeCategories) {
      for (const mem of mems) {
        g.setNode(mem.id, { width: MEMORY_WIDTH, height: MEMORY_HEIGHT });
      }
    }

    // Edges: root → category groups
    for (const root of roots) {
      for (const [cat] of activeCategories) {
        g.setEdge(root.id, `group:${cat}`);
      }
    }

    // Edges: category group → memories
    for (const [cat, mems] of activeCategories) {
      for (const mem of mems) {
        g.setEdge(`group:${cat}`, mem.id);
      }
    }

    dagre.layout(g);

    // Build React Flow nodes
    const rfNodes: Node[] = [];

    // Root nodes
    for (const root of roots) {
      const pos = g.node(root.id);
      rfNodes.push({
        id: root.id,
        type: "memoryNode",
        position: {
          x: pos ? pos.x - MEMORY_WIDTH / 2 : 0,
          y: pos ? pos.y - MEMORY_HEIGHT / 2 : 0,
        },
        data: { ...root },
      });
    }

    // Category group nodes
    for (const [cat, mems] of activeCategories) {
      const nodeId = `group:${cat}`;
      const pos = g.node(nodeId);
      rfNodes.push({
        id: nodeId,
        type: "categoryGroupNode",
        position: {
          x: pos ? pos.x - GROUP_WIDTH / 2 : 0,
          y: pos ? pos.y - GROUP_HEIGHT / 2 : 0,
        },
        data: {
          label: cat.charAt(0).toUpperCase() + cat.slice(1),
          category: cat,
          isGroup: true,
          count: mems.length,
        },
      });
    }

    // Memory nodes under groups
    for (const [, mems] of activeCategories) {
      for (const mem of mems) {
        const pos = g.node(mem.id);
        rfNodes.push({
          id: mem.id,
          type: "memoryNode",
          position: {
            x: pos ? pos.x - MEMORY_WIDTH / 2 : 0,
            y: pos ? pos.y - MEMORY_HEIGHT / 2 : 0,
          },
          data: { ...mem },
        });
      }
    }

    // Build React Flow edges
    const rfEdges: Edge[] = [];

    // Root → group edges (dashed)
    for (const root of roots) {
      for (const [cat] of activeCategories) {
        rfEdges.push({
          id: `e-${root.id.slice(0, 8)}-group-${cat}`,
          source: root.id,
          target: `group:${cat}`,
          type: "smoothstep",
          style: {
            stroke: CATEGORY_COLORS[cat] ?? "var(--border-hover)",
            strokeWidth: 1.5,
            strokeDasharray: "5 5",
          },
          animated: false,
        });
      }
    }

    // Group → memory edges (solid)
    for (const [cat, mems] of activeCategories) {
      for (const mem of mems) {
        rfEdges.push({
          id: `e-group-${cat}-${mem.id.slice(0, 8)}`,
          source: `group:${cat}`,
          target: mem.id,
          type: "smoothstep",
          style: {
            stroke: CATEGORY_COLORS[cat] ?? "var(--border-hover)",
            strokeWidth: 1.5,
          },
          animated: false,
        });
      }
    }

    return { nodes: rfNodes, edges: rfEdges };
  }, [treeData]);
}
