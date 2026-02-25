"use client";

import { useCallback, useState } from "react";

export interface ToastItem {
  id: string;
  title: string;
  description?: string;
  variant?: "default" | "success" | "error";
}

let toastId = 0;

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const toast = useCallback(
    (t: Omit<ToastItem, "id">) => {
      const id = String(++toastId);
      setToasts((prev) => [...prev, { ...t, id }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((item) => item.id !== id));
      }, 3000);
    },
    []
  );

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  return { toasts, toast, dismiss };
}
