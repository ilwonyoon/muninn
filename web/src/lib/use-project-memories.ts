"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getProject,
  listMemories,
  listTags,
} from "./api";
import type {
  Memory,
  Project,
  RecallStats,
} from "./types";

export interface ProjectMemoriesState {
  project: Project | null;
  allMemories: Memory[];
  allTags: string[];
  stats: RecallStats | null;
  loading: boolean;
  refetch: () => void;
}

export function useProjectMemories(projectId: string): ProjectMemoriesState {
  const [project, setProject] = useState<Project | null>(null);
  const [allMemories, setAllMemories] = useState<Memory[]>([]);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [stats, setStats] = useState<RecallStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(() => {
    if (!projectId) return;
    setLoading(true);
    Promise.all([
      getProject(projectId),
      listMemories(projectId),
      listTags(projectId),
    ])
      .then(([p, m, tags]) => {
        setProject(p);
        setAllMemories(m.memories);
        setStats(m.stats);
        setAllTags(tags);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    project,
    allMemories,
    allTags,
    stats,
    loading,
    refetch: fetchData,
  };
}
