import { create } from "zustand";
import { listProjects } from "./api-client";
import type { Project } from "./types";

interface ProjectStore {
  projects: Project[];
  loading: boolean;
  /** Fetch (or refresh) the project list from the API. */
  fetchProjects: () => Promise<void>;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  loading: false,
  fetchProjects: async () => {
    set({ loading: true });
    try {
      const projects = await listProjects();
      set({ projects, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
