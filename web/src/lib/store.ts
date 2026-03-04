import { create } from "zustand";
import { listProjects } from "./api-client";
import type { Project } from "./types";

interface ProjectStore {
  projects: Project[];
  loading: boolean;
  lastFetchedAt: number | null;
  /** Fetch (or refresh) the project list from the API. */
  fetchProjects: (force?: boolean) => Promise<void>;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  loading: false,
  lastFetchedAt: null,
  fetchProjects: async (force = false) => {
    const { lastFetchedAt, loading } = get();
    const now = Date.now();
    if (!force && loading) return;
    if (!force && lastFetchedAt && now - lastFetchedAt < 5000) return;

    set({ loading: true });
    try {
      const projects = await listProjects();
      set({ projects, loading: false, lastFetchedAt: Date.now() });
    } catch {
      set({ loading: false });
    }
  },
}));
