"use client";

import React, { createContext, useContext } from "react";
import { useToast, type ToastItem } from "@/hooks/use-toast";
import {
  ToastProvider as RadixToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
} from "@/components/ui/toast";

interface ToastContextValue {
  toast: (t: Omit<ToastItem, "id">) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
});

export function useAppToast() {
  return useContext(ToastContext);
}

export function ToastContextProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { toasts, toast, dismiss } = useToast();

  return (
    <ToastContext.Provider value={{ toast }}>
      <RadixToastProvider duration={3000}>
        {children}
        {toasts.map((t) => (
          <Toast key={t.id} variant={t.variant} open onOpenChange={() => dismiss(t.id)}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <ToastTitle>{t.title}</ToastTitle>
                {t.description && (
                  <ToastDescription>{t.description}</ToastDescription>
                )}
              </div>
              <ToastClose />
            </div>
          </Toast>
        ))}
        <ToastViewport />
      </RadixToastProvider>
    </ToastContext.Provider>
  );
}
