"use client";

import { ToastContextProvider } from "@/lib/toast-context";
import { CommandPalette } from "@/components/layout/command-palette";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastContextProvider>
      {children}
      <CommandPalette />
    </ToastContextProvider>
  );
}
