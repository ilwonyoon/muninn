"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  type Node,
  type NodeChange,
  type OnSelectionChangeParams,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Memory, MemoryTreeResponse } from "@/lib/types";
import { MemoryGraphNode, CategoryGroupNode } from "@/components/muninn/memory-graph-node";
import { useTreeLayout } from "@/components/muninn/use-graph-layout";
import { CATEGORY_COLORS } from "@/lib/constants";

const nodeTypes = {
  memoryNode: MemoryGraphNode,
  categoryGroupNode: CategoryGroupNode,
};

interface MemoryGraphViewProps {
  treeData: MemoryTreeResponse;
  activeMemoryId: string | null;
  onNodeSelect: (shortId: string) => void;
  onDeleteRequest: (memory: Memory) => void;
}

function MemoryGraphViewInner({
  treeData,
  onNodeSelect,
  onDeleteRequest,
}: Omit<MemoryGraphViewProps, "activeMemoryId">) {
  const { initialNodes, initialEdges } = useTreeLayout(treeData);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { fitView } = useReactFlow();
  const fittedRef = useRef(false);
  const [selectedMemoryNode, setSelectedMemoryNode] = useState<Node | null>(null);
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

  // Undo/redo for node positions
  type PositionSnapshot = Record<string, { x: number; y: number }>;
  const undoStack = useRef<PositionSnapshot[]>([]);
  const redoStack = useRef<PositionSnapshot[]>([]);
  const isDragging = useRef(false);

  const capturePositions = useCallback((): PositionSnapshot => {
    const snap: PositionSnapshot = {};
    for (const n of nodes) {
      snap[n.id] = { ...n.position };
    }
    return snap;
  }, [nodes]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      // Detect drag start → capture snapshot for undo
      const dragStart = changes.some(
        (c) => c.type === "position" && c.dragging === true
      );
      if (dragStart && !isDragging.current) {
        isDragging.current = true;
        undoStack.current.push(capturePositions());
        redoStack.current = [];
      }
      const dragEnd = changes.some(
        (c) => c.type === "position" && c.dragging === false
      );
      if (dragEnd) {
        isDragging.current = false;
      }
      onNodesChange(changes);
    },
    [onNodesChange, capturePositions]
  );

  const applyPositions = useCallback(
    (snap: PositionSnapshot) => {
      setNodes((nds) =>
        nds.map((n) => {
          const pos = snap[n.id];
          return pos ? { ...n, position: pos } : n;
        })
      );
    },
    [setNodes]
  );

  const undo = useCallback(() => {
    if (undoStack.current.length === 0) return;
    redoStack.current.push(capturePositions());
    const prev = undoStack.current.pop()!;
    applyPositions(prev);
  }, [capturePositions, applyPositions]);

  const redo = useCallback(() => {
    if (redoStack.current.length === 0) return;
    undoStack.current.push(capturePositions());
    const next = redoStack.current.pop()!;
    applyPositions(next);
  }, [capturePositions, applyPositions]);

  const toggleCategory = useCallback((category: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  }, []);

  // Sync when treeData changes or collapsed state changes
  useEffect(() => {
    // Inject collapsed state into category group nodes
    const processed = initialNodes.map((n) => {
      if (n.type === "categoryGroupNode") {
        const cat = (n.data as Record<string, unknown>).category as string;
        return { ...n, data: { ...n.data, collapsed: collapsedCategories.has(cat) } };
      }
      return n;
    });

    // Filter out memory nodes under collapsed categories
    const visible = processed.filter((n) => {
      if (n.type !== "memoryNode") return true;
      const parentEdge = initialEdges.find(
        (e) => e.target === n.id && e.source.startsWith("group:")
      );
      if (!parentEdge) return true; // root node
      const cat = parentEdge.source.replace("group:", "");
      return !collapsedCategories.has(cat);
    });

    const visibleIds = new Set(visible.map((n) => n.id));
    const filteredEdges = initialEdges.filter(
      (e) => visibleIds.has(e.source) && visibleIds.has(e.target)
    );

    setNodes(visible);
    setEdges(filteredEdges);

    if (collapsedCategories.size === 0) {
      fittedRef.current = false;
    }
  }, [initialNodes, initialEdges, collapsedCategories, setNodes, setEdges]);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const data = node.data as Record<string, unknown>;
      if (data.isGroup) {
        toggleCategory(data.category as string);
        return;
      }
      const mem = data as unknown as Memory;
      onNodeSelect(mem.short_id);
    },
    [onNodeSelect, toggleCategory]
  );

  const handleSelectionChange = useCallback(
    ({ nodes: selected }: OnSelectionChangeParams) => {
      const memNode = selected.find((n) => n.type === "memoryNode") ?? null;
      setSelectedMemoryNode(memNode);
    },
    []
  );

  // Keyboard shortcuts: DEL (delete), Ctrl+Z (undo), Ctrl+Shift+Z (redo)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      // Undo: Ctrl+Z (or Cmd+Z on Mac)
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === "z") {
        e.preventDefault();
        undo();
        return;
      }
      // Redo: Ctrl+Shift+Z (or Cmd+Shift+Z on Mac)
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "z") {
        e.preventDefault();
        redo();
        return;
      }

      // DEL / Backspace → delete selected memory node
      if (e.key !== "Delete" && e.key !== "Backspace") return;
      if (!selectedMemoryNode || selectedMemoryNode.type !== "memoryNode") return;
      e.preventDefault();
      const mem = selectedMemoryNode.data as unknown as Memory;
      onDeleteRequest(mem);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [selectedMemoryNode, onDeleteRequest, undo, redo]);

  // Fit view on first render
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
      onNodesChange={handleNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      onNodeClick={handleNodeClick}
      onSelectionChange={handleSelectionChange}
      deleteKeyCode={null}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      maxZoom={2}
      nodesDraggable
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
            0: "#10b981",
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
  onDeleteRequest,
}: MemoryGraphViewProps) {
  return (
    <div className="h-full w-full">
      <ReactFlowProvider>
        <MemoryGraphViewInner
          treeData={treeData}
          onNodeSelect={onNodeSelect}
          onDeleteRequest={onDeleteRequest}
        />
      </ReactFlowProvider>
    </div>
  );
}
